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

Prefer an authoritative host-provided browser logger only when it preserves the same all-occurrence and acknowledgement contract. Otherwise copy `assets/browser-debug-transport.mjs` into a temporary project path that client code imports and actually executes.

Install exactly one shared transport for the page realm and run. Route every browser probe through that instance, including global `fetch`, component, hook, stream, timer, and custom boundary probes. A copied asset with no runtime import and no active `recordSafe` call is not instrumentation. A second live transport is a gate failure, not extra redundancy.

Preserve `N source occurrences -> N record calls -> N queued frame items -> N persisted NDJSON records`. Place the source counter and probe at the authoritative browser callback or dispatch before any existing throttle, debounce, filter, deduplication, or aggregation; a downstream producer cannot establish the upstream `N`. A byte-framed `/ingest/batch` request is wire framing only: it carries each logical event as its own array item with its own `transportId` and `transportSequence`. Never sample, throttle, debounce, first-N, once-per-key, change-gate, anomaly-gate, aggregate, merge, coalesce, overwrite, or deduplicate occurrences after a probe is active. Reduce probe locations before the run if full occurrence capture is too expensive.

The bundled transport provides:

- a realm-global registry keyed by collector endpoint and session, so HMR and
  repeated installation return the same queue instead of starting a parallel
  drain;
- active ownership plus an append-only, page-lifetime audit of terminated run
  IDs, so a failed run cannot be silently reopened with reset counters;
- a realm producer registry with stable producer keys, mutable HMR control,
  monotonic source sequence, and token-safe teardown;
- one serialized in-memory copy of every logical event until the collector resolves its frame;
- byte-framed batches without an event-count cap or occurrence transformation;
- exactly one collector request in flight, while later occurrences continue to enqueue;
- timeout and deterministic retry with one stable `batchId`;
- strict persisted, duplicate-persisted, and terminal-discard acknowledgement classification;
- a `recordingGeneration` stamp captured when each event enters the queue, with frames kept generation-homogeneous;
- monotonic enqueue and acknowledgement watermarks plus cardinality counters;
- a captured native `fetch` and collector-URL exclusion to prevent recursion.

The queue is page-local. It does not survive navigation, reload, process termination, memory exhaustion, or an oversized event. Treat any such loss boundary as incomplete evidence.

## Setup

Configure the transport from the active ready file:

```ts
import {
  getOrCreateBrowserDebugTransport,
  installRealmDebugProducer,
  instrumentGlobalFetch,
} from './browser-debug-transport.mjs'

const debugTransport = getOrCreateBrowserDebugTransport({
  endpoint: '<ENDPOINT>',
  batchEndpoint: '<BATCH_ENDPOINT>',
  sessionId: '<SESSION_ID>',
  runId: 'initial',
  recordingGeneration: 0, // replace with the current authoritative value
  onError(status) {
    console.error('[debug transport]', status)
  },
})

export { debugTransport }
```

Create this instance in one temporary instrumentation module. Assign the only registry acquisition directly to one top-level canonical `const`, and keep every direct `recordSafe` call and bundled producer installation statically bound to that value in the same module. Export narrow event-emitter or producer-install functions to component and hook sites instead of importing or shadowing the transport binding there. Do not duplicate the constructor snippet. Read `recordingGeneration` from refreshed authoritative collector state or the active ready payload immediately before installation. `endpoint` exists only so collector traffic can be excluded from global `fetch` instrumentation; probes must never post to it directly. Do not log the dashboard token in product code.

Run `scripts/validate_browser_instrumentation.py` over the complete temporary instrumentation source set. Its canonical wiring check masks comments, strings, templates, and classified regex literals; ambiguous slash/brace syntax fails closed rather than influencing lexical scope. It rejects nested or shadowed transport bindings and accepts a sink only when it is the canonical binding's `recordSafe` call or a bundled producer whose `options.transport` directly names that binding. This prevents a copied-but-unused shared transport from passing because an unrelated fake object exposes a method with the same name. The check is conservative: use the canonical source shape instead of aliases, indirect configuration objects, or dynamic wiring, then still prove runtime occurrence/enqueue/persistence cardinality.

