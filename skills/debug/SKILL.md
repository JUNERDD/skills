---
name: debug
description: Coverage-first runtime debugging and repair from failure contract through root-cause proof, causal repair, separate verification, and cleanup, with loss-auditable all-occurrence event capture. Use to debug, troubleshoot, diagnose, investigate, fix, repair, resolve, or explain runtime bugs, regressions, flaky or timing-sensitive failures, long-lived streams, expensive or user-only reproductions, broad instrumentation, or bundled collector/dashboard operation. Treat debug/fix as end-to-end repair unless explicitly limited to diagnosis or recommendations. Reuse existing project debug instrumentation and collector sessions. Default each runtime run to a user handoff; use agent autonomy only when explicitly delegated for that run or remaining runs. Never let evidence-analysis requests rewrite reproduction ownership. Maintain one ledger through evidence, repair, verification, and cleanup.
---

# Debug

Maximize information gained per failing reproduction. Treat code reading, tests, static analysis, and existing telemetry as hypothesis inputs; require runtime evidence to prove the originating fault, its propagation, and the reported symptom.

Use one **coverage-first** workflow. Scale probe breadth with reproduction cost, residual ambiguity, privacy risk, and observer cost. Treat “one pass” as the initial failing reproduction only; allow a targeted blind-spot run and a separate post-repair verification run when needed.

## Non-negotiable event cardinality

- Once a probe is active for a run, emit exactly one immutable logical event for every execution occurrence of that probe. Preserve the contract `N source occurrences -> N queued events -> N persisted NDJSON records` through the acknowledged checkpoint; both missing and duplicate events violate it.
- Never sample, throttle, debounce, first-N, change-gate, once-per-key, anomaly-gate, aggregate, merge, coalesce, overwrite, deduplicate, or otherwise suppress active probe occurrences. Choose fewer or better probe locations before the run when observer cost is too high; never reduce occurrences after activating a probe.
- Bound fields, strings, arrays, stacks, and network-frame bytes without changing event count. A wire batch may carry multiple independently serialized events, but it must preserve their identities, ordering, and record count.
- Treat duplicate producer installation, serialization failure, byte rejection, queue loss, terminal collector discard, missing acknowledgement, or a source/transport sequence gap as an incomplete run. Never convert it into a silent no-op or successful capture.

## Existing debug process

- Inspect and continue project-owned debug instrumentation, transport, ledger, and the ledger's exact active collector session before creating anything. Repair the existing path when it violates this skill instead of adding a parallel emitter, transport instance, or collector.
- Treat a copied transport asset with no import or runtime use as absent. Prove that active probes call the shared transport and that collector state reports its acknowledged frames.
- Keep one browser transport instance per page realm and collector session through the bundled `getOrCreateBrowserDebugTransport` realm registry. Reuse it across hot reload. Give every wrapper, listener, timer, or other replaceable producer a stable realm-owned key, a token-safe release-then-reacquire lifecycle, and realm-persistent source sequence. Any acquisition while that key is active must fail before cleanup; HMR must release the current lease before reacquisition so it cannot stack producers, silently replace another source, let an old disposer remove the new owner, or reset occurrence identity.
- Before transport replacement, first detach its probe producers and call `flushAndStop()`. A successful drain terminalizes the complete run; a failed drain or forced `stop()` terminalizes it as incomplete. In either case a later acquisition must use a fresh `runId`; never reopen the terminal run or let old and new transports drain concurrently.

## Completion scope

