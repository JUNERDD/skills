---
name: receiving-code-review
description: Consume a code-review/v2 Markdown report, PR feedback, or equivalent review comments; re-verify every finding, question, test gap, and uncovered area; formally challenge incorrect or stale review claims with arguments and evidence; and implement confirmed actions through a coding subagent. Use after code review when Codex must decide what still applies, produce a complete disposition ledger, fix proven issues, close coverage gaps, verify changes, and persist a receiving-code-review/v2 resolution report. Begin with a re-review assessment subagent that decides whether multiple specialist subagents are warranted by both the change scope and review results. Preserve the user's Git index unless staging or publishing is explicitly requested.
---

# Receiving Code Review

## Mission

Treat the source review as a set of evidence-backed claims, not an unquestionable instruction list. Account for every review item, independently re-review material claims, challenge errors with proof, then delegate confirmed implementation work to a coding subagent.

The coordinating agent owns intake integrity, final dispositions, implementation boundaries, patch acceptance, verification, and the persisted resolution report.

## Required Resources

- Read [references/re-review-orchestration.md](references/re-review-orchestration.md) before delegating re-review or coding.
- Write the companion resolution report from [references/disposition-template.md](references/disposition-template.md).
- Validate it with `python scripts/validate_disposition_report.py <resolution-report> --source-report <source-report>` when a source `code-review/v2` report exists.

## Hard Gates

- Before substantive re-review or code edits, launch exactly one read-only re-review assessment subagent.
- Give the assessor both the current change scope and the complete source review results. It decides whether one verifier or multiple specialist subagents are justified.
- Do not edit code until intake, scope identity, item enumeration, and preliminary dispositions are complete.
- When at least one item requires code or test changes, launch at least one coding subagent. Do not implement those changes only in the coordinator.
- Keep re-review agents read-only. Give coding agents explicit file ownership, accepted item IDs, verification duties, and a no-staging constraint.
- If no subagent primitive is available, disclose the fallback and execute the same protocol in the coordinator. Never claim delegation that did not occur.
- Preserve staged changes exactly unless the user's current request explicitly asks to stage, commit, amend, push, or publish.

## Source Artifact and Scope Integrity

Prefer a `code-review/v2` source report. Treat it as immutable.

1. Read the complete report, including contract, scope, orchestration, index, severity cards, test gaps, coverage ledger, candidate adjudication, evidence, handoff, and self-check.
2. Recompute or inspect the current scope fingerprint, baseline, target, changed paths, and Git state.
3. Build the source item universe:
   - every `F#` finding or approval-affecting question
   - every standalone `T#` test gap
   - every `A#` area marked `Not covered`
   - every intake mismatch as a new `I#` integrity item
4. Verify that the index, cards, test gaps, coverage rows, and handoff agree.
5. If the source is stale or inconsistent, do not blindly implement it. Re-review the affected surfaces, create `I#` items, and regenerate the source review only when necessary.
6. For legacy reports without the v2 contract or for unstructured PR comments, normalize each material claim into stable IDs and record the source schema as `legacy/unstructured`.

## Re-Review Orchestration

1. Give the assessment subagent the source item universe, severities, disputed claims, scope drift, touched subsystems, existing evidence, and environment limits.
2. Require `Single verifier` or `Parallel specialists`, with risk-based rationale, assignments, intentional overlap, and required evidence.
3. Use multiple angles when findings span independent risk domains, a high-severity claim is disputed, source coverage is incomplete, or different evidence methods are needed.
4. In parallel mode, partition by claim cluster or risk angle rather than asking every agent to repeat the full report.
5. Require an independent adversarial verifier for a challenged `Blocker` or security-critical `Major` when the environment supports it.
6. The coordinator must re-check every final disposition and resolve conflicts through stronger evidence, not voting.

## Disposition Model

Give every `F#`, `T#`, `A#`, and `I#` exactly one final re-review verdict:

- `Confirmed` - the source claim still applies as written.
- `Narrowed` - a smaller failure mode or impact is proven.
- `Reclassified` - the claim applies but severity or item type changes.
- `Disproved` - stronger current evidence contradicts the claim.
- `Stale` - the source scope or code path no longer matches.
- `Duplicate` - another item fully represents the same failure mode.
- `Intentional` - evidence proves an intended product or contract change rather than a defect.
- `Unverifiable` - required evidence is unavailable; keep the approval risk explicit.
- `Open` - a material question or coverage gap remains unresolved.

Then assign an action state:

