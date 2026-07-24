#!/usr/bin/env node

import assert from 'node:assert/strict'
import {
  createBrowserDebugTransport,
  createMemoryQueue,
  getOrCreateBrowserDebugTransport,
  installRealmDebugProducer,
  instrumentGlobalFetch,
} from '../assets/browser-debug-transport.mjs'

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

function acceptedResponse(count, extra = {}) {
  return new Response(JSON.stringify({
    ok: true,
    accepted: count,
    persistedEvents: count,
    discardedEvents: 0,
    duplicateBatch: false,
    disposition: 'persisted',
    ...extra,
  }), {
    status: 202,
    headers: { 'Content-Type': 'application/json' },
  })
}

function withProducerLifecycle(transport) {
  const activeProducerKeys = new Set()
  return Object.assign(transport, {
    reportProducerLifecycleFailure(error, details) {
      transport.reportInstrumentationError(error, details)
    },
    activateProducer(producerKey) {
      assert.equal(activeProducerKeys.has(producerKey), false)
      activeProducerKeys.add(producerKey)
    },
    deactivateProducer(producerKey) {
      assert.equal(activeProducerKeys.delete(producerKey), true)
    },
    beginProducerOperation(producerKey) {
      assert.equal(activeProducerKeys.has(producerKey), true)
      let completed = false
      return () => {
        if (completed) return false
        completed = true
        return true
      }
    },
  })
}

async function testNoEventCountCapAndSingleDrainRequest() {
  let active = 0
  let maxActive = 0
  let accepted = 0
  const keepaliveValues = []
  const bodyByteLengths = []
  const requestUrls = []
  const ndjsonRecords = []
  const transportIds = new Set()
  const transportSequences = []
  const configuredFrameBytes = 16 * 1024

  const fetchImpl = async (url, init) => {
    active += 1
    maxActive = Math.max(maxActive, active)
    requestUrls.push(String(url))
    keepaliveValues.push(init.keepalive)
    bodyByteLengths.push(new TextEncoder().encode(init.body).byteLength)
    const payload = JSON.parse(init.body)
    for (const event of payload.events) {
      transportIds.add(event.transportId)
      transportSequences.push(event.transportSequence)
      ndjsonRecords.push(`${JSON.stringify(event)}\n`)
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
  assert.equal(ndjsonRecords.length, eventCount)
  assert.equal(ndjsonRecords.join('').trimEnd().split('\n').length, eventCount)
  assert.equal(transportIds.size, eventCount)
  assert.deepEqual(
    transportSequences,
    Array.from({ length: eventCount }, (_, index) => index + 1),
  )
  assert.equal(maxActive, 1)
  assert.ok(requestUrls.every((url) => url.endsWith('/ingest/batch')))
  assert.ok(keepaliveValues.every((value) => value === false))
  assert.ok(bodyByteLengths.every((value) => value <= configuredFrameBytes))
  const status = await transport.getStatus()
  assert.equal(status.eventCountLimited, false)
  assert.equal(status.deliveryScope, 'page_lifetime')
  assert.equal(status.reloadSafe, false)
  assert.equal(status.enqueuedEventWatermark, eventCount)
  assert.equal(status.acknowledgedEventWatermark, eventCount)
  assert.equal(status.recordedEvents, eventCount)
  assert.equal(status.enqueuedEvents, eventCount)
  assert.equal(status.persistedEvents, eventCount)
  assert.equal(status.acknowledgedEvents, eventCount)
  assert.equal(status.collectorReportedPersistedEvents, eventCount)
  assert.equal(status.discardedEvents, 0)
  assert.equal(status.requestConcurrencyLimit, 1)
  assert.equal(status.maxInFlightRequests, 1)
  assert.equal(status.cardinalityComplete, true)
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

async function testIncompletePersistenceAcknowledgementRetriesTheSameFrame() {
  let requestCount = 0
  let releaseDuplicateAcknowledgement
  let markDuplicateRequestStarted
  const duplicateRequestStarted = new Promise((resolve) => {
    markDuplicateRequestStarted = resolve
  })
  const duplicateAcknowledgement = new Promise((resolve) => {
    releaseDuplicateAcknowledgement = resolve
  })
  const batchIds = []
  const persistedRecords = new Map()
  const errors = []

  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-ack-validation-test',
    nativeFetch: async (_url, init) => {
      requestCount += 1
      const payload = JSON.parse(init.body)
      batchIds.push(payload.batchId)
      if (requestCount === 1) {
        for (const event of payload.events) {
          persistedRecords.set(event.transportId, `${JSON.stringify(event)}\n`)
        }
        return acceptedResponse(payload.events.length, {
          batchId: payload.batchId,
          persistedEvents: 0,
        })
      }

      markDuplicateRequestStarted()
      await duplicateAcknowledgement
      return acceptedResponse(payload.events.length, {
        batchId: payload.batchId,
        persistedEvents: 0,
        duplicateBatch: true,
      })
    },
    retryBaseMs: 1,
    retryMaxMs: 1,
    onError(status) {
      errors.push(status)
    },
  })

  await Promise.all(Array.from({ length: 3 }, () => transport.record({
    probeId: 'same-occurrence-shape',
    event: 'identical_payload',
    data: { value: 1 },
  })))
  await duplicateRequestStarted

  assert.equal(transport.queue.count(), 3)
  assert.equal((await transport.getStatus()).persistedEvents, 0)
  releaseDuplicateAcknowledgement()

  assert.equal(await transport.flush({ timeoutMs: 2_000 }), true)
  assert.equal(requestCount, 2)
  assert.equal(new Set(batchIds).size, 1)
  assert.equal(persistedRecords.size, 3)
  assert.equal([...persistedRecords.values()].join('').trimEnd().split('\n').length, 3)
  assert.ok(errors.some(
    (status) => status.error?.message
      === 'debug_transport_incomplete_persistence_acknowledgement',
  ))

  const status = await transport.getStatus()
  assert.equal(status.recordedEvents, 3)
  assert.equal(status.enqueuedEvents, 3)
  assert.equal(status.persistedEvents, 3)
  assert.equal(status.collectorReportedPersistedEvents, 0)
  assert.equal(status.duplicateConfirmedEvents, 3)
  assert.equal(status.duplicateAcknowledgedBatches, 1)
  assert.equal(status.failedRequests, 1)
  assert.equal(status.cardinalityComplete, true)
  assert.equal(transport.queue.count(), 0)
  transport.stop()
}

async function testBatchIdConflictTerminatesWithoutRetry() {
  let requests = 0
  const errors = []
  const options = {
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-batch-id-conflict-test',
    runId: 'conflicted-batch-run',
    nativeFetch: async () => {
      requests += 1
      return new Response(JSON.stringify({
        ok: false,
        error: 'transport_batch_id_conflict',
      }), {
        status: 409,
        headers: { 'Content-Type': 'application/json' },
      })
    },
    retryBaseMs: 1,
    retryMaxMs: 1,
    onError(status) {
      errors.push(status)
    },
  }
  const transport = createBrowserDebugTransport(options)
  await transport.record({ probeId: 'batch.conflict', event: 'conflict' })
  while (!(await transport.getStatus()).stopped) await delay(1)
  await delay(10)

  const status = await transport.getStatus()
  assert.equal(requests, 1)
  assert.equal(status.collectorRequestAttempts, 1)
  assert.equal(status.failedRequests, 1)
  assert.equal(status.fatalProtocolFailures, 1)
  assert.equal(status.persistedEvents, 0)
  assert.equal(status.queuedEvents, 1)
  assert.equal(status.abandonedEvents, 1)
  assert.equal(status.continuityBroken, true)
  assert.equal(status.cardinalityComplete, false)
  assert.ok(errors.some((item) => (
    item.type === 'transport_fatal_protocol_failure'
    && item.fatalProtocolFailure === 'transport_batch_id_conflict'
  )))
  assert.equal(await transport.flushAndStop({ timeoutMs: 100 }), false)
  assert.throws(
    () => getOrCreateBrowserDebugTransport(options),
    /debug_transport_run_already_terminated/,
  )

  const freshRun = getOrCreateBrowserDebugTransport({
    ...options,
    runId: 'fresh-run-after-batch-conflict',
    nativeFetch: async (_url, init) => {
      const payload = JSON.parse(init.body)
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    },
  })
  await freshRun.record({ probeId: 'batch.fresh', event: 'persisted' })
  assert.equal(await freshRun.flushAndStop({ timeoutMs: 2_000 }), true)
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
        disposition: 'discarded_frozen',
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
  assert.equal(status.recordedEvents, 2)
  assert.equal(status.enqueuedEvents, 2)
  assert.equal(status.persistedEvents, 0)
  assert.equal(status.collectorReportedPersistedEvents, 0)
  assert.equal(status.discardedEvents, 2)
  assert.equal(status.firstDiscardedEventWatermark, 1)
  assert.equal(status.acknowledgedEventWatermark, 2)
  assert.equal(status.recordingFrozen, true)
  assert.equal(status.recordingGeneration, 1)
  assert.equal(status.continuityBroken, true)
  assert.equal(status.cardinalityComplete, false)
  assert.ok(errors.some((item) => item.type === 'batch_discarded'))
  assert.ok(errors.some((item) => (
    item.confirmedPersistedEventsInBatch === 0
    && item.disposition === 'discarded_frozen'
  )))

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
  assert.equal(await transport.flushAndStop({ timeoutMs: 30 }), false)
  const terminalStatus = await transport.getStatus()
  assert.equal(terminalStatus.stopped, true)
  assert.equal(terminalStatus.abandonedEvents, 1)
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

async function testTerminatedRunBlocksReplacementUntilOldRequestSettles() {
  let activeRequests = 0
  let maxActiveRequests = 0
  let settleOldRequest
  const oldRun = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-settlement-barrier-test',
    runId: 'old-run',
    nativeFetch: async (_url, init) => new Promise((resolve) => {
      activeRequests += 1
      maxActiveRequests = Math.max(maxActiveRequests, activeRequests)
      const payload = JSON.parse(init.body)
      settleOldRequest = () => {
        activeRequests -= 1
        resolve(acceptedResponse(payload.events.length, { batchId: payload.batchId }))
      }
    }),
  })

  await oldRun.record({ probeId: 'old', event: 'pending' })
  while (!settleOldRequest) await delay(1)
  oldRun.stop()

  assert.throws(
    () => getOrCreateBrowserDebugTransport({
      batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
      sessionId: 'transport-settlement-barrier-test',
      runId: 'new-run',
    }),
    /debug_transport_previous_run_still_settling/,
  )

  settleOldRequest()
  while ((await oldRun.getStatus()).inFlightRequests > 0) await delay(1)
  const newRun = getOrCreateBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-settlement-barrier-test',
    runId: 'new-run',
    nativeFetch: async (_url, init) => {
      activeRequests += 1
      maxActiveRequests = Math.max(maxActiveRequests, activeRequests)
      const payload = JSON.parse(init.body)
      activeRequests -= 1
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    },
  })
  await newRun.record({ probeId: 'new', event: 'persisted_after_settlement' })
  assert.equal(await newRun.flushAndStop({ timeoutMs: 100 }), true)
  assert.equal(maxActiveRequests, 1)
}

