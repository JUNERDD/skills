---
name: debug
description: Evidence-first runtime debugging that maximizes the probability of identifying an application bug's root cause in a single reproduction. Use for bugs, regressions, flaky or timing-sensitive failures, expensive or hard-to-repeat reproductions, and requests such as "instrument broadly", "consider every plausible cause", "capture more breakpoints", or "find the root cause in one run". Build a broad but deduplicated causal hypothesis set, map hypotheses to structured high-information probes across boundaries, branches, state transitions, asynchronous work, caches, and external calls, collect correlated NDJSON evidence with the bundled local collector, summarize large logs without loading the full file into context, prove the causal chain, apply the smallest fix, verify with before-and-after evidence, and remove temporary instrumentation.
---

# Debug

Use runtime evidence to prove where invalid state originates, how it propagates, and where it becomes the reported symptom. Treat code reading, tests, and static analysis as hypothesis inputs rather than runtime proof.

Optimize for **information gained per reproduction**, not raw log count. A large set of low-value or high-frequency logs can hide the cause, perturb timing, exhaust context, and create a new failure.

## Select the mode

- Use **one-shot mode** when reproduction is expensive, flaky, destructive, slow, environment-specific, available only to the user, or explicitly requested as a single-pass investigation.
- Use **standard mode** when reproduction is cheap and iterative narrowing is safer.
- In one-shot mode, do not impose an arbitrary 3-5 hypothesis or 2-6 probe cap. Enumerate until every plausible subsystem and causal boundary is represented, then merge hypotheses that the same observation would confirm or reject.

Read [one-shot-debugging.md](./references/one-shot-debugging.md) before planning a one-shot pass. Read [runtime-debugging.md](./references/runtime-debugging.md) before starting or operating the bundled collector. Read [root-cause-document.md](./references/root-cause-document.md) before creating or updating the investigation document.

## Workflow

1. **Define the failure contract.** Record the expected behavior, observed behavior, smallest realistic reproduction, affected environment, occurrence rate, last-known-good boundary, and reproduction cost. State assumptions explicitly.
2. **Build a causal map.** Trace the symptom backward through outputs, state transformations, branches, async boundaries, caches, persistence, external dependencies, configuration, and inputs. Identify where a correct value can first become incorrect.
3. **Enumerate and deduplicate hypotheses.** Cover the cause families in [one-shot-debugging.md](./references/one-shot-debugging.md). Keep distinct causes separate when they require different evidence; merge only observationally equivalent variants.
4. **Create a hypothesis-probe matrix.** For every hypothesis, record confirming evidence, falsifying evidence, affected boundary, probe IDs, expected event order, and runtime-volume risk. Create the investigation document at this stage in one-shot mode so the full plan survives context compaction.
5. **Design a high-information probe graph.** Prefer shared probes that discriminate several hypotheses. Cover flow start/end sentinels, boundary entry/exit, branch decisions, state before/after mutation, async schedule/start/finish, cache read/write, external request/response metadata, exception/fallback paths, and invariants. Add probes until the matrix has no material blind spot.
6. **Control observer cost before editing.** Estimate event cardinality for each probe. Apply first-N, once-per-key, change-only, anomaly-only, aggregate, or sampled logging to loops and hot paths. Capture bounded scalars, IDs, lengths, hashes, versions, and selected fields rather than full objects.
7. **Establish the session.** Reuse authoritative logging configuration when supplied. Otherwise start the local collector with `scripts/debug_session.py start`; use headless mode by default. Treat the resulting ready file as authoritative for endpoint, session ID, log path, token, and owned artifacts.
8. **Instrument without changing behavior.** Use stable `probeId` values and include `runId`, `correlationId`, `sequence`, `hypothesisIds`, `location`, `phase`, `event`, `timestamp`, and bounded `data`. Keep logging non-blocking and failure-tolerant; use the bounded batch endpoint for bursty probes. Sync the complete active location set after edits.
9. **Pass the coverage gate.** Before requesting reproduction, verify collector health, clear stale logs, confirm the current endpoint is embedded in temporary instrumentation, and ensure every material hypothesis has a confirming or falsifying observation. Ensure async and cross-service paths have correlation IDs and start/end sentinels.
10. **Collect one clean run.** Ask the user for one smallest realistic reproduction and stop until completion. Do not mix exploratory runs into the same `runId`.
11. **Summarize before reading raw volume.** Run `scripts/summarize_debug_log.py` on the active NDJSON file, filter by run and correlation, inspect missing probes or sequence gaps, then open only the raw entries needed to prove or reject each hypothesis.
12. **Prove the causal chain.** Mark every hypothesis `CONFIRMED`, `REJECTED`, `INCONCLUSIVE`, or `NOT_REACHED`. Do not equate correlation with root cause: cite evidence for the originating condition, its propagation, and the final symptom. Update the same investigation document without deleting earlier rejected paths.
13. **Apply the smallest proven fix.** Keep useful probes active. Remove speculative code associated with rejected hypotheses instead of accumulating guards and fallbacks.
14. **Verify with a separate run.** Check collector health, refresh stale endpoints if needed, clear logs, use a distinct `runId`, reproduce the same flow, and compare before/after evidence and invariants.
15. **Clean up deterministically.** Remove all temporary probes and debug-only constants only after verification succeeds. Sync an empty location set, stop the collector with `scripts/debug_session.py stop`, delete owned artifacts, and handle the investigation document according to [root-cause-document.md](./references/root-cause-document.md).