- Treat a request to debug, troubleshoot, fix, repair, resolve, address, or make the failing behavior work as authorization for the full prove-repair-verify-cleanup loop. Do not ask for a second repair approval after proving the cause.
- Treat the work as diagnosis-only only when the user explicitly asks to diagnose, analyze, investigate, explain, collect evidence, recommend a fix, avoid edits, or otherwise stop before behavior changes.
- When repair is in scope, treat a root-cause finding or repair proposal as an intermediate update, not a terminal result. Continue until the causal mechanism is repaired, the original failure contract passes in a separate verification run, temporary instrumentation is removed, and owned artifacts are cleaned up.
- Keep one evolving investigation ledger whenever repair is in scope or the work crosses a reproduction handoff, context compaction, or multiple runs. Record the validated plan, evidence transitions, hypothesis dispositions, repair, verification, and cleanup in the same ledger. Omit the ledger only for short, agent-owned, diagnosis-only work that finishes in one turn.
- Treat lifecycle scope as `investigation > collector session > run`: one reported bug and its evolving ledger form the investigation; one collector session owns an exact ready file, endpoint, port, dashboard, and evidence file; each failing, blind-spot, or verification pass is a run with its own `runId`. A user reply, evidence-analysis turn, context compaction, repair transition, or new `runId` continues the same investigation and does not create a new collector session.
- On every continuation, read the current investigation ledger and run `scripts/debug_session.py resume --ready-file <READY_FILE>` with its exact active ready file before any `start`. If resume succeeds, reuse that collector and dashboard without calling `start` or reopening the dashboard. `resume` must not open browser UI, and session recovery must never scan the workspace for an arbitrary ready file. Start a replacement only when the recorded ready file is missing or its collector is unreachable, or when the user or host explicitly requires isolation or replacement; preserve prior evidence and record the session transition in the same ledger.
- Treat recording mode as collector-session state, not tab or run state. `Freeze` remains active across dashboard tabs, reloads, user replies, analysis turns, and new run IDs; `Clear` does not unfreeze it. Only an explicit recording Resume transition—the UI control or CLI `resume-recording`—reopens the collector write gate for a future recording generation.
- Pause for the default user-owned failing reproduction and post-repair verification, unavailable authority or dependency, or another concrete blocker. Treat each pause as a checkpoint and resume the same workflow when the blocker clears.

## Reproduction runs

- Scope `run.reproductionOwner` and `run.reproductionDelegation` to exactly `run.runId`. Default every new failing, blind-spot, and verification run to the user-handoff path unless a still-applicable explicit delegation covers it.
- Before the first failing run, enter the agent-autonomous path when the current user explicitly assigns the runtime investigation to the agent, for example, “have the agent investigate this” or “investigate this yourself.” Treat that pre-run assignment as `scope: "remaining-runs"` unless the user limits it to one run; do not require a separate instruction about reproduction.
- After a run completes, resume evidence analysis automatically. Treat “now have the agent investigate” or “analyze this” as an instruction to analyze the completed evidence, not as reproduction delegation. Never rerun, relabel, or change the owner of a completed run, and never change a future run owner from an evidence-analysis request.
- Change a future run from user ownership only when the current user explicitly delegates that future reproduction or verification, or explicitly delegates all remaining runtime runs. Create the new `runId` before applying the delegation; never apply it retroactively.
- For non-user ownership, store `run.reproductionDelegation` with `target`, `scope` (`single-run` or `remaining-runs`), `effectiveRunId` equal to the current `run.runId`, and `currentUserDirective` containing a faithful summary of the current user's instruction. Omit the object for user ownership. The validator checks structure and run consistency; the agent remains responsible for verifying the directive's source and scope.
- Never infer delegation from reproduction cost, deterministic tests or harnesses, agent capability, a headless environment, time pressure, user unavailability, or repository rules that prohibit agent-operated browser testing. Asking the user to reproduce in their own browser is not agent browser automation. If the user cannot reproduce but has not delegated an applicable future run, report the blocker.
- Keep reproduction ownership separate from dashboard startup. For a user-owned run on a browser-capable local host, leave dashboard auto-open enabled. Waiting for the user, lacking agent browser control, or prohibiting agent-operated product browsing is not a headless condition and never justifies `--no-open-dashboard` or `--headless`.
- Agent-run experiments may inform hypotheses before a user handoff, but they do not replace a required user-owned canonical run and must not be presented as the user's reproduction.
- Before planning another run, record the completed run's ID, purpose, owner, delegation, evidence, and status in the investigation ledger. Default post-repair verification to user ownership unless a still-applicable `remaining-runs` delegation or a new explicit verification delegation selects another owner. Use `external` only when the current user explicitly designates an external operator.
- A new `runId` never implies a new collector session. Reuse the ledger's active ready file across failing, blind-spot, and verification runs while that collector remains reachable.