async function testRealmRegistryReusesOneTransportAcrossRepeatedInstallation() {
  let activeRequests = 0
  let maxActiveRequests = 0
  let persistedEvents = 0
  const options = {
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-registry-reuse-test',
    runId: 'registry-run',
    nativeFetch: async (_url, init) => {
      activeRequests += 1
      maxActiveRequests = Math.max(maxActiveRequests, activeRequests)
      const payload = JSON.parse(init.body)
      await delay(1)
      persistedEvents += payload.events.length
      activeRequests -= 1
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    },
  }

  const first = createBrowserDebugTransport(options)
  await first.record({ probeId: 'registry.one', event: 'one' })
  const hmrModule = await import('../assets/browser-debug-transport.mjs?registry-hmr-test')
  const repeatedInstall = hmrModule.getOrCreateBrowserDebugTransport(options)

  assert.equal(repeatedInstall, first)
  await repeatedInstall.record({ probeId: 'registry.two', event: 'two' })
  assert.equal(await first.flushAndStop({ timeoutMs: 2_000 }), true)
  assert.equal(persistedEvents, 2)
  assert.equal(maxActiveRequests, 1)

  assert.throws(
    () => getOrCreateBrowserDebugTransport(options),
    /debug_transport_run_already_terminated/,
  )
  const afterSafeStop = getOrCreateBrowserDebugTransport({
    ...options,
    runId: 'registry-run-next',
  })
  assert.notEqual(afterSafeStop, first)
  assert.equal(await afterSafeStop.flushAndStop({ timeoutMs: 2_000 }), true)
}