`getOrCreateBrowserDebugTransport` and its compatibility name
`createBrowserDebugTransport` both use the same `Symbol.for` realm registry;
the compatibility name cannot bypass singleton ownership. Re-evaluating the
module with the same collector session and configuration returns the same
object and preserves its queue. A different run, endpoint, recording
generation, or byte configuration for an occupied collector session is an
explicit registry conflict and makes the run incomplete instead of creating a
parallel transport. The registry separates the one active owner from
terminated-run audit records. Once a run ID reaches either a complete or
incomplete terminal state, that run ID can never be opened again in the same
page realm and collector session.

The configured `sessionId` and `runId` are the transport's canonical identity.
Every persisted event is forced to that identity. A caller may omit those
fields or provide the exact canonical values; any different explicit value is
rejected as one occurrence and permanently breaks cardinality. After
serialization, the wire record must exactly preserve every transport-owned
field: `sessionId`, `runId`, `transportClientId`, `transportId`,
`transportSequence`, `transportRecordedAt`, and `recordingGeneration`. A custom
`toJSON` result cannot delete or rewrite any of them. `timestamp` is not a
transport-owned canonical field.

For deliberate reinstrumentation, first detach every producer and restore
wrapped APIs, then require `await debugTransport.flushAndStop()` to return
`true`. Every stop terminalizes the run and releases active ownership into the
terminated-run audit. A successful safe stop records a complete terminal run.
A timed-out or cardinality-incomplete safe stop records an incomplete terminal
run, counts every unresolved queued item as abandoned, aborts its active
request, and returns `false`. Legacy `stop()` does the same forced
terminalization immediately and is never the normal replacement path. A new
run may start only with a new run ID and only after the old collector request
has settled; the registry blocks old/new parallel draining. Reusing the old run
ID fails explicitly rather than resetting its counters or hiding its audit.

Every installed wrapper, listener, subscription, and timer is also a producer
with lifecycle ownership. Give each one a stable realm `producerKey`, retain
its mutable control and monotonic source sequence behind `Symbol.for`, and use
a token-safe lease/dispose pair. Any acquisition while that `producerKey` has
an active owner is an explicit ownership conflict, even when the requested
transport is the same. The failed acquisition never invokes the active
owner's cleanup, so two module sources cannot silently replace one another by
reusing a key. For HMR or deliberate reconfiguration, first call the current
release lease, then reacquire the now-inactive control. Reacquisition preserves
the producer state, monotonic source sequence, and wrapper identity. Calling
the old release lease again is a no-op and cannot detach the reacquired owner.
A different live transport is also an explicit producer conflict.
`installRealmDebugProducer` is the shared implementation of this contract;
`instrumentGlobalFetch` uses it with the `global-fetch` key. It marks the
producer active before calling `install`, allowing subscriptions that
synchronously emit their initial value to use `beginOperation()`. `install`
must synchronously return its cleanup function. Install, cleanup, rollback,
and reacquisition failures are reported through `reportInstrumentationError`,
increment the permanent
`producerLifecycleFailures` counter, and make the run incomplete. A failed
install blocks that `producerKey` for the failed transport/run so an unknown
partially installed callback cannot be stacked by an in-run retry. After that
run terminalizes incomplete, a fresh transport with a new run ID may establish
fresh control for the same stable key.

Use the exported installer for a HistoryVirtualList scroll source or any other
temporary listener/timer instead of hand-rolling HMR state:

