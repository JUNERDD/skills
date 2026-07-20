/**
 * Page-local browser transport for high-frequency runtime evidence.
 *
 * Guarantees provided by this helper:
 * - no artificial event-count cap;
 * - one collector request at a time;
 * - byte-framed batches, timeout, idempotent retry, and acknowledgement
 *   before deletion;
 * - monotonic enqueue/acknowledgement watermarks for live-stream checkpoints;
 * - one in-memory copy of each serialized event;
 * - collector traffic uses the captured native fetch and cannot log itself.
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
}

function emit(callback, payload) {
  try {
    callback(payload)
  } catch {
    // Debug status reporting must never alter the application path.
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
  } catch {
    return String(input || '')
  }
  return String(input || '')
}

function scrubUrl(rawUrl) {
  try {
    const url = new URL(rawUrl, globalThis.location?.href)
    return `${url.origin}${url.pathname}`
  } catch {
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

export function createBrowserDebugTransport({
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

  const configuredFetch = nativeFetch || globalThis.fetch
  const originalFetch = configuredFetch?.[NATIVE_FETCH_SYMBOL] || configuredFetch
  if (typeof originalFetch !== 'function') {
    throw new Error('native_fetch_unavailable')
  }
  const fetchImpl = (...args) => Reflect.apply(originalFetch, globalThis, args)
  const clientId = randomId('client')
  const eventQueue = createMemoryQueue()
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
  let stopped = false
  let retryAttempt = 0
  let acceptedEvents = 0
  let acceptedBatches = 0
  let acknowledgedEventWatermark = 0
  let failedRequests = 0
  let rejectedEvents = 0
  let discardedEvents = 0
  let firstDiscardedEventWatermark = null
  let recordingFrozen = false
  let lastError = null

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
    } catch {
      return false
    }
  }

  function statusPayload(type, extra = {}) {
    return {
      type,
      clientId,
      queueMode: eventQueue.mode,
      deliveryScope: 'page_lifetime',
      reloadSafe: false,
      durableQueue: false,
      queuedEvents: eventQueue.count(),
      queuedBytes: eventQueue.bytes(),
      acceptedEvents,
      acceptedBatches,
      enqueuedEventWatermark: eventQueue.lastKey(),
      acknowledgedEventWatermark,
      failedRequests,
      rejectedEvents,
      discardedEvents,
      firstDiscardedEventWatermark,
      recordingFrozen,
      recordingGeneration: activeRecordingGeneration,
      inFlightRequests: requestActive ? 1 : 0,
      retryPending: retryTimer !== null,
      currentBatchId: inFlightFrame?.batchId || null,
      currentFrameFirstKey: inFlightFrame?.keys?.[0] || null,
      currentFrameLastKey: inFlightFrame?.eventWatermark || null,
      currentFrameBytes: inFlightFrame?.wireBytes || 0,
      retryAttempt,
      lastError,
      continuityBroken: rejectedEvents > 0 || discardedEvents > 0,
      eventCountLimited: false,
      ...extra,
    }
  }

  function prepareFrame() {
    const queued = eventQueue.peekFrame(Math.max(frameBytes, 1))
    if (!queued.items || queued.items.length === 0) return null

    const items = [...queued.items]
    while (items.length > 0) {
      const keys = items.map((item) => item.key)
      const batchId = `${clientId}:${String(keys[0])}:${String(keys[keys.length - 1])}`
      const body = `{"batchId":${JSON.stringify(batchId)},"events":[${items
        .map((item) => item.json)
        .join(',')}]}`
      const wireBytes = byteLength(body)
      if (wireBytes <= Math.max(frameBytes, 1) || items.length === 1) {
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

    const controller = new AbortController()
    activeController = controller
    requestActive = true
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
        throw new Error(`debug_transport_http_${response ? response.status : 'unknown'}`)
      }
      const acknowledgement = await response.json()
      if (!acknowledgement || acknowledgement.accepted !== frame.items.length) {
        throw new Error('debug_transport_invalid_acknowledgement')
      }
      if (acknowledgement.batchId !== batchId) {
        throw new Error('debug_transport_batch_id_mismatch')
      }
      const discardedInFrame = acknowledgement.discardedEvents ?? 0
      if (
        !Number.isSafeInteger(discardedInFrame)
        || discardedInFrame < 0
        || discardedInFrame > frame.items.length
      ) {
        throw new Error('debug_transport_invalid_discard_count')
      }
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
      acceptedEvents += frame.items.length
      acceptedBatches += 1
      if (discardedInFrame > 0) {
        discardedEvents += discardedInFrame
        if (firstDiscardedEventWatermark === null) {
          firstDiscardedEventWatermark = keys[0]
        }
      }
      retryAttempt = 0
      lastError = null
      const acknowledgementStatus = statusPayload(
        discardedInFrame > 0 ? 'batch_discarded' : 'batch_acknowledged',
        {
          batchId,
          acknowledgedEvents: frame.items.length,
          acknowledgedEventWatermark,
          discardedEventsInBatch: discardedInFrame,
          discardedByFreeze: Boolean(acknowledgement.discardedByFreeze),
          discardedByClear: Boolean(acknowledgement.discardedByClear),
          discardedByStaleGeneration: Boolean(
            acknowledgement.discardedByStaleGeneration,
          ),
          persistedEventsInBatch: acknowledgement.persistedEvents ?? frame.items.length,
          duplicateBatch: Boolean(acknowledgement.duplicateBatch),
        },
      )
      emit(discardedInFrame > 0 ? onError : onStatus, acknowledgementStatus)
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
        emit(onError, statusPayload('transport_error', { error: lastError }))
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
        emit(onError, statusPayload('transport_loop_failed', { error: lastError }))
      })
      .finally(() => {
        drainPromise = null
        if (!stopped && eventQueue.count() > 0) scheduleDrain()
      })
    return drainPromise
  }

  async function record(event) {
    if (stopped) throw new Error('debug_transport_stopped')
    const enrichedEvent = {
      ...event,
      sessionId: event.sessionId || sessionId,
      runId: event.runId || runId,
      transportClientId: clientId,
      transportId: randomId('event'),
      transportSequence: ++transportSequence,
      transportRecordedAt: Date.now(),
      recordingGeneration: activeRecordingGeneration,
      timestamp: event.timestamp || Date.now(),
    }

    let serialized
    try {
      serialized = JSON.stringify(enrichedEvent)
      if (typeof serialized !== 'string') {
        throw new Error('debug_event_serialization_returned_undefined')
      }
    } catch (error) {
      rejectedEvents += 1
      lastError = safeError(error)
      emit(onError, statusPayload('event_rejected', {
        error: lastError,
        reason: 'serialization_failed',
      }))
      throw error
    }

    const serializedBytes = byteLength(serialized)
    if (serializedBytes > maxEventBytes) {
      const error = new Error(`debug_event_exceeds_byte_limit:${serializedBytes}`)
      rejectedEvents += 1
      lastError = safeError(error)
      emit(onError, statusPayload('event_rejected', {
        error: lastError,
        eventBytes: serializedBytes,
        maxEventBytes,
      }))
      throw error
    }

    eventQueue.appendSerialized(serialized, serializedBytes, {
      recordingGeneration: enrichedEvent.recordingGeneration,
    })
    scheduleDrain()
    return enrichedEvent.transportId
  }

  async function recordSafe(event) {
    try {
      return await record(event)
    } catch {
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
    const rejectedEventsAtCheckpoint = rejectedEvents
    const watermarkAcknowledged = await waitForWatermark(
      targetEventWatermark,
      timeoutMs,
    )
    const complete = watermarkAcknowledged && rejectedEventsAtCheckpoint === 0
      && (
        firstDiscardedEventWatermark === null
        || firstDiscardedEventWatermark > targetEventWatermark
      )
    const status = statusPayload('transport_checkpoint', {
      complete,
      watermarkAcknowledged,
      targetEventWatermark,
      rejectedEventsAtCheckpoint,
      discardedEventsAtCheckpoint: discardedEvents,
      continuityBrokenAtCheckpoint: rejectedEventsAtCheckpoint > 0 || (
        firstDiscardedEventWatermark !== null
        && firstDiscardedEventWatermark <= targetEventWatermark
      ),
    })
    emit(complete ? onStatus : onError, status)
    return status
  }

  async function flush({ timeoutMs = 30_000 } = {}) {
    const deadline = Date.now() + Math.max(timeoutMs, 0)
    while (true) {
      if (!stopped && eventQueue.count() > 0) scheduleDrain()
      if (eventQueue.count() === 0 && !drainPromise) {
        return rejectedEvents === 0 && discardedEvents === 0
      }
      if (stopped || Date.now() >= deadline) return false
      await sleep(25)
    }
  }

  async function getStatus() {
    return statusPayload('status')
  }

  function stop() {
    stopped = true
    if (activeController) {
      activeController.abort(new Error('debug_transport_stopped'))
    }
    if (wakeRetry) wakeRetry()
  }

  emit(onStatus, statusPayload('transport_started', {
    frameBytes,
  }))

  const queueStatus = Object.freeze({
    count: () => eventQueue.count(),
    bytes: () => eventQueue.bytes(),
    lastKey: () => eventQueue.lastKey(),
  })

  return {
    clientId,
    record,
    recordSafe,
    checkpoint,
    flush,
    getStatus,
    stop,
    isCollectorUrl,
    nativeFetch: fetchImpl,
    queue: queueStatus,
  }
}

export function instrumentGlobalFetch({
  transport,
  target = globalThis,
  hypothesisIds = [],
  location = 'runtime:fetch',
  runId = 'initial',
  mapRequest = null,
  resolveFlowContext = null,
} = {}) {
  if (!transport || (
    typeof transport.recordSafe !== 'function'
    && typeof transport.record !== 'function'
  )) {
    throw new Error('transport_is_required')
  }
  if (!target || typeof target.fetch !== 'function') {
    throw new Error('target_fetch_unavailable')
  }

  const originalFetch = target.fetch
  const nativeFetch = (...args) => Reflect.apply(originalFetch, target, args)
  let fetchOrdinal = 0

  function recordWithoutThrow(event) {
    try {
      const result = typeof transport.recordSafe === 'function'
        ? transport.recordSafe(event)
        : transport.record(event)
      void Promise.resolve(result).catch(() => {
        // The transport surfaces queue/network failures through onError. Never
        // change the business request result because debug evidence could not send.
      })
    } catch {
      // Preserve the application path for legacy transports that throw before
      // returning a promise.
    }
  }

  const instrumentedFetch = function instrumentedFetch(input, init) {
    const resolvedUrl = resolveUrl(input, target.location?.href || globalThis.location?.href || '')
    if (transport.isCollectorUrl(resolvedUrl)) {
      return nativeFetch(input, init)
    }

    const ordinal = ++fetchOrdinal
    const correlationId = randomId('fetch')
    let flowContext = {}
    if (typeof resolveFlowContext === 'function') {
      try {
        flowContext = sanitizeFlowContext(resolveFlowContext({
          input,
          init,
          url: resolvedUrl,
          ordinal,
        }))
      } catch {
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
      if (typeof mapRequest === 'function') {
        mappedData = mapRequest({ input, init, url: resolvedUrl, data: baseData }) || baseData
      }
      if (Object.keys(flowData).length > 0) {
        mappedData = mappedData && typeof mappedData === 'object' && !Array.isArray(mappedData)
          ? { ...mappedData, ...flowData }
          : baseData
      }
      JSON.stringify(mappedData)
    } catch {
      mappedData = baseData
    }

    recordWithoutThrow({
      runId,
      correlationId,
      ...flowContext,
      sequence: 1,
      probeId: 'fetch.lifecycle',
      hypothesisIds,
      location,
      phase: 'network',
      event: 'fetch_start',
      message: 'application fetch started',
      data: mappedData,
      timestamp: startedAt,
      monotonicMs: startedMonotonic,
    })

    let result
    try {
      result = nativeFetch(input, init)
    } catch (error) {
      recordWithoutThrow({
        runId,
        correlationId,
        ...flowContext,
        sequence: 2,
        probeId: 'fetch.lifecycle',
        hypothesisIds,
        location,
        phase: 'network',
        event: 'fetch_reject',
        level: 'error',
        message: 'application fetch threw synchronously',
        data: {
          ...baseData,
          durationMs: Date.now() - startedAt,
          error: safeError(error),
        },
      })
      throw error
    }

    return Promise.resolve(result).then(
      (response) => {
        recordWithoutThrow({
          runId,
          correlationId,
          ...flowContext,
          sequence: 2,
          probeId: 'fetch.lifecycle',
          hypothesisIds,
          location,
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
        })
        return response
      },
      (error) => {
        recordWithoutThrow({
          runId,
          correlationId,
          ...flowContext,
          sequence: 2,
          probeId: 'fetch.lifecycle',
          hypothesisIds,
          location,
          phase: 'network',
          event: 'fetch_reject',
          level: 'error',
          message: 'application fetch rejected',
          data: {
            ...baseData,
            durationMs: Date.now() - startedAt,
            error: safeError(error),
          },
        })
        throw error
      },
    )
  }
  Object.defineProperty(instrumentedFetch, NATIVE_FETCH_SYMBOL, {
    value: originalFetch,
    enumerable: false,
    configurable: false,
    writable: false,
  })
  target.fetch = instrumentedFetch

  return function restoreFetch() {
    if (target.fetch === instrumentedFetch) {
      target.fetch = originalFetch
    }
  }
}