async function testRealmRegistryRejectsParallelRunInstallation() {
  const errors = []
  const active = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-registry-conflict-test',
    runId: 'active-run',
    nativeFetch: async () => {
      throw new Error('unexpected_network_call')
    },
  })

  assert.throws(
    () => getOrCreateBrowserDebugTransport({
      batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
      sessionId: 'transport-registry-conflict-test',
      runId: 'parallel-run',
      nativeFetch: async () => {
        throw new Error('unexpected_network_call')
      },
      onError(status) {
        errors.push(status)
      },
    }),
    /debug_transport_registry_configuration_conflict/,
  )

  const status = await active.getStatus()
  assert.equal(status.registryConflicts, 1)
  assert.equal(status.continuityBroken, true)
  assert.equal(status.cardinalityComplete, false)
  assert.ok(errors.some((item) => item.type === 'transport_registry_conflict'))
  const checkpoint = await active.checkpoint({ timeoutMs: 100 })
  assert.equal(checkpoint.watermarkAcknowledged, true)
  assert.equal(checkpoint.complete, false)
  assert.equal(checkpoint.registryConflictsAtCheckpoint, 1)
  assert.equal(checkpoint.continuityBrokenAtCheckpoint, true)
  assert.equal(await active.flushAndStop({ timeoutMs: 100 }), false)
  assert.throws(
    () => getOrCreateBrowserDebugTransport({
      batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
      sessionId: 'transport-registry-conflict-test',
      runId: 'active-run',
    }),
    /debug_transport_run_already_terminated/,
  )

  const nextRun = getOrCreateBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-registry-conflict-test',
    runId: 'parallel-run',
    nativeFetch: async () => {
      throw new Error('unexpected_network_call')
    },
  })
  assert.equal(await nextRun.flushAndStop({ timeoutMs: 100 }), true)
}

async function testSameTickRecordSafeAndForceStopSurfacesAbandonedEvent() {
  let networkCalls = 0
  const errors = []
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-same-tick-stop-test',
    nativeFetch: async () => {
      networkCalls += 1
      throw new Error('unexpected_network_call')
    },
    onError(status) {
      errors.push(status)
    },
  })

  const recordResult = transport.recordSafe({
    probeId: 'stop.same-tick',
    event: 'queued_before_stop',
  })
  const stopStatus = transport.stop()

  assert.notEqual(await recordResult, null)
  assert.equal(networkCalls, 0)
  assert.equal(stopStatus.abandonedEvents, 1)
  assert.equal(stopStatus.queuedEvents, 1)
  assert.equal(stopStatus.continuityBroken, true)
  assert.equal(stopStatus.cardinalityComplete, false)
  assert.ok(errors.some((item) => (
    item.type === 'transport_force_stopped'
    && item.unresolvedEvents === 1
  )))

  assert.throws(
    () => getOrCreateBrowserDebugTransport({
      batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
      sessionId: 'transport-same-tick-stop-test',
    }),
    /debug_transport_run_already_terminated/,
  )
  await delay(1)
  const nextRun = getOrCreateBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-same-tick-stop-test',
    runId: 'after-forced-stop',
    nativeFetch: async () => {
      throw new Error('unexpected_network_call')
    },
  })
  assert.equal(await nextRun.flushAndStop({ timeoutMs: 100 }), true)
}

async function testRejectedAndDiscardedRunsRemainAuditedWhileNewRunsCanStart() {
  const rejectedOptions = {
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-rejected-run-audit-test',
    runId: 'rejected-run',
    nativeFetch: async () => {
      throw new Error('unexpected_network_call')
    },
  }
  const rejected = createBrowserDebugTransport(rejectedOptions)
  const cyclic = {}
  cyclic.self = cyclic
  assert.equal(await rejected.recordSafe({ data: cyclic }), null)
  assert.equal(await rejected.flushAndStop({ timeoutMs: 100 }), false)
  assert.throws(
    () => getOrCreateBrowserDebugTransport(rejectedOptions),
    /debug_transport_run_already_terminated/,
  )

  const afterRejection = getOrCreateBrowserDebugTransport({
    ...rejectedOptions,
    runId: 'after-rejection',
  })
  assert.equal(await afterRejection.flushAndStop({ timeoutMs: 100 }), true)

  const discardOptions = {
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-discarded-run-audit-test',
    runId: 'discarded-run',
    nativeFetch: async (_url, init) => {
      const payload = JSON.parse(init.body)
      return acceptedResponse(payload.events.length, {
        batchId: payload.batchId,
        persistedEvents: 0,
        discardedEvents: payload.events.length,
        disposition: 'discarded_frozen',
      })
    },
  }
  const discarded = createBrowserDebugTransport(discardOptions)
  await discarded.record({ probeId: 'discarded', event: 'discarded' })
  assert.equal(await discarded.flushAndStop({ timeoutMs: 2_000 }), false)
  assert.throws(
    () => getOrCreateBrowserDebugTransport(discardOptions),
    /debug_transport_run_already_terminated/,
  )

  const afterDiscard = getOrCreateBrowserDebugTransport({
    ...discardOptions,
    runId: 'after-discard',
    nativeFetch: async (_url, init) => {
      const payload = JSON.parse(init.body)
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    },
  })
  await afterDiscard.record({ probeId: 'fresh', event: 'persisted' })
  assert.equal(await afterDiscard.flushAndStop({ timeoutMs: 2_000 }), true)
}

