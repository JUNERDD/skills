# Coverage-First Debugging

Use this reference to maximize the probability that one clean failing reproduction distinguishes every material root-cause hypothesis without overwhelming or perturbing the target.

## Table of contents

- Objective and stop rule
- Failure contract
- Causal map
- Material hypotheses
- Cause-family checklist
- Deduplication
- Coverage plan
- Probe graph
- Observer cost
- Long-lived flows
- Correlation and absence
- Coverage gate
- Post-run analysis

## Objective and stop rule

Optimize for discriminating evidence per reproduction, not hypothesis count or log count. Prefer one probe that separates several mechanisms over repeated snapshots that confirm only that the symptom exists.

Do not impose an arbitrary hypothesis or probe cap. Stop expanding the first-pass plan when all of these are true:

1. Every relevant causal boundary has an invariant and one or more planned observations.
2. Every material hypothesis names a concrete mechanism and has both confirming and rejecting evidence.
3. Every material hypothesis maps to probes that can distinguish it from adjacent causes.
4. Flow sentinels, correlation, ordering, observer cost, privacy, and transport continuity are covered.
5. Excluded cause families and residual ambiguities are explicit.

Treat a hypothesis as material only when code, architecture, runtime conditions, or authoritative incident facts make it plausible and it requires distinct evidence or a distinct repair. Do not generate speculative checklist entries merely to increase coverage counts.

Scale breadth continuously:

- For expensive, flaky, destructive, timing-sensitive, production-only, user-only, or uncertain reproduction opportunities, cover every material boundary before the first failing run.
- For cheap reproductions or severe observer risk, begin with the highest-value causal cuts, but use the same plan schema and gate. Record any deferred distinction as a residual ambiguity.
- When broad instrumentation could hide the bug, prefer invariant, ordering, and boundary probes with bounded payloads instead of abandoning coverage discipline.

## Failure contract

Record these facts before generating hypotheses:

| Field | Required content |
| --- | --- |
| Expected | Observable correct behavior |
| Observed | Exact failure |
| Trigger | Smallest realistic action or input sequence |
| Scope | Affected user, tenant, route, job, device, service, data, or environment |
| Frequency | Always, percentage, burst, first-run, after-idle, under load, and so on |
| Timing | Immediate, delayed, after retry, after navigation, or another boundary |
| Last known good | Version, date, configuration, schema, or deployment boundary |
| Reproduction cost | Low, medium, high, or single opportunity |
| Constraints | Actions, systems, data, identities, or fields that must not be changed or disclosed |
| Completion | A real terminal outcome, or a bounded observable checkpoint for an intentionally long-lived flow |

Convert vague symptoms into observable assertions. For example, replace “save is broken” with “the UI reports success for operation B, but a refresh reads persisted version A from the authoritative source.”

## Causal map

Trace backward from the symptom to authoritative input. Use a compact graph:

```text
input / user intent
  -> handler or ingress
  -> validation and state ownership
  -> transformation
  -> async or transport boundary
  -> cache / persistence / external effect
  -> response or event reconciliation
  -> observed symptom
```

For each boundary, record:

- The identity, value, decision, version, or ordering relationship that crosses it.
- The invariant that must hold before and after it.
- How a correct value could first become incorrect there.
- The observation that distinguishes this boundary from its neighbors.
- Whether a shared causal-cut probe can cover several paths.

Instrument causal cuts first: points every plausible path must cross. Add branch-specific probes only when a cut cannot distinguish alternatives.

## Material hypotheses

Enumerate breadth-first before ranking:

1. Generate direct mechanisms that could produce the symptom.
2. Move upstream one causal boundary at a time until reaching authoritative input, persisted state, configuration, or an external dependency.
3. Add applicable timing, lifecycle, concurrency, resource, environment, and deployment mechanisms.
4. Add compound hypotheses only when two individually valid behaviors must interact.
5. Ground every hypothesis in inspected code, architecture, or incident facts.
6. Define confirming and rejecting observations before assigning priority.
7. Rank after coverage, not before it.

Name a mechanism, not a category. Prefer “attempt 1 finishes after attempt 2 and overwrites generation 2 because the commit path does not reject stale generations” over “race condition.”

