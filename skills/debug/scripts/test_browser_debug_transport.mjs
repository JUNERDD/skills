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
  const transportIds = new Set()
  const transportSequences = []
  const configuredFrameBytes = 16 * 1024

  const fetchImpl = async (_url, init) => {
    active += 1
    maxActive = Math.max(maxActive, active)
    keepaliveValues.push(init.keepalive)
    bodyByteLengths.push(new TextEncoder().encode(init.body).byteLength)
    const payload = JSON.parse(init.body)
    for (const event of payload.events) {
      transportIds.add(event.transportId)
      transportSequences.push(event.transportSequence)
    }
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
  assert.equal(transportIds.size, eventCount)
  assert.deepEqual(
    transportSequences,
    Array.from({ length: eventCount }, (_, index) => index + 1),
  )
  assert.equal(maxActive, 1)
  assert.ok(keepaliveValues.every((value) => value === false))
  assert.ok(bodyByteLengths.every((value) => value <= configuredFrameBytes))
  const status = await transport.getStatus()
  assert.equal(status.eventCountLimited, false)
  assert.equal(status.deliveryScope, 'page_lifetime')
  assert.equal(status.reloadSafe, false)
  assert.equal(status.enqueuedEventWatermark, eventCount)
  assert.equal(status.acknowledgedEventWatermark, eventCount)
  assert.equal(transport.queue.count(), 0)
  assert.equal(transport.queue.bytes(), 0)
  transport.stop()
}

async function testCheckpointAcknowledgesSnapshotWhileTheStreamContinues() {
  let requestCount = 0
  let releaseFirstRequest
  let markSecondRequestStarted
  const firstRequestGate = new Promise((resolve) => {
    releaseFirstRequest = resolve
  })
  const secondRequestStarted = new Promise((resolve) => {
    markSecondRequestStarted = resolve
  })

  const fetchImpl = async (_url, init) => {
    requestCount += 1
    const payload = JSON.parse(init.body)
    if (requestCount === 1) {
      await firstRequestGate
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    }
    markSecondRequestStarted()
    return new Promise((resolve, reject) => {
      void resolve
      init.signal.addEventListener('abort', () => {
        reject(init.signal.reason || new Error('aborted'))
      }, { once: true })
    })
  }

  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-checkpoint-test',
    nativeFetch: fetchImpl,
    requestTimeoutMs: 5_000,
  })

  await transport.record({ probeId: 'stream.message', event: 'message', sequence: 1 })
  while (requestCount < 1) await delay(1)

  const checkpointPromise = transport.checkpoint({ timeoutMs: 2_000 })
  await transport.record({ probeId: 'stream.message', event: 'message', sequence: 2 })
  releaseFirstRequest()

  const checkpoint = await checkpointPromise
  assert.equal(checkpoint.complete, true)
  assert.equal(checkpoint.targetEventWatermark, 1)
  assert.ok(checkpoint.acknowledgedEventWatermark >= checkpoint.targetEventWatermark)

  await secondRequestStarted
  const liveStatus = await transport.getStatus()
  assert.equal(liveStatus.enqueuedEventWatermark, 2)
  assert.equal(liveStatus.acknowledgedEventWatermark, 1)
  assert.equal(liveStatus.queuedEvents, 1)
  assert.equal(liveStatus.inFlightRequests, 1)

  transport.stop()
  await delay(1)
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

async function testFrozenAcknowledgementDropsWithoutRetryAndBreaksContinuity() {
  let requests = 0
  const errors = []
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-frozen-test',
    nativeFetch: async (_url, init) => {
      requests += 1
      const payload = JSON.parse(init.body)
      return acceptedResponse(payload.events.length, {
        batchId: payload.batchId,
        persistedEvents: 0,
        discardedEvents: payload.events.length,
        discardedByFreeze: true,
        recordingFrozen: true,
        recordingGeneration: 1,
      })
    },
    onError(status) {
      errors.push(status)
    },
  })

  await Promise.all([
    transport.record({ probeId: 'freeze.one', event: 'frozen_event' }),
    transport.record({ probeId: 'freeze.two', event: 'frozen_event' }),
  ])

  assert.equal(await transport.flush({ timeoutMs: 2_000 }), false)
  assert.equal(requests, 1)
  assert.equal(transport.queue.count(), 0)
  const status = await transport.getStatus()
  assert.equal(status.acceptedEvents, 2)
  assert.equal(status.discardedEvents, 2)
  assert.equal(status.firstDiscardedEventWatermark, 1)
  assert.equal(status.acknowledgedEventWatermark, 2)
  assert.equal(status.recordingFrozen, true)
  assert.equal(status.recordingGeneration, 1)
  assert.equal(status.continuityBroken, true)
  assert.ok(errors.some((item) => item.type === 'batch_discarded'))

  const checkpoint = await transport.checkpoint({ timeoutMs: 100 })
  assert.equal(checkpoint.watermarkAcknowledged, true)
  assert.equal(checkpoint.complete, false)
  assert.equal(checkpoint.continuityBrokenAtCheckpoint, true)
  transport.stop()
}