async function testEnrichmentAndQueueAppendFailuresAreRejectedOnce() {
  const enrichmentErrors = []
  const enrichmentTransport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-enrichment-failure-test',
    nativeFetch: async () => {
      throw new Error('unexpected_network_call')
    },
    onError(status) {
      enrichmentErrors.push(status)
    },
  })
  const unsafeEvent = new Proxy({}, {
    ownKeys() {
      throw new Error('event_enrichment_failed')
    },
  })

  assert.equal(await enrichmentTransport.recordSafe(unsafeEvent), null)
  const enrichmentStatus = await enrichmentTransport.getStatus()
  assert.equal(enrichmentStatus.rejectedEvents, 1)
  assert.equal(enrichmentStatus.firstRejectedTransportSequence, 1)
  assert.equal(enrichmentStatus.lastError.message, 'event_enrichment_failed')
  assert.equal(enrichmentErrors.length, 1)
  assert.equal(enrichmentErrors[0].reason, 'enrichment_failed')
  enrichmentTransport.stop()

  const memoryQueue = createMemoryQueue()
  const appendErrors = []
  const throwingQueue = {
    mode: 'throwing-test-queue',
    appendSerialized() {
      throw new Error('queue_append_failed')
    },
    peekFrame: memoryQueue.peekFrame,
    deleteKeys: memoryQueue.deleteKeys,
    count: memoryQueue.count,
    bytes: memoryQueue.bytes,
    lastKey: memoryQueue.lastKey,
  }
  const appendTransport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-append-failure-test',
    eventQueue: throwingQueue,
    nativeFetch: async () => {
      throw new Error('unexpected_network_call')
    },
    onError(status) {
      appendErrors.push(status)
    },
  })

  assert.equal(await appendTransport.recordSafe({
    probeId: 'queue.append',
    event: 'append_failure',
  }), null)
  const appendStatus = await appendTransport.getStatus()
  assert.equal(appendStatus.recordedEvents, 1)
  assert.equal(appendStatus.enqueuedEvents, 0)
  assert.equal(appendStatus.rejectedEvents, 1)
  assert.equal(appendStatus.firstRejectedTransportSequence, 1)
  assert.equal(appendStatus.lastError.message, 'queue_append_failed')
  assert.equal(appendErrors.length, 1)
  assert.equal(appendErrors[0].reason, 'queue_append_failed')
  appendTransport.stop()
}

async function testFrameBytesRejectsSingleEventIncludingEnvelopeOverhead() {
  let networkCalls = 0
  const errors = []
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'transport-wire-byte-limit-test',
    frameBytes: 600,
    maxEventBytes: 10_000,
    nativeFetch: async () => {
      networkCalls += 1
      throw new Error('oversized_request_must_not_be_sent')
    },
    onError(status) {
      errors.push(status)
    },
  })

  assert.equal(await transport.recordSafe({
    toJSON() {
      return {
        sessionId: this.sessionId,
        runId: this.runId,
        transportClientId: this.transportClientId,
        transportId: this.transportId,
        transportSequence: this.transportSequence,
        transportRecordedAt: this.transportRecordedAt,
        recordingGeneration: this.recordingGeneration,
        payload: 'x'.repeat(260),
      }
    },
  }), null)

  const rejection = errors.find((item) => item.reason === 'frame_byte_limit')
  assert.ok(rejection)
  assert.ok(rejection.eventBytes < rejection.frameBytes)
  assert.ok(rejection.wireBytes > rejection.frameBytes)
  assert.equal(networkCalls, 0)
  const status = await transport.getStatus()
  assert.equal(status.queuedEvents, 0)
  assert.equal(status.rejectedEvents, 1)
  assert.equal(status.continuityBroken, true)
  transport.stop()
}

async function testTransportRejectsCrossSessionAndCrossRunEvents() {
  const errors = []
  const persisted = []
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'canonical-record-session',
    runId: 'canonical-record-run',
    nativeFetch: async (_url, init) => {
      const payload = JSON.parse(init.body)
      persisted.push(...payload.events)
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    },
    onError(status) {
      errors.push(status)
    },
  })

  assert.equal(await transport.recordSafe({
    sessionId: 'other-session',
    probeId: 'identity.session',
    event: 'mismatch',
  }), null)
  assert.equal(await transport.recordSafe({
    runId: 'other-run',
    probeId: 'identity.run',
    event: 'mismatch',
  }), null)
  assert.equal(await transport.recordSafe({
    toJSON() {
      return {
        sessionId: 'canonical-record-session',
        runId: 'serialized-other-run',
      }
    },
  }), null)
  assert.notEqual(await transport.recordSafe({
    sessionId: 'canonical-record-session',
    runId: 'canonical-record-run',
    probeId: 'identity.canonical',
    event: 'match',
  }), null)
  while (transport.queue.count() > 0) await delay(1)

  assert.equal(persisted.length, 1)
  assert.equal(persisted[0].sessionId, 'canonical-record-session')
  assert.equal(persisted[0].runId, 'canonical-record-run')
  assert.ok(errors.some((item) => item.reason === 'canonical_session_mismatch'))
  assert.ok(errors.some((item) => item.reason === 'canonical_run_mismatch'))
  assert.ok(errors.some((item) => (
    item.reason === 'serialized_canonical_identity_mismatch'
  )))
  const status = await transport.getStatus()
  assert.equal(status.recordedEvents, 4)
  assert.equal(status.enqueuedEvents, 1)
  assert.equal(status.rejectedEvents, 3)
  assert.equal(status.cardinalityComplete, false)
  assert.equal(await transport.flushAndStop({ timeoutMs: 100 }), false)
}

async function testSerializedTransportOwnedFieldsCannotBeDeletedOrMutated() {
  const errors = []
  let networkCalls = 0
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'serialized-transport-fields-session',
    runId: 'serialized-transport-fields-run',
    recordingGeneration: 7,
    nativeFetch: async () => {
      networkCalls += 1
      throw new Error('invalid_serialized_event_must_not_be_sent')
    },
    onError(status) {
      errors.push(status)
    },
  })

  assert.equal(await transport.recordSafe({
    toJSON() {
      return {
        sessionId: this.sessionId,
        runId: this.runId,
        transportClientId: this.transportClientId,
        transportSequence: this.transportSequence,
        transportRecordedAt: this.transportRecordedAt,
        recordingGeneration: this.recordingGeneration,
      }
    },
  }), null)
  assert.equal(await transport.recordSafe({
    toJSON() {
      return {
        sessionId: this.sessionId,
        runId: this.runId,
        transportClientId: this.transportClientId,
        transportId: this.transportId,
        transportSequence: this.transportSequence,
        transportRecordedAt: this.transportRecordedAt,
        recordingGeneration: this.recordingGeneration + 1,
      }
    },
  }), null)

  assert.equal(networkCalls, 0)
  const identityErrors = errors.filter((item) => (
    item.reason === 'serialized_canonical_identity_mismatch'
  ))
  assert.equal(identityErrors.length, 2)
  assert.deepEqual(identityErrors[0].canonicalFields, [
    'sessionId',
    'runId',
    'transportClientId',
    'transportId',
    'transportSequence',
    'transportRecordedAt',
    'recordingGeneration',
  ])
  const status = await transport.getStatus()
  assert.equal(status.recordedEvents, 2)
  assert.equal(status.enqueuedEvents, 0)
  assert.equal(status.rejectedEvents, 2)
  assert.equal(status.firstRejectedTransportSequence, 1)
  assert.equal(status.cardinalityComplete, false)
  assert.equal(await transport.flushAndStop({ timeoutMs: 100 }), false)
  assert.throws(
    () => createBrowserDebugTransport({
      batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
      sessionId: 'serialized-transport-fields-session',
      runId: 'serialized-transport-fields-run',
      recordingGeneration: 7,
      nativeFetch: async () => {
        throw new Error('terminated_run_must_not_send')
      },
    }),
    /debug_transport_run_already_terminated/,
  )
}

