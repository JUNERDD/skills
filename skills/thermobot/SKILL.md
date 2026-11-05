---
name: thermobot
description: Run an extremely strict structural code-quality review of a change set, persist every finding in a fresh Markdown report, then verify and resolve the findings the user wants fixed through scoped, behavior-preserving repairs. The gate targets missed simplifications, responsibility concentration, abstraction and ownership boundaries, type contracts, branching growth, duplication, and 350-line file pressure; correct behavior alone does not pass. Use when the user explicitly requests Thermobot or a thermo review, or when conversation context shows an unambiguous intent to act on a Thermobot report. The review phase writes only its report and never modifies reviewed code or Git state.
---

# Thermobot

Thermobot is a harsh maintainability gate: correct behavior is not enough, and the change must also leave the code simpler to reason about. It runs in two phases:

- **Review:** sweep the requested scope for every distinct structural finding and persist the result in a fresh Markdown report. The report is the only file review may write; reviewed code and Git state stay untouched.
- **Fix:** after the report is persisted, verify and resolve the findings that the user's repair request covers. That request may arrive with the review request or after the report.

## Route And Authorization

- Start a fresh review when the user wants changes reviewed and invokes `$thermobot` or explicitly asks for Thermobot or a thermo review. A generic code-review request does not belong here.
- Enter the fix phase, with or without the invocation, when the message conveys an intent to change code in response to an identifiable Thermobot report, including one written by the earlier `thermo-review` skill. Judge that intent from meaning and conversation state, not from fixed phrases, keywords, or language.
- Resolve the source report, whether the user wants repair rather than acknowledgement or discussion, and the selection. With clear intent and no narrower scope, select all unresolved findings in the most recent unambiguous Thermobot report; an ID, title, file, location, or other semantic reference may narrow it. Ask only when intent, report, or selection stays materially ambiguous after the full conversation.
- A request to review and fix authorizes repair of verified findings within that review's scope, even before finding IDs exist. A review-only request, the report's recommendation, or a tool's suggestion authorizes nothing.
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
- Question optionality, casts, `any`, `unknown`, and loose object shapes that hide an invariant.
- Flag duplicated logic, bespoke helpers, pass-through abstractions, serialized orchestration, and partial-update flows that add reasoning cost.
- Favor the narrow change that removes moving parts, responsibility breadth, or dependency entanglement over a broad rewrite; never trade one oversized file for a larger graph of pass-through modules.
- Passing tests do not prove structural soundness, and style, naming, or formatting matter only when they hide a concrete maintainability risk.

### 350-Line Gate

In maintained source, `350` lines triggers an inspection of cohesion, dependency direction, and canonical ownership. It is a prompt to find responsibility seams, not a compaction target: a file squeezed under the number carries the same structural load.

- When a file crosses the trigger, or grows meaningfully while already over it, map its distinct reasons to change, dependency clusters, orchestration duties, side effects, and concepts owned elsewhere.
- If responsibilities are mixed, the remedy is the smallest cohesive separation that gives each unit a precise owner and contract: return a concern to its canonical owner or extract one focused unit. Deletion counts only for independently proven redundancy.
- Accept a decomposition only when the original file owns less, the new unit is understandable on its own, and dependencies stay narrow and one-way.
- Reject count-only tactics: dense rewrites, stacked statements, shortened names, dropped types or documentation, line-range splits, thin forwarding modules, and moves into catch-all `utils`, `helpers`, or `common` files.
- When the file is one cohesive responsibility and splitting would hurt locality or contracts, record an evidence-backed waiver instead of inventing a seam.
- Exclude generated files, lockfiles, vendored artifacts, snapshots, data fixtures, and intentionally monolithic external formats unless they are manually maintained source.

## Review

### Set Scope

- Honor an explicit scope: working tree, staged diff, commit range, branch diff, PR, file set, or pasted code.
- Without one, review the staged diff when staged changes exist; otherwise review the working tree against `HEAD` plus untracked, non-ignored files from `git ls-files --others --exclude-standard`, read in full.
- Read available requirements, issue or PR text, and design or migration notes before judging whether the structure fits the intent.
- Never widen the scope silently. Earlier Thermobot reports are not source changes; mark them `Not review-relevant`.
- If no reviewable scope can be resolved, stop and explain instead of fabricating a report. If the scope is too large to cover completely, review the highest-risk structural areas first, mark the report `Incomplete`, name the uncovered areas, and recommend no lower than `Discuss`.

### Recursive Sweep

1. Inventory the scope: changed files with baseline and current line counts, ownership boundaries, touched tests and config, and generated or vendored exclusions.
2. Seed a candidate frontier from every meaningful changed area: file growth, new branches, helpers, abstractions, types, imports and exports, async orchestration, persistence paths, UI state, tests, and duplicated blocks.
3. Review high-yield candidates first: whole-file and boundary issues, then abstraction and ownership, then local branch and helper simplifications.
4. Trace each candidate inward through local control flow and outward through callers, callees, public contracts, tests, and canonical helpers.
5. Add every newly exposed simplification or structural risk to the frontier, and stop only when no unreviewed candidate remains and no finding creates a dependent one.

Account for every changed structural area and frontier item in the report's coverage ledger. When exact coverage is infeasible, record the candidate count and the reviewed and skipped partitions, and mark the report incomplete rather than exhaustive.

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

Read [references/report-template.md](references/report-template.md) completely and use it as the report contract.

- Write a fresh report once the scope is resolved, including when nothing is found or coverage is incomplete.
- Generate one random lowercase identifier per run, such as 8 hex characters from `openssl rand -hex 4`, and use it in report ID `tb-YYYYMMDD-<random-id>` and in the filename.
- Follow an obvious repository convention for review artifacts when one exists; otherwise write `tmp/reviews/YYYY-MM-DD-thermobot-report-<random-id>.md` under the reviewed repository. Never overwrite an existing file; generate a new identifier instead.
- Number findings `F1`, `F2`, and so on; report ID, finding ID, and location together identify a finding durably.
- Keep the report terse: a sentence or two per card field, evidence as `file:line` pointers, and no restated diff. The report records a gate decision for someone to act on, and extra narrative only makes it slower to write and to read.
- Run the template's self-check before handoff and correct any mismatch.

Return a short summary with the report path, report ID, recommendation, completion status, severity counts, and top structural risks. Do not reproduce the full report in chat.

## Fix

Enter this phase only after the authorization gate above is satisfied. Read [references/fix-workflow.md](references/fix-workflow.md) completely, then verify, repair, and account for only the selected findings. The completed report stays fixed review input; the fix phase reports against it in a concise Markdown summary.

Never start an automatic review-fix-review loop. A post-fix review runs only when the user asks for one: scope it to the implementation delta and the boundaries it touched, and carry forward settled intent and disproved claims unless the relevant code or evidence changed.
