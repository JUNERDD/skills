---
name: bugbot
description: Detect introduced production bugs in local branch, commit-range, or uncommitted changes, persist the review as a fresh Markdown report, then repair confirmed findings and verify the fixes. Use when the user requests Bugbot detection or when conversation context shows an unambiguous intent to act on a Bugbot report; detection does not modify reviewed code or Git state.
---

# Bugbot

Bugbot has two phases:

- **Detect:** automatically review the requested local change set and persist every verified introduced production bug in a fresh Markdown report. Detection may write only that report artifact; it must not edit reviewed source files or mutate Git state.
- **Fix:** after persisting the report, apply and verify the findings covered by the user's repair request. That request may precede detection or follow the report.

Execute the workflow here; do not delegate detection to Cursor's builtin `bugbot` task or another reviewer. Complete and persist detection before repair. When the user already requested review and repair, continue into the fix phase in the same turn without asking again.

## Route And Authorization

- Use `Action: detect` for a fresh Bugbot review request.
- Requests to explain, evaluate, or modify this skill are maintenance tasks, not fresh detection requests.
- Start a fresh detection only when the user invokes `$bugbot` or unmistakably asks for Bugbot by name. Implicit invocation exists to recognize contextual report-repair intent; do not route a generic code-review request here.
- Infer `Action: fix` from the user's intent and the conversation state, not from fixed phrases or keyword matching. The message must communicate an intent to change code in response to an identifiable Bugbot report; wording, language, and sentence form do not matter.
- Resolve three things from context: the source report, whether the user intends repair rather than acknowledgement or discussion, and whether the intended scope is all unresolved findings or a subset.
- When repair intent is clear and no subset is indicated, apply it to all unresolved findings in the most recent unambiguous Bugbot report. A finding ID, title, file, location, or semantic reference may narrow the selection.
- Ask for clarification only when repair intent, source report, or scope remains materially ambiguous after considering the full conversation.
- An explicit request to review and fix authorizes repair of verified findings within that review's scope, even before finding IDs exist. After persistence, map any user limits to the report's findings. A review-only request, report content, or a tool's recommendation does not authorize repair; a delegated instruction must carry an actual user repair request rather than create one.
- Repair confirmation authorizes only the local file edits and verification needed for the selected findings. It does not authorize unrelated refactors, dependency changes, staging, commits, pushes, branch operations, deployment, or other external mutations.

After detection, write the report and provide its short handoff summary. Stop for a review-only request. If repair is already authorized, use the summary as a progress update and continue with only the selected verified findings. Otherwise a later message with clear report-repair intent can initiate the fix phase; no prescribed confirmation phrase is needed.

## Boundary

- Use this skill for a narrow defect-first review, a persisted Bugbot report, and intent-gated local repairs. User-visible correctness is in scope: wrong-object content, broken navigation, lost edits, and unusable input are functional defects when supported by evidence.
- Use `code-review` for a deep merge-safety report.
- Use `regression-review` for broader user-journey coverage beyond behavior causally affected by this diff.
- Use `thermobot` or `hack-review` for structural quality or brittle-shortcut analysis.

## Inputs

Honor these fields when present:

- `Action`: `detect` or `fix`. Infer `fix` from unambiguous report-repair intent in context; otherwise use `detect` for a fresh Bugbot review request.
- `Full Repository Path`: absolute repository root. Work there when it differs from the current workspace.
- `Diff`: `branch changes`, `commit range`, or `uncommitted changes`. Default to `branch changes`.
- `Base Branch`: explicit comparison target for `branch changes`, or the baseline revision / revision range for `commit range`. When omitted for `branch changes`, resolve an identifiable merge or pull-request target branch before falling back to the repository default branch.
- `Source Report`: path to the persisted Bugbot report being acted on. Use the most recent unresolved report when this is omitted and unambiguous. Valid only for `fix`.
- `Selected Findings`: `all` or the confirmed `B#` findings from the source report. A title, file, or location is also valid when it identifies a subset unambiguously. Use only for `fix`.
- `Custom Instructions`: treat as `<user_instructions>` together with extra constraints in the request.