async function testFetchInstrumentationUsesAndEnforcesCanonicalRun() {
  const mismatchTransport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'fetch-run-mismatch-session',
    runId: 'canonical-fetch-run',
    nativeFetch: async () => {
      throw new Error('unexpected_network_call')
    },
  })
  const mismatchTarget = {
    fetch: async () => new Response('', { status: 200 }),
    location: { href: 'https://app.example/' },
  }
  assert.throws(
    () => instrumentGlobalFetch({
      target: mismatchTarget,
      transport: mismatchTransport,
      runId: 'other-fetch-run',
    }),
    /debug_fetch_canonical_run_mismatch/,
  )
  const mismatchStatus = await mismatchTransport.getStatus()
  assert.equal(mismatchStatus.producerLifecycleFailures, 1)
  assert.equal(mismatchStatus.cardinalityComplete, false)
  assert.equal(await mismatchTransport.flushAndStop({ timeoutMs: 100 }), false)

  const persisted = []
  const nativeFetch = async (input, init = {}) => {
    if (String(input).includes('/ingest/batch')) {
      const payload = JSON.parse(init.body)
      persisted.push(...payload.events)
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    }
    return new Response('', { status: 200 })
  }
  const target = {
    fetch: nativeFetch,
    location: { href: 'https://app.example/' },
  }
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'fetch-run-canonical-session',
    runId: 'non-initial-fetch-run',
    nativeFetch,
  })
  const defaultRunRelease = instrumentGlobalFetch({ target, transport })
  assert.equal(defaultRunRelease(), true)
  const canonicalRunRelease = instrumentGlobalFetch({
    target,
    transport,
    runId: 'non-initial-fetch-run',
  })
  assert.equal(defaultRunRelease(), false)
  await target.fetch('https://api.example/canonical')
  assert.equal(canonicalRunRelease(), true)
  assert.equal(await transport.flushAndStop({ timeoutMs: 2_000 }), true)
  assert.equal(persisted.length, 2)
  assert.ok(persisted.every((event) => (
    event.sessionId === 'fetch-run-canonical-session'
    && event.runId === 'non-initial-fetch-run'
  )))
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

async function testSafeStopWaitsForPendingFetchOutcomeBeforeFinalDrain() {
  let resolveBusinessFetch
  let safeStopSettled = false
  const nativeFetch = async (input, init = {}) => {
    if (String(input).includes('/ingest/batch')) {
      const payload = JSON.parse(init.body)
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    }
    return new Promise((resolve) => {
      resolveBusinessFetch = resolve
    })
  }
  const target = {
    fetch: nativeFetch,
    location: { href: 'https://app.example/' },
  }
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'pending-fetch-safe-stop-test',
    runId: 'pending-fetch-run',
    nativeFetch,
  })
  const restore = instrumentGlobalFetch({ target, transport })
  const businessFetch = target.fetch('https://api.example/slow')
  while (!resolveBusinessFetch) await delay(1)
  assert.equal(restore(), true)

  const safeStop = transport.flushAndStop({ timeoutMs: 2_000 }).then((value) => {
    safeStopSettled = true
    return value
  })
  await delay(10)
  assert.equal(safeStopSettled, false)
  const waitingStatus = await transport.getStatus()
  assert.equal(waitingStatus.activeProducerCount, 0)
  assert.equal(waitingStatus.pendingProducerOperations, 1)

  resolveBusinessFetch(new Response('', { status: 200 }))
  await businessFetch
  assert.equal(await safeStop, true)
  const status = await transport.getStatus()
  assert.equal(status.recordedEvents, 2)
  assert.equal(status.enqueuedEvents, 2)
  assert.equal(status.persistedEvents, 2)
  assert.equal(status.producerOperationsStarted, 1)
  assert.equal(status.producerOperationsCompleted, 1)
  assert.equal(status.pendingProducerOperations, 0)
  assert.equal(status.abandonedProducerOperations, 0)
  assert.equal(status.cardinalityComplete, true)
}

async function testSafeStopTimesOutPendingFetchAndCannotBecomeCompleteLater() {
  let resolveBusinessFetch
  const nativeFetch = async (input, init = {}) => {
    if (String(input).includes('/ingest/batch')) {
      const payload = JSON.parse(init.body)
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    }
    return new Promise((resolve) => {
      resolveBusinessFetch = resolve
    })
  }
  const target = {
    fetch: nativeFetch,
    location: { href: 'https://app.example/' },
  }
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'pending-fetch-timeout-test',
    runId: 'timed-out-fetch-run',
    nativeFetch,
  })
  const restore = instrumentGlobalFetch({ target, transport })
  const businessFetch = target.fetch('https://api.example/never-during-stop')
  while (!resolveBusinessFetch) await delay(1)
  assert.equal(restore(), true)

  assert.equal(await transport.flushAndStop({ timeoutMs: 30 }), false)
  const terminalStatus = await transport.getStatus()
  assert.equal(terminalStatus.pendingProducerOperations, 1)
  assert.equal(terminalStatus.abandonedProducerOperations, 1)
  assert.equal(terminalStatus.cardinalityComplete, false)

  resolveBusinessFetch(new Response('', { status: 200 }))
  await businessFetch
  await delay(1)
  const lateStatus = await transport.getStatus()
  assert.equal(lateStatus.pendingProducerOperations, 0)
  assert.equal(lateStatus.producerOperationsCompleted, 1)
  assert.equal(lateStatus.abandonedProducerOperations, 1)
  assert.equal(lateStatus.rejectedEvents, 1)
  assert.equal(lateStatus.cardinalityComplete, false)
  assert.equal(await transport.flushAndStop({ timeoutMs: 100 }), false)
}

