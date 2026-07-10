# One-Shot Debugging Strategy

Use this reference when one reproduction is expensive or when the user explicitly asks for broad first-pass instrumentation.

## Table of contents

- Objective
- Activation criteria
- Failure contract
- Causal map
- Hypothesis enumeration
- Cause-family checklist
- Deduplication rules
- Hypothesis-probe matrix
- Probe graph design
- Probe selection score
- Observer-cost controls
- Correlation and ordering
- Proving absence
- Data-capture rules
- Frontend and browser guidance
- Backend and distributed guidance
- Concurrency guidance
- Coverage gate
- Post-run analysis
- Common anti-patterns

## Objective

Maximize the probability that one clean reproduction contains enough evidence to identify the originating fault and its propagation path. Do not promise certainty. Report what percentage of material hypotheses and causal boundaries the instrumentation can distinguish before reproduction.

Treat "more logs" as a means, not the objective. Prefer 30 discriminating probes over 300 repeated snapshots of the same state. Add more probes whenever they close a real blind spot and control their dynamic event volume.

## Activation criteria

Use one-shot mode when any of these conditions applies:

- The user asks to find the cause in one run or to instrument broadly.
- The failure is intermittent, race-sensitive, destructive, or production-only.
- Reproduction requires a human, credentialed account, special data, a device, a long workflow, or an external system.
- Restarting the environment is costly.
- The bug disappears under iterative debugging.
- The next reproduction opportunity is uncertain.

Use standard iterative mode when reproduction is cheap and broad instrumentation would materially perturb timing or performance.

## Failure contract

Record these facts before generating hypotheses:

| Field | Required content |
| --- | --- |
| Expected | Observable correct behavior |
| Observed | Exact incorrect behavior or failure |
| Trigger | Smallest realistic action sequence |
| Scope | User, tenant, route, job, device, service, data set, or environment |
| Frequency | Always, percentage, burst, first-run-only, after-idle, etc. |
| Timing | Immediate, delayed, after retry, after navigation, under load, etc. |
| Last known good | Version, date, configuration, schema, or deployment boundary |
| Reproduction cost | Low, medium, high, or single opportunity |
| Constraints | Things the agent may not start, open, mutate, or disclose |

Convert vague symptoms into observable assertions. For example, replace "checkout is broken" with "the submit action emits request X, receives HTTP 200, but the persisted order omits line item Y and the UI returns to the cart."

## Causal map

Trace backward from the symptom and identify causal boundaries. Use a compact graph rather than a prose dump:

```text
user action
  -> event handler
  -> local state / validation
  -> request construction
  -> transport / retry
  -> API handler
  -> domain transformation
  -> cache / database / queue
  -> response transformation
  -> client reconciliation
  -> rendered symptom
```

For each edge, ask:

1. What value, decision, or timing relationship crosses this boundary?
2. What invariant should hold before and after it?
3. How could a correct value first become wrong here?
4. What observation would distinguish this boundary from its neighbors?
5. Can one probe cover several adjacent hypotheses without losing discrimination?

Instrument causal cuts: points that every plausible path must cross. Add branch-specific probes only where a cut cannot distinguish alternatives.

## Hypothesis enumeration

Enumerate breadth-first before ranking. Stop only when every plausible cause family and every causal boundary has at least one candidate or a documented reason for exclusion.

Use this sequence:

1. Start at the symptom and generate direct local causes.
2. Move one boundary upstream and generate causes that would produce the same local state.
3. Repeat until reaching authoritative input, persisted state, environment, or an external dependency.
4. Add cross-cutting timing, lifecycle, configuration, and resource hypotheses.
5. Mark compound hypotheses when two individually valid behaviors interact to create the bug.
6. Merge observationally equivalent hypotheses only after defining the evidence that would distinguish them.
7. Rank after coverage, not before it.

A hypothesis must be falsifiable and name a concrete mechanism. Reject statements such as "state issue" or "race condition". Prefer "the stale request from attempt 1 resolves after attempt 2 and overwrites the newer cart version because the reducer does not compare request generations."

## Cause-family checklist

Cover applicable families. Do not force irrelevant categories.

### Input and contract

- Missing, malformed, stale, duplicated, locale-dependent, truncated, or unexpectedly encoded input
- Schema/version mismatch
- Defaulting or coercion that changes meaning
- Validation performed at the wrong boundary
- Caller/callee disagreement over nullability, units, time zones, ordering, or identifiers

### Control flow