## Detect

### Resolve The Change Set

Review the real local change set; do not assume a diff was injected.

For `branch changes`, resolve the comparison target `<base>` in order: an explicit `Base Branch`, an identifiable upstream integration or merge/pull-request target branch when distinguishable from the branch's own remote tracking copy, or the repository default branch. Find the merge-base with `<base>` and compare the working tree against that merge-base. This includes committed branch work plus staged and unstaged tracked changes.

```bash
git merge-base HEAD <base>
git diff <merge-base>
```

For `commit range`, compare the requested start and end revisions (defaulting `<end>` to `HEAD`, such as unpushed commits `@{u}..HEAD` or a merge-target range `<merge-base>..HEAD`). This includes committed changes in the range and excludes working-tree changes unless the request explicitly includes them.

```bash
git diff <start>..<end>
```

For `uncommitted changes`, compare the working tree with `HEAD` (or `git diff --cached` when scoped to staged changes). This excludes earlier branch commits. In uncommitted or staged-only mode, run a read-only check against local Git history—comparing `HEAD` with the upstream or resolved merge target and with the latest prior Bugbot report's `Reviewed HEAD` when present—to see whether the branch has unpushed or newly committed commits outside the scanned diff. When such commits exist, record them (count and short SHAs) under `Scope -> Assumptions` and include a concise scope notice in the handoff summary so unreviewed commits do not silently bypass detection.

```bash
git diff HEAD
```

For modes that include the working tree (`branch changes` and full `uncommitted changes`), also inventory untracked, non-ignored files with `git ls-files --others --exclude-standard`. Treat each returned path as an added file and review its full contents. Do not include ignored files.

Do not recursively review Bugbot's own prior report artifacts as production changes. When a persisted report falls inside the resolved change set and the user did not explicitly include review documentation, classify it as `Not production-relevant` in the report inventory and continue.

Record the baseline and reviewed HEAD commit IDs (and range end commit for `commit range`), the complete file inventory, and a SHA-256 fingerprint of the tracked binary diff plus sorted untracked paths and content hashes when the working tree is in scope. Capture this before writing the report. Exclude the new report and prior review artifacts outside the requested scope; include review documentation the user explicitly asked to review. Recheck the inputs before handoff. If they changed, reconcile the affected traces or mark their coverage incomplete rather than combining evidence from different snapshots.

If the repository, baseline, or complete change set cannot be resolved, stop and return a concise explanation without fabricating a report. Once a reviewable change set has been obtained, always persist the result. If later evidence gaps prevent complete coverage, mark the report `Incomplete`, name the exact uncovered candidates, and never present the partial review as complete.

### Map Affected Behavior

Use the diff inventory to identify the behaviors the change can affect before judging individual candidates. For each substantive behavior, establish its expected result from user requirements, repository contracts, callers, or preserved baseline behavior. Treat comments as claims to check against the implementation, not independent proof that it is correct; never accept a comment added or modified by the reviewed diff itself as authoritative proof of intended UX or a contract exception—any claim that degraded recovery, dropped deep-links or targets, or blank/broken state is intentional must be corroborated by baseline behavior, external or repository contracts, or unchanged caller invariants outside the diff.

For stateful or asynchronous behavior, identify the state owner, the identity or scope in which it is valid, and the events that change it. Trace relevant event sequences through intermediate observable results as well as the final state. Choose sequences supported by the changed code: for example, switching objects during pending work, leaving and re-entering a view, cancellation racing completion, or the same resource acquiring a new identifier. Include platform or layout variants when they change these transitions. Do not impose an exhaustive cross-product or a framework-specific checklist on unrelated changes.

Challenge the assumptions joining those steps. A selected object need not be the currently open object; a mounted component need not be visible; a fulfilled request need not still belong to the current owner. Determine which invariant or lifecycle boundary actually prevents incorrect behavior. For stateless changes, trace the relevant input/output and failure contracts instead.