async function testCheckpointCannotCompleteAfterForcedStopWithActiveProducer() {
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'forced-stop-checkpoint-session',
    runId: 'forced-stop-checkpoint-run',
    nativeFetch: async () => {
      throw new Error('empty_queue_must_not_send')
    },
  })
  let cleanupCalls = 0
  const release = installRealmDebugProducer({
    target: {},
    producerKey: 'forced-stop-active-producer',
    transport,
    install: () => () => {
      cleanupCalls += 1
    },
  })

  const stoppedStatus = transport.stop()
  assert.equal(stoppedStatus.stopped, true)
  assert.equal(stoppedStatus.terminalComplete, false)
  assert.equal(stoppedStatus.abandonedProducerCount, 1)

  const checkpoint = await transport.checkpoint({ timeoutMs: 0 })
  assert.equal(checkpoint.watermarkAcknowledged, true)
  assert.equal(checkpoint.complete, false)
  assert.equal(checkpoint.stoppedAtCheckpoint, true)
  assert.equal(checkpoint.acceptingEventsAtCheckpoint, false)
  assert.equal(checkpoint.transportLiveAtCheckpoint, false)
  assert.equal(checkpoint.transportLiveAtCompletion, false)
  assert.equal(checkpoint.abandonedProducerOperationsAtCheckpoint, 0)
  assert.equal(checkpoint.abandonedProducerCountAtCheckpoint, 1)
  assert.equal(checkpoint.continuityBrokenAtCheckpoint, true)

  assert.equal(release(), true)
  assert.equal(cleanupCalls, 1)
}

async function testFetchInstrumentationHmrRenewalDoesNotStackAndKeepsSequence() {
  const events = []
  let businessCalls = 0
  const nativeFetch = async () => {
    businessCalls += 1
    return new Response('', { status: 200 })
  }
  const target = {
    fetch: nativeFetch,
    location: { href: 'https://app.example/' },
  }
  const transport = withProducerLifecycle({
    isCollectorUrl: () => false,
    async recordSafe(event) {
      events.push(event)
      return `event-${events.length}`
    },
    reportInstrumentationError(error) {
      throw error
    },
  })

  const firstRestore = instrumentGlobalFetch({
    target,
    transport,
    location: 'src/first.ts:1',
  })
  const wrapper = target.fetch
  await target.fetch('https://api.example/first')
  assert.equal(firstRestore(), true)

  const hmrModule = await import('../assets/browser-debug-transport.mjs?producer-hmr-test')
  const secondRestore = hmrModule.instrumentGlobalFetch({
    target,
    transport,
    location: 'src/second.ts:2',
  })
  assert.equal(target.fetch, wrapper)
  assert.equal(firstRestore(), false)
  assert.equal(target.fetch, wrapper)

  const beforeRenewedFetch = events.length
  await target.fetch('https://api.example/second')
  assert.equal(events.length - beforeRenewedFetch, 2)
  assert.equal(businessCalls, 2)
  assert.deepEqual(events.map((event) => event.data.ordinal), [1, 1, 2, 2])
  assert.deepEqual(events.slice(-2).map((event) => event.location), [
    'src/second.ts:2',
    'src/second.ts:2',
  ])

  assert.equal(secondRestore(), true)
  assert.equal(target.fetch, nativeFetch)
  assert.equal(secondRestore(), false)
  assert.equal(target.fetch, nativeFetch)
}

async function testFetchInstrumentationRejectsDifferentLiveTransport() {
  const firstEvents = []
  const secondErrors = []
  const nativeFetch = async () => new Response('', { status: 200 })
  const target = {
    fetch: nativeFetch,
    location: { href: 'https://app.example/' },
  }
  const firstTransport = withProducerLifecycle({
    isCollectorUrl: () => false,
    async recordSafe(event) {
      firstEvents.push(event)
    },
    reportInstrumentationError(error) {
      throw error
    },
  })
  const secondTransport = withProducerLifecycle({
    isCollectorUrl: () => false,
    async recordSafe() {
      throw new Error('conflicting_transport_must_not_record')
    },
    reportInstrumentationError(error, details) {
      secondErrors.push({ error, details })
    },
  })

  const restore = instrumentGlobalFetch({ target, transport: firstTransport })
  const wrapper = target.fetch
  assert.throws(
    () => instrumentGlobalFetch({ target, transport: secondTransport }),
    /debug_producer_transport_conflict/,
  )
  assert.equal(target.fetch, wrapper)
  await target.fetch('https://api.example/only-first')
  assert.equal(firstEvents.length, 2)
  assert.equal(secondErrors.length, 1)
  assert.equal(secondErrors[0].details.producerKey, 'global-fetch')

  assert.equal(restore(), true)
  assert.equal(target.fetch, nativeFetch)
}

async function testReusableProducerRenewsWithoutDuplicateCallbacks() {
  const realm = {}
  const source = new EventTarget()
  const events = []
  const errors = []
  const transport = withProducerLifecycle({
    async recordSafe() {},
    reportInstrumentationError(error, details) {
      errors.push({ error, details })
    },
  })

  function installScrollProducer(api, label) {
    return api({
      target: realm,
      producerKey: 'history-virtual-list-scroll',
      transport,
      config: { label },
      createState: () => ({ installCount: 0 }),
      install(producer) {
        producer.state.installCount += 1
        const handler = () => {
          events.push({
            installCount: producer.state.installCount,
            label: producer.getConfig().label,
            sourceSequence: producer.nextSourceSequence(),
          })
        }
        source.addEventListener('scroll', handler)
        return () => source.removeEventListener('scroll', handler)
      },
    })
  }

  const firstRelease = installScrollProducer(installRealmDebugProducer, 'first')
  source.dispatchEvent(new Event('scroll'))
  assert.equal(firstRelease(), true)
  const hmrModule = await import('../assets/browser-debug-transport.mjs?custom-producer-hmr-test')
  const latestRelease = installScrollProducer(
    hmrModule.installRealmDebugProducer,
    'second',
  )

  assert.equal(firstRelease(), false)
  source.dispatchEvent(new Event('scroll'))
  assert.deepEqual(events, [
    { installCount: 1, label: 'first', sourceSequence: 1 },
    { installCount: 2, label: 'second', sourceSequence: 2 },
  ])
  assert.equal(errors.length, 0)
  assert.equal(latestRelease(), true)
  source.dispatchEvent(new Event('scroll'))
  assert.equal(events.length, 2)
}