```ts
const releaseHistoryScroll = installRealmDebugProducer({
  target: globalThis,
  producerKey: 'history-virtual-list:scroll',
  transport: debugTransport,
  config: { scrollElement },
  createState: () => ({ source: 'history-virtual-list' }),
  install({ state, getConfig, getTransport, nextSourceSequence }) {
    const { scrollElement: activeElement } = getConfig()
    const onScroll = () => {
      void getTransport().recordSafe({
        probeId: 'history-virtual-list.scroll',
        event: 'scroll_callback',
        sequence: nextSourceSequence(),
        data: { source: state.source, scrollTop: activeElement.scrollTop },
      })
    }
    activeElement.addEventListener('scroll', onScroll, { passive: true })
    return () => activeElement.removeEventListener('scroll', onScroll)
  },
})
```

The context's `state` object, `getConfig()`, `getTransport()`, and monotonic
`nextSourceSequence()` survive same-transport release and reacquisition. The
old release function becomes a no-op; only the latest lease detaches the
producer. Call the source callback and counter at the authoritative dispatch
before existing product filters. For a finite asynchronous lifecycle that must emit a terminal event,
call `const endOperation = beginOperation()` at its start and invoke that token
exactly once after the terminal `recordSafe` enqueue settles. Do not hold an
operation token for an open-ended SSE, WebSocket, subscription, or timer
lifetime; use an explicit observation checkpoint for those streams.

The following patterns fail the browser gate:

- any direct, fire-and-forget `fetch` to `/ingest` or `/ingest/batch` outside the shared transport;
- `keepalive: true` for steady event delivery, `sendBeacon`, or one request per occurrence;
- `.catch(() => {})`, an empty `catch`, or any other swallowed enqueue or delivery failure;
- a copied-but-unused transport asset or probes that bypass the shared instance;
- more than one live transport in the same page realm and run;
- any occurrence-level sampling, deduplication, aggregation, coalescing, or gating.

## Recording generations and Freeze

Dashboard `Freeze` controls the collector-wide HTTP-ingest write gate. The dashboard continues polling while frozen, and the mode survives other tabs, dashboard reloads, user replies, analysis turns, and new run IDs because it belongs to the collector session. `Clear` remains available and does not unfreeze recording. Before a reproduction, use `dashboard-status`; when it reports `recording: frozen`, run `resume-recording`, refresh state, and initialize the run's transport from the resulting live `recordingGeneration`. Session `resume` only reuses the collector and never changes this gate.

The transport stamps `recordingGeneration` when `record` or `recordSafe` enqueues an event. It does not rewrite queued events when a later collector acknowledgement announces a newer generation, and it does not combine different generations in one frame. Therefore a frame recorded while frozen or before Resume remains identifiable as stale even if network delay or retry delivers it after Resume.

The collector terminally acknowledges a frozen, stale-generation, or post-Clear retry frame with `persistedEvents: 0`, a full-frame `discardedEvents` count, and a discard disposition. It stores no corresponding NDJSON lines and adds nothing to the index. The transport removes that terminally resolved FIFO prefix only to prevent replay, increments `discardedEvents`, leaves `persistedEvents` unchanged, and sets `continuityBroken`. It must never normalize the frame as persistence. A batch that persisted before Clear but retries after its evidence was truncated receives `discarded_cleared`; it is neither resurrected nor counted as persisted. Legacy `accepted` / `acceptedEvents` means terminally resolved and can include discard. Any discard makes the affected run and checkpoint incomplete.

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

Call `recordSafe` once for every occurrence of the active probe without awaiting collector I/O in the product callback. It returns the transport ID or `null`; enrichment, serialization, queue-append, event-size, and exact wire-frame failures remain visible through `onError`, `lastError`, `recordedEvents`, `enqueuedEvents`, `rejectedEvents`, and `firstRejectedTransportSequence` without creating an unhandled rejection. Each failed occurrence increments rejection cardinality exactly once. Do not wrap the call in an empty catch. Use `record` only when the caller deliberately handles and surfaces rejection.

