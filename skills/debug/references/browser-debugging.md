# Browser Debugging

Use this reference only when evidence originates in browser code, when the failure crosses navigation or reload, or when every application `fetch` lifecycle event must be auditable.

## Table of contents

- Transport choice
- Setup
- Recording generations and Freeze
- Flow correlation
- Custom probes
- Complete fetch capture
- Delivery and backlog
- Long-lived response and event streams
- Lifecycle boundaries
- Observer cost and security
- Browser coverage gate

## Transport choice

Prefer an authoritative host-provided browser logger when one exists. Otherwise copy `assets/browser-debug-transport.mjs` into a temporary project path that client code can import.

Use the bundled transport for high-frequency streams or complete page-lifetime `fetch` coverage. Its batch is a finite network frame, not an evidence-reduction rule or a wait-for-stream-completion mechanism. Recording schedules delivery immediately; it does not wait to fill a batch. The transport provides:

- one serialized in-memory copy of each event until terminal collector acknowledgement;
- byte-framed batches without an event-count cap;
- one collector request at a time;
- timeout and deterministic retry with one stable `batchId`;
- deletion only after complete acknowledgement;
- a `recordingGeneration` stamp captured when each event enters the queue, with frames kept generation-homogeneous;
- terminal discard handling for frozen or stale-generation events without delayed replay;
- monotonic enqueue and acknowledgement watermarks for live checkpoints;
- a captured native `fetch` and collector-URL exclusion to prevent recursion.

The queue is page-local. It does not survive navigation, reload, process termination, memory exhaustion, or an oversized event.

## Setup

Configure the transport from the active ready file:

```ts
import {
  createBrowserDebugTransport,
  instrumentGlobalFetch,
} from './browser-debug-transport.mjs'

const debugTransport = createBrowserDebugTransport({
  endpoint: '<ENDPOINT>',
  batchEndpoint: '<BATCH_ENDPOINT>',
  sessionId: '<SESSION_ID>',
  runId: 'initial',
  recordingGeneration: 0, // replace with the current authoritative value
  onError(status) {
    console.error('[debug transport]', status)
  },
})
```

Read `recordingGeneration` from refreshed authoritative collector state or the active ready payload immediately before installing the transport. Do not log the dashboard token in product code. The ingest endpoints use the session ID; operator APIs remain token-protected and same-origin.

Create one transport per page realm and run, then reuse it for every probe. During hot reload or reinstrumentation, restore wrapped APIs and stop the prior transport before installing a replacement. One transport issues at most one collector request at a time; simultaneous live batch requests therefore require checking for multiple page realms, duplicate transport instances, or stale/retried DevTools rows.

## Recording generations and Freeze

Dashboard `Freeze` controls the collector-wide HTTP-ingest write gate. The dashboard continues polling while frozen, and the mode survives other tabs, dashboard reloads, user replies, analysis turns, and new run IDs because it belongs to the collector session. `Clear` remains available and does not unfreeze recording. Before a reproduction, use `dashboard-status`; when it reports `recording: frozen`, run `resume-recording`, refresh state, and initialize the run's transport from the resulting live `recordingGeneration`. Session `resume` only reuses the collector and never changes this gate.

The transport stamps `recordingGeneration` when `record` or `recordSafe` enqueues an event. It does not rewrite queued events when a later collector acknowledgement announces a newer generation, and it does not combine different generations in one frame. Therefore a frame recorded while frozen or before Resume remains identifiable as stale even if network delay or retry delivers it after Resume.

The collector terminally acknowledges a frozen, stale-generation, or post-Clear retry frame with `discardedEvents` and a discard disposition, stores no corresponding NDJSON lines, and adds nothing to the index. The transport deletes that resolved FIFO prefix so it cannot replay later, retains the same stable `batchId` for any acknowledgement retry, increments discard status, and sets `continuityBroken`. A batch that persisted before Clear but retries after its evidence was truncated receives `discarded_cleared`; it is neither resurrected nor reported as still persisted. Terminal acknowledgement means queue resolution, not persisted evidence: legacy `accepted` / `acceptedEvents` counts include terminally discarded events, so use `persistedEvents` and `discardedEvents` to classify the outcome. If a required event is discarded, the affected run or checkpoint is incomplete.

The collector response updates the transport's active generation for later events. If a transport did not observe a Freeze/Resume transition before enqueueing the first post-transition frame, that stale frame may be deliberately discarded while synchronizing to the current generation; do not count it as evidence. Refresh state and initialize the correct generation before a deliberate run rather than relying on that recovery path.

## Flow correlation

