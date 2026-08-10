# Browser Debugging

Use this optional reference only when evidence originates in browser code, the failure crosses navigation or reload, every application `fetch` lifecycle event matters, or a long-lived client stream needs a bounded observation window. The collector protocol itself remains language-neutral.

## Table of contents

- Logging-path choice
- Setup
- Collection controls
- Flow correlation
- Custom probes
- Complete fetch capture
- Delivery and backlog
- Long-lived response and event streams
- Lifecycle boundaries
- Observer cost and security
- Browser coverage gate

## Logging-path choice

Prefer this order:

1. Reuse the application's existing structured logger or an authoritative host logger when it can preserve the planned event fields.
2. Otherwise use the browser/runtime HTTP API already accepted by the project to post to the collector's `/ingest` endpoint.
3. Send either one event object or an exact `{"events": [...]}` envelope to that same endpoint. Each array item remains one logical event and one NDJSON line.
4. Create a small project-local adapter only when repeating endpoint, serialization, headers, and error handling would be unsafe. Match the repository's language, framework, module system, and lifecycle conventions.

The debug skill does not require a bundled browser client. Do not copy a preselected JavaScript module into a non-JavaScript project, and do not make browser-specific client APIs a prerequisite for collector use.

Preserve the logical goal `N source occurrences -> N emitted events -> N persisted NDJSON records` for the bounded evidence window. Achieve it with the selected project's logger or runtime-native HTTP path. Do not add sampling, first-N, once-per-key, change-gating, aggregation, coalescing, overwrite, or deduplication after a probe is active.

Browser memory and page lifetime are not durable boundaries. When the page can navigate, reload, terminate, or exhaust memory before a send finishes, either establish the planned sentinel and verify it before that boundary, use an existing authoritative server-side logger, or mark the affected interval incomplete.

## Setup

Read the active ready file and configure only the values the selected logger needs:

- `endpoint` for either one JSON object or an exact `{"events": [...]}` envelope;
- `sessionId` and the current `runId` as event fields;
- the planned probe, location, correlation, event, timestamp, and bounded data fields.

Do not put the dashboard token in product instrumentation. It is for same-origin operator actions, not ingestion.

Before the deliberate reproduction:

1. Inspect the complete temporary instrumentation source set.
2. Enumerate every debug-only helper reference. Inline a one-file adapter when practical; otherwise create the shared helper first, resolve each importer independently, and validate aliases or package/module references with the project's own browser and SSR resolver configuration. Use `scripts/debug_import_path.py` only for slash-delimited file-relative systems, as described in [runtime-debugging.md](./runtime-debugging.md).
3. Verify that each active probe calls the selected logger exactly once per source occurrence.
4. Verify that HMR, component remount, or repeated setup cannot stack wrappers, listeners, subscriptions, or timers. Use the project's existing cleanup/dispose mechanism.
5. Send one bounded test event and verify that it appears in the collector and NDJSON file.
6. Clear the test event when it would pollute the deliberate run.
7. Run the narrowest relevant native resolution, syntax, type, build, or test command for every applicable browser and SSR boundary.

This is a runtime wiring gate, not a mandate for a particular import name, top-level binding shape, singleton implementation, or browser-only static validator.

## Collection controls

Dashboard `Freeze` controls the collector-wide write gate. It is not a browser-tab queue state. Every dashboard tab and page reload observes the same collector state, while the dashboard keeps polling.

When the collector is frozen:

- later `/ingest` requests persist zero events;
- an in-flight request that spans Freeze/Resume is rejected and cannot enter the next recording window;
- the non-success response must make that outcome explicit;
- the collector does not buffer those events for a later Resume;
- Clear and Stop remain available;
- a browser reload does not Resume collection.

Resume accepts only future requests and requires no collector-specific producer state. Before a deliberate run, refresh `dashboard-status` and require live collection. After the run reaches its planned terminal or observation checkpoint and its final ordinary logging call completes, Freeze may be used to stabilize the evidence view for analysis.

## Flow correlation

