/**
 * Page-local browser transport for high-frequency runtime evidence.
 *
 * Guarantees provided by this helper:
 * - no artificial event-count cap or occurrence transformation;
 * - one collector request at a time;
 * - byte-framed batches preserve one frame item per logical event;
 * - timeout, idempotent retry, and strict persistence acknowledgement before
 *   successful deletion;
 * - monotonic enqueue/acknowledgement watermarks for live-stream checkpoints;
 * - recorded, enqueued, persisted, rejected, and discarded cardinality;
 * - one in-memory copy of each serialized event;
 * - collector traffic uses the captured native fetch and cannot log itself.
 * - realm-stable transport/run audit and token-safe producer ownership across
 *   repeated installation and HMR.
 * - final-stop settlement of finite producer operations before queue drain.
 *
 * The queue exists only for the current page lifetime. Navigation, reload,
 * process termination, memory exhaustion, and oversized events remain explicit
 * evidence-loss boundaries. Surface them through onError/onStatus and never
 * describe an incomplete run as complete.
 */

const DEFAULT_FRAME_BYTES = 512 * 1024
const DEFAULT_MAX_EVENT_BYTES = 3 * 1024 * 1024
const DEFAULT_REQUEST_TIMEOUT_MS = 10_000
const DEFAULT_RETRY_BASE_MS = 100
const DEFAULT_RETRY_MAX_MS = 5_000
const JSON_ENVELOPE_BYTES = 32
const textEncoder = new TextEncoder()
const NATIVE_FETCH_SYMBOL = Symbol.for('openai.debug.nativeFetch')
const REALM_PRODUCER_REGISTRY_SYMBOL = Symbol.for('openai.debug.producerRegistry')
const TRANSPORT_REGISTRY_SYMBOL = Symbol.for('openai.debug.browserTransportRegistry')
const FETCH_PRODUCER_KEY = 'global-fetch'

function byteLength(value) {
  return textEncoder.encode(value).byteLength
}

