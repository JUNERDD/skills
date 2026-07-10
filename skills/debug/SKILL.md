---
name: debug
description: Evidence-first runtime debugging for application bugs, regressions, flaky or timing-sensitive failures, expensive reproductions, and high-frequency browser request streams. Use when asked to instrument broadly, record every fetch, capture causal boundaries, or prove a root cause from runtime evidence. Build and deduplicate hypotheses, map them to structured probes, collect correlated NDJSON through the bundled collector and page-local byte-framed browser transport, summarize evidence, prove propagation, repair the evidence-proven root cause, treat minimal change as a scope constraint only after causal sufficiency, verify separately, and remove temporary instrumentation.
---

# Debug

Use runtime evidence to prove where invalid state originates, how it propagates, and where it becomes the reported symptom. Treat code reading, tests, and static analysis as hypothesis inputs rather than runtime proof. Make eliminating the proven causal mechanism and restoring the violated invariant or contract the repair objective.

Treat change size as a constraint, not the objective. Among causally sufficient repairs, choose the narrowest safe, coherent scope. Never prefer a smaller workaround that leaves the proven causal mechanism active, and never add unrelated cleanup merely because the root-cause repair is already broad.

Optimize for **information gained per reproduction**, not raw log count. A large set of low-value logs can hide the cause, perturb timing, exhaust context, and create a new failure. When the investigation targets `fetch`, record every application `fetch` actually issued during the page lifetime; never sample, truncate, or cap those lifecycle events by count.

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
6. **Control observer cost before editing.** Estimate event cardinality for each probe. Apply first-N, once-per-key, change-only, anomaly-only, aggregate, or sampled logging to general loops and hot paths when that does not remove evidence required by the failure contract. For `fetch` investigations, exempt actual application `fetch` lifecycle events from count-based suppression: capture every start and terminal outcome, bound only each event payload and transport frame by bytes, and redact sensitive fields.
7. **Establish the session.** Reuse authoritative logging configuration when supplied. Otherwise start the local collector with `scripts/debug_session.py start`; let it open the local dashboard automatically after HTTP readiness. Use `--no-open-dashboard` only for an explicitly headless, CI, container-only, or remote session. Treat the resulting ready file as authoritative for endpoint, dashboard status, session ID, log path, token, and owned artifacts. Distinguish an accepted OS open request from the stronger `dashboardFrontendOpenRecorded` page-load signal.
8. **Instrument without changing behavior.** Use stable `probeId` values and include `runId`, `correlationId`, `sequence`, `hypothesisIds`, `location`, `phase`, `event`, `timestamp`, and bounded `data`. For browser `fetch` or high-frequency streams, copy and configure `assets/browser-debug-transport.mjs`: it keeps one serialized in-memory copy of each event until acknowledgement, frames by bytes, uses one drain request at a time, retries a stuck request, and sends through the captured native `fetch` so collector traffic cannot instrument itself. Sync the complete active location set after edits.
9. **Pass the coverage gate.** Before requesting reproduction, verify collector health, clear stale logs, confirm the current endpoint is embedded in temporary instrumentation, and ensure every material hypothesis has a confirming or falsifying observation. Ensure async and cross-service paths have correlation IDs and start/end sentinels. For browser capture, confirm the reproduction does not require the in-memory queue to survive navigation, reload, or process termination; arrange another authoritative logger at such boundaries or mark continuity inconclusive. In a browser-capable local session, query state and require `dashboardFrontendOpenRecorded: true`; when it is false, run `debug_session.py open-dashboard`, re-query state, and make at most two fallback attempts. If the page still does not load, surface the exact dashboard URL and opener errors, then continue through CLI and NDJSON evidence rather than silently omitting the console or restarting a healthy collector.
10. **Collect one clean run.** Ask the user for one smallest realistic reproduction and stop until completion. Do not mix exploratory runs into the same `runId`.
11. **Summarize before reading raw volume.** Run `scripts/summarize_debug_log.py` on the active NDJSON file, filter by run and correlation, inspect missing probes or sequence gaps, then open only the raw entries needed to prove or reject each hypothesis.
12. **Prove the causal chain.** Mark every hypothesis `CONFIRMED`, `REJECTED`, `INCONCLUSIVE`, or `NOT_REACHED`. Do not equate correlation with root cause: cite evidence for the originating condition, its propagation, and the final symptom. Update the same investigation document without deleting earlier rejected paths.
13. **Repair the evidence-proven root cause.** Eliminate the causal mechanism and restore the violated invariant or contract for the full failure scope, not only the observed example. Apply scope minimization only after establishing causal sufficiency: choose the narrowest safe, coherent repair, include every causally necessary file or layer, and exclude unrelated cleanup. Keep useful probes active. Remove speculative code associated with rejected hypotheses instead of accumulating downstream guards and fallbacks.
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
- For transport-managed browser events, retain `transportId`, `transportSequence`, and `transportBatchId` so retries and ordering can be audited without imposing an event-count limit.

## Guardrails

- Never promise that one reproduction will always identify the cause; maximize and report first-pass coverage instead.
- Never claim a root cause from code inspection or a single correlated value without propagation evidence.
- Never log secrets, credentials, tokens, raw authorization headers, passwords, API keys, payment data, or unnecessary PII.
- Never impose an artificial count cap, first-N rule, sampling rule, or rate limit on actual application `fetch` lifecycle events when the investigation requires complete request coverage.
- Never claim that the page-local browser queue survives navigation, reload, process termination, or memory exhaustion.
- Never continue a reproduction while `queuedEvents` or `queuedBytes` grows without bound; stop and report incomplete delivery when the collector cannot drain it.
- Never let collector `/ingest`, `/ingest/batch`, or dashboard traffic pass through an instrumented global `fetch`; use the captured native `fetch` and URL exclusion together.
- Never use `keepalive: true` for the steady-state debug stream. Flush the acknowledged queue while the page is alive and surface any undrained events.
- Never let instrumentation block the product path or throw into application code.
- Never use sleeps, arbitrary delays, or `setTimeout` as the repair.
- Never ship a symptom-level workaround while the proven causal mechanism remains active.
- Never retain speculative guards after their hypothesis is rejected.
- Never remove probes before post-repair evidence succeeds.
- Never analyze collector stdout when the NDJSON evidence file is available.
- Never create an app-local proxy solely to forward browser logs when the collector endpoint is directly reachable.
- Never reopen the dashboard after `dashboardFrontendOpenRecorded` is true, and never exceed two fallback open attempts for one session.
- Never leave temporary probes, stale collector endpoints, or collector-owned artifacts after successful cleanup.

## Visible handoffs

Before reproduction, show a concise hypothesis-family summary, the applied probe coverage, material observer-cost controls, and the exact reproduction steps. Keep the full matrix in the investigation document when it is large.

After reproduction, show hypothesis dispositions with cited probe evidence, the causal chain, the investigation-document path, the proposed root-cause repair, why its scope is causally sufficient and no broader than necessary, and the verification request. After success, report verification and cleanup status without dumping the entire raw log.