- `No change needed`
- `Fix required`
- `Test required`
- `Evidence/answer required`
- `Coverage verification required`
- `Carried forward`

Do not dismiss a blocker without evidence stronger than the source report. Do not use passing lint, typecheck, or unrelated tests as counter-evidence.

## Formal Challenge Protocol

A challenge is allowed and expected when current evidence undermines the source review. Persist every material challenge as a `C#` card containing:

- source claim and source evidence
- counterclaim
- argument linking evidence to the counterclaim
- concrete code, runtime, test, contract, or history evidence
- limits and residual uncertainty
- settlement criterion that would decide the dispute
- final verdict and effect on severity or action

Distinguish disagreement from disproof. When evidence is incomplete, use `Narrowed`, `Unverifiable`, `Open`, or a lower confidence rather than declaring the source wrong.

## Implementation Delegation

After final dispositions are stable:

1. Build the actionable set from items marked `Fix required` or `Test required`.
2. State the intended changes, affected surfaces, regression/security/contract risks, verification plan, file ownership, and no-staging rule.
3. Launch one coding subagent by default. Use multiple coding agents only for disjoint file ownership or isolated worktrees with no shared generated artifacts or migration ordering.
4. Give the coding subagent only confirmed or explicitly accepted actionable items. Do not pass disproved, stale, duplicate, or intentional items as tasks.
5. Require a focused patch, changed-file list, per-item mapping, tests run, residual risks, and any newly discovered issue.
6. Inspect the patch in the coordinator, reject unrelated churn, and independently run the most important verification.
7. Keep all new changes unstaged unless the current request explicitly authorizes staging or publication.
8. If no actionable item exists, record `Coding stage not required` and the evidence supporting that decision.

## Git State Hard Gate

Treat the index as user-owned state.

- Do not run `git add`, `git add -A`, `git add -p`, `git add -N`, `git commit`, `git commit --amend`, `git reset`, or equivalent index-mutating commands without explicit current-request authorization.
- If changes were already staged, preserve them exactly. Keep new fixes unstaged.
- If the source review covered the staged diff and code is changed, do not silently update the staged set. Record the working-tree fix and the scope drift.
- Avoid tools that stage as a side effect.
- If a coding subagent mutates the index, stop, inspect the before/after state, undo only its known changes without disturbing prior staged work, and disclose the incident.

## Persistence and Review Refresh

- Write a fresh companion report with schema `receiving-code-review/v2`; never overwrite the source review.
- Follow a repository convention or use `tmp/reviews/YYYY-MM-DD-code-review-resolution-<source-report-id>-<random-id>.md`.
- Persist source identity, scope match, re-review orchestration, complete disposition ledger, challenge cards, coding delegation, patch mapping, verification, residual risk, and final Git state.
- Run the disposition validator and fix all structural errors.
- After material behavior, security, contract, migration, or test changes, refresh `code-review` against the correct current scope. Link the refreshed report from the resolution report.
- Do not claim resolution while any source item lacks a disposition or any implemented item lacks targeted verification.

## Workflow

1. Locate and read the complete source review or normalize unstructured feedback.
2. Capture current Git state and scope identity without mutating either.
3. Build the complete `F#`, `T#`, `A#`, and `I#` item universe.
4. Launch the re-review assessment subagent.
5. Execute the single-verifier or specialist re-review plan.
6. Verify each item against current code, contracts, tests, runtime behavior, and relevant history.
7. Create formal `C#` challenges where source claims are contradicted or overstated.
8. Assign every item a final verdict and action state.
9. Derive the actionable implementation set.
10. Present the scoped implementation and verification plan.
11. Launch the coding subagent when code or tests must change.
12. Inspect the patch and run focused independent verification.
13. Refresh `code-review` when changes materially alter the reviewed risk surface.
14. Write and validate the `receiving-code-review/v2` resolution report.
15. Return a short summary with source report, resolution report, re-review mode, challenged items, implemented items, verification, residual risks, and unstaged Git status.

## Completion Gate

Do not claim completion until:

- every source `F#`, `T#`, and unresolved `A#` has exactly one disposition
- every intake inconsistency has an `I#` disposition
- every challenge has a claim, counterclaim, argument, evidence, limits, and settlement criterion
- every actionable code/test item was delegated to a coding subagent or the unavailable fallback is disclosed
- every changed surface has targeted verification
- any material refreshed review is linked
- the resolution validator passes
- pre-existing staged work remains unchanged
