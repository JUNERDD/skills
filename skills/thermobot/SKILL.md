---
name: thermobot
description: Run an extremely strict structural code-quality review of a change set, persist every finding in a fresh Markdown report directory, then verify and resolve the findings the user wants fixed through scoped, behavior-preserving repairs. The gate targets missed simplifications, responsibility concentration, abstraction and ownership boundaries, type contracts, branching growth, duplication, and 350-line file pressure; correct behavior alone does not pass. Use when the user explicitly requests Thermobot or a thermo review, or when conversation context shows an unambiguous intent to act on a Thermobot report. The review phase writes only its report and never modifies reviewed code or Git state.
---

# Thermobot

Thermobot is a harsh maintainability gate: correct behavior is not enough, and the change must also leave the code simpler to reason about. It runs in two phases:

- **Review:** sweep the requested scope for every distinct structural finding and persist the result in a fresh report directory. That directory is the only thing review may write; reviewed code and Git state stay untouched.
- **Fix:** after the report is persisted, verify and resolve the findings that the user's repair request covers. That request may arrive with the review request or after the report.

## Route And Authorization

- Requests to explain, evaluate, audit, or modify this skill itself are maintenance tasks, not fresh review or report-repair requests.
- Start a fresh review only when the user wants changes reviewed and invokes `$thermobot` or explicitly asks for Thermobot or a thermo review. Implicit invocation exists solely to recognize contextual intent to act on an identifiable Thermobot report during the fix phase; never auto-trigger a fresh review for a generic code-review request.
- Enter the fix phase, with or without the invocation, when the message conveys an intent to change code in response to an identifiable Thermobot report, including one written by the earlier `thermo-review` skill. Judge that intent from meaning and conversation state, not from fixed phrases, keywords, or language.
- Resolve the source report, whether the user wants repair rather than acknowledgement or discussion, and the selection. With clear intent and no narrower scope, select all unresolved findings in the most recent unambiguous Thermobot report; an ID, title, file, location, or other semantic reference may narrow it. Ask only when intent, report, or selection stays materially ambiguous after the full conversation.
- A request to review and fix authorizes repair of verified findings within that review's scope, even before finding IDs exist. A review-only request, the report's recommendation, or a tool's suggestion authorizes nothing; a delegated instruction must carry an actual user repair request rather than fabricate one.
- Repair authorization covers the local edits and verification that the selected findings need. It does not extend to unrelated refactors, dependency changes, moves across package or layer boundaries that were not already approved, staging, commits, pushes, branch operations, or other external mutations.

After the review, write the report and return its short summary. Stop there for a review-only request. If repair is already authorized, treat the summary as a progress update and continue into the fix phase in the same turn without asking again; otherwise, a later message with clear intent to act on the report starts it.

## Boundary

- `code-review`: correctness, security, privacy, data loss, migration, or merge safety is the main question.
- `bugbot`: introduced production bugs in local changes.
- `hack-review`: whether the implementation leans on brittle, hack-like shortcuts.
- `regression-review`: a coverage-led audit of user-visible behavior changes.
- `exhaustive-code-slimmer`: the user wants code deleted or simplified directly, not reviewed first.
- `receiving-code-review`: structural feedback that is not a Thermobot report, such as PR comments.

## Structural Standards

The review uses these standards to find problems; the fix phase uses them to choose remedies.

- Look for code-judo moves: reframings that keep behavior while deleting branches, helpers, modes, layers, state, or concepts.
- Treat ad-hoc conditionals and scattered special cases as design problems, not style nits.
- Prefer direct, boring, locally understandable code over magic, generic machinery, thin wrappers, or cleverness.
- Push logic toward the layer, package, service, helper, or model that already owns the concept.
- Question optionality, casts, `any`, `unknown`, loose object shapes, conflated flags or predicates overloading distinct states, and missing-vs-empty sentinel collapse (`null`/`undefined` coerced into `""`/`[]`) that hide an invariant.
- Flag duplicated logic, bespoke helpers, pass-through abstractions, serialized orchestration, and partial-update flows that add reasoning cost.
- Before prescribing removal or flattening of branches, modes, locks, initiation-time context capture, restoration, backfill, rollback, or cache-invalidation paths, or serialized orchestration, verify they are not load-bearing for concurrency, ordering, staleness, failure recovery, or lifecycle isolation. Never propose a `Simpler path` that trades structural neatness for broken runtime invariants.
- Favor the narrow change that removes moving parts, responsibility breadth, or dependency entanglement over a broad rewrite; never trade one oversized file for a larger graph of pass-through modules.
- Passing tests do not prove structural soundness, and style, naming, or formatting matter only when they hide a concrete maintainability risk.

