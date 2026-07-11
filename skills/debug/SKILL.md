---
name: debug
description: Coverage-first runtime debugging that maximizes the chance that one failing reproduction proves an application bug's root cause. Use for bugs, regressions, flaky or timing-sensitive failures, expensive or user-only reproductions, unclear runtime behavior, and requests to instrument broadly, capture causal boundaries, collect sufficient logs in one pass, or prove a root cause from runtime evidence. Build a code-grounded causal map, validate a machine-readable hypothesis-and-probe plan, collect correlated evidence with bounded observer cost, prove origin-to-symptom propagation, repair only when authorized, verify separately, and remove temporary instrumentation.
---

# Debug

Maximize information gained per failing reproduction. Treat code reading, tests, static analysis, and existing telemetry as hypothesis inputs; require runtime evidence to prove the originating fault, its propagation, and the reported symptom.

Use one **coverage-first** workflow. Scale probe breadth with reproduction cost, residual ambiguity, privacy risk, and observer cost. Treat “one pass” as the initial failing reproduction only; allow a targeted blind-spot run and a separate post-repair verification run when needed.

## Read selectively

- Read [coverage-first-debugging.md](./references/coverage-first-debugging.md) before creating the causal map, hypotheses, or coverage plan.
- Read [runtime-debugging.md](./references/runtime-debugging.md) before resolving the plan validator, starting a session, or operating the bundled collector.
- Read [browser-debugging.md](./references/browser-debugging.md) only for browser instrumentation, complete application-`fetch` capture, high-frequency client streams, or page-lifecycle boundaries.
- Read [root-cause-document.md](./references/root-cause-document.md) before creating or updating a durable investigation ledger.

## Workflow

1. **Confirm scope and authority.** Determine whether the request is diagnosis-only or includes repair, whether temporary instrumentation is allowed, and whether the agent, user, or an external operator owns reproduction. Reproduce autonomously when it is safe and in scope; request user action only when their environment, credentials, device, or judgment is required.
2. **Define the failure contract.** Record expected and observed behavior, smallest realistic trigger, affected scope and environment, frequency, timing, last-known-good boundary, reproduction cost, and constraints. Convert the symptom into observable assertions.
3. **Inspect before instrumenting.** Read the relevant execution path, tests, configuration, deployment boundaries, and existing logs. Reuse authoritative trace, request, operation, job, transaction, and version identifiers when available.
4. **Build the causal map.** Trace backward from the symptom through outputs, state transitions, branches, async boundaries, persistence, caches, dependencies, configuration, and inputs. Mark causal cuts and the earliest boundary where a correct value can become incorrect.
5. **Enumerate material hypotheses.** Cover applicable cause families, name concrete falsifiable mechanisms, and merge only observationally equivalent variants. Treat a hypothesis as material when it is code- or architecture-grounded and requires distinct evidence or a distinct repair. Record unsupported families as exclusions rather than inventing probes.
6. **Create the coverage plan.** Write one `debug-plan/v1` JSON file containing the failure contract, reviewed cause-family exclusions with reasons, reproduction owner and steps, causal boundaries, hypotheses, probes, observer controls, privacy review, transport checks, and residual ambiguities. Use the same file for validation, location sync, and expected-probe analysis. If writes are not authorized, present the plan without claiming the coverage gate passed.
7. **Validate the plan.** Run `scripts/debug_plan.py validate <PLAN_FILE>` with the resolved Python 3 interpreter. Require every material hypothesis to define both confirming and rejecting evidence, every hypothesis and boundary to map to probes, flow start and terminal sentinels, and every gate flag to pass. Fix validation errors before editing product code.
8. **Design high-information probes.** Prefer shared causal-cut and invariant probes over repeated snapshots. Cover boundary entry/exit, branch decisions, state before/after mutation, async schedule/start/finish/cancel, cache and persistence operations, external calls, exception/fallback paths, and flow sentinels as applicable.
9. **Bound observer cost.** Estimate dynamic event count and bytes. Apply change-only, once-per-key, anomaly-only, aggregation, deterministic sampling, or other documented controls only when they preserve required evidence. Bound payloads, redact sensitive data, and make serialization and delivery failure-tolerant. Follow the browser reference when complete `fetch` lifecycle coverage is required.
10. **Establish and instrument the session.** Reuse authoritative logging configuration or start the bundled collector. Use stable probe IDs and a correlation hierarchy such as `runId -> parentCorrelationId/flowId -> operationId -> requestId/attempt`. Do not add a correlation header when it could change CORS, cache, routing, or product behavior; prefer existing IDs or side-channel metadata.
11. **Pass the runtime gate.** Validate the plan again, run the narrowest relevant compile/typecheck/test for the instrumentation, verify collector health and ingest acknowledgement, sync locations from the plan, confirm transport capacity and lifecycle continuity, clear stale logs, and use a unique run ID. Treat the dashboard as optional operator UX, never as an evidence prerequisite.
12. **Collect one clean failing run.** Execute or hand off the exact reproduction steps. Keep setup traffic and exploratory activity outside the run. Preserve deterministic fault seeds and authoritative before-state when the reproduction uses controlled timing or dependency failures.
13. **Summarize and classify.** Run the bundled summarizer with the plan as `--expected-probes-file`, filter by run and correlation hierarchy, inspect sentinels, missing probes, suppression counters, queue drain, sequence gaps, and residual ambiguities, then read only the raw events needed to mark every hypothesis `CONFIRMED`, `REJECTED`, `INCONCLUSIVE`, or `NOT_REACHED`.
14. **Prove or narrow.** Claim a root cause only when evidence identifies the earliest invalid state, decision, ordering, or external result and traces it through propagation to the symptom. If evidence is insufficient, preserve the ledger and add only probes that close the smallest unresolved causal interval.
15. **Respect the requested terminal condition.** For diagnosis-only work, preserve requested evidence, remove temporary instrumentation and owned runtime artifacts, then report the proven cause and a causally sufficient repair recommendation without changing behavior. When repair is authorized, eliminate the proven mechanism and restore the violated invariant at the owning boundary; reject smaller symptom masks that leave the mechanism active.
16. **Verify and clean up an authorized repair.** Keep discriminating probes for a separate post-repair run with a new run ID, compare the same invariants and probe IDs, then remove temporary instrumentation. Sync an empty location set only for an owned session, follow host ownership policy for shared sessions, stop owned collectors, and delete only owned ephemeral artifacts.

