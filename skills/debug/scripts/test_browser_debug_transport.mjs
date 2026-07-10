#!/usr/bin/env node

import assert from 'node:assert/strict'
import {
  createBrowserDebugTransport,
  createMemoryQueue,
  instrumentGlobalFetch,
} from '../assets/browser-debug-transport.mjs'

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

function acceptedResponse(count, extra = {}) {
  return new Response(JSON.stringify({ ok: true, accepted: count, ...extra }), {
    status: 202,
    headers: { 'Content-Type': 'application/json' },
  })
}

async function testNoEventCountCapAndSingleDrainRequest() {
  let active = 0
  let maxActive = 0
  let accepted = 0
  const keepaliveValues = []
  const bodyByteLengths = []
  const configuredFrameBytes = 16 * 1024

  const fetchImpl = async (_url, init) => {
    active += 1
    maxActive = Math.max(maxActive, active)
    keepaliveValues.push(init.keepalive)
    bodyByteLengths.push(new TextEncoder().encode(init.body).byteLength)
    const payload = JSON.parse(init.body)
    await delay(1)
    accepted += payload.events.length
    active -= 1
    return acceptedResponse(payload.events.length, { batchId: payload.batchId })
  }

  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    endpoint: 'http://127.0.0.1:43125/ingest',
    sessionId: 'transport-count-test',
    nativeFetch: fetchImpl,
    frameBytes: configuredFrameBytes,
    requestTimeoutMs: 2_000,
  })

  const eventCount = 5_000
  await Promise.all(Array.from({ length: eventCount }, (_, index) => transport.record({
    probeId: 'fetch.lifecycle',
    event: 'fetch_start',
    correlationId: `fetch-${index}`,
    sequence: 1,
    data: { index },
  })))

  assert.equal(await transport.flush({ timeoutMs: 20_000 }), true)
  assert.equal(accepted, eventCount)
  assert.equal(maxActive, 1)
  assert.ok(keepaliveValues.every((value) => value === false))
  assert.ok(bodyByteLengths.every((value) => value <= configuredFrameBytes))
  const status = await transport.getStatus()
  assert.equal(status.eventCountLimited, false)
  assert.equal(status.deliveryScope, 'page_lifetime')
  assert.equal(status.reloadSafe, false)
  assert.equal(transport.queue.count(), 0)
  assert.equal(transport.queue.bytes(), 0)
  transport.stop()
}

async function testHungRequestIsAbortedAndRetriedWithoutDroppingEvents() {
  let attempts = 0
  let active = 0
  let maxActive = 0
  const batchIds = []

  const fetchImpl = (_url, init) => {
    attempts += 1
    active += 1
    maxActive = Math.max(maxActive, active)
    const payload = JSON.parse(init.body)
    batchIds.push(payload.batchId)

    if (attempts === 1) {
      return new Promise((resolve, reject) => {
        void resolve
        init.signal.addEventListener('abort', () => {
          active -= 1
          reject(init.signal.reason || new Error('aborted'))
        }, { once: true })
      })
    }

    active -= 1
    return Promise.resolve(acceptedResponse(payload.events.length, { batchId: payload.batchId }))
  }

  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-retry-test',
    nativeFetch: fetchImpl,
    frameBytes: 1024 * 1024,
    requestTimeoutMs: 20,
    retryBaseMs: 1,
    retryMaxMs: 2,
  })

  await Promise.all(Array.from({ length: 250 }, (_, index) => transport.record({
    probeId: 'fetch.lifecycle',
    event: 'fetch_start',
    correlationId: `retry-${index}`,
    sequence: 1,
  })))
  await delay(5)
  await transport.record({
    probeId: 'fetch.lifecycle',
    event: 'fetch_start',
    correlationId: 'retry-late-arrival',
    sequence: 1,
  })

  assert.equal(await transport.flush({ timeoutMs: 5_000 }), true)
  assert.ok(attempts >= 2)
  assert.equal(maxActive, 1)
  assert.equal(batchIds[0], batchIds[1])
  assert.ok(batchIds.length >= 3)
  assert.equal(transport.queue.count(), 0)
  transport.stop()
}

async function testMemoryQueueFramesAndDeletesOnlyAcknowledgedPrefix() {
  const queue = createMemoryQueue()
  const keys = queue.appendMany([
    { event: 'one', data: 'a'.repeat(20) },
    { event: 'two', data: 'b'.repeat(20) },
    { event: 'three', data: 'c'.repeat(20) },
  ])
  const originalBytes = queue.bytes()
  const frame = queue.peekFrame(1)

  assert.equal(frame.items.length, 1)
  assert.equal(queue.count(), 3)
  assert.throws(
    () => queue.deleteKeys([keys[1]]),
    /debug_queue_delete_requires_acknowledged_prefix/,
  )
  queue.deleteKeys([keys[0]])
  assert.equal(queue.count(), 2)
  assert.ok(queue.bytes() < originalBytes)
  queue.deleteKeys(keys.slice(1))
  assert.equal(queue.count(), 0)
  assert.equal(queue.bytes(), 0)
}

async function testRecordSerializesEachEventOnce() {
  let serializationCount = 0
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-serialization-test',
    nativeFetch: async (_url, init) => {
      const payload = JSON.parse(init.body)
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    },
  })

  await transport.record({
    probeId: 'serialize.once',
    event: 'custom',
    data: {
      toJSON() {
        serializationCount += 1
        return { value: 1 }
      },
    },
  })
  assert.equal(await transport.flush({ timeoutMs: 2_000 }), true)
  assert.equal(serializationCount, 1)
  transport.stop()
}