- Wrong branch, guard, feature flag, early return, fallback, or exception path
- A branch is not reached because an earlier condition consumes the flow
- Retry, deduplication, or idempotency path is selected incorrectly
- Error is swallowed and converted to apparent success

### State and lifecycle

- Stale closure, stale snapshot, missed reset, reused singleton, leaked state, or invalid initialization order
- State written in one owner and read from another
- Lost update, overwrite, double mutation, or mutation after disposal/unmount
- Derived state not invalidated after its source changes

### Timing and concurrency

- Out-of-order completion, race, lock gap, TOCTOU, missed wake-up, duplicate delivery, or cancellation failure
- Event emitted before listener registration
- Work runs before required initialization or after teardown
- Clock, timer, debounce, throttle, backoff, or deadline interaction

### Cache and persistence

- Wrong key, namespace, TTL, invalidation, read-after-write assumption, replica lag, transaction boundary, or serialization format
- Old schema or migration state
- Partial write or non-atomic multi-record update
- Cache and source-of-truth disagree

### Transformation and serialization

- Field dropped, renamed, rounded, clamped, reordered, merged, normalized, or converted incorrectly
- Numeric precision, Unicode, date/time, enum, or binary conversion
- Client/server serialization asymmetry
- A mapper uses the wrong source field or version

### External dependency and I/O

- Timeout, partial response, retry amplification, rate limit, connection reuse, DNS, proxy, filesystem, queue, or third-party behavior
- Success code with semantically invalid payload
- Dependency version or capability drift
- Callback/webhook duplication or reordering

### Configuration and environment

- Feature flag, environment variable, build mode, region, locale, permission, path, case sensitivity, runtime version, or deployment skew
- Configuration loaded once and not refreshed
- Different nodes or bundles run different code/schema versions

### Security and identity

- Wrong principal, tenant, scope, authorization cache, token audience, session rotation, impersonation, or row-level policy
- Identity changes between asynchronous steps
- Permission failure converted to empty data

### Resource and pressure

- Memory, file descriptor, thread, pool, queue, payload, storage, or rate limit
- Backpressure, dropped work, load shedding, timeout budget, or GC pause
- Logging or instrumentation itself changes scheduling or volume

### UI and event systems

- Duplicate handler, propagation/default behavior, stale DOM reference, controlled/uncontrolled mismatch, hydration, reconciliation key, focus, composition, or browser lifecycle
- Navigation/pagehide drops work
- Render commits a stale async result

### Build and dependency boundary

- Generated code, stale artifact, module duplication, tree shaking, conditional export, dependency upgrade, or ABI/API mismatch
- Source and deployed bundle differ
- Tests and runtime resolve different implementations

## Deduplication rules

Keep two hypotheses separate when any of these differs:

- Originating boundary
- Expected event order
- Confirming or falsifying value
- Responsible owner or component
- Required fix

Merge candidates when the same probes would produce the same observations and the same fix would address them. Preserve variants under one hypothesis note so they can be reopened if evidence diverges.

Do not discard low-priority hypotheses solely to reduce the table. Map them to shared boundary or invariant probes whenever the marginal observer cost is low.

## Hypothesis-probe matrix

Use this shape in the investigation document:

| ID | Mechanism | Boundary | Confirmed by | Rejected by | Probe IDs | Expected order | Volume risk | Priority | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `H-race-overwrite` | Attempt 1 overwrites attempt 2 | async completion -> reducer | older generation commits after newer generation | reducer rejects older generation or order never reverses | `request.start`, `request.finish`, `reducer.commit` | start1, start2, finish2, commit2, finish1, commit1 | medium | high | PENDING |

Requirements:

- Every material hypothesis must have both confirming and falsifying evidence.
- Every probe must map to at least one hypothesis or a causal-boundary sentinel.
- A shared probe may list multiple hypothesis IDs.
- Record expected absence only when enclosing sentinels prove execution and delivery.
- Mark hypotheses that cannot be distinguished in the planned run; add probes or state the residual ambiguity before reproduction.

## Probe graph design

Use stable probe IDs based on semantic location, not physical line number alone.

### Flow sentinels

Add a start and terminal probe for the reproduction flow. Include outcome and correlation ID. These prove that the run is complete and distinguish a missing interior event from an incomplete reproduction.

### Boundary pairs

Place entry/exit probes around transformations, service calls, persistence, cache operations, and async tasks. Capture the same compact identity/version fields on both sides so the agent can compare them.

### Branch probes