## Mandatory user-reproduction output gate

If the current response asks the user to perform a reproduction, the response is invalid unless it renders as the exact Markdown structure below. Begin with `Dashboard:`; put no heading, greeting, readiness claim, or other prose before it. Never replace the actual URL with wording such as “opened successfully.” Emit the template as ordinary Markdown, not as a code block.

```markdown
Dashboard: <status> — <dashboardUrl-or-unavailable> (frontend confirmed: <true|false|unknown>; recording: <live|frozen|unknown>) [— error: <non-empty error>]

### Failure contract

- **Expected:** <expected behavior>
- **Observed:** <observed behavior>
- **Trigger:** <smallest realistic trigger>

### Coverage

- **Hypotheses:** <material hypothesis-family and mapped-coverage summary>
- **Probes and boundaries:** <probe count, shared probes, and causal-boundary coverage>
- **Observer controls:** <volume, privacy, and perturbation controls>

### Residual ambiguities

- <`None.` or one explicit ambiguity per bullet>

### Reproduction

1. <exact step>
2. <additional exact step when needed>
3. <exact checkpoint and host completion action, or reply `done`>
```

Derive the dashboard values mechanically: use `frontend_confirmed` and `true` when a URL exists and the frontend callback is recorded; `disabled` and `false` when a URL exists and auto-open is disabled; `frontend_not_confirmed` and `false` when a URL exists otherwise; and `unavailable`, `unavailable`, and `unknown` when no URL exists. Derive recording independently from authoritative collector state as `live`, `frozen`, or `unknown`; never infer it from frontend confirmation or collector health. Append the normalized error only when non-empty. Normalize embedded newlines in the dashboard status or error to spaces. For a newly established browser-capable local session, treat `disabled` as an accidental opt-out: run `open-dashboard`, refresh `dashboard-status`, and surface the refreshed line. If that bounded recovery fails, include its exact URL and error without blocking reproduction, even when the refreshed status remains `disabled`. For a healthy session recovered from the investigation ledger with `resume`, preserve its existing dashboard state, do not call `open-dashboard`, and surface the refreshed status and exact URL. Skip recovery and proceed directly with `disabled` when the collector host is verified to have no usable local graphical browser. Immediately before a deliberate recording pass, if `dashboard-status` reports `recording: frozen`, run `scripts/debug_session.py resume-recording --ready-file <READY_FILE>`, rerun `dashboard-status`, and require `recording: live` before handing off reproduction. Session `resume` only reuses and health-checks the collector; it never changes recording mode. If recording remains `unknown`, refresh authoritative state and report the exact error rather than claiming the gate is live.

Make `### Reproduction` the final section and stop for the user's completion signal. Before sending, verify that the first character begins `Dashboard:`, a blank line separates the dashboard paragraph and every subsequent section, the four headings appear exactly once in the shown order, every heading is followed by a blank line and its list, the URL is literal or `unavailable`, and no text follows the reproduction list. Do not rely on soft line breaks, trailing spaces, raw HTML, or renderer-specific behavior. Rewrite the response if any check fails.

## Read selectively

- Read [coverage-first-debugging.md](./references/coverage-first-debugging.md) before creating the causal map, hypotheses, or coverage plan.
- Read [runtime-debugging.md](./references/runtime-debugging.md) before resolving the plan validator, starting a session, or operating the bundled collector.
- Read [browser-debugging.md](./references/browser-debugging.md) only for browser instrumentation, complete application-`fetch` capture, long-lived or high-frequency client streams, or page-lifecycle boundaries.
- Read [root-cause-document.md](./references/root-cause-document.md) before creating or updating the investigation ledger.

## Workflow