async function testTransportAdoptsGenerationAfterTerminalStaleDrop() {
  const sentGenerations = []
  let requestCount = 0
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-generation-test',
    recordingGeneration: 0,
    nativeFetch: async (_url, init) => {
      requestCount += 1
      const payload = JSON.parse(init.body)
      sentGenerations.push(payload.events.map((event) => event.recordingGeneration))
      if (requestCount === 1) {
        return acceptedResponse(payload.events.length, {
          batchId: payload.batchId,
          persistedEvents: 0,
          discardedEvents: payload.events.length,
          discardedByFreeze: false,
          discardedByStaleGeneration: true,
          disposition: 'discarded_stale_generation',
          recordingFrozen: false,
          recordingGeneration: 2,
        })
      }
      return acceptedResponse(payload.events.length, {
        batchId: payload.batchId,
        persistedEvents: payload.events.length,
        discardedEvents: 0,
        disposition: 'persisted',
        recordingFrozen: false,
        recordingGeneration: 2,
      })
    },
  })

  await transport.record({ probeId: 'old-generation', event: 'stale' })
  assert.equal(await transport.flush({ timeoutMs: 2_000 }), false)
  await transport.record({ probeId: 'current-generation', event: 'persist' })
  while (transport.queue.count() > 0) await delay(1)

  assert.deepEqual(sentGenerations, [[0], [2]])
  const status = await transport.getStatus()
  assert.equal(status.recordingGeneration, 2)
  assert.equal(status.discardedEvents, 1)
  assert.equal(status.acknowledgedEventWatermark, 2)
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

async function testRecordSafeContainsSerializationAndSizeFailures() {
  const errors = []
  let networkCalls = 0
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-record-safe-test',
    maxEventBytes: 512,
    nativeFetch: async () => {
      networkCalls += 1
      throw new Error('unexpected_network_call')
    },
    onError(status) {
      errors.push(status)
    },
  })
  const cyclic = {}
  cyclic.self = cyclic

  assert.equal(await transport.recordSafe({
    probeId: 'record-safe.serialization',
    event: 'custom',
    data: cyclic,
  }), null)
  assert.equal(await transport.recordSafe({
    probeId: 'record-safe.size',
    event: 'custom',
    data: { payload: 'x'.repeat(2_000) },
  }), null)

  const status = await transport.getStatus()
  assert.equal(status.rejectedEvents, 2)
  assert.equal(status.continuityBroken, true)
  assert.equal(status.queuedEvents, 0)
  assert.equal(networkCalls, 0)
  assert.ok(errors.some((item) => item.reason === 'serialization_failed'))
  assert.ok(errors.some((item) => item.eventBytes > item.maxEventBytes))
  const checkpoint = await transport.checkpoint({ timeoutMs: 100 })
  assert.equal(checkpoint.watermarkAcknowledged, true)
  assert.equal(checkpoint.complete, false)
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

async function testFetchFlowContextIsStableAcrossResolveAndRejectEvents() {
  const events = []
  const resolvedContexts = []
  let legacyRecordCalls = 0
  const target = {
    location: { href: 'https://app.example/' },
    performance: { now: () => Date.now() },
    fetch: async (input) => {
      if (String(input).includes('/reject')) throw new Error('business_rejected')
      return new Response('', { status: 201 })
    },
  }
  const restore = instrumentGlobalFetch({
    target,
    transport: {
      isCollectorUrl: () => false,
      record() {
        legacyRecordCalls += 1
        throw new Error('record_should_not_be_used_when_record_safe_exists')
      },
      async recordSafe(event) {
        events.push(event)
        return `record-${events.length}`
      },
    },
    resolveFlowContext(context) {
      resolvedContexts.push(context)
      return {
        parentCorrelationId: ' shared-parent ',
        operationId: 'shared-operation',
        requestId: `request-${context.ordinal}`,
        correlationId: 'must-not-replace-child',
        ignored: 'not-a-flow-field',
      }
    },
  })

  assert.equal((await target.fetch('https://api.example/resolve?secret=1')).status, 201)
  await assert.rejects(
    target.fetch('https://api.example/reject?secret=2'),
    /business_rejected/,
  )

  assert.equal(legacyRecordCalls, 0)
  assert.deepEqual(resolvedContexts.map((context) => context.ordinal), [1, 2])
  assert.equal(events.length, 4)
  const childCorrelationIds = new Set(events.map((event) => event.correlationId))
  assert.equal(childCorrelationIds.size, 2)
  assert.ok(!childCorrelationIds.has('must-not-replace-child'))

  for (const correlationId of childCorrelationIds) {
    const lifecycle = events.filter((event) => event.correlationId === correlationId)
    assert.deepEqual(lifecycle.map((event) => event.sequence), [1, 2])
    assert.equal(lifecycle[0].parentCorrelationId, 'shared-parent')
    assert.equal(lifecycle[1].parentCorrelationId, lifecycle[0].parentCorrelationId)
    assert.equal(lifecycle[1].operationId, lifecycle[0].operationId)
    assert.equal(lifecycle[1].requestId, lifecycle[0].requestId)
    assert.equal(lifecycle[0].data.operationId, lifecycle[0].operationId)
    assert.equal(lifecycle[1].data.operationId, lifecycle[0].operationId)
    assert.equal(lifecycle[0].data.requestId, lifecycle[0].requestId)
    assert.equal(lifecycle[1].data.requestId, lifecycle[0].requestId)
    assert.equal(Object.hasOwn(lifecycle[0], 'ignored'), false)
  }
  assert.deepEqual(
    events.filter((event) => event.sequence === 2).map((event) => event.event),
    ['fetch_resolve', 'fetch_reject'],
  )

  restore()
}

