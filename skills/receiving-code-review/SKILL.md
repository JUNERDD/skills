---
name: receiving-code-review
description: Consume a `code-review` Markdown report, PR review feedback, or related review comments and turn them into evidence-backed next actions. Use when Codex is given `Blocker`, `Major`, `Minor`, `Question`, `Complete Findings Index`, `Test Gaps`, `Review Coverage Ledger`, `Not covered`, or coverage-gap items from a code-review report and must verify whether each finding still applies, fix proven issues, disprove or challenge stale findings, answer approval-affecting questions, close coverage gaps, and report a disposition for every item before changing or claiming completion while leaving Git staging untouched unless the user explicitly asks for staging, committing, or PR publication in the current request.
---

# Receiving Code Review

## Overview

Use this skill after `code-review` has produced a report or when equivalent PR review feedback is provided. Treat the review as an evidence-backed approval artifact, not as an instruction list to execute blindly.

The primary job is to account for every `F#` finding, every `T#` test gap, every approval-affecting question, and every uncovered review-relevant area before claiming the review is resolved.

## Skill Boundary

- Use `code-review` to create or refresh the report.
- Use `receiving-code-review` to consume the report and decide what to do next.
- Use `receiving-regression-review` instead when the report is a coverage-led `regression-review` report.
- Use `receiving-hack-review` instead when the report is a coverage-led `hack-review` report.

## Core Principles

Build a disposition ledger before editing code.

Before editing code, present a concrete change plan and self-assess whether the plan can introduce regressions, broaden behavior changes, weaken security boundaries, or alter public contracts. Name the affected surfaces, why the plan is scoped, what verification will be needed, and that any fixes will remain unstaged unless the user explicitly requested staging or a publish flow. If the plan carries material risk, narrow it or ask before editing.

Never stage changes while consuming a review report unless the user explicitly asks for staging or committing in the current request. Do not run `git add`, partial staging commands, or tooling that stages files as a side effect.

## Git State Hard Gate

Treat the Git index as user-owned state. Addressing review feedback is not permission to prepare a commit.

- Do not run `git add`, `git add -A`, `git add -p`, `git add -N`, `git commit`, `git commit --amend`, or equivalent index-mutating commands unless the user's current request explicitly asks for staging, committing, or PR publication.
- Do not stage files after editing code just to make a follow-up review, `git diff --cached`, commit message, or PR body easier.
- If there are already staged changes when you start, inspect them only as needed and preserve them exactly. Keep any new fixes unstaged so they do not get mixed into the user's staged set.
- If a report was generated from a staged diff and the fix changes code, do not update the staged diff yourself. Explain that the fix is present in the working tree and ask before staging or regenerating a staged-diff review.
- If a tool would stage files as a side effect, do not use it. Choose an unstaged working-tree diff, branch diff, or explicit file inspection instead.
- If you accidentally stage changes, stop immediately, unstage only your own additions when that can be done without disturbing pre-existing staged work, and report what happened.

Keep review integrity aligned with evidence:

- Treat `Complete Findings Index` as the enumeration source for findings.
- Treat `Test Gaps` as actionable coverage items unless the same gap is already disposed through a finding.
- Treat `Review Coverage Ledger` as the enumeration source for reviewed, non-relevant, and uncovered review areas.
- Treat `Not covered` rows on review-relevant or unknown-impact areas as unresolved review items until they are covered, regenerated, or explicitly accepted as out of scope.
- Verify the current behavior, contract, security boundary, or test coverage before implementing a fix.
- Do not dismiss a `Blocker` item without stronger counter-evidence.
- Do not treat lint, typecheck, or unrelated passing tests as proof that a finding is false.
- Do not claim completion while any indexed finding, test gap, approval-affecting question, or coverage gap lacks a disposition.

## Response Pattern

WHEN receiving a code-review report:

1. Read the full report, including `Scope`, `Review Snapshot`, `Complete Findings Index`, `Blocker`, `Major`, `Minor`, `Questions`, `Test Gaps`, `Review Coverage Ledger`, `Evidence Appendix`, and `Report Self-Check` when present.
2. Confirm the report still applies to the current diff, branch, baseline, and user-requested scope.
3. Build a disposition ledger before changing code:
   - Add every `F#` from `Complete Findings Index`.
   - Add every finding card from `Blocker`, `Major`, `Minor`, and `Questions`.
   - Add every `T#` from `Test Gaps`.
   - Add every `Review Coverage Ledger` row whose status is `Not covered`, `Finding F#`, or unknown.
   - Add any mismatch between the index, severity sections, test gaps, and coverage ledger as an intake problem.