1. **Resolve scope and authority.** Apply the completion-scope and reproduction-run rules above without seeking redundant confirmation. Before the first run, an explicit assignment of runtime investigation to the agent may establish a `remaining-runs` autonomous path. After a completed run, treat requests for agent investigation as evidence analysis unless the current user explicitly delegates a future reproduction or verification. Default every otherwise uncovered run to user ownership.
2. **Define the failure contract.** Record expected and observed behavior, smallest realistic trigger, affected scope and environment, frequency, timing, last-known-good boundary, reproduction cost, and constraints. State whether the flow terminates or is intentionally long-lived. For a long-lived flow, define a bounded observable checkpoint condition that closes the evidence window without claiming the business stream ended.
3. **Inspect before instrumenting.** Read the relevant execution path, tests, configuration, deployment boundaries, and existing logs. Reuse authoritative trace, request, operation, job, transaction, and version identifiers when available.
4. **Build the causal map.** Trace backward from the symptom through outputs, state transitions, branches, async boundaries, persistence, caches, dependencies, configuration, and inputs. Mark causal cuts and the earliest boundary where a correct value can become incorrect.
5. **Enumerate material hypotheses.** Cover applicable cause families, name concrete falsifiable mechanisms, and merge only observationally equivalent variants. Treat a hypothesis as material when it is code- or architecture-grounded and requires distinct evidence or a distinct repair. Record unsupported families as exclusions rather than inventing probes.
6. **Create the coverage plan.** Write one coverage-plan JSON file containing the failure contract, reviewed cause-family exclusions with reasons, the current planned run, explicit completion mode, causal boundaries, hypotheses, probes, the fixed all-occurrence cardinality contract, structured payload-only bounds, privacy review, transport checks, and residual ambiguities. Do not express occurrence selection or event-count policy in free text or an extra field elsewhere in the plan; the schema rejects unknown keys at every object. Set `run.reproductionOwner` to `user` by default. For `agent` or `external`, include an owner-matched `run.reproductionDelegation` whose `effectiveRunId` equals the current `run.runId`. Use the same file for validation, location sync, and expected-probe analysis. If writes are not authorized, present the plan without claiming the coverage gate passed.
7. **Validate the plan and start the ledger.** Run `scripts/debug_plan.py validate <PLAN_FILE>` with the resolved Python 3 interpreter. Require every material hypothesis to define both confirming and rejecting evidence, every hypothesis and boundary to map to probes, a flow-start sentinel plus the configured `flow-terminal` or `observation-checkpoint` sentinel, and every gate flag to pass. The machine validator closes the structural policy surface; separately read every free-text failure-contract, exclusion, step, evidence, redaction, and ambiguity field and fail semantic review if any text instructs instrumentation to sample, filter, suppress, aggregate, deduplicate, or cap occurrences. Product behavior may mention those mechanisms as the bug under investigation, but prose never overrides `every-execution` / `all-occurrences`. Fix validation or semantic-review errors before editing product code. After both pass, create or resume the evolving investigation ledger when the completion-scope rules require it.
8. **Design high-information probes.** Prefer shared causal-cut and invariant probes over repeated snapshots. Cover boundary entry/exit, branch decisions, state before/after mutation, async schedule/start/finish/cancel, cache and persistence operations, external calls, exception/fallback paths, and configured flow sentinels. For cardinality-sensitive producers, place the source probe at the authoritative callback or dispatch before any existing throttle, debounce, filter, deduplication, or aggregation; a downstream probe cannot prove how many upstream occurrences were removed. After selecting a probe, emit every occurrence. For a real-time stream, probe open/headers, every source event with its source sequence, close/cancel/error, and observation checkpoints at the real dispatch, decoder, or reader-loop boundary.
9. **Bound payload and observer cost without reducing events.** Estimate dynamic event count and bytes before the run. Move or remove low-value probe sites before validation if the projected observer effect is unsafe. For every retained probe, keep each payload compact and redacted while preserving every occurrence; do not add runtime gates, sampling, aggregation, or suppression.
10. **Establish or resume and instrument the collector session.** On a continuing investigation, read the ledger's exact active ready file and run `scripts/debug_session.py resume --ready-file <READY_FILE>` before any start attempt; never discover a session by scanning `.debug-logs/` or other workspace files. A successful resume is authoritative: preserve its endpoint, session ID, port, token, dashboard, evidence path, and cleanup ownership, and do not call `start` or `open-dashboard`. If there is no recorded active session, reuse an authoritative logging session supplied by the host or user; otherwise run `scripts/debug_session.py start`. Start a replacement only for a missing or unreachable recorded session or an explicit isolation or replacement directive, then append the old and new session details and reason to the same ledger. In a newly started browser-capable local session, let startup attempt to open and confirm the dashboard by default. Pass `--no-open-dashboard` only when the collector host is verified to have no usable local graphical browser, such as CI, container-only, or remote operation. Capture the returned ready file and `dashboardRecovery` status. Use stable probe IDs and a correlation hierarchy such as `runId -> parentCorrelationId/flowId -> operationId -> requestId/attempt`. For browser probes, import `getOrCreateBrowserDebugTransport` from `assets/browser-debug-transport.mjs`, assign its only acquisition directly to one top-level canonical `const`, and route every probe through that binding. Never hand-write fire-and-forget `fetch('/ingest')`, use `keepalive: true` for steady delivery, call `sendBeacon`, swallow transport failures, or create one transport per component or event. Install replaceable producers through stable realm keys; release the current lease before reacquiring the same key, then call the shared transport exactly once for every probe occurrence without awaiting collector I/O in the product callback. Do not add a correlation header when it could change CORS, caching, routing, or product behavior.
11. **Pass the runtime gate.** Validate the plan again, run the narrowest relevant compile/typecheck/test for the instrumentation, verify collector health and ingest acknowledgement, sync locations from the plan, and confirm transport capacity and lifecycle continuity. For each browser page realm/run, run `scripts/validate_browser_instrumentation.py <COMPLETE_INSTRUMENTATION_SOURCE_SET>` and require it to pass; do not validate a hand-picked subset. Treat this conservative static pass as necessary but not sufficient: runtime occurrence/enqueue/persistence reconciliation is still mandatory. Its canonical wiring gate masks comments, strings, templates, and classified regex literals, fails closed on ambiguous slash/brace syntax, requires exactly one unaliased registry factory import and call assigned to one top-level `const`, and counts only `recordSafe` or bundled producer calls statically bound to that returned transport. Fail the gate if a direct `/ingest` fetch, `keepalive: true`, empty transport catch, copied-but-unused or fake transport, multiple live transport instances, duplicate live producers, an HMR source-sequence reset, or occurrence-level suppression remains. Verify that the active sender uses `/ingest/batch` only as wire framing, keeps at most one collector request in flight, preserves every transport-owned serialized identity field, and preserves every logical event as a distinct frame item and NDJSON record. A collector `transport_batch_id_conflict` must terminalize the run incomplete after one request, never retry or count the frame as persisted. Before clearing a reused session, finish the prior run's summary and ledger transition, preserve any raw evidence that must survive truncation, remove superseded temporary probes, debug logging calls, and breakpoints, and sync the exact remaining active locations; then clear stale collector logs and use a unique run ID in the same healthy collector session. `Clear` remains valid while recording is frozen and does not change recording mode or generation. Retain only discriminating probes that the next planned or verification run still requires. For a continuous browser stream, require monotonic event IDs and an acknowledged-prefix checkpoint; do not wait for the live queue to become empty. Immediately before every user-owned reproduction handoff, run `scripts/debug_session.py dashboard-status --ready-file <READY_FILE>`. If it reports `recording: frozen`, run `scripts/debug_session.py resume-recording --ready-file <READY_FILE>` and rerun `dashboard-status`; require `recording: live` before reproduction. Do not substitute session `resume`, which never opens the recording gate. For a newly established browser-capable local session that reports `disabled`, run `scripts/debug_session.py open-dashboard --ready-file <READY_FILE>`, refresh `dashboard-status`, and only then copy its `line` as the handoff's first line. After a healthy ledger-based resume, do not call `open-dashboard`; use the existing dashboard status and URL. When those commands are unavailable, derive the same line and recovery decision from authoritative session state. Dashboard visibility is operator UX, never evidence or a reproduction prerequisite; a bounded open failure does not block the run.
12. **Collect one clean failing run or observation window.** Hand off the exact reproduction steps and pause when ownership is user, which is the default. Execute them directly only for a validated agent-autonomous plan; coordinate with the designated operator for external ownership. Keep setup traffic and exploratory activity outside the run. For an intentionally open stream, stop at the plan's observable checkpoint condition, record the checkpoint sentinel, and confirm every event through that transport watermark while later events may continue. Preserve deterministic fault seeds and authoritative before-state when the reproduction uses controlled timing or dependency failures. On completion, finalize the run ID, purpose, owner, delegation, evidence, and status in the ledger before planning another run.
13. **Summarize and classify.** Resume automatically after a completed handoff. Treat any request for the agent to investigate at this point as confirmation to analyze the existing evidence, not as reproduction delegation. Run the bundled summarizer with the plan as `--expected-probes-file`, filter by run and correlation hierarchy, inspect configured sentinels, expected occurrence counts, source and transport sequence gaps, acknowledged watermarks, rejected or discarded events, final drain when production stopped, and residual ambiguities, then read only the raw events needed to mark every hypothesis `CONFIRMED`, `REJECTED`, `INCONCLUSIVE`, or `NOT_REACHED`.
14. **Prove or narrow.** Claim a root cause only when evidence identifies the earliest invalid state, decision, ordering, or external result and traces it through propagation to the symptom. If evidence is insufficient, preserve the ledger and add only probes that close the smallest unresolved causal interval.
15. **Complete the requested terminal condition.** For diagnosis-only work, preserve requested evidence, remove temporary instrumentation and owned runtime artifacts, then report the proven cause and a causally sufficient repair recommendation without changing behavior. When repair is in scope, immediately eliminate the proven mechanism and restore the violated invariant at the owning boundary; reject smaller symptom masks that leave the mechanism active. Update the ledger instead of ending at the diagnosis.
16. **Verify and clean up the repair.** Keep discriminating probes for a separate post-repair run with a new run ID. Default verification to user ownership; apply a still-valid `remaining-runs` delegation or a new explicit verification delegation only to the new verification run. Compare the same invariants and probe IDs, and pause for a canonical user handoff when ownership is user. Continue iterating if the failure contract still fails. Only after verification succeeds, remove every temporary probe, debug logging call, breakpoint or debugger statement, helper, and transport hook; sync an empty location set for an owned session; clear or stop owned collector logging according to retention policy; follow host ownership policy for shared sessions; delete only owned ephemeral artifacts; and record terminal status in the ledger.

