#!/usr/bin/env node

import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const dashboardUtilsSource = await readFile(
  new URL('./local_log_collector/static/dashboard-utils.js', import.meta.url),
  'utf8',
)
const dashboardUtilsModule = await import(
  `data:text/javascript;base64,${Buffer.from(dashboardUtilsSource).toString('base64')}`
)
const {
  STATUS_BG,
  STATUS_COLOR,
  STATUS_DOT_COLOR,
  STATUS_LABEL,
  deriveCollectorStatus,
  getFreezeControl,
  getLogEntrySummary,
  getStableLogPageRequest,
  toDescendingLogPage,
} = dashboardUtilsModule

const cases = [
  {
    name: 'prefers the human-readable message',
    entry: { message: 'commit decision rejected', event: 'commit_decision', probeId: 'save.commit' },
    expected: 'commit decision rejected',
  },
  {
    name: 'uses the structured event when message is missing',
    entry: { event: 'flow_terminal', probeId: 'flow.terminal' },
    expected: 'flow_terminal',
  },
  {
    name: 'uses the probe ID when message and event are missing',
    entry: { probeId: 'flow.start' },
    expected: 'flow.start',
  },
  {
    name: 'ignores whitespace-only candidates',
    entry: { message: '  ', event: '\t', probeId: ' search.commit ' },
    expected: 'search.commit',
  },
  {
    name: 'preserves collector-normalized string values',
    entry: { message: '0', event: 'flow_terminal', probeId: 'flow.terminal' },
    expected: '0',
  },
  {
    name: 'keeps the final empty-state fallback',
    entry: {},
    expected: 'No message',
  },
  {
    name: 'handles a missing entry',
    entry: undefined,
    expected: 'No message',
  },
]

for (const testCase of cases) {
  assert.equal(getLogEntrySummary(testCase.entry), testCase.expected, testCase.name)
}

assert.equal(STATUS_LABEL.frozen, 'FROZEN', 'frozen status label')
assert.equal(STATUS_COLOR.frozen, 'text-warn', 'frozen status color')
assert.match(STATUS_BG.frozen, /warn/, 'frozen status background')
assert.equal(STATUS_DOT_COLOR.frozen, 'bg-warn', 'frozen status dot')

const statusCases = [
  { name: 'loads before state arrives', input: {}, expected: 'loading' },
  { name: 'shows live for collector data', input: { hasData: true }, expected: 'running' },
  {
    name: 'shows frozen for the collector recording state',
    input: { serviceStatus: 'frozen', hasData: true },
    expected: 'frozen',
  },
  {
    name: 'uses the explicit recording flag as a fallback',
    input: { recordingFrozen: true, hasData: true },
    expected: 'frozen',
  },
  {
    name: 'does not freeze before collector state arrives',
    input: { recordingFrozen: true, hasData: false },
    expected: 'loading',
  },
  {
    name: 'preserves disconnected precedence',
    input: { error: true, serviceStatus: 'frozen', hasData: true },
    expected: 'error',
  },
  {
    name: 'preserves stopping precedence',
    input: { stopped: true, serviceStatus: 'frozen', hasData: true },
    expected: 'stopping',
  },
  {
    name: 'preserves stopped precedence',
    input: { shutdownComplete: true, serviceStatus: 'frozen', hasData: true },
    expected: 'stopped',
  },
]

for (const testCase of statusCases) {
  assert.equal(deriveCollectorStatus(testCase.input), testCase.expected, testCase.name)
}

assert.deepEqual(
  getFreezeControl('running', false),
  {
    label: 'Freeze',
    pressed: false,
    disabled: false,
    title: 'Freeze writing new debug events; existing logs can still be cleared.',
  },
  'live status exposes the Freeze action',
)
assert.deepEqual(
  getFreezeControl('frozen', true),
  {
    label: 'Resume',
    pressed: true,
    disabled: false,
    title: 'Resume writing new debug events.',
  },
  'frozen status replaces Freeze with Resume in the same control',
)
assert.equal(getFreezeControl('stopping', true).disabled, true, 'stopping disables Resume')
assert.equal(getFreezeControl('error', false).disabled, true, 'disconnected disables Freeze')
assert.equal(getFreezeControl('running', false, true).disabled, true, 'busy action disables Freeze')

const pageCases = [
  {
    name: 'empty snapshot',
    input: [0, 0],
    expected: { offset: 0, limit: 0, order: 'asc' },
  },
  {
    name: 'single short page',
    input: [9, 0],
    expected: { offset: 0, limit: 9, order: 'asc' },
  },
  {
    name: 'newest full page uses an append-stable absolute offset',
    input: [300, 0],
    expected: { offset: 180, limit: 120, order: 'asc' },
  },
  {
    name: 'middle page uses an append-stable absolute offset',
    input: [300, 120],
    expected: { offset: 60, limit: 120, order: 'asc' },
  },
  {
    name: 'oldest partial page stays inside the requested snapshot',
    input: [300, 240],
    expected: { offset: 0, limit: 60, order: 'asc' },
  },
]

for (const testCase of pageCases) {
  assert.deepEqual(getStableLogPageRequest(...testCase.input), testCase.expected, testCase.name)
}

const indexedEntries = Array.from({ length: 300 }, (_, entryIndex) => entryIndex)
for (const pageStart of [0, 120, 240]) {
  const request = getStableLogPageRequest(indexedEntries.length, pageStart)
  const page = toDescendingLogPage(
    indexedEntries.slice(request.offset, request.offset + request.limit),
  )
  const expected = Array.from(
    { length: request.limit },
    (_, index) => indexedEntries.length - pageStart - index - 1,
  )
  assert.deepEqual(page, expected, `stable descending page at ${pageStart}`)
}

const totalAssertions = cases.length + 4 + statusCases.length + 5 + pageCases.length + 3
console.log(`dashboard utilities: ${totalAssertions} assertions passed`)