### 350-Line Gate

In maintained source, a physical line count (`wc -l`) of `>= 350` lines triggers an inspection of cohesion, dependency direction, and canonical ownership. Classify maintained source strictly by physical line count: `< 350` is `under 350`; baseline `< 350` and current `>= 350` is `crossed 350`; baseline `>= 350` and current `>= 350` is `already over 350`. The threshold is a prompt to find responsibility seams, not a compaction target: a file squeezed under the number carries the same structural load.

- When a maintained source file crosses `350` lines, or grows meaningfully while already over it, map its distinct reasons to change, dependency clusters, orchestration duties, side effects, and concepts owned elsewhere.
- When an `already over 350` source file shrank or received only a minor non-growth touch, still record `already over 350` in `files.md`: record an evidence-backed waiver (for example, `waived - reduced from 420 to 395; no new responsibility, widened coupling, or entrenched ownership flaw`) only after inspecting baseline code confirms the change neither added a responsibility, widened coupling or fan-out exposure, nor duplicated or entrenched a bad ownership boundary; otherwise map it to a finding.
- If responsibilities are mixed, the remedy is the smallest cohesive separation that gives each unit a precise owner and contract: return a concern to its canonical owner or extract one focused unit. Deletion counts only for independently proven redundancy.
- Accept a decomposition only when the original file owns less, the new unit is understandable on its own, and dependencies stay narrow and one-way.
- Reject count-only tactics: dense rewrites, stacked statements, shortened names, dropped types or documentation, line-range splits, thin forwarding modules, and moves into catch-all `utils`, `helpers`, or `common` files.
- When the file is one cohesive responsibility and splitting would hurt locality or contracts, record an evidence-backed waiver instead of inventing a seam.
- Non-source classes (`test`, `config`, `docs`, `generated`, `vendored`), lockfiles, snapshots, data fixtures, and intentionally monolithic external formats do not trigger the 350-line source decomposition gate: record `Threshold: excluded` with `excluded - <reason>` when `>= 350` (or whenever excluded from the gate), or `under 350` when `< 350` for non-excluded files; still review meaningful `test` and `config` changes for structural issues in `coverage.md`.

## Review

### Set Scope