## Evidence contract

- Keep `probeId` stable across failing and verification runs.
- Map every active probe occurrence to exactly one independently serialized transport event. Require source occurrence count, queued/enqueued count, and persisted NDJSON count to agree through each completed checkpoint.
- Require `runId`, `probeId`, `location`, `event`, and `timestamp` for every planned event.
- Require correlation and ordering fields whenever work crosses async, concurrent, process, service, queue, persistence, or browser-lifecycle boundaries.
- Give every active real-time event a monotonic realm- or process-owned source sequence that survives producer replacement, and every browser-transport event a unique `transportId` plus monotonic `transportSequence`; delete it only after collector persistence acknowledgement.
- For the bundled browser transport, stamp the collector's current `recordingGeneration`, retry one stable `batchId`, preserve each event as a distinct frame item, and require zero rejected, abandoned, discarded, or registry-conflict events. Treat any such count as `continuityBroken`, never persisted evidence.
- Record compact identities, versions, hashes, counts, branch operands, durations, attempts, and invariant results instead of full payloads or state trees.
- Interpret a missing interior event only when enclosing sentinels, collector continuity, current instrumentation, expected occurrence counts, and acknowledged watermarks prove that absence.
- Separate root cause, enabling conditions, downstream symptoms, and unresolved alternatives.

