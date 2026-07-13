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
const { getLogEntrySummary } = dashboardUtilsModule

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

console.log(`dashboard log summary: ${cases.length} tests passed`)