async function testReusableProducerConflictsAndFailuresFailClosed() {
  const realm = {}
  const source = new EventTarget()
  const errors = []
  const transport = withProducerLifecycle({
    async recordSafe() {},
    reportInstrumentationError(error, details) {
      errors.push({ error, details })
    },
  })
  const conflictingTransport = withProducerLifecycle({
    async recordSafe() {},
    reportInstrumentationError(error, details) {
      errors.push({ error, details })
    },
  })
  let callbackCount = 0
  let cleanupFails = true
  const release = installRealmDebugProducer({
    target: realm,
    producerKey: 'history-virtual-list-scroll',
    transport,
    install() {
      const handler = () => {
        callbackCount += 1
      }
      source.addEventListener('scroll', handler)
      return () => {
        if (cleanupFails) throw new Error('custom_cleanup_failed')
        source.removeEventListener('scroll', handler)
      }
    },
  })

  assert.throws(
    () => installRealmDebugProducer({
      target: realm,
      producerKey: 'history-virtual-list-scroll',
      transport: conflictingTransport,
      install: () => () => {},
    }),
    /debug_producer_transport_conflict/,
  )
  assert.throws(
    () => installRealmDebugProducer({
      target: realm,
      producerKey: 'history-virtual-list-scroll',
      transport,
      install: () => () => {},
    }),
    /debug_producer_active_acquisition_conflict/,
  )
  source.dispatchEvent(new Event('scroll'))
  assert.equal(callbackCount, 1)
  assert.ok(errors.some((item) => item.details.phase === 'producer_acquire'))

  assert.throws(() => release(), /custom_cleanup_failed/)
  assert.ok(errors.some((item) => item.details.phase === 'producer_cleanup'))

  cleanupFails = false
  assert.equal(release(), true)
  source.dispatchEvent(new Event('scroll'))
  assert.equal(callbackCount, 1)

  const failedRealm = {}
  assert.throws(
    () => installRealmDebugProducer({
      target: failedRealm,
      producerKey: 'failing-install',
      transport,
      install() {
        throw new Error('custom_install_failed')
      },
    }),
    /custom_install_failed/,
  )
  assert.ok(errors.some((item) => item.details.phase === 'producer_install'))
  assert.throws(
    () => installRealmDebugProducer({
      target: failedRealm,
      producerKey: 'failing-install',
      transport,
      install: () => () => {},
    }),
    /debug_producer_lifecycle_blocked/,
  )
}

async function testSameKeyDifferentSourceCannotReplaceActiveProducer() {
  const realm = {}
  const firstSource = new EventTarget()
  const secondSource = new EventTarget()
  let firstCallbackCalls = 0
  let secondCallbackCalls = 0
  let firstCleanupCalls = 0
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'producer-owner-proof-test',
    runId: 'producer-owner-proof-run',
    nativeFetch: async () => {
      throw new Error('unexpected_network_call')
    },
  })
  const releaseFirst = installRealmDebugProducer({
    target: realm,
    producerKey: 'shared-scroll-key',
    transport,
    install() {
      const handler = () => {
        firstCallbackCalls += 1
      }
      firstSource.addEventListener('scroll', handler)
      return () => {
        firstCleanupCalls += 1
        firstSource.removeEventListener('scroll', handler)
      }
    },
  })

  assert.throws(
    () => installRealmDebugProducer({
      target: realm,
      producerKey: 'shared-scroll-key',
      transport,
      install() {
        const handler = () => {
          secondCallbackCalls += 1
        }
        secondSource.addEventListener('scroll', handler)
        return () => secondSource.removeEventListener('scroll', handler)
      },
    }),
    /debug_producer_active_acquisition_conflict/,
  )
  assert.equal(firstCleanupCalls, 0)
  firstSource.dispatchEvent(new Event('scroll'))
  secondSource.dispatchEvent(new Event('scroll'))
  assert.equal(firstCallbackCalls, 1)
  assert.equal(secondCallbackCalls, 0)
  const conflictStatus = await transport.getStatus()
  assert.equal(conflictStatus.activeProducerCount, 1)
  assert.equal(conflictStatus.producerLifecycleFailures, 1)
  assert.equal(conflictStatus.continuityBroken, true)
  assert.equal(conflictStatus.cardinalityComplete, false)

  assert.equal(releaseFirst(), true)
  assert.equal(firstCleanupCalls, 1)
  assert.equal(await transport.flushAndStop({ timeoutMs: 100 }), false)
}

async function testFailedProducerRenewalPermanentlyBreaksRunCompleteness() {
  const realm = {}
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'producer-renewal-failure-test',
    runId: 'failed-renewal-run',
    nativeFetch: async () => {
      throw new Error('unexpected_network_call')
    },
  })
  const oldRelease = installRealmDebugProducer({
    target: realm,
    producerKey: 'history-virtual-list-scroll',
    transport,
    install: () => () => {},
  })
  assert.equal(oldRelease(), true)

  assert.throws(
    () => installRealmDebugProducer({
      target: realm,
      producerKey: 'history-virtual-list-scroll',
      transport,
      install() {
        throw new Error('renewal_install_failed')
      },
    }),
    /renewal_install_failed/,
  )
  assert.equal(oldRelease(), false)
  const status = await transport.getStatus()
  assert.equal(status.activeProducerCount, 0)
  assert.ok(status.producerLifecycleFailures > 0)
  assert.equal(status.continuityBroken, true)
  assert.equal(status.cardinalityComplete, false)
  assert.equal(await transport.flushAndStop({ timeoutMs: 100 }), false)

  const freshTransport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'producer-renewal-failure-test',
    runId: 'fresh-run-after-failed-renewal',
    nativeFetch: async () => {
      throw new Error('unexpected_network_call')
    },
  })
  const freshRelease = installRealmDebugProducer({
    target: realm,
    producerKey: 'history-virtual-list-scroll',
    transport: freshTransport,
    install: () => () => {},
  })
  assert.equal(freshRelease(), true)
  assert.equal(await freshTransport.flushAndStop({ timeoutMs: 100 }), true)
}