## Guardrails

- Never promise that one reproduction will always identify the cause; report first-pass coverage and residual ambiguity.
- Never equate correlation, overlap, or a single suspicious value with causation.
- Never log secrets, credentials, tokens, authorization headers, passwords, payment data, or unnecessary PII.
- Never equate one bounded in-flight browser transport request with loss or deadlock; inspect collector acknowledgement, queue watermarks, retry state, and sequence continuity. Treat multiple simultaneous direct `/ingest` Pending rows from one page as a failed instrumentation gate, not a normal transport state.
- Never sample, first-N, change-gate, once-per-key, anomaly-gate, aggregate, merge, coalesce, overwrite, deduplicate, or silently discard any active probe occurrence.
- Never hand-write fire-and-forget browser ingestion, use `keepalive: true` for the steady stream, or swallow transport errors. A copied but unused bundled transport does not satisfy the gate.
- Never stack wrappers, listeners, timers, or other probe producers during hot reload, and never let a stale disposer detach the current producer.
- Never replace or tear down the registry-owned browser transport with `stop()` during a valid run. Detach producers and require `flushAndStop()` to succeed. A failed drain or forced abandonment makes that run terminally incomplete; start later work under a fresh `runId`, never by resetting the same run.
- Never claim lossless completion across reload, navigation, tab/process termination, memory exhaustion, or storage exhaustion with only the page-local memory queue; use an authoritative durable producer-side logger or report the run incomplete.
- Never let instrumentation block, throw into, or materially alter the product path.
- Never use sleeps, arbitrary delays, retries, guards, fallbacks, or coercions as a repair unless they eliminate the proven mechanism and restore the violated contract.
- Never apply a repair when the user requested diagnosis only.
- Never rewrite a completed run's owner or treat a request to analyze completed evidence as delegation of a future reproduction.
- Never start a second collector or reopen its dashboard for a continuing investigation after the ledger's exact active ready file resumes successfully; a new turn, phase, or `runId` is not a session boundary.
- Never treat dashboard `FROZEN` as disconnection, collector-health failure, evidence completion, or a transport checkpoint. It is the collector-wide write gate: the UI keeps polling, while events that arrive frozen or with an obsolete recording generation are terminally acknowledged and discarded without entering NDJSON or the index. `Clear` remains available and does not unfreeze recording. Use `resume-recording` and recheck `dashboard-status` before a deliberate recording pass; session `resume` only reuses the existing collector.
- Never assume the collector recording gate protects a direct append to `logFile`; direct file writers bypass HTTP ingestion, recording generations, and frozen-event discard semantics.
- Never remove discriminating probes before in-scope repair verification succeeds.
- Never analyze collector stdout when structured evidence is available, and never load an unbounded raw log before summarization.
- Never leave temporary probes, debug logging calls, breakpoints or debugger statements, stale endpoints, collector-owned files, or debug-only transport code after successful cleanup.

