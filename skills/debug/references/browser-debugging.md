# Browser Debugging

Use this reference only when evidence originates in browser code, when the failure crosses navigation or reload, or when every application `fetch` lifecycle event must be auditable.

## Table of contents

- Transport choice
- Setup
- Flow correlation
- Custom probes
- Complete fetch capture
- Delivery and backlog
- Lifecycle boundaries
- Observer cost and security
- Browser coverage gate

## Transport choice

Prefer an authoritative host-provided browser logger when one exists. Otherwise copy `assets/browser-debug-transport.mjs` into a temporary project path that client code can import.

Use the bundled transport for high-frequency streams or complete page-lifetime `fetch` coverage. It provides:

- one serialized in-memory copy of each event until acknowledgement;
- byte-framed batches without an event-count cap;
- one collector request at a time;
- timeout and deterministic batch retry;
- deletion only after complete acknowledgement;
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
  onError(status) {
    console.error('[debug transport]', status)
  },
})
```

Do not log the dashboard token in product code. The ingest endpoints use the session ID; operator APIs remain token-protected and same-origin.

## Flow correlation

Keep each actual `fetch` call as a unique child correlation with sequence `1` for start and `2` for terminal outcome. Attach it to the reproduction-wide flow through `parentCorrelationId`, `operationId`, and an existing `requestId` when available:

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

It records method and a query-stripped URL by default. Do not add raw request or response bodies, authorization headers, cookies, access tokens, or sensitive query values. Use `mapRequest` only for compact, JSON-serializable, non-secret metadata.

Never instrument collector `/ingest`, `/ingest/batch`, `/api/*`, or dashboard traffic as application traffic. Keep both captured-native-fetch and URL-exclusion protections active.

Complete `fetch` capture is conditional: use it only when the failure contract requires every application request. For a localized non-network bug, prefer targeted boundary probes instead of wrapping global `fetch`.

## Delivery and backlog

The transport separates event count from network framing:

- Bound each serialized event with `maxEventBytes`.
- Bound each collector request with `frameBytes`.
- Keep one request active while allowing any number of application requests to enqueue evidence.
- Retry the same deterministic `batchId` after timeout; collector acknowledgement is idempotent.
- Keep `keepalive: false` for the steady stream.

Inspect:

```ts
const status = await debugTransport.getStatus()
```

Review `queuedEvents`, `queuedBytes`, `inFlightRequests`, `failedRequests`, `rejectedEvents`, `deliveryScope`, and `reloadSafe`. Before leaving the page:

```ts
restoreFetch()
const drained = await debugTransport.flush({ timeoutMs: 30_000 })
```

Claim page-lifetime delivery only when `drained` is true, `queuedEvents` is zero, `inFlightRequests` is zero, and no rejected or suppressed required event remains unexplained.

Stop the reproduction and report incomplete delivery when backlog grows without draining. Do not block the product path or silently discard required events to protect the collector.

## Lifecycle boundaries

Navigation, reload, page termination, and memory exhaustion are evidence-loss boundaries. When the reproduction crosses one:

1. Record a pre-boundary sentinel.
2. Restore wrapped APIs and drain the page-local queue while the page is alive.
3. Confirm zero backlog or mark continuity inconclusive.
4. Use an authoritative server logger or newly initialized page logger on the other side.
5. Correlate both sides with an existing durable flow, operation, or request identifier.

Do not claim that `sendBeacon`, `keepalive`, or the page-local queue provides authoritative cross-navigation continuity. A small teardown sentinel may use them only as supplemental evidence.

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
- [ ] Sensitive request fields are excluded.
- [ ] Flow start, pre-boundary when applicable, and terminal sentinels are planned.
- [ ] Instrumented client code passes the narrowest relevant syntax, type, or build check.

Dashboard visibility is not part of this gate.
