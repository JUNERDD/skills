---
name: thermo-review
description: Perform an extremely strict, report-writing code quality review focused on structural simplification, responsibility concentration, abstraction quality, file-size pressure, spaghetti branching, canonical ownership, type boundaries, and exhaustive recursive candidate sweeps. Use for thermo-nuclear code quality review, thermonuclear review, harsh maintainability review, deep code quality audit, structural quality gate, or when asked whether a change is too complex or should be restructured. Writes a Markdown report and does not make code changes unless explicitly asked for fixes.
---

# Thermo Review

## Overview

Treat the requested scope as a harsh maintainability and structural quality gate. Correct behavior is not enough; the implementation must also leave the codebase simpler to reason about.

Always produce a Markdown report file and a short terminal summary. Do not edit code unless the user explicitly asks for fixes after the review.

The primary job is to exhaustively identify distinct structural review findings in the reviewed scope: missed simplifications, spaghetti growth, file-size pressure, weak abstraction boundaries, type-contract muddiness, duplicated logic, and ownership drift.

## Skill Boundary

- Use this skill for thermo-nuclear, thermonuclear, harsh, strict, or deep code quality review requests.
- Use `code-review` instead when correctness, security, privacy, data loss, migration safety, or merge safety is the main question.
- Use `hack-review` instead when the main question is whether an implementation relies on brittle hack-like shortcuts.
- Use `exhaustive-code-slimmer` instead when the user wants code changed to remove or simplify implementation, not only reviewed.

## Set Scope First

- Prefer an explicit scope from the user: working tree, staged changes, commit range, branch diff, PR, file set, or pasted code.
- If no scope is named, inspect Git context and choose the smallest reasonable review scope. Prefer staged changes when they exist; otherwise use the working tree against `HEAD`.
- State the assumed scope and baseline in the report.
- Do not silently review unrelated changes or the whole repository when a narrower scope is implied.
- If the scope is too large to cover completely, review the highest-risk structural areas first, mark the report `Incomplete`, list the exact areas not covered, and set the recommendation no lower than `Discuss`.
- If requirements, issue text, a PR description, migration notes, or design docs exist, read them before judging whether the structure fits the intent.

## Review Bar

Apply these standards aggressively:

- Look for code-judo moves: reframings that preserve behavior while deleting branches, helpers, modes, layers, state, or concepts.
- Treat ad-hoc conditionals and scattered special cases as design problems, not style nits.
- Prefer direct, boring, locally understandable code over magic, generic machinery, or thin wrappers.
- Push logic toward the canonical layer, package, service, helper, or model that already owns the concept.
- Question unnecessary optionality, casts, `any`, `unknown`, and loosely shaped objects when they hide an invariant.
- Flag duplicated logic, bespoke helpers, pass-through abstractions, serialized orchestration, and partial-update flows when they add reasoning cost.
- Prefer recommendations that reduce moving parts, responsibility breadth, and dependency entanglement. Do not trade one oversized file for a larger pass-through module graph.

## 350-Line Structural Gate

- Use `350` lines as the default trigger for inspecting cohesion, dependency direction, and canonical ownership in maintained source. Do not turn the number into a text-compaction target.
- For a threshold crossing or meaningful growth in a file already over the trigger, map its distinct reasons to change, dependency clusters, orchestration duties, side effects, and concepts owned elsewhere.
- When the map exposes mixed responsibilities, recommend the smallest cohesive separation that gives each unit a precise owner and contract. Reuse a canonical owner when one exists; otherwise extract a focused unit. Treat deletion as valid only for independently proven redundancy.
- Accept a decomposition only when the original file owns less, the new unit is independently understandable, and dependencies remain narrow and one-way. A lower physical line count alone does not close the finding.
- Reject dense rewrites, stacked statements, shortened names, removal of useful types or documentation, line-range splits, thin forwarding modules, and moves into generic `utils`, `helpers`, or `common` files when their purpose is only to alter the count.
- If the file represents one cohesive responsibility and splitting would worsen locality or contracts, record an evidence-backed waiver instead of inventing a seam.
- Do not count generated files, lockfiles, vendored artifacts, snapshots, data fixtures, or intentionally monolithic external formats unless they are manually maintained source.
- A waiver must be explicit in the report and supported by evidence.

## Recursive Exhaustive Sweep

Use a recursive candidate frontier, adapted from exhaustive code slimming, but do not modify code during review.

1. Build a diff inventory: changed files, line counts before and after, ownership boundaries, touched tests, touched config, and generated or vendored exclusions.
2. Seed the candidate frontier with every meaningful changed area: file growth, new branches, new helpers, abstractions, types, imports, exports, async orchestration, persistence paths, UI state, tests, and duplicated blocks.
3. Review candidates high-yield first: whole-file or boundary issues, then abstraction and ownership issues, then local branch/helper simplifications. Diagnose responsibility seams before proposing a remedy for a threshold candidate.
4. For each candidate, trace inward to local control flow and outward to callers, callees, public contracts, tests, and canonical helpers.
5. When a candidate reveals another possible simplification or structural risk, add that new candidate to the frontier and review it.
6. Continue until a fixed point: no unreviewed candidate remains in the current frontier and no finding creates a new dependent candidate.
7. Record the sweep in the report so coverage is auditable.