If the first run is inconclusive, preserve the evidence and investigation ledger. Add only probes that close identified blind spots; do not repeat a rejected path without new contradictory evidence.

## Instrumentation contract

Use this logical event shape. Keep backward-compatible singular `hypothesisId` only when the active session cannot accept `hypothesisIds`.

```json
{
  "sessionId": "checkout-1733456789000",
  "runId": "initial",
  "correlationId": "flow-8f31",
  "sequence": 12,
  "probeId": "cart.commit.before",
  "hypothesisIds": ["H-cache-stale", "H-race-overwrite"],
  "location": "src/cart.ts:118",
  "phase": "mutation",
  "event": "before_commit",
  "message": "cart state before persistence",
  "data": {"cartVersion": 7, "itemCount": 3, "payloadHash": "..."},
  "timestamp": 1733456789000
}
```

- Keep `probeId` stable across initial and verification runs.
- Increment `sequence` within each correlation scope; also capture monotonic time when the runtime exposes it.
- Use one probe for multiple hypotheses when the observation discriminates them; list every mapped hypothesis ID.
- Record absence safely with sentinels. A missing interior event is evidence only when the enclosing start/end or delivery probes prove the path and collector were active.
- Capture exception type, code, retry/attempt, and bounded causal metadata; do not dump full stack-local state indiscriminately.

## Guardrails

- Never promise that one reproduction will always identify the cause; maximize and report first-pass coverage instead.
- Never claim a root cause from code inspection or a single correlated value without propagation evidence.
- Never log secrets, credentials, tokens, raw authorization headers, passwords, API keys, payment data, or unnecessary PII.
- Never add unbounded logging or an unbounded client queue to loops, render paths, polling, streaming, or retry storms.
- Never let instrumentation block the product path or throw into application code.
- Never use sleeps, arbitrary delays, or `setTimeout` as the fix.
- Never retain speculative guards after their hypothesis is rejected.
- Never remove probes before post-fix evidence succeeds.
- Never analyze collector stdout when the NDJSON evidence file is available.
- Never create an app-local proxy solely to forward browser logs when the collector endpoint is directly reachable.
- Never leave temporary probes, stale collector endpoints, or collector-owned artifacts after successful cleanup.

## Visible handoffs

Before reproduction, show a concise hypothesis-family summary, the applied probe coverage, material observer-cost controls, and the exact reproduction steps. Keep the full matrix in the investigation document when it is large.

After reproduction, show hypothesis dispositions with cited probe evidence, the causal chain, the investigation-document path, the proven fix, and the verification request. After success, report verification and cleanup status without dumping the entire raw log.