Do not route a probe by supplying another `sessionId` or `runId` in the event.
Use the shared transport for the intended run. Explicit cross-session or
cross-run values fail closed with `canonical_session_mismatch` or
`canonical_run_mismatch`; they are never silently overwritten or persisted
under a different run than the registry audit.

## Complete fetch capture

The global wrapper records every actual application `fetch` start and resolve/reject event during the covered page lifetime. It does not sample, rate-limit, first-N, or count-cap those lifecycle events.

An active `global-fetch` producer must be restored before another
`instrumentGlobalFetch` acquisition. Calling it again while active is an
ownership conflict and leaves the current wrapper unchanged. After the current
restore lease detaches it, reacquisition for the same transport reuses one
wrapper and continues the same monotonic fetch ordinal; it does not wrap the
wrapper. Calling the old restore lease again is harmless. A different live
transport also fails installation and leaves the current wrapper unchanged.

Omit `runId` to inherit the transport's canonical run, including non-`initial`
runs. Supplying the same canonical value is allowed. Supplying a different
value rejects installation immediately, increments
`producerLifecycleFailures`, and makes that transport run incomplete; fetch
events can never be attributed to another run.

`fetch_resolve` means the Fetch promise resolved and response headers became available. It does **not** prove that a response body was consumed, completed, or remained error-free. Instrument the actual decoder or reader loop when body-stream behavior is material.

It records method and a query-stripped URL by default. Do not add raw request or response bodies, authorization headers, cookies, access tokens, or sensitive query values. Use `mapRequest` only for compact, JSON-serializable, non-secret metadata.

Never instrument collector `/ingest`, `/ingest/batch`, `/api/*`, or dashboard traffic as application traffic. Keep both captured-native-fetch and URL-exclusion protections active.

Complete `fetch` capture is conditional: use it only when the failure contract requires every application request. For a localized non-network bug, prefer targeted boundary probes instead of wrapping global `fetch`.

## Delivery and backlog

The transport separates logical event count from network framing:

- Bound each serialized event with `maxEventBytes` and the complete JSON request body with `frameBytes`; never use either bound to reduce the number of events. `frameBytes` includes the `batchId`, `events` envelope, brackets, commas, and the serialized event. Therefore the effective single-event limit is lower than both configured values. Reject an event before enqueue when its one-item request cannot fit, and never send an oversized request or retry it forever.
- Keep exactly one request active while any number of later occurrences enqueue. Use `/ingest/batch` only; keep `keepalive: false` for steady delivery.
- Serialize every queued event independently into the frame's `events` array. For a frame of length `N`, require `N` distinct frame items and, after persistence, `N` NDJSON records.
- Retry the same deterministic `batchId` after timeout or invalid acknowledgement; never mint a new ID for the same frame.
- For a non-duplicate success, delete the FIFO prefix only when `accepted === N`, the `batchId` matches, `persistedEvents === N`, `discardedEvents === 0`, and the disposition is `persisted`.
- For a duplicate persisted acknowledgement, require the same stable `batchId`, `duplicateBatch: true`, `discardedEvents === 0`, and the persisted disposition. The collector reports zero newly persisted events; the transport records `N` as duplicate-confirmed persistence because the original idempotent batch remains in NDJSON.
- For a terminal discard, require `persistedEvents === 0`, `discardedEvents === N`, and an explicit discard disposition. Remove the resolved prefix to prevent replay, but increment only discard counters and mark continuity broken.
- Treat HTTP `409` with `{ "error": "transport_batch_id_conflict" }` as a fatal protocol failure. The collector has proved that the stable `batchId` was previously associated with different content, so retrying cannot recover the run. Do not retry, persist, or delete that frame. Terminalize the run incomplete, count its queued events as abandoned, retain the terminated-run audit, and start any later attempt with a new run ID and fresh transport only after the failed request settles.
- Retain and retry the frame after any missing, partial, contradictory, or mismatched acknowledgement. Never advance a watermark or delete a frame based only on `ok`, HTTP success, or legacy `accepted`.