4. Stop and regenerate or clarify the report before implementing when scope, baseline, completion status, or finding enumeration is stale or inconsistent.
5. Restate each finding as a concrete user, security, data, contract, or test risk, not as a code edit.
6. Verify each item against current code, outputs, tests, fixtures, logs, runtime behavior, and relevant call sites.
7. Decide each disposition: fix, disprove, narrow, downgrade, answer question, add test, decline test with evidence, close coverage gap, keep coverage gap open, or ask for clarification.
8. Before editing code, state the intended change plan, a regression/security/contract-risk self-assessment, and that Git staging will remain untouched.
9. Address items in severity order and verify each affected surface before moving on.
10. End with a short disposition ledger that accounts for every item consumed from the report, and mention any files changed are left unstaged unless the user asked otherwise.
11. Refresh the review by rerunning `code-review` or updating the reviewer with concrete evidence when changes materially alter behavior, security, contracts, tests, or coverage.

## Intake Checklist

Before changing code, confirm:

- Which scope was reviewed: working tree, staged diff, commit range, branch diff, PR, file set, or pasted code.
- Which baseline the report compares against.
- Whether the current checkout still matches that scope and baseline.
- Whether `Completion` is `Complete within reviewed scope` or `Incomplete`.
- Whether every `F#` in `Complete Findings Index` has a matching card in `Blocker`, `Major`, `Minor`, or `Questions`.
- Whether every `Finding F#` in `Review Coverage Ledger` maps to a known finding.
- Which `T#` test gaps are standalone versus already represented by a finding.
- Which `Not covered` rows affect review-relevant or unknown-impact areas.
- Which blind spots limit confidence.

If scope, baseline, completion status, or item enumeration is stale or unclear, stop and regenerate or clarify the report before implementing.

## Handle Each Item Type

### `Blocker`

Treat `Blocker` as "stop the change from shipping until fixed or disproven."

For each `Blocker` item:

- Reproduce the failure, or trace the current code path strongly enough to show the report is still correct.
- Fix the bug, contract break, security issue, data risk, or missing release-critical coverage.
- Disprove the finding only with stronger evidence than the report currently has.
- Do not skip ahead to lower-severity cleanup while a real `Blocker` remains unresolved.

Valid outcomes:

- Fix the issue.
- Prove the reported path is unreachable or already protected by an equivalent guard.
- Downgrade to `Major` or `Question`, but only with concrete evidence.

### `Major`

Treat `Major` as "fix or answer before approval."

- Verify the current failure mode and impact.
- Prefer focused fixes or focused tests over broad refactors.
- Promote to `Blocker` if verification proves release-blocking impact.
- Downgrade to `Minor` or `Question` only with concrete evidence.

### `Minor`

Treat `Minor` as "note it, then decide whether cheap mitigation is worth it."

- Add a targeted test, comment, guard, or follow-up when the risk matters.
- Avoid unnecessary churn when the issue is low-impact and already understood.
- Keep the item in the final disposition even when no code change is made.

### `Question`

Treat `Question` as approval-affecting missing context.

- Answer it with product, contract, security, migration, or test evidence when possible.
- Ask for clarification only when the needed context cannot be discovered locally and a reasonable assumption would be risky.
- Convert the question into a fix, disproof, intentional decision, or carried-forward open question.
- Do not leave the question out of the final ledger.

### `Test Gaps`

Treat standalone `T#` rows as review items.

- Add or strengthen focused tests when the gap covers changed behavior and the risk is meaningful.
- If a test gap is not worth fixing now, state why and carry it forward as a caveat or follow-up.
- Do not claim a test gap is closed because unrelated tests passed.

### `Review Coverage Ledger`

Treat coverage rows as review evidence, not background notes.