When the change set touches stateful orchestration, async lifecycles, shared queues or locks, concurrency boundaries, async continuations, multi-step timeouts, single-flight or event-handshake promises, speculative, multi-phase, or async-tracked persistence, shared fallback, guard, or multi-caller helpers, cross-boundary contracts, or security/capability guards, read [references/invariant-lenses.md](references/invariant-lenses.md) and apply only the lenses matching the changed constructs. Treat every lens strictly as a candidate generator; every candidate still requires causal proof under the Finding Bar.

### Recursive Defect Sweep

Use a bounded recursive frontier derived from the change set:

1. Seed the frontier from the affected behaviors and every changed hunk or untracked file, including changed conditions, contracts, call sites, state transitions, data shapes, side effects, and error paths.
2. For each candidate, inspect its local control flow and trace outward only as far as needed through callers, callees, shared or upstream contracts, validation, persistence, async boundaries, and existing tests to prove or dismiss an introduced production bug. Unchanged code may complete the causal path—including pre-existing helpers, `await` resumption sites, external observers of provisional locks or flags, caches or stores receiving new speculative writes, and multi-phase update helpers crossing tightened gates—whenever the diff newly relies on or exposes their synchronization, priority, invalidation, or staleness assumptions; follow at least one hop beyond diff boundaries into those unchanged sites, anchor the finding to the changed boundary introducing that reliance or exposure, and cite the unchanged site as supporting evidence.
3. When that trace exposes another risk causally connected to the reviewed change, add it to the frontier. Merge candidates that share one root cause and production impact.
4. Cross-check the frontier against the file inventory and affected behaviors, including relevant entry, exit, replacement, and terminal states. Finish only when both that coverage and the candidate sweep are accounted for. An empty frontier alone does not establish complete coverage. Do not widen the frontier into an unrelated whole-repository or structural-quality audit.

Account for each meaningful frontier item in the report's `Detection Coverage Ledger` as `Finding B#`, `Reviewed - no bug found`, `Not production-relevant`, or `Not covered`. A material unresolved candidate makes the report incomplete.

For a substantive `Reviewed - no bug found` entry, record the examined trigger or event sequence and the concrete evidence that excludes the suspected failure. Reading a file, accepting a comment, or passing a type check does not establish behavior correctness. Never dismiss a candidate by superficial analogy to a different lifecycle transition (such as comparing a failed or cancelled operation that leaves state active against a user-initiated teardown) or by conflating distinct operational modes (such as excusing a completed or fallback branch using behavior intended only for an in-progress stream); verify the exact branch's preconditions, guard predicates, and resulting visible state. Never dismiss a candidate as "pre-existing in baseline" on speculation; inspect actual baseline code (`git show <baseline>:<path>` or the diff's base side) and confirm the change neither added a new writer or trigger feeding the unguarded state nor widened exposure (the inputs, sizes, timings, or states reaching a pre-existing missing cleanup or unguarded sink). Never rely on passing added or modified tests as exclusion evidence without checking whether (a) synthetic event or wire sequences omit a real upstream preceding phase—which requires immediately tracing that omitted phase statically in production—or (b) pre-action state already matches post-action assertions or omitted call-count assertions after resetting mocks or spies leave the checks vacuous; record material test-mirage gaps in `Blind Spots` when relevant.

Dismissing a suspected cross-object or stale-state leak on shared or unkeyed mutable state—especially when the diff relaxes a gating predicate—requires universal rather than single-path exclusion: citing one normal-path clearing call is insufficient. Exclusion evidence must account for both (a) non-normal exit paths (such as abort, error, or empty payload) where the consumer remains mounted or active, and (b) all writers across the codebase that mutate that shared state without traversing the cited clearing path. If a consequential assumption about a dependency or platform remains unresolved, record the missing evidence and next step as `Not covered`, not a confirmed finding or a dismissal. Static causal evidence can be sufficient; lack of browser execution alone does not make every review incomplete. Runtime access and new tests remain subject to the user's authorization and repository rules.