## Visible handoffs

Use scannable rendered Markdown for every user-visible checkpoint and terminal response. Never serialize multiple named sections into one paragraph or depend on single newlines to create visual separation. Use short `###` headings, leave a blank line after each heading and before every bullet or numbered list, and keep one evidence claim or action per bullet. Prefer lists over tables so handoffs remain readable in narrow viewports. Omit empty optional sections instead of filling them with prose.

The mandatory output gate above applies to every user-owned reproduction request; never send a steps-only handoff. After collection, use this shape:

```markdown
### Evidence outcome

- **Status:** <root cause proven | smallest unresolved interval>
- **Earliest divergence:** <boundary and cited evidence>
- **Propagation:** <origin-to-symptom chain>

### Hypothesis disposition

- `<hypothesis ID> — <CONFIRMED | REJECTED | INCONCLUSIVE | NOT_REACHED>`: <cited evidence>

### Artifacts

- <ledger and bounded evidence paths>

### Next action

- <repair action or smallest additional evidence action>
```

When repair is in scope, make the evidence result a progress handoff and continue directly into repair rather than ending with a recommendation or request for redundant approval. After verification, use this shape without dumping the raw log:

```markdown
### Repair

- **Mechanism changed:** <causally sufficient change>
- **Invariant restored:** <owning-boundary invariant>

### Verification

- **Failure contract:** <PASS | FAIL>
- **Independent run:** <new run ID and decisive evidence>
- **Regression checks:** <relevant checks and results>

### Cleanup

- **Instrumentation:** <removed or explicitly retained with reason>
- **Ledger:** <terminal status and path>
- **Owned artifacts:** <cleanup status>
```