function randomId(prefix = 'debug') {
  if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
    return `${prefix}-${globalThis.crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

function safeError(error) {
  try {
    if (error instanceof Error) {
      return {
        name: error.name,
        message: error.message,
      }
    }
    return {
      name: 'Error',
      message: String(error),
    }
  } catch (serializationError) {
    void serializationError
    return {
      name: 'Error',
      message: 'debug_transport_unprintable_error',
    }
  }
}

function emit(callback, payload) {
  try {
    callback(payload)
  } catch (error) {
    void error
    // Debug status reporting must never alter the application path.
  }
}

function requireAcknowledgementCount(value, field, frameLength) {
  if (
    !Number.isSafeInteger(value)
    || value < 0
    || value > frameLength
  ) {
    throw new Error(`debug_transport_invalid_${field}`)
  }
  return value
}

/**
 * Classify a collector acknowledgement without confusing terminal resolution
 * with NDJSON persistence.
 */
function classifyAcknowledgement(acknowledgement, frame) {
  const frameLength = frame.items.length
  if (!acknowledgement || acknowledgement.ok !== true) {
    throw new Error('debug_transport_invalid_acknowledgement')
  }
  if (acknowledgement.accepted !== frameLength) {
    throw new Error('debug_transport_invalid_accepted_count')
  }
  if (acknowledgement.batchId !== frame.batchId) {
    throw new Error('debug_transport_batch_id_mismatch')
  }

  const persistedEvents = requireAcknowledgementCount(
    acknowledgement.persistedEvents,
    'persisted_event_count',
    frameLength,
  )
  const discardedEvents = requireAcknowledgementCount(
    acknowledgement.discardedEvents,
    'discarded_event_count',
    frameLength,
  )
  if (typeof acknowledgement.duplicateBatch !== 'boolean') {
    throw new Error('debug_transport_invalid_duplicate_batch_flag')
  }

  if (discardedEvents > 0) {
    if (persistedEvents !== 0 || discardedEvents !== frameLength) {
      throw new Error('debug_transport_invalid_discard_acknowledgement')
    }
    if (
      typeof acknowledgement.disposition !== 'string'
      || !acknowledgement.disposition.startsWith('discarded_')
    ) {
      throw new Error('debug_transport_invalid_discard_disposition')
    }
    return {
      outcome: 'discarded',
      persistedEvents,
      discardedEvents,
      duplicateBatch: acknowledgement.duplicateBatch,
    }
  }

  if (acknowledgement.disposition !== 'persisted') {
    throw new Error('debug_transport_invalid_persisted_disposition')
  }
  if (acknowledgement.duplicateBatch) {
    if (persistedEvents !== 0) {
      throw new Error('debug_transport_invalid_duplicate_acknowledgement')
    }
  } else if (persistedEvents !== frameLength) {
    throw new Error('debug_transport_incomplete_persistence_acknowledgement')
  }

  return {
    outcome: 'persisted',
    persistedEvents,
    discardedEvents,
    duplicateBatch: acknowledgement.duplicateBatch,
  }
}

function normalizeFrameItems(records, startIndex, maxBytes) {
  const items = []
  let bytes = JSON_ENVELOPE_BYTES
  for (let index = startIndex; index < records.length; index += 1) {
    const record = records[index]
    if (
      items.length > 0
      && record.recordingGeneration !== items[0].recordingGeneration
    ) break
    const nextBytes = bytes + record.bytes + (items.length > 0 ? 1 : 0)
    if (items.length > 0 && nextBytes > maxBytes) break
    items.push(record)
    bytes = nextBytes
  }
  return { items, bytes }
}

export function createMemoryQueue() {
  let nextKey = 1
  let records = []
  let headIndex = 0
  let queuedBytes = 0

  function compact() {
    if (headIndex === records.length) {
      records = []
      headIndex = 0
      return
    }
    if (headIndex >= 1024 && headIndex * 2 >= records.length) {
      records = records.slice(headIndex)
      headIndex = 0
    }
  }

  function appendSerialized(json, bytes = byteLength(json), metadata = {}) {
    if (typeof json !== 'string') throw new Error('debug_queue_json_required')
    const resolvedBytes = Number(bytes)
    if (!Number.isFinite(resolvedBytes) || resolvedBytes < 0) {
      throw new Error('debug_queue_invalid_byte_length')
    }
    const record = {
      key: nextKey++,
      json,
      bytes: resolvedBytes,
      recordingGeneration: metadata.recordingGeneration,
      transportSequence: metadata.transportSequence,
    }
    records.push(record)
    queuedBytes += resolvedBytes
    return record.key
  }

  return {
    mode: 'memory',

    append(event) {
      const json = JSON.stringify(event)
      return appendSerialized(json, byteLength(json), {
        recordingGeneration: event?.recordingGeneration,
      })
    },

    appendMany(events) {
      return events.map((event) => this.append(event))
    },

    appendSerialized,

    peekFrame(maxBytes) {
      return normalizeFrameItems(records, headIndex, Math.max(maxBytes, 1))
    },

    deleteKeys(keys) {
      if (keys.length === 0) return
      if (keys.length > records.length - headIndex) {
        throw new Error('debug_queue_delete_exceeds_length')
      }
      for (let index = 0; index < keys.length; index += 1) {
        const record = records[headIndex + index]
        if (record.key !== keys[index]) {
          throw new Error('debug_queue_delete_requires_acknowledged_prefix')
        }
      }
      for (let index = 0; index < keys.length; index += 1) {
        const record = records[headIndex + index]
        queuedBytes -= record.bytes
      }
      headIndex += keys.length
      compact()
    },

    count() {
      return records.length - headIndex
    },

    bytes() {
      return queuedBytes
    },

    lastKey() {
      return nextKey - 1
    },

    clear() {
      records = []
      headIndex = 0
      queuedBytes = 0
    },
  }
}

function resolveUrl(input, baseUrl) {
  try {
    if (typeof input === 'string' || input instanceof URL) {
      return new URL(String(input), baseUrl).href
    }
    if (input && typeof input.url === 'string') {
      return new URL(input.url, baseUrl).href
    }
  } catch (error) {
    void error
    return String(input || '')
  }
  return String(input || '')
}

function scrubUrl(rawUrl) {
  try {
    const url = new URL(rawUrl, globalThis.location?.href)
    return `${url.origin}${url.pathname}`
  } catch (error) {
    void error
    return String(rawUrl).split('?')[0].split('#')[0]
  }
}

function requestMethod(input, init) {
  const explicitMethod = init && typeof init.method === 'string' ? init.method : ''
  if (explicitMethod) return explicitMethod.toUpperCase()
  if (input && typeof input.method === 'string') return input.method.toUpperCase()
  return 'GET'
}

function sanitizeFlowContext(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}

  const context = {}
  for (const field of ['parentCorrelationId', 'operationId', 'requestId']) {
    const candidate = value[field]
    if (typeof candidate === 'string' && candidate.trim()) {
      context[field] = candidate.trim()
    }
  }
  return context
}

function createUnregisteredBrowserDebugTransport({
  endpoint,
  batchEndpoint,
  sessionId,
  runId = 'initial',
  recordingGeneration = 0,
  nativeFetch,
  frameBytes = DEFAULT_FRAME_BYTES,
  maxEventBytes = DEFAULT_MAX_EVENT_BYTES,
  requestTimeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
  retryBaseMs = DEFAULT_RETRY_BASE_MS,
  retryMaxMs = DEFAULT_RETRY_MAX_MS,
  onStatus = () => {},
  onError = () => {},
  eventQueue = createMemoryQueue(),
} = {}, {
  terminalizeRegistry = () => {},
  settleRegistry = () => {},
} = {}) {
  if (!batchEndpoint || !sessionId) {
    throw new Error('batchEndpoint_and_sessionId_are_required')
  }
  if (
    !Number.isSafeInteger(recordingGeneration)
    || recordingGeneration < 0
  ) {
    throw new Error('recordingGeneration_must_be_a_non_negative_integer')
  }
  if (!Number.isSafeInteger(frameBytes) || frameBytes < 1) {
    throw new Error('frameBytes_must_be_a_positive_safe_integer')
  }
  if (!Number.isSafeInteger(maxEventBytes) || maxEventBytes < 1) {
    throw new Error('maxEventBytes_must_be_a_positive_safe_integer')
  }
  for (const method of [
    'appendSerialized',
    'peekFrame',
    'deleteKeys',
    'count',
    'bytes',
    'lastKey',
  ]) {
    if (!eventQueue || typeof eventQueue[method] !== 'function') {
      throw new Error(`debug_queue_${method}_required`)
    }
  }

  const configuredFetch = nativeFetch || globalThis.fetch
  const originalFetch = configuredFetch?.[NATIVE_FETCH_SYMBOL] || configuredFetch
  if (typeof originalFetch !== 'function') {
    throw new Error('native_fetch_unavailable')
  }
  const fetchImpl = (...args) => Reflect.apply(originalFetch, globalThis, args)
  const clientId = randomId('client')
  const baseUrl = globalThis.location?.href || batchEndpoint
  const collectorUrls = new Set(
    [endpoint, batchEndpoint]
      .filter(Boolean)
      .map((value) => resolveUrl(value, baseUrl)),
  )

  let transportSequence = 0
  let activeRecordingGeneration = recordingGeneration
  let drainPromise = null
  let inFlightFrame = null
  let requestActive = false
  let activeController = null
  let retryTimer = null
  let wakeRetry = null
  let acceptingEvents = true
  let stopped = false
  let registryTerminalized = false
  let retryAttempt = 0
  let recordedEvents = 0
  let enqueuedEvents = 0
  let acknowledgedEvents = 0
  let acknowledgedBatches = 0
  let persistedEvents = 0
  let persistedBatches = 0
  let collectorReportedPersistedEvents = 0
  let duplicateConfirmedEvents = 0
  let duplicateAcknowledgedBatches = 0
  let instrumentationErrors = 0
  let lastInstrumentationError = null
  let acknowledgedEventWatermark = 0
  let collectorRequestAttempts = 0
  let maxInFlightRequests = 0
  let failedRequests = 0
  let rejectedEvents = 0
  let firstRejectedTransportSequence = null
  let abandonedEvents = 0
  let firstAbandonedEventWatermark = null
  let discardedEvents = 0
  let firstDiscardedEventWatermark = null
  let recordingFrozen = false
  let lastError = null
  let registryConflicts = 0
  let producerOperationsStarted = 0
  let producerOperationsCompleted = 0
  let pendingProducerOperations = 0
  let abandonedProducerOperations = 0
  let abandonedProducerCount = 0
  let producerLifecycleFailures = 0
  let fatalProtocolFailures = 0
  const activeProducerKeys = new Set()
  const observers = { onStatus, onError }

  function isCollectorUrl(input) {
    const resolved = resolveUrl(input, baseUrl)
    if (collectorUrls.has(resolved)) return true
    try {
      const candidate = new URL(resolved)
      const collector = new URL(batchEndpoint)
      return candidate.origin === collector.origin && (
        candidate.pathname === '/ingest'
        || candidate.pathname === '/ingest/batch'
        || candidate.pathname.startsWith('/api/')
      )
    } catch (error) {
      void error
      return false
    }
  }

  function statusPayload(type, extra = {}) {
    return {
      type,
      clientId,
      sessionId,
      runId,
      queueMode: eventQueue.mode,
      deliveryScope: 'page_lifetime',
      reloadSafe: false,
      durableQueue: false,
      queuedEvents: eventQueue.count(),
      queuedBytes: eventQueue.bytes(),
      recordedEvents,
      enqueuedEvents,
      acknowledgedEvents,
      acknowledgedBatches,
      persistedEvents,
      persistedBatches,
      collectorReportedPersistedEvents,
      duplicateConfirmedEvents,
      duplicateAcknowledgedBatches,
      instrumentationErrors,
      lastInstrumentationError,
      // Backward-compatible aliases. Collector "accepted" means terminally
      // resolved and can include discarded events; use persistedEvents for
      // evidence cardinality.
      acceptedEvents: acknowledgedEvents,
      acceptedBatches: acknowledgedBatches,
      enqueuedEventWatermark: eventQueue.lastKey(),
      acknowledgedEventWatermark,
      collectorRequestAttempts,
      requestConcurrencyLimit: 1,
      maxInFlightRequests,
      failedRequests,
      rejectedEvents,
      firstRejectedTransportSequence,
      abandonedEvents,
      firstAbandonedEventWatermark,
      discardedEvents,
      firstDiscardedEventWatermark,
      recordingFrozen,
      recordingGeneration: activeRecordingGeneration,
      acceptingEvents,
      stopped,
      inFlightRequests: requestActive ? 1 : 0,
      retryPending: retryTimer !== null,
      currentBatchId: inFlightFrame?.batchId || null,
      currentFrameFirstKey: inFlightFrame?.keys?.[0] || null,
      currentFrameLastKey: inFlightFrame?.eventWatermark || null,
      currentFrameBytes: inFlightFrame?.wireBytes || 0,
      currentFrameEventCount: inFlightFrame?.items?.length || 0,
      retryAttempt,
      lastError,
      registryConflicts,
      activeProducerCount: activeProducerKeys.size,
      activeProducerKeys: [...activeProducerKeys],
      producerOperationsStarted,
      producerOperationsCompleted,
      pendingProducerOperations,
      abandonedProducerOperations,
      abandonedProducerCount,
      producerLifecycleFailures,
      fatalProtocolFailures,
      producerSettlementPending: pendingProducerOperations > 0,
      continuityBroken: rejectedEvents > 0
        || abandonedEvents > 0
        || discardedEvents > 0
        || registryConflicts > 0
        || abandonedProducerOperations > 0
        || abandonedProducerCount > 0
        || producerLifecycleFailures > 0
        || fatalProtocolFailures > 0,
      cardinalityComplete: recordedEvents === enqueuedEvents
        && enqueuedEvents === persistedEvents
        && rejectedEvents === 0
        && abandonedEvents === 0
        && discardedEvents === 0
        && registryConflicts === 0
        && activeProducerKeys.size === 0
        && pendingProducerOperations === 0
        && abandonedProducerOperations === 0
        && abandonedProducerCount === 0
        && producerLifecycleFailures === 0
        && fatalProtocolFailures === 0,
      eventCountLimited: false,
      ...extra,
    }
  }

  function rejectOccurrence(error, reason, eventTransportSequence, extra = {}) {
    rejectedEvents += 1
    firstRejectedTransportSequence ??= eventTransportSequence
    lastError = safeError(error)
    emit(observers.onError, statusPayload('event_rejected', {
      error: lastError,
      reason,
      transportSequence: eventTransportSequence,
      ...extra,
    }))
  }

  function singleEventWireBytes(serialized, key) {
    const batchId = `${clientId}:${String(key)}:${String(key)}`
    return byteLength(
      `{"batchId":${JSON.stringify(batchId)},"events":[${serialized}]}`,
    )
  }

  function rejectQueuedOversizedEvent(record, wireBytes) {
    const error = new Error(`debug_event_exceeds_frame_byte_limit:${wireBytes}`)
    eventQueue.deleteKeys([record.key])
    rejectOccurrence(
      error,
      'frame_byte_limit',
      record.transportSequence ?? record.key,
      {
        eventBytes: record.bytes,
        wireBytes,
        frameBytes,
      },
    )
  }

  function prepareFrame() {
    const queued = eventQueue.peekFrame(frameBytes)
    if (!queued.items || queued.items.length === 0) return null

    const items = [...queued.items]
    while (items.length > 0) {
      const keys = items.map((item) => item.key)
      const batchId = `${clientId}:${String(keys[0])}:${String(keys[keys.length - 1])}`
      const body = `{"batchId":${JSON.stringify(batchId)},"events":[${items
        .map((item) => item.json)
        .join(',')}]}`
      const wireBytes = byteLength(body)
      if (wireBytes <= frameBytes) {
        return {
          items,
          keys,
          batchId,
          body,
          wireBytes,
          eventWatermark: keys[keys.length - 1],
          recordingGeneration: items[0].recordingGeneration,
        }
      }
      if (items.length === 1) {
        rejectQueuedOversizedEvent(items[0], wireBytes)
        return null
      }
      items.pop()
    }
    return null
  }

  function waitForRetry(milliseconds) {
    return new Promise((resolve) => {
      wakeRetry = () => {
        if (retryTimer !== null) clearTimeout(retryTimer)
        retryTimer = null
        wakeRetry = null
        resolve()
      }
      retryTimer = setTimeout(wakeRetry, milliseconds)
    })
  }

  async function sendFrame(frame) {
    const { keys, batchId, body } = frame

    if (requestActive) {
      throw new Error('debug_transport_concurrent_collector_request')
    }
    const controller = new AbortController()
    activeController = controller
    requestActive = true
    collectorRequestAttempts += 1
    maxInFlightRequests = Math.max(maxInFlightRequests, 1)
    const timeout = setTimeout(() => {
      controller.abort(new Error('debug_transport_request_timeout'))
    }, Math.max(requestTimeoutMs, 1))

    try {
      const response = await fetchImpl(batchEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Debug-Session-Id': sessionId,
        },
        body,
        cache: 'no-store',
        credentials: 'omit',
        keepalive: false,
        signal: controller.signal,
      })
      if (!response || !response.ok) {
        if (response?.status === 409) {
          let conflict
          try {
            conflict = await response.json()
          } catch (error) {
            void error
          }
          if (conflict?.error === 'transport_batch_id_conflict') {
            const error = new Error('transport_batch_id_conflict')
            Object.defineProperty(error, 'fatalTransportProtocol', {
              value: true,
            })
            throw error
          }
        }
        throw new Error(`debug_transport_http_${response ? response.status : 'unknown'}`)
      }
      const acknowledgement = await response.json()
      const classification = classifyAcknowledgement(acknowledgement, frame)
      if (typeof acknowledgement.recordingFrozen === 'boolean') {
        recordingFrozen = acknowledgement.recordingFrozen
      }
      if (
        Number.isSafeInteger(acknowledgement.recordingGeneration)
        && acknowledgement.recordingGeneration >= 0
      ) {
        activeRecordingGeneration = acknowledgement.recordingGeneration
      }
      eventQueue.deleteKeys(keys)
      acknowledgedEventWatermark = Math.max(
        acknowledgedEventWatermark,
        frame.eventWatermark,
      )
      acknowledgedEvents += frame.items.length
      acknowledgedBatches += 1
      collectorReportedPersistedEvents += classification.persistedEvents
      if (classification.duplicateBatch) {
        duplicateAcknowledgedBatches += 1
      }
      if (classification.outcome === 'discarded') {
        discardedEvents += classification.discardedEvents
        if (firstDiscardedEventWatermark === null) {
          firstDiscardedEventWatermark = keys[0]
        }
        lastError = safeError(new Error(
          `debug_transport_frame_${acknowledgement.disposition}`,
        ))
      } else {
        persistedEvents += frame.items.length
        persistedBatches += 1
        if (classification.duplicateBatch) {
          duplicateConfirmedEvents += frame.items.length
        }
        if (
          rejectedEvents === 0
          && abandonedEvents === 0
          && discardedEvents === 0
          && registryConflicts === 0
        ) lastError = null
      }
      retryAttempt = 0
      const acknowledgementStatus = statusPayload(
        classification.outcome === 'discarded'
          ? 'batch_discarded'
          : 'batch_persisted',
        {
          batchId,
          acknowledgedEventsInBatch: frame.items.length,
          acknowledgedEventWatermark,
          discardedEventsInBatch: classification.discardedEvents,
          discardedByFreeze: Boolean(acknowledgement.discardedByFreeze),
          discardedByClear: Boolean(acknowledgement.discardedByClear),
          discardedByStaleGeneration: Boolean(
            acknowledgement.discardedByStaleGeneration,
          ),
          collectorReportedPersistedEventsInBatch: classification.persistedEvents,
          confirmedPersistedEventsInBatch: classification.outcome === 'persisted'
            ? frame.items.length
            : 0,
          duplicateBatch: classification.duplicateBatch,
          disposition: acknowledgement.disposition,
        },
      )
      emit(
        classification.outcome === 'discarded'
          ? observers.onError
          : observers.onStatus,
        acknowledgementStatus,
      )
    } finally {
      clearTimeout(timeout)
      if (activeController === controller) activeController = null
      requestActive = false
    }
  }

  async function drainLoop() {
    while (!stopped && eventQueue.count() > 0) {
      try {
        if (!inFlightFrame) inFlightFrame = prepareFrame()
        if (!inFlightFrame) return
        await sendFrame(inFlightFrame)
        inFlightFrame = null
      } catch (error) {
        failedRequests += 1
        retryAttempt += 1
        lastError = safeError(error)
        emit(observers.onError, statusPayload('transport_error', { error: lastError }))
        if (error?.fatalTransportProtocol === true) {
          fatalProtocolFailures += 1
          const status = terminalize('fatal_protocol_failure', false)
          emit(observers.onError, statusPayload('transport_fatal_protocol_failure', {
            error: lastError,
            stopMode: 'fatal_protocol_failure',
            fatalProtocolFailure: 'transport_batch_id_conflict',
            terminalStatus: status,
          }))
          return
        }
        if (stopped) return
        const delay = Math.min(
          Math.max(retryBaseMs, 1) * (2 ** Math.min(retryAttempt - 1, 10)),
          Math.max(retryMaxMs, 1),
        )
        await waitForRetry(delay)
      }
    }
  }

  function scheduleDrain() {
    if (stopped || drainPromise || eventQueue.count() === 0) return drainPromise
    drainPromise = Promise.resolve()
      .then(drainLoop)
      .catch((error) => {
        failedRequests += 1
        lastError = safeError(error)
        emit(
          observers.onError,
          statusPayload('transport_loop_failed', { error: lastError }),
        )
      })
      .finally(() => {
        drainPromise = null
        if (!stopped && eventQueue.count() > 0) scheduleDrain()
      })
    return drainPromise
  }

  async function record(event) {
    const eventTransportSequence = ++transportSequence
    recordedEvents += 1
    if (!acceptingEvents || stopped) {
      const error = new Error(
        stopped ? 'debug_transport_stopped' : 'debug_transport_stopping',
      )
      rejectOccurrence(
        error,
        stopped ? 'transport_stopped' : 'transport_stopping',
        eventTransportSequence,
      )
      throw error
    }

    let rejectionReason = 'enrichment_failed'
    let rejectionDetails = {}
    let enrichedEvent
    let serialized
    try {
      if (event != null && Object.hasOwn(event, 'sessionId')) {
        const providedSessionId = event.sessionId
        if (providedSessionId !== sessionId) {
          rejectionReason = 'canonical_session_mismatch'
          rejectionDetails = { canonicalField: 'sessionId' }
          throw new Error('debug_event_canonical_session_mismatch')
        }
      }
      if (event != null && Object.hasOwn(event, 'runId')) {
        const providedRunId = event.runId
        if (providedRunId !== runId) {
          rejectionReason = 'canonical_run_mismatch'
          rejectionDetails = { canonicalField: 'runId' }
          throw new Error('debug_event_canonical_run_mismatch')
        }
      }

      enrichedEvent = {
        ...event,
        sessionId,
        runId,
        transportClientId: clientId,
        transportId: randomId('event'),
        transportSequence: eventTransportSequence,
        transportRecordedAt: Date.now(),
        recordingGeneration: activeRecordingGeneration,
        timestamp: event?.timestamp || Date.now(),
      }

      rejectionReason = 'serialization_failed'
      serialized = JSON.stringify(enrichedEvent)
      if (typeof serialized !== 'string') {
        throw new Error('debug_event_serialization_returned_undefined')
      }
      const serializedEvent = JSON.parse(serialized)
      if (
        !serializedEvent
        || typeof serializedEvent !== 'object'
        || Array.isArray(serializedEvent)
        || serializedEvent.sessionId !== sessionId
        || serializedEvent.runId !== runId
        || serializedEvent.transportClientId !== clientId
        || serializedEvent.transportId !== enrichedEvent.transportId
        || serializedEvent.transportSequence !== eventTransportSequence
        || serializedEvent.transportRecordedAt !== enrichedEvent.transportRecordedAt
        || serializedEvent.recordingGeneration !== enrichedEvent.recordingGeneration
      ) {
        rejectionReason = 'serialized_canonical_identity_mismatch'
        rejectionDetails = {
          canonicalFields: [
            'sessionId',
            'runId',
            'transportClientId',
            'transportId',
            'transportSequence',
            'transportRecordedAt',
            'recordingGeneration',
          ],
        }
        throw new Error('debug_event_serialized_canonical_identity_mismatch')
      }

      const serializedBytes = byteLength(serialized)
      if (serializedBytes > maxEventBytes) {
        rejectionReason = 'event_byte_limit'
        rejectionDetails = { eventBytes: serializedBytes, maxEventBytes }
        throw new Error(`debug_event_exceeds_byte_limit:${serializedBytes}`)
      }

      const nextEventKey = eventQueue.lastKey() + 1
      const wireBytes = singleEventWireBytes(serialized, nextEventKey)
      if (wireBytes > frameBytes) {
        rejectionReason = 'frame_byte_limit'
        rejectionDetails = { eventBytes: serializedBytes, wireBytes, frameBytes }
        throw new Error(`debug_event_exceeds_frame_byte_limit:${wireBytes}`)
      }

      rejectionReason = 'queue_append_failed'
      eventQueue.appendSerialized(serialized, serializedBytes, {
        recordingGeneration: enrichedEvent.recordingGeneration,
        transportSequence: eventTransportSequence,
      })
      enqueuedEvents += 1
    } catch (error) {
      rejectOccurrence(
        error,
        rejectionReason,
        eventTransportSequence,
        rejectionDetails,
      )
      throw error
    }

    scheduleDrain()
    return enrichedEvent.transportId
  }

  async function recordSafe(event) {
    try {
      return await record(event)
    } catch (error) {
      void error
      return null
    }
  }

  async function waitForWatermark(targetEventWatermark, timeoutMs) {
    const deadline = Date.now() + Math.max(timeoutMs, 0)
    while (true) {
      if (acknowledgedEventWatermark >= targetEventWatermark) return true
      if (!stopped && eventQueue.count() > 0) scheduleDrain()
      if (stopped) return false
      if (Date.now() >= deadline) return false
      await sleep(25)
    }
  }

  async function checkpoint({ timeoutMs = 30_000 } = {}) {
    const targetEventWatermark = eventQueue.lastKey()
    const recordedEventsAtCheckpoint = recordedEvents
    const enqueuedEventsAtCheckpoint = enqueuedEvents
    const rejectedEventsAtCheckpoint = rejectedEvents
    const abandonedEventsAtCheckpoint = abandonedEvents
    const registryConflictsAtCheckpoint = registryConflicts
    const pendingProducerOperationsAtCheckpoint = pendingProducerOperations
    const abandonedProducerOperationsAtCheckpoint = abandonedProducerOperations
    const abandonedProducerCountAtCheckpoint = abandonedProducerCount
    const activeProducerKeysAtCheckpoint = [...activeProducerKeys]
    const producerLifecycleFailuresAtCheckpoint = producerLifecycleFailures
    const fatalProtocolFailuresAtCheckpoint = fatalProtocolFailures
    const stoppedAtCheckpoint = stopped
    const acceptingEventsAtCheckpoint = acceptingEvents
    const transportLiveAtCheckpoint = !stoppedAtCheckpoint
      && acceptingEventsAtCheckpoint
    const watermarkAcknowledged = await waitForWatermark(
      targetEventWatermark,
      timeoutMs,
    )
    const transportLiveAtCompletion = !stopped && acceptingEvents
    const complete = transportLiveAtCheckpoint
      && transportLiveAtCompletion
      && watermarkAcknowledged
      && rejectedEventsAtCheckpoint === 0
      && abandonedEventsAtCheckpoint === 0
      && registryConflictsAtCheckpoint === 0
      && pendingProducerOperationsAtCheckpoint === 0
      && abandonedProducerOperationsAtCheckpoint === 0
      && abandonedProducerCountAtCheckpoint === 0
      && producerLifecycleFailuresAtCheckpoint === 0
      && fatalProtocolFailuresAtCheckpoint === 0
      && recordedEventsAtCheckpoint === enqueuedEventsAtCheckpoint
      && (
        firstDiscardedEventWatermark === null
        || firstDiscardedEventWatermark > targetEventWatermark
      )
    const status = statusPayload('transport_checkpoint', {
      complete,
      watermarkAcknowledged,
      targetEventWatermark,
      recordedEventsAtCheckpoint,
      enqueuedEventsAtCheckpoint,
      rejectedEventsAtCheckpoint,
      abandonedEventsAtCheckpoint,
      registryConflictsAtCheckpoint,
      pendingProducerOperationsAtCheckpoint,
      abandonedProducerOperationsAtCheckpoint,
      abandonedProducerCountAtCheckpoint,
      activeProducerKeysAtCheckpoint,
      producerLifecycleFailuresAtCheckpoint,
      fatalProtocolFailuresAtCheckpoint,
      stoppedAtCheckpoint,
      acceptingEventsAtCheckpoint,
      transportLiveAtCheckpoint,
      transportLiveAtCompletion,
      discardedEventsAtCheckpoint: discardedEvents,
      continuityBrokenAtCheckpoint: !transportLiveAtCheckpoint
        || !transportLiveAtCompletion
        || rejectedEventsAtCheckpoint > 0
        || abandonedEventsAtCheckpoint > 0
        || registryConflictsAtCheckpoint > 0
        || pendingProducerOperationsAtCheckpoint > 0
        || abandonedProducerOperationsAtCheckpoint > 0
        || abandonedProducerCountAtCheckpoint > 0
        || producerLifecycleFailuresAtCheckpoint > 0
        || fatalProtocolFailuresAtCheckpoint > 0
        || (
          firstDiscardedEventWatermark !== null
          && firstDiscardedEventWatermark <= targetEventWatermark
        ),
    })
    emit(complete ? observers.onStatus : observers.onError, status)
    return status
  }

  async function flush({ timeoutMs = 30_000 } = {}) {
    const deadline = Date.now() + Math.max(timeoutMs, 0)
    while (true) {
      if (!stopped && eventQueue.count() > 0) scheduleDrain()
      if (eventQueue.count() === 0 && !drainPromise) {
        return recordedEvents === enqueuedEvents
          && enqueuedEvents === persistedEvents
          && rejectedEvents === 0
          && abandonedEvents === 0
          && discardedEvents === 0
          && registryConflicts === 0
          && pendingProducerOperations === 0
          && producerLifecycleFailures === 0
          && fatalProtocolFailures === 0
      }
      if (stopped || Date.now() >= deadline) return false
      await sleep(25)
    }
  }

  async function getStatus() {
    return statusPayload('status')
  }

  function reportInstrumentationError(error, details = {}) {
    instrumentationErrors += 1
    lastInstrumentationError = safeError(error)
    emit(observers.onError, statusPayload('instrumentation_error', {
      error: lastInstrumentationError,
      ...details,
    }))
  }

  function reportProducerLifecycleFailure(error, details = {}) {
    producerLifecycleFailures += 1
    reportInstrumentationError(error, details)
  }

  function reportRegistryConflict(error, details = {}) {
    registryConflicts += 1
    lastError = safeError(error)
    emit(observers.onError, statusPayload('transport_registry_conflict', {
      error: lastError,
      ...details,
    }))
  }

  function activateProducer(producerKey) {
    if (stopped || !acceptingEvents) {
      throw new Error('debug_transport_not_accepting_producers')
    }
    if (activeProducerKeys.has(producerKey)) {
      throw new Error('debug_transport_producer_already_active')
    }
    activeProducerKeys.add(producerKey)
    emit(observers.onStatus, statusPayload('producer_activated', { producerKey }))
  }

  function deactivateProducer(producerKey) {
    if (!activeProducerKeys.delete(producerKey)) {
      throw new Error('debug_transport_producer_not_active')
    }
    emit(observers.onStatus, statusPayload('producer_deactivated', { producerKey }))
  }

  function beginProducerOperation(producerKey) {
    if (!activeProducerKeys.has(producerKey)) {
      throw new Error('debug_transport_producer_not_active')
    }
    if (stopped || !acceptingEvents) {
      throw new Error('debug_transport_not_accepting_producer_operations')
    }
    producerOperationsStarted += 1
    pendingProducerOperations += 1
    let completed = false
    return function endProducerOperation() {
      if (completed) return false
      completed = true
      pendingProducerOperations -= 1
      producerOperationsCompleted += 1
      return true
    }
  }

  function markQueuedEventsAbandoned() {
    const unresolvedEvents = eventQueue.count()
    if (unresolvedEvents === 0) return 0

    abandonedEvents += unresolvedEvents
    firstAbandonedEventWatermark ??= inFlightFrame?.keys?.[0]
      ?? (eventQueue.lastKey() - unresolvedEvents + 1)
    return unresolvedEvents
  }

  function terminalize(stopMode, complete) {
    if (stopped && registryTerminalized) {
      return statusPayload('transport_stopped', {
        stopMode,
        terminalComplete: false,
      })
    }
    acceptingEvents = false
    const unresolvedEvents = complete ? 0 : markQueuedEventsAbandoned()
    if (!complete) {
      abandonedProducerOperations += pendingProducerOperations
      abandonedProducerCount += activeProducerKeys.size
    }
    stopped = true
    if (activeController) {
      activeController.abort(new Error('debug_transport_stopped'))
    }
    if (wakeRetry) wakeRetry()

    const status = statusPayload('transport_stopped', {
      stopMode,
      terminalComplete: complete,
      unresolvedEvents,
    })
    if (!registryTerminalized) {
      registryTerminalized = true
      const pendingDrain = drainPromise
      const networkSettled = !requestActive && !pendingDrain
      terminalizeRegistry(status, { networkSettled })
      if (!networkSettled && pendingDrain) {
        void pendingDrain.then(settleRegistry, settleRegistry)
      }
    }
    return status
  }

  async function flushAndStop({ timeoutMs = 30_000 } = {}) {
    if (stopped) return false
    emit(observers.onStatus, statusPayload('transport_stopping'))

    const deadline = Date.now() + Math.max(timeoutMs, 0)
    if (activeProducerKeys.size > 0) {
      const error = new Error('debug_transport_safe_stop_active_producers')
      lastError = safeError(error)
      acceptingEvents = false
      emit(observers.onError, statusPayload('transport_safe_stop_failed', {
        error: lastError,
      }))
      const status = terminalize('incomplete', false)
      emit(observers.onError, status)
      return false
    }

    while (pendingProducerOperations > 0 && Date.now() < deadline) {
      await sleep(25)
    }
    if (pendingProducerOperations > 0) {
      const error = new Error('debug_transport_producer_settlement_timeout')
      lastError = safeError(error)
      acceptingEvents = false
      emit(observers.onError, statusPayload('transport_safe_stop_failed', {
        error: lastError,
      }))
      const status = terminalize('incomplete', false)
      emit(observers.onError, status)
      return false
    }

    acceptingEvents = false
    const drained = await flush({ timeoutMs: Math.max(deadline - Date.now(), 0) })
    const finalStatus = statusPayload('transport_stop_check')
    if (!drained || !finalStatus.cardinalityComplete) {
      const error = new Error('debug_transport_safe_stop_incomplete')
      lastError = safeError(error)
      emit(observers.onError, statusPayload('transport_safe_stop_failed', {
        error: lastError,
      }))
      const status = terminalize('incomplete', false)
      emit(observers.onError, status)
      return false
    }

    const status = terminalize('flushed', true)
    emit(observers.onStatus, status)
    return true
  }

  function stop() {
    if (stopped) return statusPayload('transport_stopped')

    acceptingEvents = false
    const unresolvedEvents = eventQueue.count()
    if (unresolvedEvents > 0) {
      const error = new Error(
        `debug_transport_force_stopped_with_unconfirmed_events:${unresolvedEvents}`,
      )
      lastError = safeError(error)
      const status = terminalize('forced', false)
      emit(observers.onError, statusPayload('transport_force_stopped', {
        error: lastError,
        stopMode: 'forced',
        unresolvedEvents,
      }))
      return status
    }

    const complete = statusPayload('transport_stop_check').cardinalityComplete
    const status = terminalize(complete ? 'empty' : 'incomplete', complete)
    emit(complete ? observers.onStatus : observers.onError, status)
    return status
  }

  emit(observers.onStatus, statusPayload('transport_started', {
    frameBytes,
    maxEventBytes,
  }))

  const queueStatus = Object.freeze({
    count: () => eventQueue.count(),
    bytes: () => eventQueue.bytes(),
    lastKey: () => eventQueue.lastKey(),
  })

  const transport = {
    clientId,
    record,
    recordSafe,
    checkpoint,
    flush,
    flushAndStop,
    getStatus,
    stop,
    isCollectorUrl,
    reportInstrumentationError,
    nativeFetch: fetchImpl,
    queue: queueStatus,
  }

  Object.defineProperties(transport, {
    activateProducer: {
      value: activateProducer,
    },
    deactivateProducer: {
      value: deactivateProducer,
    },
    beginProducerOperation: {
      value: beginProducerOperation,
    },
    reportProducerLifecycleFailure: {
      value: reportProducerLifecycleFailure,
    },
    updateObservers: {
      value(nextOptions = {}) {
        if (typeof nextOptions.onStatus === 'function') {
          observers.onStatus = nextOptions.onStatus
        }
        if (typeof nextOptions.onError === 'function') {
          observers.onError = nextOptions.onError
        }
      },
    },
    reportRegistryReuse: {
      value() {
        emit(observers.onStatus, statusPayload('transport_reused'))
      },
    },
    reportRegistryConflict: {
      value: reportRegistryConflict,
    },
    canonicalIdentity: {
      value: Object.freeze({ sessionId, runId }),
    },
    registryConfiguration: {
      value: Object.freeze({
        batchEndpoint: resolveUrl(batchEndpoint, baseUrl),
        endpoint: endpoint ? resolveUrl(endpoint, baseUrl) : null,
        sessionId,
        runId,
        recordingGeneration,
        frameBytes,
        maxEventBytes,
      }),
    },
  })

  return transport
}

function getTransportRegistry() {
  const existing = globalThis[TRANSPORT_REGISTRY_SYMBOL]
  if (
    existing
    && existing.active instanceof Map
    && existing.terminated instanceof Map
  ) return existing

  // Migrate the previous Map-only registry in place. The symbol is deliberately
  // non-configurable so HMR cannot replace ownership state with a fresh map.
  if (existing instanceof Map) {
    Object.defineProperties(existing, {
      active: {
        value: existing,
        enumerable: false,
      },
      terminated: {
        value: new Map(),
        enumerable: false,
      },
    })
    return existing
  }

  if (existing) throw new Error('debug_transport_registry_shape_conflict')

  const registry = Object.freeze({
    active: new Map(),
    terminated: new Map(),
  })
  Object.defineProperty(globalThis, TRANSPORT_REGISTRY_SYMBOL, {
    value: registry,
    configurable: false,
    enumerable: false,
    writable: false,
  })
  return registry
}

function getTerminatedRuns(registry, identity) {
  let runs = registry.terminated.get(identity)
  if (!runs) {
    runs = new Map()
    registry.terminated.set(identity, runs)
  }
  return runs
}

function transportRegistryIdentity({ batchEndpoint, sessionId } = {}) {
  if (!batchEndpoint || !sessionId) {
    throw new Error('batchEndpoint_and_sessionId_are_required')
  }
  const baseUrl = globalThis.location?.href || batchEndpoint
  return JSON.stringify([resolveUrl(batchEndpoint, baseUrl), sessionId])
}

/**
 * Return the only transport allowed to drain a collector session in this page
 * realm. The global symbol registry survives module re-evaluation during HMR.
 */
export function getOrCreateBrowserDebugTransport(options = {}) {
  const registry = getTransportRegistry()
  const identity = transportRegistryIdentity(options)
  const requestedRunId = options.runId ?? 'initial'
  const existing = registry.active.get(identity)
  if (existing) {
    existing.updateObservers(options)
    const configuration = existing.registryConfiguration
    const baseUrl = globalThis.location?.href || options.batchEndpoint
    const requestedEndpoint = options.endpoint
      ? resolveUrl(options.endpoint, baseUrl)
      : null
    const requestedRecordingGeneration = options.recordingGeneration ?? 0
    const requestedFrameBytes = options.frameBytes ?? DEFAULT_FRAME_BYTES
    const requestedMaxEventBytes = options.maxEventBytes ?? DEFAULT_MAX_EVENT_BYTES
    if (
      configuration.runId !== requestedRunId
      || configuration.endpoint !== requestedEndpoint
      || configuration.recordingGeneration !== requestedRecordingGeneration
      || configuration.frameBytes !== requestedFrameBytes
      || configuration.maxEventBytes !== requestedMaxEventBytes
    ) {
      const error = new Error('debug_transport_registry_configuration_conflict')
      existing.reportRegistryConflict(error, {
        activeRunId: configuration.runId,
        requestedRunId,
        activeEndpoint: configuration.endpoint,
        requestedEndpoint,
        activeRecordingGeneration: configuration.recordingGeneration,
        requestedRecordingGeneration,
        activeFrameBytes: configuration.frameBytes,
        requestedFrameBytes,
        activeMaxEventBytes: configuration.maxEventBytes,
        requestedMaxEventBytes,
      })
      throw error
    }
    existing.reportRegistryReuse()
    return existing
  }

  const terminatedRuns = getTerminatedRuns(registry, identity)
  if (terminatedRuns.has(requestedRunId)) {
    throw new Error('debug_transport_run_already_terminated')
  }
  if ([...terminatedRuns.values()].some((audit) => !audit.networkSettled)) {
    throw new Error('debug_transport_previous_run_still_settling')
  }

  let transport
  transport = createUnregisteredBrowserDebugTransport(options, {
    terminalizeRegistry(status, { networkSettled }) {
      if (registry.active.get(identity) === transport) {
        registry.active.delete(identity)
      }
      terminatedRuns.set(requestedRunId, {
        runId: requestedRunId,
        status,
        terminalizedAt: Date.now(),
        networkSettled,
        networkSettledAt: networkSettled ? Date.now() : null,
      })
    },
    settleRegistry() {
      const audit = terminatedRuns.get(requestedRunId)
      if (!audit || audit.networkSettled) return
      audit.networkSettled = true
      audit.networkSettledAt = Date.now()
    },
  })
  registry.active.set(identity, transport)
  return transport
}

/**
 * Compatibility name. It deliberately uses the same realm registry and cannot
 * be used to construct a parallel transport.
 */
export function createBrowserDebugTransport(options = {}) {
  return getOrCreateBrowserDebugTransport(options)
}

function getRealmProducerRegistry(target) {
  const existing = target[REALM_PRODUCER_REGISTRY_SYMBOL]
  if (existing instanceof Map) return existing
  if (existing) throw new Error('debug_producer_registry_shape_conflict')

  const registry = new Map()
  Object.defineProperty(target, REALM_PRODUCER_REGISTRY_SYMBOL, {
    value: registry,
    configurable: false,
    enumerable: false,
    writable: false,
  })
  return registry
}

function reportProducerError(transport, error, phase, producerKey) {
  transport.reportProducerLifecycleFailure(error, {
    phase,
    producerKey,
  })
}

/**
 * Install a listener, timer, subscription, or wrapper as one realm-owned
 * producer. An active owner must release its lease before reacquisition;
 * reacquiring inactive control preserves state and source sequence.
 *
 * @param {object} options - Realm ownership and installation contract.
 * @param {string} options.producerKey - Stable key for this logical producer.
 * @param {Function} options.install - Synchronous installer returning cleanup.
 * @returns {Function} Token-safe cleanup for this acquisition.
 */
export function installRealmDebugProducer({
  target = globalThis,
  producerKey,
  transport,
  config = {},
  createState = () => ({}),
  install,
} = {}) {
  if (
    !transport
    || typeof transport.recordSafe !== 'function'
    || typeof transport.reportInstrumentationError !== 'function'
    || typeof transport.reportProducerLifecycleFailure !== 'function'
    || typeof transport.activateProducer !== 'function'
    || typeof transport.deactivateProducer !== 'function'
    || typeof transport.beginProducerOperation !== 'function'
  ) throw new Error('shared_browser_debug_transport_is_required')
  if (!target || (typeof target !== 'object' && typeof target !== 'function')) {
    throw new Error('debug_producer_realm_target_required')
  }
  if (typeof producerKey !== 'string' || producerKey.length === 0) {
    throw new Error('debug_producer_key_required')
  }
  if (typeof createState !== 'function') {
    throw new Error('debug_producer_create_state_required')
  }
  if (typeof install !== 'function') {
    throw new Error('debug_producer_install_callback_required')
  }

  const registry = getRealmProducerRegistry(target)
  let control = registry.get(producerKey)

  if (control) {
    if (!control.active && control.transport !== transport) {
      control = null
    } else {
      if (control.blocked) {
        const error = new Error('debug_producer_lifecycle_blocked')
        reportProducerError(transport, error, 'producer_acquire', producerKey)
        throw error
      }
      if (control.active) {
        const error = new Error(
          control.transport === transport
            ? 'debug_producer_active_acquisition_conflict'
            : 'debug_producer_transport_conflict',
        )
        reportProducerError(transport, error, 'producer_acquire', producerKey)
        throw error
      }
    }
  }

  if (!control) {
    let state
    try {
      state = createState()
    } catch (error) {
      reportProducerError(transport, error, 'producer_state_initialize', producerKey)
      throw error
    }
    control = {
      active: false,
      blocked: false,
      cleanup: null,
      config,
      context: null,
      leaseToken: null,
      sourceSequence: 0,
      state,
      transport,
    }
    control.context = Object.freeze({
      producerKey,
      state,
      getConfig: () => control.config,
      getTransport: () => control.transport,
      nextSourceSequence: () => ++control.sourceSequence,
      beginOperation: () => control.transport.beginProducerOperation(producerKey),
    })
    registry.set(producerKey, control)
  }

  control.config = config
  let cleanup
  try {
    control.transport.activateProducer(producerKey)
    cleanup = install(control.context)
    if (typeof cleanup !== 'function') {
      throw new Error('debug_producer_install_cleanup_required')
    }
  } catch (error) {
    if (typeof cleanup === 'function') {
      try {
        cleanup()
      } catch (cleanupError) {
        reportProducerError(
          transport,
          cleanupError,
          'producer_install_rollback',
          producerKey,
        )
      }
    }
    try {
      control.transport.deactivateProducer(producerKey)
    } catch (deactivateError) {
      reportProducerError(
        transport,
        deactivateError,
        'producer_install_rollback',
        producerKey,
      )
    }
    control.active = false
    control.blocked = true
    control.cleanup = null
    control.leaseToken = null
    reportProducerError(transport, error, 'producer_install', producerKey)
    throw error
  }

  const leaseToken = Symbol(producerKey)
  control.active = true
  control.cleanup = cleanup
  control.leaseToken = leaseToken

  return function releaseProducerLease() {
    if (control.leaseToken !== leaseToken) return false
    try {
      control.cleanup()
    } catch (error) {
      reportProducerError(control.transport, error, 'producer_cleanup', producerKey)
      throw error
    }
    control.transport.deactivateProducer(producerKey)
    control.active = false
    control.cleanup = null
    control.leaseToken = null
    return true
  }
}

export function instrumentGlobalFetch({
  transport,
  target = globalThis,
  hypothesisIds = [],
  location = 'runtime:fetch',
  runId,
  mapRequest = null,
  resolveFlowContext = null,
} = {}) {
  if (
    !transport
    || typeof transport.recordSafe !== 'function'
    || typeof transport.isCollectorUrl !== 'function'
    || typeof transport.reportInstrumentationError !== 'function'
    || typeof transport.reportProducerLifecycleFailure !== 'function'
  ) {
    throw new Error('shared_browser_debug_transport_is_required')
  }
  if (!target || typeof target.fetch !== 'function') {
    throw new Error('target_fetch_unavailable')
  }

  const canonicalRunId = transport.canonicalIdentity?.runId
  const activeRunId = runId === undefined ? canonicalRunId ?? 'initial' : runId
  if (canonicalRunId !== undefined && activeRunId !== canonicalRunId) {
    const error = new Error('debug_fetch_canonical_run_mismatch')
    transport.reportProducerLifecycleFailure(error, {
      phase: 'producer_install',
      producerKey: FETCH_PRODUCER_KEY,
      canonicalRunId,
      requestedRunId: activeRunId,
    })
    throw error
  }

  const config = {
    hypothesisIds: [...hypothesisIds],
    location,
    runId: activeRunId,
    mapRequest,
    resolveFlowContext,
  }

  return installRealmDebugProducer({
    target,
    producerKey: FETCH_PRODUCER_KEY,
    transport,
    config,
    createState() {
      const configuredFetch = target.fetch
      const nativeFetch = configuredFetch?.[NATIVE_FETCH_SYMBOL] || configuredFetch
      if (typeof nativeFetch !== 'function') throw new Error('target_fetch_unavailable')
      return {
        detachedFetch: configuredFetch,
        nativeFetch,
        wrapper: null,
      }
    },
    install(producer) {
      const { state } = producer
      if (target.fetch !== state.detachedFetch) {
        throw new Error('debug_producer_target_ownership_conflict')
      }

      function recordWithoutBlocking(activeTransport, event) {
        // recordSafe serializes and enqueues before yielding, reports rejection
        // through transport status, and never waits for collector I/O.
        void activeTransport.recordSafe(event)
      }

      function recordOutcomeAndEnd(activeTransport, event, endOperation) {
        const recorded = activeTransport.recordSafe(event)
        void recorded.then(endOperation, endOperation)
      }

      if (!state.wrapper) state.wrapper = function instrumentedFetch(input, init) {
        // Capture one producer generation so an in-flight request's start and
        // outcome remain paired across an HMR release and reacquisition.
        const activeConfig = producer.getConfig()
        const activeTransport = producer.getTransport()
        const resolvedUrl = resolveUrl(
          input,
          target.location?.href || globalThis.location?.href || '',
        )
        if (activeTransport.isCollectorUrl(resolvedUrl)) {
          return Reflect.apply(state.nativeFetch, target, [input, init])
        }

        const endOperation = producer.beginOperation()
        const ordinal = producer.nextSourceSequence()
        const correlationId = randomId('fetch')
        let flowContext = {}
        if (typeof activeConfig.resolveFlowContext === 'function') {
          try {
            flowContext = sanitizeFlowContext(activeConfig.resolveFlowContext({
              input,
              init,
              url: resolvedUrl,
              ordinal,
            }))
          } catch (error) {
            activeTransport.reportInstrumentationError(error, {
              phase: 'resolve_flow_context',
              probeId: 'fetch.lifecycle',
            })
            flowContext = {}
          }
        }
        const flowData = {}
        if (flowContext.operationId) flowData.operationId = flowContext.operationId
        if (flowContext.requestId) flowData.requestId = flowContext.requestId
        const startedAt = Date.now()
        const startedMonotonic = target.performance?.now?.()
        const baseData = {
          ordinal,
          method: requestMethod(input, init),
          url: scrubUrl(resolvedUrl),
          ...flowData,
        }
        let mappedData = baseData
        try {
          if (typeof activeConfig.mapRequest === 'function') {
            mappedData = activeConfig.mapRequest({
              input,
              init,
              url: resolvedUrl,
              data: baseData,
            }) || baseData
          }
          if (Object.keys(flowData).length > 0) {
            mappedData = mappedData && typeof mappedData === 'object' && !Array.isArray(mappedData)
              ? { ...mappedData, ...flowData }
              : baseData
          }
          JSON.stringify(mappedData)
        } catch (error) {
          activeTransport.reportInstrumentationError(error, {
            phase: 'map_request',
            probeId: 'fetch.lifecycle',
          })
          mappedData = baseData
        }

        recordWithoutBlocking(activeTransport, {
          runId: activeConfig.runId,
          correlationId,
          ...flowContext,
          sequence: 1,
          probeId: 'fetch.lifecycle',
          hypothesisIds: activeConfig.hypothesisIds,
          location: activeConfig.location,
          phase: 'network',
          event: 'fetch_start',
          message: 'application fetch started',
          data: mappedData,
          timestamp: startedAt,
          monotonicMs: startedMonotonic,
        })

        let result
        try {
          result = Reflect.apply(state.nativeFetch, target, [input, init])
        } catch (error) {
          recordOutcomeAndEnd(activeTransport, {
            runId: activeConfig.runId,
            correlationId,
            ...flowContext,
            sequence: 2,
            probeId: 'fetch.lifecycle',
            hypothesisIds: activeConfig.hypothesisIds,
            location: activeConfig.location,
            phase: 'network',
            event: 'fetch_reject',
            level: 'error',
            message: 'application fetch threw synchronously',
            data: {
              ...baseData,
              durationMs: Date.now() - startedAt,
              error: safeError(error),
            },
          }, endOperation)
          throw error
        }

        return Promise.resolve(result).then(
          (response) => {
            recordOutcomeAndEnd(activeTransport, {
              runId: activeConfig.runId,
              correlationId,
              ...flowContext,
              sequence: 2,
              probeId: 'fetch.lifecycle',
              hypothesisIds: activeConfig.hypothesisIds,
              location: activeConfig.location,
              phase: 'network',
              event: 'fetch_resolve',
              message: 'application fetch response headers available; body may still be active',
              data: {
                ...baseData,
                status: response.status,
                ok: response.ok,
                redirected: response.redirected,
                responseType: response.type,
                responseBodyPresent: response.body !== null && response.body !== undefined,
                responseBodyUsed: Boolean(response.bodyUsed),
                durationMs: Date.now() - startedAt,
              },
            }, endOperation)
            return response
          },
          (error) => {
            recordOutcomeAndEnd(activeTransport, {
              runId: activeConfig.runId,
              correlationId,
              ...flowContext,
              sequence: 2,
              probeId: 'fetch.lifecycle',
              hypothesisIds: activeConfig.hypothesisIds,
              location: activeConfig.location,
              phase: 'network',
              event: 'fetch_reject',
              level: 'error',
              message: 'application fetch rejected',
              data: {
                ...baseData,
                durationMs: Date.now() - startedAt,
                error: safeError(error),
              },
            }, endOperation)
            throw error
          },
        )
      }
      if (!state.wrapper[NATIVE_FETCH_SYMBOL]) {
        Object.defineProperty(state.wrapper, NATIVE_FETCH_SYMBOL, {
          value: state.nativeFetch,
          enumerable: false,
          configurable: false,
          writable: false,
        })
      }
      target.fetch = state.wrapper
      return function restoreFetchProducer() {
        if (target.fetch !== state.wrapper) {
          throw new Error('debug_producer_target_ownership_conflict')
        }
        target.fetch = state.nativeFetch
        state.detachedFetch = state.nativeFetch
      }
    },
  })
}
