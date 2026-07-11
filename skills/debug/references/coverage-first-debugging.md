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
  "schemaVersion": "debug-plan/v1",
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
    "residualAmbiguities": []
  },
  "boundaries": [
    {
      "id": "B-commit",
      "invariant": "an older base version cannot overwrite a newer commit",
      "probeIds": ["save.commit.decision"]
    }
  ],
  "hypotheses": [
    {
      "id": "H-race-overwrite",
      "mechanism": "attempt A commits after B without a stale-generation guard",
      "boundaryIds": ["B-commit"],
      "confirmedBy": ["A commits after B from an older base version"],
      "rejectedBy": ["the commit path rejects every older base version"],
      "probeIds": ["save.commit.decision"],
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

Use these probe roles: `flow-start`, `flow-terminal`, `boundary`, `branch`, `state`, `async`, `external`, `exception`, `invariant`, or `observation`.

Write every probe location as a workspace-relative source path followed by a positive numeric line, for example `src/save.ts:88`. Revalidate after instrumentation moves a probe.

Keep `boundary.probeIds`, `hypothesis.probeIds`, and each probe's `boundaryIds` and `hypothesisIds` bidirectionally consistent. Run:

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

When the contract requires every application `fetch`, preserve every start and terminal lifecycle event during the covered page lifetime. Bound fields and transport frames rather than imposing an event-count cap. Follow [browser-debugging.md](./browser-debugging.md).

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
- [ ] Every hypothesis and probe mapping is bidirectionally consistent.
- [ ] Flow start and terminal sentinels exist.
- [ ] Correlation and ordering survive every relevant async or service boundary.
- [ ] Event cardinality, bytes, perturbation risk, and suppression visibility were reviewed.
- [ ] Sensitive fields are excluded or redacted.
- [ ] Logging is failure-tolerant and cannot block the product path.
- [ ] The plan validator succeeds.
- [ ] Instrumented code passes the narrowest relevant compile, type, or syntax check.
- [ ] Collector health, ingest acknowledgement, endpoint freshness, and expected-probe sync succeed.
- [ ] Browser or process lifecycle evidence-loss boundaries are covered or declared residual.
- [ ] The run ID is unique and stale evidence is cleared.

Do not include dashboard visibility in this gate. A dashboard can improve operator experience but does not prove evidence delivery.

## Post-run analysis

1. Summarize the exact run before reading raw volume.
2. Select the failing parent correlation, operation, request, and attempt.
3. Verify start/terminal sentinels, delivery continuity, queue drain, missing expected probes, suppression counters, and sequence gaps.
4. Evaluate every hypothesis against its confirming and rejecting evidence.
5. Identify the earliest invalid value, decision, ordering, or external result.
6. Trace it forward through boundaries to the observed symptom.
7. Separate root cause, enabling conditions, downstream effects, and residual ambiguity.
8. Read only the raw causal interval needed to cite proof.

If all instrumented boundaries are correct, add probes only inside the smallest unresolved interval. If the failing flow never reached the suspected subsystem, move upstream. Never repeat a rejected path without new contradictory evidence.