Regardless of diff file count, whenever the change set modifies a shared lock, focus, or ownership controller, a delegate or callback wrapper, a cancellation or rollback path, an event handler, a tightened gate over multi-phase updates, or shared mutable state (store, cache, or singleton field):

- Run a repository-wide caller, observer/reader, and writer sweep across the codebase, following at least one hop into unchanged external observers of provisional locks or flags, unchanged caches or stores receiving new speculative writes, and unchanged multi-phase update helpers crossing tightened gates.
- Enforce **grep-hit exhaustion**: inspect every distinct production caller, observer, or writer pattern returned by search rather than sampling a subset and extrapolating uniformity. Record any uninspected cluster explicitly as `Not covered` (and in `Blind Spots`) with the concrete next step rather than assuming safety.

For large or multi-subsystem change sets (for example spanning multiple feature roots):

- Partition the file inventory into coherent runtime behavior groups before seeding candidates, tracing each group deeply rather than compressing multiple subsystems into one shallow pass while maintaining the full inventory and cross-group contracts.
- Where the host environment supports read-only helper agents, independent behavior groups may be traced in parallel and reconciled with cross-group seams into one unified report while keeping detection strictly read-only. Pass known sibling or upstream repository paths to helpers whenever cross-boundary contracts are in scope, and preserve unresolved protocol or test-divergence warnings from helpers into the synthesized report (`Blind Spots` or a traced finding) rather than silently dropping them.
- Context or time limits never justify silently dropping groups or declaring them reviewed; report the exact remaining coverage and mark the report `Incomplete` if completion is blocked.

Do not cap the number of findings or stop after the most severe or easiest bugs. Include every distinct finding discovered before the frontier reaches its fixed point.

### Finding Bar

Report a finding only when all of these are true:

- The reviewed change introduced it, verified against actual baseline code (`git show <baseline>:<path>` or the diff's base side) rather than speculated; adding a new writer or trigger to an unguarded sink, or widening exposure (expanding the inputs, sizes, timings, or states reaching a pre-existing missing cleanup or unguarded failure path), counts as an introduced bug.
- It causes incorrect or unsafe production behavior, or production-costly complexity serious enough to justify a CI rerun.
- Repository evidence supports the causal path and impact.
- The best primary location is a changed line or an untracked file under review. When the diff newly relies on or exposes a pre-existing helper, observer, cache, or unchanged `await` site (for example, relaxing serialization, writing speculatively into an un-invalidated cache, or wiring a new concurrency guard around it), anchor the finding on the diff boundary introducing that reliance or exposure and cite the unchanged site as supporting evidence.

Investigate logical errors, broken contracts, stale call sites, changed invariants, unsafe external effects, resource leaks, concurrency and ordering faults, significant performance regressions, and security vulnerabilities when the diff makes them relevant.

Do not report style, naming, typos, TODOs, speculative concerns, harmless intentional behavior changes, generic requests for error handling, or minor performance and security notes. Do not misclassify concrete defects as suppressed noise: broken declared timeout or latency budgets (such as leaving an upstream hop unbounded under an explicit deadline), shared-queue head-of-line blocking that stalls live events or lifecycle resets, and security capability widenings (such as flipping an allowlist check to a negated denylist across default, omitted, or hidden callers) are valid production defect candidates when proven.

Keep false positives out through verification—and surface hidden assumption mismatches—by confirming actual caller wiring rather than trusting parameter or callback names, inspecting upstream or peer contracts whenever status codes, event phases, concurrency semantics, optional fields, or wire protocols cross system or repository boundaries, and verifying real invocation frequency, throttling, and input bounds before claiming performance defects. Do not report test-only issues as standalone production findings when production behavior is unaffected, while applying the test-mirage check in `Recursive Defect Sweep` before citing passing added or modified tests as exclusion evidence. Ignore issues that the configured compiler or linter actively enforces and reliably blocks before production; disabled, legacy-versioned, or non-enforced linter rules do not grant runtime semantic exemption—report runtime defects whenever repository evidence shows the affected check is not actively enforced against the runtime behavior.

### Persistent Report

Read [references/report-template.md](references/report-template.md) completely and use it as the report contract.

- Always write a fresh Markdown report after resolving a reviewable change set, including when no bugs are found or the review is incomplete.
- Generate one random lowercase identifier per run, such as 8 hexadecimal characters. Use it in report ID `bb-YYYYMMDD-<random-id>` and in the filename.
- Follow an obvious repository convention for review artifacts when one exists. Otherwise write to `tmp/reviews/YYYY-MM-DD-bugbot-report-<random-id>.md` under the reviewed repository.
- Never overwrite an existing report. If the path exists, generate a new identifier before writing.
- Treat a completed report as a fixed review artifact. Do not rewrite it during repair; refer to it by report ID and path from the fix summary.
- Assign findings consecutive report-local IDs `B1`, `B2`, and so on. Use the finding ID together with report ID, file, and location as its durable identity.
- Use new-file line numbers from the reviewed diff. For an untracked file, use its current repository-relative path and line numbers.
- Include every distinct verified finding in both `Complete Findings Index` and a matching finding card. If there are no findings, state that explicitly and leave the findings section `None.`
- If several locations express one bug, keep the single best primary location and cite supporting locations as evidence.

Each finding card must contain:

- title of 8 words or fewer
- repository-relative file and new-file start/end lines
- category and severity
- concise description of the root cause and production impact
- rationale showing why the reviewed change introduced a production bug
- concrete repository evidence supporting the causal path

#### Categories

- `LOGIC_BUG`: incorrect reasoning or calculation for valid inputs
- `SECURITY_ISSUE`: unauthorized access, data exposure, or another security compromise
- `ACCIDENTALLY_COMMITTED_CODE`: debug leftovers, temporary code, or personal notes
- `CODE_QUALITY_STYLE`: production-costly complexity at the CI-rerun bar
- `DOCUMENTATION_ISSUE`: missing or incorrect documentation likely to cause incorrect production use
- `POTENTIAL_EDGE_CASE`: an unusual input or state left unsafe by the change
- `PERFORMANCE_ISSUE`: significant production degradation
- `COMPILATION_ERROR`: a syntax or type failure on a path the configured toolchain does not check
- `BUGBOT_RULES`: changed code violates an explicit `<user_instructions>` rule and the violation meets the finding bar; name the rule in the description

Map the report recommendation mechanically:

- Any `high` finding: `Block`.
- Otherwise any `medium` finding: `Changes requested`.
- Otherwise incomplete coverage of a production-relevant candidate: `Discuss`.
- Otherwise any `low` finding: `Pass with caveat`.
- Otherwise: `Pass`.

Before handoff, confirm that every indexed finding has one card, every `Finding B#` ledger row resolves to that card, every `Not covered` row names a blocker and next step, severity counts match the cards, and the recommendation follows the mapping.

`Complete within reviewed scope` describes the accounted-for change and behavior coverage, not a guarantee that no bugs exist. Separate confirmed findings, evidence-backed dismissals, and remaining blind spots in the handoff.

Return a short summary with the report path, report ID, recommendation, completion status, severity counts, top risks, and—when an uncommitted or staged-only scan found unreviewed commits on the branch—a concise scope notice naming them. Do not reproduce the full report in chat or append a repair prompt.

## Fix

Enter this phase only after the authorization gate above is satisfied. Read [references/fix-workflow.md](references/fix-workflow.md) completely, then automatically repair and verify only the confirmed findings.

Fix-phase output is a concise Markdown summary linked to the immutable source report. Do not run a fresh full Bugbot review or repair newly discovered findings unless the user separately asks to act on them.