## Evidence contract

- Keep `probeId` stable across failing and verification runs.
- Require `runId`, `probeId`, `location`, `event`, and `timestamp` for every planned event.
- Require correlation and ordering fields whenever work crosses async, concurrent, process, service, queue, persistence, or browser-lifecycle boundaries.
- Record compact identities, versions, hashes, counts, branch operands, durations, attempts, and invariant results instead of full payloads or state trees.
- Interpret a missing interior event only when enclosing sentinels, collector continuity, current instrumentation, and suppression metadata prove that absence.
- Separate root cause, enabling conditions, downstream symptoms, and unresolved alternatives.

## Guardrails

- Never promise that one reproduction will always identify the cause; report first-pass coverage and residual ambiguity.
- Never equate correlation, overlap, or a single suspicious value with causation.
- Never log secrets, credentials, tokens, authorization headers, passwords, payment data, or unnecessary PII.
- Never let instrumentation block, throw into, or materially alter the product path.
- Never use sleeps, arbitrary delays, retries, guards, fallbacks, or coercions as a repair unless they eliminate the proven mechanism and restore the violated contract.
- Never apply a repair when the user requested diagnosis only.
- Never remove discriminating probes before authorized repair verification succeeds.
- Never analyze collector stdout when structured evidence is available, and never load an unbounded raw log before summarization.
- Never leave temporary probes, stale endpoints, collector-owned files, or debug-only transport code after successful cleanup.

## Visible handoffs

Before a user-owned reproduction, show the failure contract, concise hypothesis-family coverage, probe and observer-cost summary, residual ambiguities, and exact steps. After collection, show hypothesis dispositions with cited evidence, the origin-to-symptom chain or smallest unresolved interval, artifact paths, and the next authorized action. After verification, report invariant restoration and cleanup status without dumping the raw log.