Log the selected branch plus the inputs that determined it. Do not log every condition separately when one decision record can show the evaluated operands and result.

### State-transition probes

Capture before/after versions, ownership, mutation reason, and invariant result. Prefer diffs, selected fields, lengths, and hashes over full objects.

### Async probes

Capture schedule, start, finish, cancel, timeout, retry, and commit. Include correlation, attempt, generation, task/thread identity, and monotonic time where available.

### External-call probes

Capture method/operation, destination class, request identity/hash, attempt, timeout budget, response status, semantic result, duration, and bounded error metadata. Redact credentials and payload content.

### Exception and fallback probes

Capture exception type/code, handling branch, retry/fallback decision, and whether the error becomes user-visible or is swallowed.

### Invariant probes

Log invariant name, pass/fail, compact operands, and owner boundary. Invariants often cover more hypotheses than raw snapshots.

## Probe selection score

Use this qualitative score when observer cost matters:

```text
value = hypothesis coverage x discriminating power x causal centrality x failure relevance
        -------------------------------------------------------------------------------
        runtime cost x expected event count x payload size x privacy risk x perturbation risk
```

Prioritize high-value probes first. Continue adding lower-cost probes until all material hypotheses are distinguishable. Do not use the score to justify an uninstrumented boundary in one-shot mode.

## Observer-cost controls

Estimate dynamic events, not just static probe count.

Use one or more controls for general hot paths when complete event coverage is not required by the failure contract:

- **First-N:** record only the first N events per run, correlation, probe, or key.
- **Once-per-key:** record the first event for each stable identity/version.
- **Change-only:** record when selected fields or a state hash changes.
- **Anomaly-only:** record invariant failures, unexpected branches, slow durations, retries, or stale generations.
- **Aggregate:** count repeated events and emit a summary at the end of the flow.
- **Sampling:** deterministic sampling by correlation or key; avoid random samples that may omit the failing flow.
- **Payload bounding:** cap strings, arrays, stack depth, and nested fields; store lengths and hashes.
- **Rate limiting:** emit a dropped-event counter so suppression is visible.
- **Byte framing:** combine queued events into request frames bounded by serialized bytes. Do not impose an event-count cap when complete `fetch` coverage is required.

Never silently suppress all evidence from a probe. Emit a compact summary with recorded and dropped counts.

For an investigation that must explain every application `fetch`, do not apply First-N, sampling, rate limiting, anomaly-only filtering, or count-based batching to `fetch_start` and terminal `fetch_resolve`/`fetch_reject` events. Record every actual call during the page lifetime. Control overhead by bounding fields, redacting secrets, keeping one serialized in-memory copy per event, and draining byte-framed requests with acknowledgement and retry.

## Correlation and ordering

Use a correlation ID that survives every relevant boundary. Reuse an existing request, trace, job, transaction, or session ID when safe; otherwise create a temporary debug correlation at flow start and propagate it only through temporary instrumentation.

Use `sequence` within a correlation scope. For distributed or concurrent systems, also capture:

- Wall-clock timestamp for cross-process alignment
- Monotonic timestamp or duration for local ordering
- Process/service/component
- Thread, task, worker, or actor identity when relevant
- Attempt/generation/version
- Parent correlation/span when work fans out

Do not infer strict causal order from wall-clock timestamps alone when clocks may differ.

## Proving absence

A missing log is ambiguous unless all of these are true:

1. The flow-start sentinel was recorded.
2. The collector remained healthy and accepted nearby events.
3. The enclosing branch or boundary was recorded.
4. The probe was present at the current source location and used the current endpoint.
5. The flow-end or an upstream terminating event was recorded.
6. Suppression counters show the event was not sampled or rate-limited away; for complete page-lifetime `fetch` capture, verify that no count-based suppression was configured and that the transport queue reached zero queued events before any navigation or reload.

Classify an otherwise missing probe as `INCONCLUSIVE` or `NOT_REACHED`, not automatically `REJECTED`.

## Data-capture rules

Prefer:

- Stable identifiers or redacted suffixes
- Schema/version/generation numbers
- Counts, lengths, booleans, enums, status codes, and durations
- Hashes of canonicalized non-secret payloads
- Selected before/after fields
- Error type/code and bounded message
- Branch operands and result
- Retry and cancellation metadata

Avoid:

- Full request/response bodies
- Full application state trees
- Raw user text, authorization data, cookies, tokens, secrets, or payment information
- Huge stack traces on every repeated event
- Objects whose serialization triggers getters, cycles, or behavior changes