Inspect:

```ts
const status = await debugTransport.getStatus()
```

Reconcile `recordedEvents`, `enqueuedEvents`, `persistedEvents`, `acknowledgedEvents`, `collectorReportedPersistedEvents`, `duplicateConfirmedEvents`, `discardedEvents`, `rejectedEvents`, and `abandonedEvents`. Also review `queuedEvents`, `queuedBytes`, `enqueuedEventWatermark`, `acknowledgedEventWatermark`, `inFlightRequests`, `requestConcurrencyLimit`, `maxInFlightRequests`, `collectorRequestAttempts`, `failedRequests`, `instrumentationErrors`, `lastInstrumentationError`, `lastError`, `firstRejectedTransportSequence`, `firstAbandonedEventWatermark`, `firstDiscardedEventWatermark`, `registryConflicts`, `activeProducerCount`, `activeProducerKeys`, `producerOperationsStarted`, `producerOperationsCompleted`, `pendingProducerOperations`, `abandonedProducerOperations`, `abandonedProducerCount`, `producerLifecycleFailures`, `fatalProtocolFailures`, `producerSettlementPending`, `recordingFrozen`, `recordingGeneration`, `acceptingEvents`, `stopped`, `continuityBroken`, `cardinalityComplete`, `deliveryScope`, `durableQueue`, and `reloadSafe`.

At runtime, the correct Network-panel shape is zero or one temporary `Pending` request to `/ingest/batch`. One pending batch only means its acknowledgement is outstanding. Multiple simultaneous direct `/ingest` `Pending` rows from one page fail the gate immediately; they prove probes bypassed the shared queue. Multiple simultaneous `/ingest/batch` requests require locating duplicate page realms or multiple live transports before reproduction. Do not accept a Pending flood as normal high-frequency logging.

For a stream that continues producing, snapshot and confirm only the prefix that exists at the observation boundary. Do not press dashboard Freeze as a substitute for a transport checkpoint:

```ts
const checkpoint = await debugTransport.checkpoint({ timeoutMs: 30_000 })
if (!checkpoint.complete) {
  throw new Error('debug evidence is incomplete through the checkpoint watermark')
}
```

`targetEventWatermark`, `recordedEventsAtCheckpoint`, `enqueuedEventsAtCheckpoint`, and `rejectedEventsAtCheckpoint` are captured when `checkpoint` starts. Later events may continue to enqueue and do not invalidate that bounded prefix. A checkpoint is eligible to complete only when the transport is live and accepting events both when the snapshot is taken and when acknowledgement finishes. A stopping or terminalized transport always returns `complete: false`, even when its queue is empty and its watermark is acknowledged. Require `recordedEventsAtCheckpoint === enqueuedEventsAtCheckpoint`, `watermarkAcknowledged: true`, `rejectedEventsAtCheckpoint: 0`, `abandonedProducerOperationsAtCheckpoint: 0`, `abandonedProducerCountAtCheckpoint: 0`, `discardedEventsAtCheckpoint: 0`, `continuityBrokenAtCheckpoint: false`, and no source or transport-sequence gap through the target. Forced stop cannot be reinterpreted as a complete checkpoint after producer abandonment.

After event production and instrumentation have stopped, drain the final queue
and release its realm-registry ownership before leaving the page:

```ts
restoreFetch()
const drained = await debugTransport.flushAndStop({ timeoutMs: 30_000 })
```

Restoring a producer blocks new occurrences but does not erase finite business
operations already in flight. Final `flushAndStop()` first requires every
producer to be detached, then waits within the same timeout for pending
operation tokens to enqueue their terminal events, and only then closes event
acceptance and drains the queue. A timeout terminalizes the run as incomplete,
increments `abandonedProducerOperations`, and can never later become complete
when a delayed outcome arrives. Ordinary `flush()` and long-stream checkpoints
do not wait for an open-ended producer lifetime.