## Cause-family checklist

Cover only applicable families and record a reason for material exclusions:

- **Input and contract:** malformed, stale, duplicated, truncated, encoded, defaulted, coerced, schema-skewed, or unit/identity disagreement.
- **Control flow:** wrong branch, guard, flag, early return, retry, idempotency, fallback, swallowed exception, or apparent success.
- **State and lifecycle:** stale snapshot, initialization order, owner mismatch, missed reset, leaked state, lost update, double mutation, or work after teardown.
- **Timing and concurrency:** out-of-order completion, lock gap, TOCTOU, duplicate delivery, cancellation failure, missed event, debounce, throttle, deadline, or backoff interaction.
- **Cache and persistence:** wrong key, namespace, TTL, invalidation, replica lag, transaction boundary, partial write, schema migration, serialization, or cache/source disagreement.
- **Transformation:** dropped, renamed, rounded, reordered, merged, normalized, or version-dependent fields.
- **External dependency and I/O:** timeout, partial or semantically invalid success, retry amplification, rate limit, proxy, filesystem, queue, webhook, or dependency drift.
- **Configuration and environment:** flag, permission, locale, path, runtime, region, build, deployment, or configuration refresh skew.
- **Security and identity:** wrong principal, tenant, scope, session rotation, authorization cache, impersonation, or row-level policy.
- **Resource and pressure:** memory, pool, thread, file descriptor, queue, payload, storage, backpressure, load shedding, timeout budget, or instrumentation overhead.
- **UI and event systems:** duplicate handlers, stale closures, reconciliation, hydration, propagation, focus, composition, navigation, or stale async commits.
- **Build and dependency boundaries:** stale artifacts, generated code, module duplication, conditional exports, incompatible versions, or source/bundle mismatch.

## Deduplication

Keep hypotheses separate when the originating boundary, expected order, confirming value, responsible owner, or required repair differs.

Merge variants when the same probes would produce the same observations and the same repair would eliminate them. Preserve merged variants in a note so contradictory evidence can reopen them.

Do not discard a material hypothesis merely because it is low priority. Map it to a shared boundary or invariant probe when marginal observer cost is small; otherwise record the residual ambiguity.

## Coverage plan

Create one JSON file inside the authorized workspace scratch area. Use it as the authority for plan validation, collector location synchronization, and expected-probe analysis.

Use this shape:

```json
{
  "failureContract": {
    "expected": "UI success means the latest operation is durable",
    "observed": "refresh returns an older version",
    "trigger": "submit A, then B during network jitter",
    "scope": "save flow in test environment",
    "frequency": "intermittent under overlapping requests",
    "timing": "attempt A may complete after attempt B",
    "lastKnownGood": "unknown; capture source and build revision",
    "reproductionCost": "high",
    "constraints": ["do not record payload bodies"]
  },
  "excludedCauseFamilies": [
    {
      "family": "security-and-identity",
      "reason": "the inspected fixture has one fixed local identity and no authorization boundary"
    }
  ],
  "run": {
    "runId": "initial",
    "reproductionOwner": "agent",
    "steps": ["seed version 7", "submit A then B", "refresh after terminal events"],
    "completion": {"mode": "flow-terminal"}
  },
  "boundaries": [
    {
      "id": "B-commit",
      "invariant": "an older base version cannot overwrite a newer commit"
    }
  ],
  "hypotheses": [
    {
      "id": "H-race-overwrite",
      "mechanism": "attempt A commits after B without a stale-generation guard",
      "boundaryIds": ["B-commit"],
      "confirmedBy": ["A commits after B from an older base version"],
      "rejectedBy": ["the commit path rejects every older base version"],
      "status": "PENDING"
    }
  ],
  "probes": [
    {
      "probeId": "flow.start",
      "location": "src/save.ts:10",
      "event": "flow_start",
      "role": "flow-start",
      "boundaryIds": [],
      "hypothesisIds": [],
      "expectedEvents": ["exactly one per failing flow"],
      "volumeControl": "required sentinel; never sampled",
      "dataFields": ["flowId", "sourceRevision"],
      "redactions": []
    },
    {
      "probeId": "save.commit.decision",
      "location": "src/save.ts:88",
      "event": "commit_decision",
      "role": "invariant",
      "boundaryIds": ["B-commit"],
      "hypothesisIds": ["H-race-overwrite"],
      "expectedEvents": ["once per save attempt"],
      "volumeControl": "bounded selected fields",
      "dataFields": ["operationId", "baseVersion", "currentVersion", "accepted"],
      "redactions": ["hash record identity"]
    },
    {
      "probeId": "flow.terminal",
      "location": "src/save.ts:120",
      "event": "flow_terminal",
      "role": "flow-terminal",
      "boundaryIds": [],
      "hypothesisIds": [],
      "expectedEvents": ["exactly one per completed flow"],
      "volumeControl": "required sentinel; never sampled",
      "dataFields": ["flowId", "outcome", "queuedEvents"],
      "redactions": []
    }
  ],
  "coverage": {
    "causeFamiliesReviewed": true,
    "observerCostReviewed": true,
    "privacyReviewed": true,
    "transportChecked": true,
    "correlationChecked": true,
    "residualAmbiguities": []
  }
}
```