- For `Finding F#`, verify that the referenced finding is in the disposition ledger.
- For `Reviewed - no issue found`, leave the row alone unless current code or new evidence contradicts it.
- For `Not review-relevant`, challenge the classification if the touched path can affect correctness, security, data, contracts, user-visible behavior, generated output, or tests.
- For `Not covered`, either perform the missing verification, regenerate the review for that area, or leave it as an open coverage gap with a concrete next step.

## When to Push Back

Push back when:

- The report was generated for a different scope or stale branch.
- The report is incomplete but presents the recommendation as resolved.
- The `Complete Findings Index`, severity sections, `Test Gaps`, and `Review Coverage Ledger` disagree.
- The finding describes an intended product or contract change, not a defect.
- Current runtime, output, search, or code-path evidence contradicts the report.
- The cited path is no longer reachable.
- The report misses an equivalent guard, permission check, validation path, or test that now lives elsewhere.
- A `Not covered` row requires credentials, data, platform access, or runtime setup that is not available in the current environment.

Push back with evidence, not tone:

- Cite the current code path, output, test, log, screenshot, or runtime result.
- State what the report got right and what no longer applies.
- Say what additional verification would settle the disagreement if proof is still incomplete.

## Implementation Order

For multi-item reports:

1. Clarify stale or unclear scope first.
2. Build the disposition ledger from `Complete Findings Index`, severity sections, `Questions`, `Test Gaps`, and `Review Coverage Ledger`.
3. Resolve report inconsistencies or stale coverage before code changes.
4. Present the code-change plan, regression/security/contract-risk self-assessment, and no-staging intent before editing.
5. Fix or disprove every unresolved `Blocker` item.
6. Resolve `Major` items with fixes, proof, or explicit carry-forward decisions.
7. Decide whether `Minor` items need mitigation now.
8. Answer or carry forward approval-affecting `Question` items.
9. Close or explicitly carry forward standalone `Test Gaps`.
10. Close or explicitly carry forward `Not covered` review-relevant or unknown-impact areas.
11. Re-run targeted verification for every touched surface.
12. Refresh the code-review report if your changes materially altered behavior, security, contracts, tests, or coverage.

## Disposition Ledger Format

Use this shape in the final response or report update when multiple items were consumed:

```md
| ID / area | Original status | Disposition | Evidence | Next action |
| --- | --- | --- | --- | --- |
| F1 | Blocker | Fixed | Duplicate submit guard restored and targeted test passes. | None |
| F2 | Major | Disproved | Current serializer still emits the legacy field through the shared adapter. | Note in review |
| F3 | Question | Answered | PR spec confirms the migration intentionally drops the old flag. | Leave unchanged |
| T1 | Test gap | Closed | Added regression coverage for empty export output. | None |
| Billing export | Not covered | Open | Requires integration credentials not available locally. | Verify in staging |
```

Keep it concise, but account for every report item.

## Response Style

Do not use performative agreement. Use short technical acknowledgments.

Good:

- `F1 reproduces on the current diff. Restoring the pending-state guard.`
- `F2 does not reproduce on this branch; the serializer still emits the legacy field through [file].`
- `F3 is an intentional contract change per the migration note. Leaving behavior unchanged.`
- `The billing export row was marked Not covered; local credentials cannot verify it, so I am carrying it forward with a staging check.`

Bad:

- `You're absolutely right.`
- `Great catch, I'll fix all of this now.`
- `Thanks for the detailed report.`

## Common Mistakes

- Treat the report title as the bug instead of the underlying user, security, data, contract, or test risk.
- Process only the top items in `Review Snapshot` and ignore `Complete Findings Index`.
- Treat `Not covered` rows as harmless notes.
- Downgrade a `Blocker` without stronger evidence.
- Stage fixes after editing code without a current explicit staging, commit, or PR request.
- Fold new fixes into an already staged diff while consuming the review report.
- Claim a finding is false because lint, typecheck, or unrelated tests passed.
- Keep implementing while scope, baseline, completion status, or finding enumeration is unclear.
- Stop after code changes without rerunning the affected path, output check, or targeted tests.
- Claim the review is clean without accounting for every `F#`, `T#`, question, and open coverage row.

## Bottom Line

A code-review report is an approval artifact. Consume it the same way a strong reviewer would: verify the current behavior and contracts, preserve severity semantics, account for every finding, question, test gap, and coverage row, then fix, challenge, answer, or carry forward each item with evidence.