async function testSynchronousSubscriptionCanBeginDuringInstallation() {
  let recordPromise
  const transport = createBrowserDebugTransport({
    batchEndpoint: 'http://127.0.0.1:43125/ingest/batch',
    sessionId: 'producer-sync-install-test',
    runId: 'sync-install-run',
    nativeFetch: async (_url, init) => {
      const payload = JSON.parse(init.body)
      return acceptedResponse(payload.events.length, { batchId: payload.batchId })
    },
  })
  const release = installRealmDebugProducer({
    target: {},
    producerKey: 'synchronous-subscription',
    transport,
    install(producer) {
      const endOperation = producer.beginOperation()
      recordPromise = producer.getTransport().recordSafe({
        probeId: 'subscription.sync',
        event: 'synchronous_initial_value',
        sequence: producer.nextSourceSequence(),
      }).then(endOperation, endOperation)
      return () => {}
    },
  })

  await recordPromise
  assert.equal(release(), true)
  assert.equal(await transport.flushAndStop({ timeoutMs: 2_000 }), true)
  const status = await transport.getStatus()
  assert.equal(status.persistedEvents, 1)
  assert.equal(status.producerOperationsStarted, 1)
  assert.equal(status.producerOperationsCompleted, 1)
  assert.equal(status.producerLifecycleFailures, 0)
}

async function testFetchFlowContextIsStableAcrossResolveAndRejectEvents() {
  const events = []
  const instrumentationErrors = []
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
    transport: withProducerLifecycle({
      isCollectorUrl: () => false,
      record() {
        legacyRecordCalls += 1
        throw new Error('record_should_not_be_used_when_record_safe_exists')
      },
      async recordSafe(event) {
        events.push(event)
        return `record-${events.length}`
      },
      reportInstrumentationError(error, details) {
        instrumentationErrors.push({ error, details })
      },
    }),
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
  assert.equal(instrumentationErrors.length, 0)
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

async function testFetchFlowContextFailuresAreSurfacedAndFallBack() {
  const events = []
  const instrumentationErrors = []
  const target = {
    location: { href: 'https://app.example/' },
    fetch: async () => new Response('', { status: 200 }),
  }
  const restore = instrumentGlobalFetch({
    target,
    transport: withProducerLifecycle({
      isCollectorUrl: () => false,
      async recordSafe(event) {
        events.push(event)
      },
      reportInstrumentationError(error, details) {
        instrumentationErrors.push({ error, details })
      },
    }),
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
  assert.equal(instrumentationErrors.length, 1)
  assert.match(instrumentationErrors[0].error.message, /context_lookup_failed/)
  assert.equal(instrumentationErrors[0].details.phase, 'resolve_flow_context')
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
  const instrumentationErrors = []
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
    transport: withProducerLifecycle({
      isCollectorUrl: () => false,
      async recordSafe(event) {
        events.push(event)
      },
      reportInstrumentationError(error, details) {
        instrumentationErrors.push({ error, details })
      },
    }),
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
  assert.equal(instrumentationErrors.length, 1)
  assert.match(instrumentationErrors[0].error.message, /mapped_data_getter_fired/)
  assert.equal(instrumentationErrors[0].details.phase, 'map_request')
  for (const event of events) {
    assert.equal(event.data.operationId, 'operation-safe')
    assert.equal(event.data.requestId, 'request-safe')
    assert.equal(Object.hasOwn(event.data, 'unsafeDuringSpread'), false)
  }

  restore()
}

async function testFetchInstrumentationRejectsLegacyTransport() {
  let recordCalls = 0
  const target = {
    location: { href: 'https://app.example/' },
    fetch: async () => new Response('', { status: 200 }),
  }
  assert.throws(
    () => instrumentGlobalFetch({
      target,
      transport: {
        isCollectorUrl: () => false,
        record() {
          recordCalls += 1
          return Promise.reject(new Error('legacy_record_rejected'))
        },
      },
    }),
    /shared_browser_debug_transport_is_required/,
  )

  assert.equal((await target.fetch('https://api.example/items')).status, 200)
  assert.equal(recordCalls, 0)
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
    transport: withProducerLifecycle({
      isCollectorUrl: () => false,
      async recordSafe() {
        wrapperEvents += 1
      },
      reportInstrumentationError() {},
    }),
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
await testIncompletePersistenceAcknowledgementRetriesTheSameFrame()
await testBatchIdConflictTerminatesWithoutRetry()
await testFrozenAcknowledgementDropsWithoutRetryAndBreaksContinuity()
await testTransportAdoptsGenerationAfterTerminalStaleDrop()
await testMemoryQueueFramesAndDeletesOnlyAcknowledgedPrefix()
await testRecordSerializesEachEventOnce()
await testUndefinedSerializationIsRejectedAndSurfaced()
await testRecordSafeContainsSerializationAndSizeFailures()
await testFlushSurfacesAnUndrainedPageQueue()
await testStopAbortsTheActiveCollectorRequest()
await testTerminatedRunBlocksReplacementUntilOldRequestSettles()
await testRealmRegistryReusesOneTransportAcrossRepeatedInstallation()
await testRealmRegistryRejectsParallelRunInstallation()
await testSameTickRecordSafeAndForceStopSurfacesAbandonedEvent()
await testRejectedAndDiscardedRunsRemainAuditedWhileNewRunsCanStart()
await testEnrichmentAndQueueAppendFailuresAreRejectedOnce()
await testFrameBytesRejectsSingleEventIncludingEnvelopeOverhead()
await testTransportRejectsCrossSessionAndCrossRunEvents()
await testSerializedTransportOwnedFieldsCannotBeDeletedOrMutated()
await testFetchInstrumentationUsesAndEnforcesCanonicalRun()
await testEveryApplicationFetchIsRecordedWithoutCollectorRecursion()
await testSafeStopWaitsForPendingFetchOutcomeBeforeFinalDrain()
await testSafeStopTimesOutPendingFetchAndCannotBecomeCompleteLater()
await testCheckpointCannotCompleteAfterForcedStopWithActiveProducer()
await testFetchInstrumentationHmrRenewalDoesNotStackAndKeepsSequence()
await testFetchInstrumentationRejectsDifferentLiveTransport()
await testReusableProducerRenewsWithoutDuplicateCallbacks()
await testReusableProducerConflictsAndFailuresFailClosed()
await testSameKeyDifferentSourceCannotReplaceActiveProducer()
await testFailedProducerRenewalPermanentlyBreaksRunCompleteness()
await testSynchronousSubscriptionCanBeginDuringInstallation()
await testFetchFlowContextIsStableAcrossResolveAndRejectEvents()
await testFetchFlowContextFailuresAreSurfacedAndFallBack()
await testFetchRequestMappingCannotThrowIntoTheProductPath()
await testFetchInstrumentationRejectsLegacyTransport()
await testTransportUnwrapsAnExistingFetchInstrumentationWrapper()
console.log('browser debug transport: 39 tests passed')