Keep each actual `fetch` call as a unique child correlation with sequence `1` for start and `2` for the Fetch-promise outcome: response headers available or rejection. This is terminal only for the promise, not for a streaming response body. Attach it to the reproduction-wide flow through `parentCorrelationId`, `operationId`, and an existing `requestId` when available:

```ts
const restoreFetch = instrumentGlobalFetch({
  transport: debugTransport,
  hypothesisIds: ['H-request-order', 'H-response-race'],
  location: 'src/api/client.ts:1',
  runId: 'initial',
  resolveFlowContext({ input }) {
    const operation = currentSaveOperationFor(input)
    return {
      parentCorrelationId: operation?.flowId,
      operationId: operation?.id,
      requestId: operation?.requestId,
    }
  },
})
```

The callback accepts only non-empty string values for those three fields. It cannot replace the unique child `correlationId`; invalid values or callback failures are ignored.

Prefer identifiers already present in application state or request infrastructure. Do not add a header or query parameter when it could trigger CORS preflight, change caching or signing, alter routing, or otherwise perturb the failure.

## Custom probes

Use the non-throwing interface for temporary application probes:

```ts
void debugTransport.recordSafe({
  parentCorrelationId: flowId,
  operationId,
  correlationId: requestId,
  sequence: 3,
  probeId: 'cart.commit.before',
  hypothesisIds: ['H-cache-stale', 'H-race-overwrite'],
  location: 'src/cart.ts:118',
  phase: 'mutation',
  event: 'before_commit',
  message: 'cart state before persistence',
  data: { cartVersion: 7, itemCount: 3 },
})
```

`recordSafe` returns the transport ID or `null`; serialization and event-size failures remain visible through `onError` and `rejectedEvents` without creating an unhandled rejection. Use `record` only when the caller deliberately handles rejection.

## Complete fetch capture

The global wrapper records every actual application `fetch` start and resolve/reject event during the covered page lifetime. It does not sample, rate-limit, first-N, or count-cap those lifecycle events.

`fetch_resolve` means the Fetch promise resolved and response headers became available. It does **not** prove that a response body was consumed, completed, or remained error-free. Instrument the actual decoder or reader loop when body-stream behavior is material.

It records method and a query-stripped URL by default. Do not add raw request or response bodies, authorization headers, cookies, access tokens, or sensitive query values. Use `mapRequest` only for compact, JSON-serializable, non-secret metadata.

Never instrument collector `/ingest`, `/ingest/batch`, `/api/*`, or dashboard traffic as application traffic. Keep both captured-native-fetch and URL-exclusion protections active.

Complete `fetch` capture is conditional: use it only when the failure contract requires every application request. For a localized non-network bug, prefer targeted boundary probes instead of wrapping global `fetch`.

## Delivery and backlog

The transport separates event count from network framing:

- Bound each serialized event with `maxEventBytes`.
- Bound each collector request with `frameBytes`.
- Keep one request active while allowing any number of application requests to enqueue evidence.
- Retry the same deterministic `batchId` after timeout; never mint a new ID for the same frame. Collector acknowledgement is idempotent and preserves the frame's original persisted or discarded outcome across Clear and Resume.
- Advance the acknowledged watermark only after the collector confirms the complete FIFO prefix; never delete an unacknowledged event.
- Treat `discardedEvents` as a terminally resolved but unpersisted prefix and set `continuityBroken`; acknowledgement alone is not proof that NDJSON contains the frame.
- Keep `keepalive: false` for the steady stream.

Inspect:

```ts
const status = await debugTransport.getStatus()
```

Review `queuedEvents`, `queuedBytes`, `enqueuedEventWatermark`, `acknowledgedEventWatermark`, `inFlightRequests`, `failedRequests`, `rejectedEvents`, `discardedEvents`, `firstDiscardedEventWatermark`, `recordingFrozen`, `recordingGeneration`, `continuityBroken`, `deliveryScope`, `durableQueue`, and `reloadSafe`.

For a stream that continues producing, snapshot and confirm only the prefix that exists at the observation boundary. Do not press dashboard Freeze as a substitute for a transport checkpoint:

```ts
const checkpoint = await debugTransport.checkpoint({ timeoutMs: 30_000 })
if (!checkpoint.complete) {
  throw new Error('debug evidence is incomplete through the checkpoint watermark')
}
```

`targetEventWatermark` and `rejectedEventsAtCheckpoint` are captured when `checkpoint` starts. Later events may continue to enqueue and do not invalidate that already-bounded prefix. Require `watermarkAcknowledged: true`, `rejectedEventsAtCheckpoint: 0`, `discardedEventsAtCheckpoint: 0`, `continuityBrokenAtCheckpoint: false`, and no transport-sequence gap through the target. A `/ingest/batch` request may appear as `Pending` while its acknowledgement is outstanding; use these fields and collector state instead of the Network-panel label to decide delivery.