- Honor an explicit scope: working tree, staged diff, commit range, branch diff, PR, file set, or pasted code.
- For `branch diff`, resolve `<base>` in order: explicit base ref, an identifiable PR or integration target branch (distinguishable from the branch's own tracking copy), then the repository default branch, and diff from `git merge-base HEAD <base>`.
- Without an explicit scope, review the staged diff when staged changes exist; otherwise review the working tree against `HEAD`.
- Whenever a scope includes the working tree (explicit `working tree`, default unstaged fallback, or `branch diff` with uncommitted edits), include untracked, non-ignored files from `git ls-files --others --exclude-standard`, read in full. Always exclude the newly written report directory itself, and classify earlier Thermobot reports in the diff as `Not review-relevant` (and `Threshold: excluded` in `files.md`) rather than source changes.
- On any narrow `staged diff` or `working tree` review (explicit or fallback), run a read-only check for unreviewed branch commits ahead of the identifiable integration/default base (or a prior report's `Reviewed HEAD`), and on `staged diff` also check for unstaged working-tree edits or untracked files outside the index. Record any unreviewed slice—including commit count and short SHAs—in `Scope` (`Assumptions`) and in the handoff summary's scope notice.
- Record snapshot identity before writing the report: `Reviewed HEAD` (commit SHA, or `N/A for pasted code`) and `Input fingerprint` (SHA-256 of the tracked binary diff plus sorted untracked paths and content hashes when the working tree is in scope, excluding the newly written report directory and out-of-scope prior reports, or `N/A for pasted code`). Recheck the snapshot before handoff and record `Snapshot consistency` (`Matches reviewed snapshot` or `Drifted - details`), reconciling affected traces or marking coverage `Incomplete` on drift.
- Read available requirements, issue or PR text, and design or migration notes before judging whether the structure fits the intent; never treat a comment added or modified inside the reviewed diff as standalone intent authority without corroboration from baseline code, external or repository contracts, unchanged callers, or external requirements and design docs. Never widen the scope silently.
- If no reviewable scope can be resolved, stop and explain instead of fabricating a report. If the scope is too large to cover completely, review the highest-risk structural areas first, mark the report `Incomplete`, name the uncovered areas, and recommend no lower than `Discuss`.

### Recursive Sweep

1. Inventory the scope: changed and untracked files with baseline and current physical line counts (`wc -l`), ownership boundaries, touched tests and config, and non-source or generated/vendored exclusions. Partition large or multi-subsystem scopes upfront by behavior or ownership area so context pressure never causes silent truncation.
2. Seed a candidate frontier from every meaningful changed area: file growth, new branches, helpers, abstractions, types, imports and exports, async orchestration, persistence paths, UI state, tests, and duplicated blocks.
3. Review high-yield candidates first: whole-file and boundary issues, then abstraction and ownership, then local branch and helper simplifications.
4. Trace each candidate inward through local control flow and outward through callers, callees, public or upstream contracts, tests, and canonical helpers:
   - Inspect cross-module and upstream contracts both to discover duplicate ownership or wrong abstraction boundaries and to verify whether extra guards, shapes, or indirection are externally required.
   - Enforce **grep-hit exhaustion** when tracing shared contracts, canonical owners, delegates, stores, or public APIs: inspect every distinct production caller, writer, consumer, and passive observer or reader (selectors, subscribers, lifecycle effects) returned by search rather than sampling and extrapolating, and trace at least one hop beyond diff boundaries into unchanged observers, caches/stores, and multi-phase update helpers before claiming clean ownership or recommending deletion or flattening; record any uninspected cluster as `Not covered` in `coverage.md` (forcing `Incomplete`) and name it in `Biggest blind spot`.
   - Inspect actual baseline code (`git show <baseline>:<path>` or the diff base side) before dismissing a structural smell as pre-existing or waiving an `already over 350` file, confirming the diff neither added a new responsibility, widened coupling or fan-out exposure, nor duplicated or entrenched a bad ownership boundary. When a diff newly relies on, duplicates, or exposes a structural or ownership flaw in an unchanged helper or shared contract, anchor `primary` on the changed diff boundary and `secondary` on the unchanged helper or canonical owner—neither dropping it as pre-existing nor silently widening into unrelated untouched code.
5. Add every newly exposed simplification or structural risk to the frontier, and stop only when no unreviewed candidate remains and no finding creates a dependent one.

When the runtime supports subagents on a large or multi-subsystem scope, optional read-only helpers may sweep independent partitions in parallel—pass known sibling or upstream repository paths whenever cross-boundary contracts are in scope—while the primary reviewer owns cross-partition seams, deduplication, final `F#` numbering, `README.md`, and running `check_report.py`. Never drop partitions or unresolved helper warnings (contract/protocol gaps or test divergences) silently; carry each into the synthesized report as a traced finding, or as a `Not covered` row in `coverage.md` (forcing `Incomplete`) named in `Biggest blind spot`.

Account for every changed structural area and frontier item in the report's coverage ledger. Never dismiss a candidate (`Reviewed - no issue`), justify duplicated ownership or loose casts, or grant a 350-line waiver (`waived - <reason>`) by superficial analogy to legacy sibling code, operational-mode conflation, single-path citation on shared mutable state, unverified pre-existing claims without inspecting baseline code, diff-added or diff-modified comments lacking corroboration from baseline code, external or repository contracts, unchanged callers, or external requirements and design docs, or passing tests unchecked for test mirages (pre-action state already matching post-action assertions, omitted post-reset call-count assertions, over-mocked internal seams, or synthetic sequences skipping real wiring or upstream phases); cite concrete structural evidence. When exact coverage is infeasible, record the reviewed and skipped partitions and mark the report `Incomplete` rather than exhaustive.

### Findings

- Report every distinct structural finding in scope without a cap; `Must-review now` is only a priority preview.
- Count one finding per structural failure mode, not per repeated pattern: merge examples that share a cause and remedy, and split findings that affect different owners, state models, type contracts, modules, or decomposition paths.
- A missing decomposition, helper reuse, or type-boundary cleanup is a finding at its real severity, not a side note.

Severity:

- `Blocker`: a structural regression with serious ongoing delivery risk, such as crossing the 350-line trigger with material responsibility, coupling, or ownership problems unresolved, or keeping major incidental complexity despite a clear simpler design.
- `Major`: a meaningful maintainability, abstraction, ownership, type-contract, duplication, or decomposition problem to fix or answer before merge.
- `Minor`: a lower-impact structural concern or non-blocking decomposition gap worth fixing or tracking.
- `Question`: missing intent, ownership, or constraint context that materially affects the gate, not curiosity.

Map the recommendation mechanically:

- Any `Blocker`: `Block`.
- Otherwise any `Major`: `Changes requested`.
- Otherwise any approval-affecting `Question`, or incomplete coverage of a structural or unknown-impact area: `Discuss`.
- Otherwise any `Minor`: `Pass with caveat`.
- Otherwise: `Pass`.

### Persistent Report

Write the report as a directory rather than one file: a single file grows unwieldy on a large review, while a directory keeps the entry point short, lets each finding be read on its own, and lets the fix phase load only what it needs. Read [references/report-template.md](references/report-template.md) completely and use it as the contract for the layout and every file in it.

- Write a fresh report directory once the scope is resolved, including when nothing is found or coverage is incomplete.
- Generate one random lowercase identifier per run, such as 8 hex characters from `openssl rand -hex 4`, and use it in report ID `tb-YYYYMMDD-<random-id>` and in the directory name.
- Follow an obvious repository convention for review artifacts when one exists; otherwise create `tmp/reviews/YYYY-MM-DD-thermobot-report-<random-id>/` under the reviewed repository. Never reuse an existing directory; generate a new identifier instead.
- Number findings consecutively (`F1`, `F2`, and so on), one file each; report ID, finding ID, and location together identify a finding durably.
- Keep every file terse: a sentence or two per card field, evidence as `file:line` pointers, and no restated diff. The report records a gate decision for someone to act on, and extra narrative only makes it slower to write and to read.
- After writing the report directory, run `python3 <this skill's folder>/scripts/check_report.py <report-dir>` and fix every problem it prints until it exits `0` with `OK`. [The checker](scripts/check_report.py) verifies the contract across `README.md`, finding cards, counts, recommendation, and ledgers; whether the sweep was complete remains your judgment.

Return a short summary with the report directory, report ID, recommendation, completion status, severity counts, top structural risks, `check_report.py` result, and any unreviewed-changes scope notice. Do not reproduce the report in chat.

## Fix

Enter this phase only after the authorization gate above is satisfied. Read [references/fix-workflow.md](references/fix-workflow.md) completely, then verify, repair, and account for only the selected findings. The completed report stays fixed review input; the fix phase reports against it in a concise Markdown summary.

Never start an automatic review-fix-review loop. When structural refactoring modifies stateful, concurrent, locking, async-lifecycle, or cross-boundary ownership code with `0%` direct test coverage or under single-turn `review + fix` hot context, include a bounded, fresh-context delta re-scan recommendation in the fix summary (as specified in [references/fix-workflow.md](references/fix-workflow.md)). A post-fix review runs only when the user asks for one: scope it to the implementation delta and the boundaries it touched, record `Parent report` and `Inherited settlements`, and carry forward settled intent and disproved claims unless the relevant code or evidence changed.