Make logging serialization failure-tolerant. A debug probe must not throw into product code.

## Frontend and browser guidance

- Instrument user-event receipt, handler generation, state ownership, render/commit, request lifecycle, navigation/pagehide, and stale-result guards.
- Use direct collector requests when reachable; do not add a production API route only for temporary logs.
- Use `assets/browser-debug-transport.mjs` for high-frequency or complete page-lifetime `fetch` capture. It uses the native uninstrumented `fetch`, a single-copy in-memory queue, byte-framed acknowledged batches, timeout, and retry.
- Do not use `keepalive: true` for the continuous debug stream. Flush before intentional navigation; when a reproduction must cross navigation or reload, use an authoritative logger on both sides and do not claim that the browser queue provides continuity. Reserve a small beacon/keepalive request only for an optional teardown sentinel.
- Never instrument collector `/ingest`, `/ingest/batch`, or dashboard requests as application traffic.
- Avoid logging every render. Record relevant state-version changes, selected branches, and invariant failures.
- Distinguish event time, render time, effect time, request time, and commit time.
- Capture component/key identity when reconciliation or stale instances are plausible.

## Backend and distributed guidance

- Reuse trace/request/job identifiers when available.
- Instrument ingress, validation, domain transformation, persistence/cache, outbound calls, queue publish/consume, retry, and egress.
- Capture node/service/version to detect deployment skew.
- Record transaction and idempotency identities without sensitive data.
- For queues, capture message ID, attempt, enqueue/dequeue time, visibility/deadline, deduplication result, and terminal disposition.
- For databases, capture operation class, key/hash, transaction boundary, affected-row count, version, and duration; do not log raw sensitive rows.

## Concurrency guidance

For each potentially racing operation, capture:

- Creation/schedule sequence
- Start and completion sequence
- Generation/version at start and commit
- Cancellation request and acknowledgement
- Lock/lease ownership changes when safe
- Commit decision and reason

A race hypothesis is confirmed by an invalid ordering plus a missing or ineffective guard, not merely by overlapping timestamps.

## Coverage gate

Do not ask for the expensive reproduction until all applicable checks pass:

- [ ] The failure contract is precise.
- [ ] Every causal boundary is represented in the map.
- [ ] Every material hypothesis has confirming and falsifying observations.
- [ ] Every matrix row maps to one or more probe IDs.
- [ ] Flow start and terminal sentinels exist.
- [ ] Cross-service and async work has correlation and ordering metadata.
- [ ] Probe IDs are stable and source locations are synced.
- [ ] Hot paths have explicit volume controls and dropped-event visibility.
- [ ] Payloads are bounded and sensitive fields are excluded.
- [ ] Logging is non-blocking and failure-tolerant.
- [ ] The collector is healthy and the endpoint/session values are current.
- [ ] Old logs are cleared and the run ID is unique.
- [ ] The plan identifies any residual ambiguity that one run cannot resolve.

Report a compact coverage summary, for example: `14 hypotheses; 31 probes; 12 shared probes; 100% hypotheses mapped; 9 causal boundaries covered; 4 hot-path controls; 2 residual ambiguities.`

## Post-run analysis

1. Run the bundled summarizer before opening the full NDJSON file.
2. Select the exact run and failing correlation.
3. Verify start/end sentinels and collector continuity.
4. Check missing probe IDs, sequence gaps, suppression counters, and unexpected correlations.
5. Reconstruct the compact event timeline.
6. Evaluate every hypothesis against its confirming and falsifying evidence.
7. Identify the earliest invalid state or invalid ordering.
8. Trace that state forward to the symptom.
9. Separate root cause, enabling conditions, and downstream symptoms.
10. Inspect only the raw entries needed to cite proof.

If evidence shows the failing flow never reached the expected subsystem, move upstream. If evidence reaches a boundary with correct input and wrong output, localize inside that boundary. If all logged boundaries remain correct, add probes only inside the smallest unresolved interval.

## Common anti-patterns

- Generating many synonymous hypotheses without distinct falsifiers
- Logging every line instead of causal boundaries and invariants
- Counting static log statements but ignoring loop frequency
- Dumping entire objects and overwhelming the collector or model context
- Omitting correlation IDs in concurrent flows
- Treating missing logs as proof without sentinels
- Instrumenting only the suspected component and missing the upstream origin
- Fixing the first correlated anomaly without proving propagation
- Running several exploratory reproductions under one run ID
- Loading a large NDJSON file directly into model context before summarization