After event production and instrumentation have stopped, drain the final queue before leaving the page:

```ts
restoreFetch()
const drained = await debugTransport.flush({ timeoutMs: 30_000 })
```

Claim final page-lifetime delivery only when `drained` is true, `queuedEvents` is zero, `inFlightRequests` is zero, `rejectedEvents` is zero, `discardedEvents` is zero, `continuityBroken` is false, and no required source or transport sequence is missing.

Stop the reproduction and report incomplete delivery when backlog grows without draining. Do not block the product path or silently discard required events to protect the collector.

## Long-lived response and event streams

For SSE, WebSocket, subscriptions, long polling, or `ReadableStream` bodies, instrument the existing application dispatch, decoder, or reader-loop boundary. Do not make transport completion depend on the business stream closing.

Record:

- connection/request start and headers/open;
- every failure-contract-required source event with a monotonic `streamSequence`;
- reconnect/attempt/generation changes;
- close, cancel, abort, decoder error, and reader error;
- one `observation-checkpoint` sentinel when the coverage plan's bounded condition is met.

Call `recordSafe` without awaiting collector I/O in the business callback. The call serializes and enqueues before yielding, while delivery proceeds independently. Never count-cap, sample, coalesce, overwrite, or first-N a source event that the failure contract requires exhaustively. Bound the fields of each event; if serialization or the byte limit rejects a required event, stop and mark the run incomplete.

Do not automatically clone, tee, or consume `response.body` merely to observe it. Those techniques can change backpressure, cancellation, buffering, and memory behavior. Add probes to the consumer the application already owns, or use an authoritative producer/server-side logger.

At the observation boundary, record the checkpoint sentinel and call `checkpoint`. The business stream may remain open. Only after the producer stops should `flush` require the entire queue to reach zero.

If collector recording becomes frozen during a required stream, arriving frames are intentionally discarded rather than buffered for Resume. Stop using that interval as complete evidence, record the continuity break, and establish a live future generation before a new run.

## Lifecycle boundaries

Navigation, reload, page termination, and memory exhaustion are evidence-loss boundaries. When the reproduction crosses one:

1. Record a pre-boundary sentinel.
2. Restore wrapped APIs and drain the page-local queue while the page is alive.
3. Confirm zero backlog or mark continuity inconclusive.
4. Use an authoritative server logger or newly initialized page logger on the other side.
5. Correlate both sides with an existing durable flow, operation, or request identifier.

Do not claim that `sendBeacon`, `keepalive`, or the page-local queue provides authoritative cross-navigation continuity. A small teardown sentinel may use them only as supplemental evidence.

Collector recording mode itself is not page-local: a new or reloaded page must read the collector's current `recordingGeneration` before installing a transport. Reloading a page does not unfreeze the collector, and a fresh page queue does not make an older generation current.

## Observer cost and security

- Avoid logging every render; record relevant version changes, branch decisions, commits, and invariant failures.
- Bound URLs, strings, arrays, nested fields, and stacks.
- Record hashes, counts, enums, status, duration, attempt, generation, and selected fields.
- Avoid objects whose serialization invokes getters, cycles, or application behavior.
- Monitor queue bytes during expected peak traffic before consuming a rare reproduction opportunity.
- Bind the collector to loopback, keep operator tokens out of instrumentation, and never expose it publicly.
- Post directly to the collector when reachable; do not create an app-local proxy only for temporary browser logs.

## Browser coverage gate

Before the failing run, require:

- [ ] The plan identifies page-lifecycle boundaries and continuity strategy.
- [ ] Parent flow, operation, child request, attempt, and ordering fields are available without changing request semantics.
- [ ] Collector URLs cannot recurse through the wrapper.
- [ ] Serialization failures and oversized events are surfaced through `recordSafe` status.
- [ ] Expected peak event and byte volume can drain without unbounded backlog.
- [ ] Authoritative collector state is `recording: live`, and the transport was initialized with its current `recordingGeneration`.
- [ ] Every retry preserves the frame's stable `batchId`; no discarded frame can be renamed and replayed after Resume.
- [ ] Every required source event has a monotonic source sequence, and the transport checkpoint proves an acknowledged gap-free prefix with zero rejected or discarded required events and `continuityBroken: false`.
- [ ] Sensitive request fields are excluded.
- [ ] Flow start, pre-boundary when applicable, and the configured terminal or observation-checkpoint sentinel are planned.
- [ ] Instrumented client code passes the narrowest relevant syntax, type, or build check.

Dashboard visibility is not part of this gate.