Use these probe roles: `flow-start`, `flow-terminal`, `observation-checkpoint`, `boundary`, `branch`, `state`, `async`, `external`, `exception`, `invariant`, or `observation`.

Omitting `run.completion` preserves the default `flow-terminal` requirement. For an intentionally long-lived flow, set `run.completion` to `{"mode":"observation-checkpoint","condition":"<bounded observable stop condition>"}` and include an `observation-checkpoint` sentinel. The checkpoint closes only the evidence window; it does not claim that the business stream terminated.

Write every probe location as a workspace-relative source path followed by a positive numeric line, for example `src/save.ts:88`. Revalidate after instrumentation moves a probe.

Map every boundary and hypothesis from at least one probe through `boundaryIds` and `hypothesisIds`. Run:

```bash
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_plan.py validate <PLAN_FILE>
```

Do not claim the coverage gate passed when validation fails. Update the same plan rather than creating divergent location or expected-probe lists.

## Probe graph

Use stable semantic probe IDs.

- **Flow sentinels:** record start and terminal outcome so missing interior events are interpretable.
- **Boundary pairs:** capture compact identity, version, hash, and invariant fields on both sides of transformations, service calls, persistence, and caches.
- **Branch probes:** record the selected branch and bounded operands that determined it.
- **State probes:** capture before/after versions, ownership, mutation reason, selected diffs, and invariant results.
- **Async probes:** capture schedule, start, finish, cancel, timeout, retry, attempt, generation, task identity, and monotonic time.
- **External probes:** capture operation class, destination class, request identity, attempt, timeout budget, semantic result, duration, and bounded error metadata.
- **Exception probes:** capture type/code, handling branch, retry/fallback decision, and whether the error became visible or apparent success.
- **Invariant probes:** record invariant name, pass/fail, compact operands, and owning boundary.

## Observer cost

Estimate dynamic events and bytes, not static statement count. Prefer:

- once per correlation, identity, version, or state change;
- invariant failures and selected branch decisions;
- end-of-flow aggregates with recorded and suppressed counts;
- deterministic sampling by correlation only when the failing flow remains represented;
- bounded strings, arrays, stack depth, and canonical non-secret hashes;
- byte-framed transport and explicit backlog monitoring.

Never silently suppress all evidence from a required probe. Record the control in `volumeControl` and emit enough metadata to distinguish absence from suppression.

When the contract requires every application `fetch` or every source event from a real-time flow, preserve every required event during the covered page lifetime. Bound fields and transport frames rather than imposing an event-count cap. Follow [browser-debugging.md](./browser-debugging.md).

## Long-lived flows

Treat SSE, WebSocket, subscription, long-poll, and `ReadableStream` flows as first-class when they are intentionally open:

1. Distinguish connection/request state from evidence delivery. A browser Network-panel `Pending` row can be a live business stream or an unacknowledged debug frame; it is not itself proof of a stall or lost event.
2. Instrument the real dispatch, decoder, or reader loop. Record open/headers, every required source event with a monotonic source sequence, reconnect, close, cancel, error, and the configured observation checkpoint. Do not clone, tee, or consume a response body merely to observe it when that would change backpressure, cancellation, or memory behavior.
3. Choose a checkpoint condition tied to an observable assertion, event count, protocol state, operator action, or justified product deadline. Do not wait for an intentionally open business stream to terminate.
4. At the checkpoint, snapshot the debug transport's current event watermark and wait only until that complete FIFO prefix is acknowledged. Let later events continue to enqueue. Require zero required-event rejections and no source or transport sequence gap through the target watermark.
5. Use a final queue-empty flush only after the producer is stopped. If reload, navigation, process loss, memory exhaustion, or unavailable durable storage can discard an unacknowledged event, use an authoritative producer/server-side logger or mark continuity incomplete.

No finite page-local memory queue can guarantee an unbounded producer across every lifecycle failure. The enforceable contract is: never intentionally count-cap, sample, overwrite, or delete a successfully serialized required event before acknowledgement; never claim a wider lossless interval than the acknowledged continuous prefix proves.

## Correlation and absence

Use a hierarchy that preserves both flow grouping and local ordering:

```text
runId
  -> parentCorrelationId / flowId
      -> operationId
          -> requestId or child correlationId
              -> attempt / generation / sequence
```

Reuse existing identifiers. Do not introduce headers or parameters that alter preflight, caching, routing, signing, or authorization behavior merely to improve logging.

Do not infer strict distributed order from wall-clock timestamps alone. Capture wall time for cross-process alignment and monotonic time for local duration and ordering.

Treat a missing probe as evidence only when flow sentinels, collector continuity, enclosing branch or boundary execution, current source locations and endpoint, transport acknowledgement, and suppression metadata prove it should have arrived. Otherwise mark it `INCONCLUSIVE` or `NOT_REACHED`.

## Coverage gate

Before the first failing reproduction, require:

- [ ] The failure contract and reproduction owner are precise.
- [ ] Applicable cause families were reviewed and every exclusion has a reason.
- [ ] Every relevant causal boundary has an invariant and mapped probe.
- [ ] Every material hypothesis has both confirming and rejecting evidence.
- [ ] Every boundary and hypothesis is covered by at least one probe, and every probe reference resolves.
- [ ] A flow-start sentinel and the configured flow-terminal or observation-checkpoint sentinel exist.
- [ ] Correlation and ordering survive every relevant async or service boundary.
- [ ] Event cardinality, bytes, perturbation risk, and suppression visibility were reviewed.
- [ ] Sensitive fields are excluded or redacted.
- [ ] Logging is failure-tolerant and cannot block the product path.
- [ ] The plan validator succeeds.
- [ ] Instrumented code passes the narrowest relevant compile, type, or syntax check.
- [ ] Collector health, ingest acknowledgement, endpoint freshness, and expected-probe sync succeed.
- [ ] Required source and transport sequences, acknowledgement watermarks, and browser/process lifecycle evidence-loss boundaries are covered or declared residual.
- [ ] The run ID is unique and stale evidence is cleared.

Do not include dashboard visibility in this gate. A dashboard can improve operator experience but does not prove evidence delivery.

## Post-run analysis

1. Summarize the exact run before reading raw volume.
2. Select the failing parent correlation, operation, request, and attempt.
3. Verify the start and configured completion sentinels, acknowledged delivery prefix, missing expected probes, required-event rejections, suppression counters, and source/transport sequence gaps. Require a queue-empty drain only when production has stopped.
4. Evaluate every hypothesis against its confirming and rejecting evidence.
5. Identify the earliest invalid value, decision, ordering, or external result.
6. Trace it forward through boundaries to the observed symptom.
7. Separate root cause, enabling conditions, downstream effects, and residual ambiguity.
8. Read only the raw causal interval needed to cite proof.

If all instrumented boundaries are correct, add probes only inside the smallest unresolved interval. If the failing flow never reached the suspected subsystem, move upstream. Never repeat a rejected path without new contradictory evidence.