async function testFetchFlowContextFailuresFallBackSilently() {
  const events = []
  const target = {
    location: { href: 'https://app.example/' },
    fetch: async () => new Response('', { status: 200 }),
  }
  const restore = instrumentGlobalFetch({
    target,
    transport: {
      isCollectorUrl: () => false,
      async recordSafe(event) {
        events.push(event)
      },
    },
    resolveFlowContext({ ordinal }) {
      if (ordinal === 1) throw new Error('context_lookup_failed')
      if (ordinal === 2) return 'not-an-object'
      return {
        parentCorrelationId: '   ',
        operationId: 42,
        requestId: '',
        extraId: 'ignored',
      }
    },
  })

  await target.fetch('https://api.example/one')
  await target.fetch('https://api.example/two')
  await target.fetch('https://api.example/three')

  assert.equal(events.length, 6)
  for (const event of events) {
    assert.equal(Object.hasOwn(event, 'parentCorrelationId'), false)
    assert.equal(Object.hasOwn(event, 'operationId'), false)
    assert.equal(Object.hasOwn(event, 'requestId'), false)
    assert.equal(Object.hasOwn(event.data, 'operationId'), false)
    assert.equal(Object.hasOwn(event.data, 'requestId'), false)
    assert.equal(Object.hasOwn(event, 'extraId'), false)
  }

  restore()
}

async function testFetchRequestMappingCannotThrowIntoTheProductPath() {
  const events = []
  let nativeFetchCalls = 0
  const target = {
    location: { href: 'https://app.example/' },
    fetch: async () => {
      nativeFetchCalls += 1
      return new Response(null, { status: 204 })
    },
  }
  const unsafeMappedData = {
    toJSON() {
      return { safeDuringJsonStringify: true }
    },
    get unsafeDuringSpread() {
      throw new Error('mapped_data_getter_fired')
    },
  }
  const restore = instrumentGlobalFetch({
    target,
    transport: {
      isCollectorUrl: () => false,
      async recordSafe(event) {
        events.push(event)
      },
    },
    mapRequest() {
      return unsafeMappedData
    },
    resolveFlowContext() {
      return {
        parentCorrelationId: 'parent-safe',
        operationId: 'operation-safe',
        requestId: 'request-safe',
      }
    },
  })

  assert.equal((await target.fetch('https://api.example/items')).status, 204)
  assert.equal(nativeFetchCalls, 1)
  assert.equal(events.length, 2)
  for (const event of events) {
    assert.equal(event.data.operationId, 'operation-safe')
    assert.equal(event.data.requestId, 'request-safe')
    assert.equal(Object.hasOwn(event.data, 'unsafeDuringSpread'), false)
  }

  restore()
}

async function testLegacyTransportRecordRejectionsAreContained() {
  let recordCalls = 0
  const target = {
    location: { href: 'https://app.example/' },
    fetch: async () => new Response('', { status: 200 }),
  }
  const restore = instrumentGlobalFetch({
    target,
    transport: {
      isCollectorUrl: () => false,
      record() {
        recordCalls += 1
        return Promise.reject(new Error('legacy_record_rejected'))
      },
    },
  })

  assert.equal((await target.fetch('https://api.example/items')).status, 200)
  await delay(0)
  assert.equal(recordCalls, 2)
  restore()
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
await testCheckpointAcknowledgesSnapshotWhileTheStreamContinues()
await testHungRequestIsAbortedAndRetriedWithoutDroppingEvents()
await testFrozenAcknowledgementDropsWithoutRetryAndBreaksContinuity()
await testTransportAdoptsGenerationAfterTerminalStaleDrop()
await testMemoryQueueFramesAndDeletesOnlyAcknowledgedPrefix()
await testRecordSerializesEachEventOnce()
await testUndefinedSerializationIsRejectedAndSurfaced()
await testRecordSafeContainsSerializationAndSizeFailures()
await testFlushSurfacesAnUndrainedPageQueue()
await testStopAbortsTheActiveCollectorRequest()
await testEveryApplicationFetchIsRecordedWithoutCollectorRecursion()
await testFetchFlowContextIsStableAcrossResolveAndRejectEvents()
await testFetchFlowContextFailuresFallBackSilently()
await testFetchRequestMappingCannotThrowIntoTheProductPath()
await testLegacyTransportRecordRejectionsAreContained()
await testTransportUnwrapsAnExistingFetchInstrumentationWrapper()
console.log('browser debug transport: 17 tests passed')