Keep each actual application `fetch` call as a unique child correlation with sequence `1` for start and `2` for the Fetch-promise outcome: response headers available or rejection. This is terminal only for the promise, not for a streaming response body. Attach it to the reproduction-wide flow through `parentCorrelationId`, `operationId`, and an existing `requestId` when available.

Conceptually:

```json
{
  "runId": "initial",
  "parentCorrelationId": "save-flow-8f31",
  "operationId": "save-B",
  "requestId": "req-42",
  "correlationId": "fetch-17",
  "sequence": 1,
  "probeId": "http.fetch.start",
  "event": "fetch_start",
  "location": "src/api/client.ts:40",
  "timestamp": 1733456789000,
  "data": {"method": "POST", "urlClass": "/api/cart"}
}
```

Prefer identifiers already present in application state or request infrastructure. Do not add a header or query parameter when it could trigger CORS preflight, change caching or signing, alter routing, or otherwise perturb the failure.

## Custom probes

Create one immutable JSON object per active-probe occurrence and send it through the selected project/host logger or target-runtime HTTP adapter. Include the shared schema from [runtime-debugging.md](./runtime-debugging.md), especially `runId`, `probeId`, `hypothesisIds`, `location`, `event`, `timestamp`, and the relevant correlation and sequence fields.

Do not await network I/O inside a hot product callback. Use an existing asynchronous logger or a bounded project-local queue when needed, and expose send/serialization failures through normal diagnostics. If the selected path cannot report whether the bounded interval persisted, state that limitation and do not use a missing event as proof.

Do not mutate one event object and reuse it for later occurrences. Do not let serialization or logging errors throw into product code.

## Complete fetch capture

Wrap global or shared `fetch` only when the failure contract requires every application request during the covered page lifetime. For a localized non-network bug, prefer targeted boundary probes.

A complete wrapper must:

- record every actual application `fetch` start and resolve/reject occurrence;
- create a distinct child correlation for each call;
- preserve the receiver, arguments, return type, rejection, and timing behavior of the original call;
- record method and a query-stripped or classified URL by default;
- exclude collector `/ingest`, `/api/*`, and dashboard traffic to prevent recursion;
- use the project's normal install/cleanup lifecycle so HMR or remount cannot stack wrappers;
- restore the exact prior `fetch` implementation during cleanup.

`fetch_resolve` means the Fetch promise resolved and response headers became available. It does not prove that a response body was consumed, completed, or remained error-free. Instrument the actual decoder or reader loop when body-stream behavior is material.

Do not log raw request or response bodies, authorization headers, cookies, access tokens, or sensitive query values. Record compact, JSON-serializable, non-secret metadata only.

## Delivery and backlog

The collector's single `/ingest` endpoint accepts either one object or an exact `{"events": [...]}` envelope. Keep delivery simple:

- bound each serialized event and complete request body by bytes;
- preserve one array item for every logical event in a multi-event envelope;
- parse HTTP failures and collector responses instead of swallowing them;
- when the response reports `persistedEvents`, require it to match the submitted event count;
- keep any project-local queue bounded and observable enough to detect backlog;
- stop and mark the interval incomplete when serialization, send, payload-size, or persisted-count checks fail.

Do not require a universal retry algorithm. If the project's logger retries, preserve its documented semantics and avoid retrying a request when doing so could duplicate evidence. When exact-once delivery is not available, use stable event fields to recognize possible duplicates during analysis and report the limitation. The bundled collector does not maintain producer-specific replay or deduplication state.

For a stream that continues producing, close the evidence window at the planned natural checkpoint:

1. emit the `observation-checkpoint` sentinel from the real dispatch, decoder, or reader-loop boundary;
2. snapshot the source occurrence count available to that producer;
3. wait only for the selected logger's ordinary completion signal when it has one;
4. verify the checkpoint and available persisted count in NDJSON;
5. detach the temporary probe using the application's normal cleanup path;
6. Freeze the collector only after the checkpoint evidence has arrived when a stable analysis view is needed.

Do not expose an instrumentation-only helper through `window` or `globalThis`, and do not ask the user to evaluate console JavaScript merely to close the evidence window.

## Long-lived response and event streams