If exact coverage is infeasible, state the candidate count, reviewed partitions, skipped partitions, and why the result is incomplete rather than globally exhaustive.

## Completeness Contract

- Output every distinct structural finding discovered within the reviewed scope.
- Use `Must-review now` only as a short priority preview. The full findings sections and `Complete Findings Index` must include all findings.
- Maintain a `Recursive Coverage Ledger` that maps every changed structural area or candidate to one of:
  - `Finding F#`
  - `Reviewed - no issue found`
  - `Not review-relevant`
  - `Not covered`
- Treat structural areas broadly: file size, module boundaries, data flow, state model, async orchestration, type contracts, canonical helpers, duplication, tests, config, generated output, and touched shared utilities.
- Give every `crossed 350` or `already over 350` candidate a cohesion, ownership, and dependency diagnosis before assigning a finding or waiver.
- If a candidate issue is investigated and dismissed, record the dismissal in the evidence appendix when it explains coverage or prevents duplicate review.
- Do not claim complete coverage unless the recursive ledger accounts for every changed structural area and every discovered candidate frontier item.

## Output Rules

- Always write a Markdown file.
- Generate a fresh random id for each report filename, such as 8 lowercase hex characters from `openssl rand -hex 4`, `uuidgen`, or an equivalent local source.
- If the repo already has an obvious location for reviews or reports, follow that convention, but still append the random id immediately before `.md` unless the convention already guarantees a unique per-run filename.
- Otherwise write to `tmp/reviews/YYYY-MM-DD-thermo-nuclear-code-quality-report-<random-id>.md`.
- Do not overwrite an existing report. If the chosen path exists, generate a new id and choose a new path before writing.
- Use [references/report-template.md](references/report-template.md) as the default output shape.
- End with a short terminal summary containing the report path, recommendation, completion status, counts by severity, and top structural risks.

## Severity Labels

- `Blocker`: A structural regression that creates serious ongoing delivery risk, prevents a maintainable merge, crosses the 350-line trigger while leaving material responsibility, coupling, or ownership problems unresolved, or preserves major incidental complexity despite a clear simpler design.
- `Major`: A meaningful maintainability, abstraction, ownership, type-contract, duplication, or decomposition problem that should be fixed or answered before merge.
- `Minor`: A lower-impact structural concern or non-blocking decomposition gap worth addressing or tracking.
- `Question`: Missing intent, ownership, or constraint context that materially affects the quality gate. Do not use `Question` for curiosity.

Do not lead with style, naming, formatting, or broad taste preferences unless they hide a concrete maintainability risk.

## Recommendation Mapping

- If any unresolved finding is `Blocker`, the report recommendation MUST be `Block`.
- Else if any unresolved finding is `Major`, the recommendation MUST be `Changes requested`.
- Else if any approval-affecting finding is `Question`, the recommendation MUST be `Discuss`.
- Else if coverage is incomplete for a structural or unknown-impact area, the recommendation MUST be `Discuss`.
- Else if any unresolved finding is `Minor`, the recommendation MUST be `Pass with caveat`.
- Else use `Pass`.

## What Counts As One Finding

- Count one item per distinct structural failure mode or review risk, not per repeated syntax pattern.
- Merge repeated examples that share the same cause and remedy.
- Split findings when different ownership boundaries, state models, type contracts, modules, or decomposition paths are affected.
- Prefer high-conviction findings over cosmetic notes, but do not omit distinct structural risks for brevity.

## Workflow

1. Define the review scope and comparison baseline.
2. Build the diff and line-count inventories; for threshold candidates, also inventory responsibilities, dependencies, and plausible ownership seams.
3. Enumerate the recursive candidate frontier across every changed structural area.
4. Read the diff plus relevant call sites, tests, fixtures, schemas, config, docs, and canonical helpers needed to judge structure.
5. Trace each candidate inward and outward; append newly discovered candidates until the frontier reaches a fixed point or coverage becomes infeasible.
6. Gather proof and code pointers for each candidate finding.
7. De-duplicate findings by structural failure mode and classify severity.
8. Build the `Recursive Coverage Ledger`.
9. Write the report from `references/report-template.md`.
10. Run the report self-check:
    - Every changed structural or unknown-impact area appears in `Recursive Coverage Ledger`.
    - Every finding in a severity section appears in `Complete Findings Index`.
    - Every `Finding F#` ledger row has a matching card.
    - Every `Not covered` row has a reason and concrete next step.
    - Every maintained source file over `350` lines has a boundary diagnosis and maps to a finding or evidence-backed waiver.
    - No threshold item is resolved only through formatting density, arbitrary relocation, or another count-only tactic.
    - The recommendation follows the mapping rules.

## Guardrails

- Do not make code changes during review unless the user explicitly asks for fixes.
- Do not stage, commit, push, or mutate Git state.
- Do not silently widen the review scope.
- Do not recommend broad rewrites when a narrow decomposition or simpler model would address the risk.
- Do not recommend mechanical line reduction or a structureless extraction as a threshold remedy.
- Do not praise cleverness when direct code would be easier to maintain.
- Do not treat passing tests as proof that the implementation is structurally sound.
