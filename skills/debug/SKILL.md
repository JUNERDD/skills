---
name: debug
description: Coverage-first runtime debugging and repair from failure contract through root-cause proof, causal changes, separate verification, and cleanup. Use for requests to debug, troubleshoot, diagnose, investigate, fix, repair, resolve, or explain runtime application bugs, regressions, flaky or timing-sensitive failures, long-lived streams, expensive or user-only reproductions, unclear behavior, broad instrumentation, root-cause proof, or bundled collector/dashboard operation. Treat debug/fix requests as end-to-end repair unless explicitly limited to diagnosis, evidence, explanation, or recommendations. Default each runtime run to a user handoff; use agent autonomy only when the current user explicitly delegates the applicable run or remaining runs, and never let post-run evidence-analysis requests rewrite reproduction ownership. Maintain one ledger through evidence, repair, verification, and cleanup.
---

# Debug

Maximize information gained per failing reproduction. Treat code reading, tests, static analysis, and existing telemetry as hypothesis inputs; require runtime evidence to prove the originating fault, its propagation, and the reported symptom.

Use one **coverage-first** workflow. Scale probe breadth with reproduction cost, residual ambiguity, privacy risk, and observer cost. Treat “one pass” as the initial failing reproduction only; allow a targeted blind-spot run and a separate post-repair verification run when needed.

## Completion scope

- Treat a request to debug, troubleshoot, fix, repair, resolve, address, or make the failing behavior work as authorization for the full prove-repair-verify-cleanup loop. Do not ask for a second repair approval after proving the cause.
- Treat the work as diagnosis-only only when the user explicitly asks to diagnose, analyze, investigate, explain, collect evidence, recommend a fix, avoid edits, or otherwise stop before behavior changes.
- When repair is in scope, treat a root-cause finding or repair proposal as an intermediate update, not a terminal result. Continue until the causal mechanism is repaired, the original failure contract passes in a separate verification run, temporary instrumentation is removed, and owned artifacts are cleaned up.
- Keep one evolving investigation ledger whenever repair is in scope or the work crosses a reproduction handoff, context compaction, or multiple runs. Record the validated plan, evidence transitions, hypothesis dispositions, repair, verification, and cleanup in the same ledger. Omit the ledger only for short, agent-owned, diagnosis-only work that finishes in one turn.
- Pause for the default user-owned failing reproduction and post-repair verification, unavailable authority or dependency, or another concrete blocker. Treat each pause as a checkpoint and resume the same workflow when the blocker clears.

## Reproduction runs

- Scope `run.reproductionOwner` and `run.reproductionDelegation` to exactly `run.runId`. Default every new failing, blind-spot, and verification run to the user-handoff path unless a still-applicable explicit delegation covers it.
- Before the first failing run, enter the agent-autonomous path when the current user explicitly assigns the runtime investigation to the agent, for example, “have the agent investigate this” or “investigate this yourself.” Treat that pre-run assignment as `scope: "remaining-runs"` unless the user limits it to one run; do not require a separate instruction about reproduction.
- After a run completes, resume evidence analysis automatically. Treat “now have the agent investigate” or “analyze this” as an instruction to analyze the completed evidence, not as reproduction delegation. Never rerun, relabel, or change the owner of a completed run, and never change a future run owner from an evidence-analysis request.
- Change a future run from user ownership only when the current user explicitly delegates that future reproduction or verification, or explicitly delegates all remaining runtime runs. Create the new `runId` before applying the delegation; never apply it retroactively.
- For non-user ownership, store `run.reproductionDelegation` with `target`, `scope` (`single-run` or `remaining-runs`), `effectiveRunId` equal to the current `run.runId`, and `currentUserDirective` containing a faithful summary of the current user's instruction. Omit the object for user ownership. The validator checks structure and run consistency; the agent remains responsible for verifying the directive's source and scope.
- Never infer delegation from reproduction cost, deterministic tests or harnesses, agent capability, a headless environment, time pressure, user unavailability, or repository rules that prohibit agent-operated browser testing. Asking the user to reproduce in their own browser is not agent browser automation. If the user cannot reproduce but has not delegated an applicable future run, report the blocker.
- Agent-run experiments may inform hypotheses before a user handoff, but they do not replace a required user-owned canonical run and must not be presented as the user's reproduction.
- Before planning another run, record the completed run's ID, purpose, owner, delegation, evidence, and status in the investigation ledger. Default post-repair verification to user ownership unless a still-applicable `remaining-runs` delegation or a new explicit verification delegation selects another owner. Use `external` only when the current user explicitly designates an external operator.