For SSE, WebSocket, subscriptions, long polling, or `ReadableStream` bodies, instrument the existing application dispatch, decoder, or reader-loop boundary. Do not make evidence completion depend on the business stream closing.

Record:

- connection/request start and headers/open;
- every source-event occurrence at each active probe with a monotonic domain `streamSequence` in bounded `data`, alongside the correlation-scoped top-level logging `sequence`;
- reconnect and attempt/version changes;
- close, cancel, abort, decoder error, and reader error;
- one `observation-checkpoint` sentinel when the coverage plan's bounded condition is met.

Do not automatically clone, tee, or consume `response.body` merely to observe it. Those techniques can change backpressure, cancellation, buffering, and memory behavior. Add probes to the consumer the application already owns, or use an authoritative producer/server-side logger.

At the observation boundary, verify the sentinel and available generic persisted counts, then detach only the temporary debug producer. The business stream may remain open. If the collector is frozen before required events arrive, mark that interval incomplete; Resume applies only to a later observation interval.

## Lifecycle boundaries

Navigation, reload, page termination, and memory exhaustion are evidence-loss boundaries. When the reproduction crosses one:

1. Record a pre-boundary sentinel.
2. Let the selected logger complete its ordinary finite send while the page is alive when possible.
3. Confirm the sentinel in NDJSON or mark continuity inconclusive.
4. Use an authoritative server logger or a newly initialized page logger on the other side.
5. Correlate both sides with an existing durable flow, operation, or request identifier.

Do not rely on `sendBeacon` or `keepalive` as proof that evidence persisted across navigation. They may be appropriate application mechanisms, but the analysis may claim only what the collector or authoritative logger actually recorded.

Collector Freeze/Resume state is not page-local. A new or reloaded page must read current session state before a deliberate pass; reloading does not Resume the collector.

## Observer cost and security

- Select probe locations whose full occurrence volume is acceptable. Do not activate a render or loop probe unless every occurrence can be emitted; once active, never suppress later occurrences.
- Bound URLs, strings, arrays, nested fields, and stacks.
- Record hashes, counts, enums, status, duration, attempt, version, and selected fields.
- Avoid objects whose serialization invokes getters, cycles, or application behavior.
- Monitor the selected logger's queue or error signal during expected peak traffic before consuming a rare reproduction opportunity.
- Bind the collector to loopback, keep operator tokens out of instrumentation, and never expose it publicly.
- Post directly to the collector when reachable; do not create an app-local proxy only for temporary browser logs.

## Browser coverage gate

Before the failing run, require:

- [ ] The plan identifies page-lifecycle boundaries and a realistic continuity strategy.
- [ ] The selected project/host logger or target-runtime HTTP adapter is actually called by every active browser probe.
- [ ] Every debug-only helper reference resolves from its actual importer to the intended existing target in each applicable browser and SSR build.
- [ ] Setup, HMR, remount, and cleanup leave one intended copy of each wrapper, listener, subscription, and timer.
- [ ] One bounded test event reached the active collector and was removed before the deliberate run when necessary.
- [ ] Each active probe emits one immutable event per source occurrence, with bounded payload fields and visible failures.
- [ ] A multi-event envelope preserves one array item and one NDJSON record per logical event.
- [ ] Parent flow, operation, child request, attempt, and ordering fields are available without changing request semantics.
- [ ] Collector and dashboard URLs cannot recurse through application `fetch` instrumentation.
- [ ] Expected peak event and byte volume can drain without unbounded product-side backlog.
- [ ] Collector state is live before the deliberate run.
- [ ] Every long-lived flow has a natural observation checkpoint and does not depend on business-stream termination.
- [ ] Reload, navigation, termination, and memory-loss boundaries are covered or declared residual.
- [ ] Sensitive request fields are excluded.
- [ ] Flow start, pre-boundary when applicable, and the configured terminal or observation-checkpoint sentinel are planned.
- [ ] Instrumented client code passes the narrowest relevant syntax, type, build, or test check.

Dashboard visibility is not part of this gate. Auto-open, live polling, Freeze/Resume, Clear, Stop, IDE selection, synchronized locations, source opening, log detail, metrics, and responsive frontend interactions remain available operator features, but none proves event delivery by itself.