Claim final page-lifetime delivery only when `drained` and `cardinalityComplete` are true, `recordedEvents === enqueuedEvents === persistedEvents`, `queuedEvents` is zero, `inFlightRequests`, `activeProducerCount`, `pendingProducerOperations`, `abandonedProducerOperations`, `abandonedProducerCount`, and `producerLifecycleFailures` are zero, `rejectedEvents`, `abandonedEvents`, `discardedEvents`, and `registryConflicts` are zero, `continuityBroken` is false, and no active source or transport sequence is missing. Confirm the collector contains the same NDJSON record count through the acknowledged watermark.

Stop the reproduction and report incomplete delivery when backlog grows without draining. `flushAndStop()` still terminalizes that failed run; start any later attempt with a new run ID after its network settlement barrier clears. Do not block the product path or silently discard active probe events to protect the collector.

## Long-lived response and event streams

For SSE, WebSocket, subscriptions, long polling, or `ReadableStream` bodies, instrument the existing application dispatch, decoder, or reader-loop boundary. Do not make transport completion depend on the business stream closing.

Record:

- connection/request start and headers/open;
- every source-event occurrence at each active probe with a monotonic `streamSequence`;
- reconnect/attempt/generation changes;
- close, cancel, abort, decoder error, and reader error;
- one `observation-checkpoint` sentinel when the coverage plan's bounded condition is met.

Call `recordSafe` without awaiting collector I/O in the business callback. The call serializes and enqueues before yielding, while delivery proceeds independently. Never count-cap, sample, coalesce, overwrite, or first-N any active probe occurrence. Bound the fields of each event; if serialization or the byte limit rejects an event, stop and mark the run incomplete.

Do not automatically clone, tee, or consume `response.body` merely to observe it. Those techniques can change backpressure, cancellation, buffering, and memory behavior. Add probes to the consumer the application already owns, or use an authoritative producer/server-side logger.

At the observation boundary, record the checkpoint sentinel and call `checkpoint`. The business stream may remain open. Only after the producer stops should `flush` require the entire queue to reach zero.

If collector recording becomes frozen during a required stream, arriving frames are intentionally discarded rather than buffered for Resume. Stop using that interval as complete evidence, record the continuity break, and establish a live future generation before a new run.

## Lifecycle boundaries

Navigation, reload, page termination, and memory exhaustion are evidence-loss boundaries. When the reproduction crosses one:

1. Record a pre-boundary sentinel.
2. Restore wrapped APIs and complete `flushAndStop()` while the page is alive.
3. Confirm zero backlog or mark continuity inconclusive.
4. Use an authoritative server logger or newly initialized page logger on the other side.
5. Correlate both sides with an existing durable flow, operation, or request identifier.

Do not use `sendBeacon` or `keepalive` as a cross-navigation fallback. The page-local queue proves only its acknowledged continuous prefix; if navigation or termination interrupts a later prefix, mark the run incomplete.

Collector recording mode itself is not page-local: a new or reloaded page must read the collector's current `recordingGeneration` before installing a transport. Reloading a page does not unfreeze the collector, and a fresh page queue does not make an older generation current.

## Observer cost and security

- Select probe locations whose full occurrence volume is acceptable. Do not activate a render or loop probe unless every occurrence can be retained; once active, never suppress later occurrences.
- Bound URLs, strings, arrays, nested fields, and stacks.
- Record hashes, counts, enums, status, duration, attempt, generation, and selected fields.
- Avoid objects whose serialization invokes getters, cycles, or application behavior.
- Monitor queue bytes during expected peak traffic before consuming a rare reproduction opportunity.
- Bind the collector to loopback, keep operator tokens out of instrumentation, and never expose it publicly.
- Post directly to the collector when reachable; do not create an app-local proxy only for temporary browser logs.