## Mandatory user-reproduction output gate

If the current response asks the user to perform a reproduction, the response is invalid unless it renders as the exact Markdown structure below. Begin with `Dashboard:`; put no heading, greeting, readiness claim, or other prose before it. Never replace the actual URL with wording such as “opened successfully.” Emit the template as ordinary Markdown, not as a code block.

```markdown
Dashboard: <status> — <dashboardUrl-or-unavailable> (frontend confirmed: <true|false|unknown>) [— error: <non-empty error>]

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

Derive the dashboard values mechanically: use `frontend_confirmed` and `true` when a URL exists and the frontend callback is recorded; `disabled` and `false` when a URL exists and auto-open is disabled; `frontend_not_confirmed` and `false` when a URL exists otherwise; and `unavailable`, `unavailable`, and `unknown` when no URL exists. Append the normalized error only when non-empty. Normalize embedded newlines in the dashboard status or error to spaces.

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
6. **Create the coverage plan.** Write one coverage-plan JSON file containing the failure contract, reviewed cause-family exclusions with reasons, the current planned run, explicit completion mode, causal boundaries, hypotheses, probes, observer controls, privacy review, transport checks, and residual ambiguities. Set `run.reproductionOwner` to `user` by default. For `agent` or `external`, include an owner-matched `run.reproductionDelegation` whose `effectiveRunId` equals the current `run.runId`. Use the same file for validation, location sync, and expected-probe analysis. If writes are not authorized, present the plan without claiming the coverage gate passed.
7. **Validate the plan and start the ledger.** Run `scripts/debug_plan.py validate <PLAN_FILE>` with the resolved Python 3 interpreter. Require every material hypothesis to define both confirming and rejecting evidence, every hypothesis and boundary to map to probes, a flow-start sentinel plus the configured `flow-terminal` or `observation-checkpoint` sentinel, and every gate flag to pass. Fix validation errors before editing product code. After validation passes, create or resume the evolving investigation ledger when the completion-scope rules require it.
8. **Design high-information probes.** Prefer shared causal-cut and invariant probes over repeated snapshots. Cover boundary entry/exit, branch decisions, state before/after mutation, async schedule/start/finish/cancel, cache and persistence operations, external calls, exception/fallback paths, and configured flow sentinels. For a required real-time stream, probe open/headers, every source event with its source sequence, close/cancel/error, and observation checkpoints at the real dispatch, decoder, or reader-loop boundary.
9. **Bound observer cost without losing required events.** Estimate dynamic event count and bytes. Apply change-only, once-per-key, anomaly-only, aggregation, deterministic sampling, or other documented controls only to evidence the failure contract does not require exhaustively. Never count-cap, sample, merge, or discard required real-time events. Bound each payload and redact sensitive data; treat any required-event serialization or size rejection as an incomplete run rather than silently continuing.
10. **Establish and instrument the session.** Reuse an authoritative logging session when supplied. Otherwise run `scripts/debug_session.py start`; in a browser-capable local session, let it attempt to open and confirm the dashboard by default. Pass `--no-open-dashboard` only for an explicitly headless, CI, container-only, or remote session. Capture the returned ready file and `dashboardRecovery` status. Use stable probe IDs and a correlation hierarchy such as `runId -> parentCorrelationId/flowId -> operationId -> requestId/attempt`. Do not add a correlation header when it could change CORS, caching, routing, or product behavior.
11. **Pass the runtime gate.** Validate the plan again, run the narrowest relevant compile/typecheck/test for the instrumentation, verify collector health and ingest acknowledgement, sync locations from the plan, confirm transport capacity and lifecycle continuity, clear stale logs, and use a unique run ID. For a continuous browser stream, require monotonic event IDs and an acknowledged-prefix checkpoint; do not wait for the live queue to become empty. Immediately before every user-owned reproduction handoff, run `scripts/debug_session.py dashboard-status --ready-file <READY_FILE>` and copy its `line` as the handoff's first line. When that command is unavailable, derive the same line from authoritative session state. Dashboard visibility is operator UX, never evidence or a reproduction prerequisite.
12. **Collect one clean failing run or observation window.** Hand off the exact reproduction steps and pause when ownership is user, which is the default. Execute them directly only for a validated agent-autonomous plan; coordinate with the designated operator for external ownership. Keep setup traffic and exploratory activity outside the run. For an intentionally open stream, stop at the plan's observable checkpoint condition, record the checkpoint sentinel, and confirm every event through that transport watermark while later events may continue. Preserve deterministic fault seeds and authoritative before-state when the reproduction uses controlled timing or dependency failures. On completion, freeze the run ID, purpose, owner, delegation, evidence, and status in the ledger before planning another run.
13. **Summarize and classify.** Resume automatically after a completed handoff. Treat any request for the agent to investigate at this point as confirmation to analyze the existing evidence, not as reproduction delegation. Run the bundled summarizer with the plan as `--expected-probes-file`, filter by run and correlation hierarchy, inspect configured sentinels, missing probes, source and transport sequence gaps, acknowledged watermarks, rejected events, suppression counters, final drain when production stopped, and residual ambiguities, then read only the raw events needed to mark every hypothesis `CONFIRMED`, `REJECTED`, `INCONCLUSIVE`, or `NOT_REACHED`.
14. **Prove or narrow.** Claim a root cause only when evidence identifies the earliest invalid state, decision, ordering, or external result and traces it through propagation to the symptom. If evidence is insufficient, preserve the ledger and add only probes that close the smallest unresolved causal interval.
15. **Complete the requested terminal condition.** For diagnosis-only work, preserve requested evidence, remove temporary instrumentation and owned runtime artifacts, then report the proven cause and a causally sufficient repair recommendation without changing behavior. When repair is in scope, immediately eliminate the proven mechanism and restore the violated invariant at the owning boundary; reject smaller symptom masks that leave the mechanism active. Update the ledger instead of ending at the diagnosis.
16. **Verify and clean up the repair.** Keep discriminating probes for a separate post-repair run with a new run ID. Default verification to user ownership; apply a still-valid `remaining-runs` delegation or a new explicit verification delegation only to the new verification run. Compare the same invariants and probe IDs, and pause for a canonical user handoff when ownership is user. Continue iterating if the failure contract still fails. Only after verification succeeds, remove temporary instrumentation, sync an empty location set for an owned session, follow host ownership policy for shared sessions, stop owned collectors, delete only owned ephemeral artifacts, and record terminal status in the ledger.

## Evidence contract

- Keep `probeId` stable across failing and verification runs.
- Require `runId`, `probeId`, `location`, `event`, and `timestamp` for every planned event.
- Require correlation and ordering fields whenever work crosses async, concurrent, process, service, queue, persistence, or browser-lifecycle boundaries.
- Give every required real-time event a monotonic source sequence and every browser-transport event a unique `transportId` plus monotonic `transportSequence`; delete it only after collector acknowledgement.
- Record compact identities, versions, hashes, counts, branch operands, durations, attempts, and invariant results instead of full payloads or state trees.
- Interpret a missing interior event only when enclosing sentinels, collector continuity, current instrumentation, and suppression metadata prove that absence.
- Separate root cause, enabling conditions, downstream symptoms, and unresolved alternatives.

## Guardrails

- Never promise that one reproduction will always identify the cause; report first-pass coverage and residual ambiguity.
- Never equate correlation, overlap, or a single suspicious value with causation.
- Never log secrets, credentials, tokens, authorization headers, passwords, payment data, or unnecessary PII.
- Never equate a browser Network-panel `Pending` row with loss or deadlock; inspect collector acknowledgement, queue watermarks, retry state, and sequence continuity.
- Never sample, first-N, aggregate away, overwrite, or silently discard an event the failure contract requires exhaustively.
- Never claim lossless completion across reload, navigation, tab/process termination, memory exhaustion, or storage exhaustion with only the page-local memory queue; use an authoritative durable producer-side logger or report the run incomplete.
- Never let instrumentation block, throw into, or materially alter the product path.
- Never use sleeps, arbitrary delays, retries, guards, fallbacks, or coercions as a repair unless they eliminate the proven mechanism and restore the violated contract.
- Never apply a repair when the user requested diagnosis only.
- Never rewrite a completed run's owner or treat a request to analyze completed evidence as delegation of a future reproduction.
- Never remove discriminating probes before in-scope repair verification succeeds.
- Never analyze collector stdout when structured evidence is available, and never load an unbounded raw log before summarization.
- Never leave temporary probes, stale endpoints, collector-owned files, or debug-only transport code after successful cleanup.

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