async function testUndefinedSerializationIsRejectedAndSurfaced() {
  const errors = []
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-undefined-serialization-test',
    nativeFetch: async () => {
      throw new Error('unexpected_network_call')
    },
    onError(status) {
      errors.push(status)
    },
  })

  await assert.rejects(
    transport.record({
      probeId: 'serialize.undefined',
      event: 'custom',
      toJSON() {
        return undefined
      },
    }),
    /debug_event_serialization_returned_undefined/,
  )
  const status = await transport.getStatus()
  assert.equal(status.rejectedEvents, 1)
  assert.equal(status.queuedEvents, 0)
  assert.ok(errors.some((item) => item.reason === 'serialization_failed'))
  transport.stop()
}

async function testFlushSurfacesAnUndrainedPageQueue() {
  const errors = []
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-undrained-test',
    nativeFetch: async () => {
      throw new Error('collector_unavailable')
    },
    retryBaseMs: 1,
    retryMaxMs: 2,
    onError(status) {
      errors.push(status)
    },
  })

  await transport.record({ probeId: 'p', event: 'e' })
  assert.equal(await transport.flush({ timeoutMs: 30 }), false)
  const status = await transport.getStatus()
  assert.equal(status.queuedEvents, 1)
  assert.ok(status.failedRequests > 0)
  assert.ok(errors.some((item) => item.type === 'transport_error'))
  transport.stop()
}

async function testStopAbortsTheActiveCollectorRequest() {
  let aborted = false
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-stop-test',
    nativeFetch: async (_url, init) => new Promise((resolve, reject) => {
      void resolve
      init.signal.addEventListener('abort', () => {
        aborted = true
        reject(init.signal.reason || new Error('aborted'))
      }, { once: true })
    }),
    requestTimeoutMs: 5_000,
  })

  await transport.record({ probeId: 'p', event: 'e' })
  await delay(1)
  transport.stop()
  await delay(1)
  assert.equal(aborted, true)
  assert.equal((await transport.getStatus()).inFlightRequests, 0)
}

async function testEveryApplicationFetchIsRecordedWithoutCollectorRecursion() {
  let businessCalls = 0
  let collectorCalls = 0
  let acceptedEvents = 0

  const nativeFetch = async (input, init = {}) => {
    const url = String(input)
    if (url.includes('/ingest/batch')) {
      collectorCalls += 1
      const payload = JSON.parse(init.body)
      acceptedEvents += payload.events.length
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    }
    businessCalls += 1
    return new Response('', { status: 200 })
  }

  const target = {
    fetch: nativeFetch,
    location: { href: 'https://app.example/dashboard' },
    performance: { now: () => Date.now() },
  }
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    endpoint: 'http://127.0.0.1:43125/ingest',
    sessionId: 'instrument-fetch-test',
    nativeFetch,
    frameBytes: 64 * 1024,
    requestTimeoutMs: 2_000,
  })
  const restore = instrumentGlobalFetch({
    transport,
    target,
    hypothesisIds: ['H-fetch-order'],
    location: 'src/api.ts:1',
    mapRequest({ data }) {
      if (data.ordinal !== 1) return data
      const cyclic = { ...data }
      cyclic.self = cyclic
      return cyclic
    },
  })

  const fetchCount = 1_000
  await Promise.all(Array.from({ length: fetchCount }, (_, index) => (
    target.fetch(`https://api.example/items/${index}?token=secret`)
  )))
  assert.equal(await transport.flush({ timeoutMs: 20_000 }), true)

  assert.equal(businessCalls, fetchCount)
  assert.ok(collectorCalls > 0)
  assert.equal(acceptedEvents, fetchCount * 2)
  assert.equal(transport.queue.count(), 0)

  restore()
  assert.equal(target.fetch, nativeFetch)
  transport.stop()
}

async function testTransportUnwrapsAnExistingFetchInstrumentationWrapper() {
  let wrapperEvents = 0
  let collectorEvents = 0
  const target = {
    location: { href: 'https://app.example/' },
    fetch: async (_url, init = {}) => {
      const payload = JSON.parse(init.body)
      collectorEvents += payload.events.length
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    },
  }
  const restoreWrapper = instrumentGlobalFetch({
    target,
    transport: {
      isCollectorUrl: () => false,
      async record() {
        wrapperEvents += 1
      },
    },
  })

  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'unwrap-existing-wrapper-test',
    nativeFetch: target.fetch,
  })
  await transport.record({ probeId: 'p', event: 'e' })
  assert.equal(await transport.flush({ timeoutMs: 2_000 }), true)
  assert.equal(collectorEvents, 1)
  assert.equal(wrapperEvents, 0)

  transport.stop()
  restoreWrapper()
}

await testNoEventCountCapAndSingleDrainRequest()
await testHungRequestIsAbortedAndRetriedWithoutDroppingEvents()
await testMemoryQueueFramesAndDeletesOnlyAcknowledgedPrefix()
await testRecordSerializesEachEventOnce()
await testUndefinedSerializationIsRejectedAndSurfaced()
await testFlushSurfacesAnUndrainedPageQueue()
await testStopAbortsTheActiveCollectorRequest()
await testEveryApplicationFetchIsRecordedWithoutCollectorRecursion()
await testTransportUnwrapsAnExistingFetchInstrumentationWrapper()
console.log('browser debug transport: 9 tests passed')