## Browser coverage gate

Before the failing run, require:

- [ ] The plan identifies page-lifecycle boundaries and continuity strategy.
- [ ] Exactly one shared transport is live in the page realm and run, and every active browser probe imports and calls it.
- [ ] The shared module installs through `getOrCreateBrowserDebugTransport`; HMR/repeated installation returns the same queue, and no registry conflict exists.
- [ ] Static validation sees exactly one unaliased registry factory import and call assigned to one top-level canonical `const`; comments, literals, nested/shadowed bindings, fake sinks, and producer options bound to another object do not satisfy usage.
- [ ] Every wrapper, listener, subscription, and timer has one stable realm `producerKey`, a monotonic source sequence, and token-safe teardown; active acquisition conflicts before cleanup, while release-then-reacquire preserves state and an old HMR dispose cannot detach the current producer.
- [ ] Custom producers install through `installRealmDebugProducer`; synchronous initial emission can begin an operation, reacquisition after release has exactly one callback, and any lifecycle failure permanently breaks completeness and blocks unsafe reinstall.
- [ ] Global-fetch HMR restores the active wrapper before reacquisition, then reuses that wrapper and its sequence; a different live transport fails instead of stacking, and a terminated run ID cannot be reopened.
- [ ] The copied transport asset is used at runtime; no copied-but-unused transport or parallel emitter remains.
- [ ] Source inspection finds no direct fire-and-forget `/ingest`, steady `keepalive: true`, `sendBeacon`, empty transport catch, or per-component/per-event transport constructor.
- [ ] Source inspection finds no sampling, throttling, debouncing, first-N, once-per-key, change gate, anomaly gate, aggregation, merge, coalescing, overwrite, or deduplication on an active probe occurrence.
- [ ] Parent flow, operation, child request, attempt, and ordering fields are available without changing request semantics.
- [ ] Collector URLs cannot recurse through the wrapper.
- [ ] Serialization failures and oversized events are surfaced through `recordSafe` status.
- [ ] The serialized record exactly retains every transport-owned identity, sequence, time, and generation field; custom `toJSON` deletion or mutation is rejected before enqueue.
- [ ] Enrichment and queue-append failures are surfaced exactly once, and a one-item request including envelope overhead fits `frameBytes` before any event is enqueued.
- [ ] Flow-context and request-mapping callback failures are surfaced through `instrumentationErrors`; none remain unexplained.
- [ ] Expected peak event and byte volume can drain without unbounded backlog.
- [ ] Authoritative collector state is `recording: live`, and the transport was initialized with its current `recordingGeneration`.
- [ ] Every retry preserves the frame's stable `batchId`; no discarded frame can be renamed and replayed after Resume.
- [ ] DevTools shows at most one temporary `/ingest/batch` `Pending` request and no direct `/ingest` `Pending` rows; any Pending flood is resolved before reproduction.
- [ ] Every source-event occurrence at each active probe has a monotonic source sequence, and a live accepting transport checkpoint proves `recorded === enqueued === persisted`, an acknowledged gap-free prefix, zero rejected, abandoned, producer-abandonment, discarded, registry-conflict, or fatal-protocol events, and `continuityBroken: false`; no stopping or terminalized transport checkpoint is accepted.
- [ ] A collector `transport_batch_id_conflict` produces one request only, never retries or deletes the queued frame, and leaves an incomplete terminated-run audit before any fresh run begins.
- [ ] Producer teardown leaves zero active producers, then `flushAndStop()` settles every finite pending producer operation before the final drain; timeout or abandonment remains an incomplete terminated-run audit.
- [ ] Sensitive request fields are excluded.
- [ ] Flow start, pre-boundary when applicable, and the configured terminal or observation-checkpoint sentinel are planned.
- [ ] Instrumented client code passes the narrowest relevant syntax, type, or build check.

Dashboard visibility is not part of this gate.
