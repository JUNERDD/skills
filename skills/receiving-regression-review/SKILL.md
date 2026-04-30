---
name: receiving-regression-review
description: Consume a coverage-led `regression-review` Markdown report or related PR feedback and turn it into evidence-backed next actions. Use when Codex is given `Block`, `Discuss`, `Watch`, `Intentional Changes`, `Complete Findings Index`, `Coverage Ledger`, `Not covered`, or coverage-gap items from a regression-review report and must verify whether each user-visible finding still applies, fix proven regressions, disprove or challenge stale findings, confirm intentional product changes, close coverage gaps, and report a disposition for every item before changing or claiming completion.
---

# Receiving Regression Review

## Overview

Use this skill after `regression-review` has produced a coverage-led report. Treat the report as an evidence-backed audit artifact, not as an instruction list to execute blindly.

The primary job is to account for every `F#` finding, every `I#` intentional visible change, and every uncovered user-visible or unknown-impact surface before claiming the gate is resolved.

## Skill Boundary

- Use `regression-review` to create or refresh the report.
- Use `receiving-regression-review` to consume the report and decide what to do next.
- Use `receiving-code-review` instead when the feedback is general code review rather than a user-visible regression gate.

## Core Principles

Build a disposition ledger before editing code.

Before editing code, present a concrete change plan and self-assess whether the plan can introduce regressions or broaden user-visible behavior changes. Name the affected surfaces, why the plan is scoped, and what verification will be needed. If the plan carries material regression risk, narrow it or ask before editing.

Never stage changes while consuming a review report unless the user explicitly asks for staging or committing in the current request. Do not run `git add`, partial staging commands, or tooling that stages files as a side effect.

Keep gate integrity aligned with evidence:

- Treat `Complete Findings Index` as the enumeration source for findings.
- Treat `Coverage Ledger` as the enumeration source for reviewed, intentional, non-user-visible, and uncovered surfaces.
- Treat `Not covered` rows on user-visible or unknown-impact surfaces as unresolved gate items until they are covered, regenerated, or explicitly accepted as out of scope.
- Verify the current user-visible behavior before implementing a fix.
- Do not dismiss a `Block` item without stronger counter-evidence.
- Do not "fix" an `Intentional Changes` item back to the old behavior unless product intent changed.
- Do not treat lint, typecheck, or unrelated passing tests as proof that a finding is false.
- Do not claim completion while any indexed finding, intentional change, or coverage gap lacks a disposition.

## Response Pattern

WHEN receiving a regression review report:

1. Read the full report, including `Scope`, `Gate Snapshot`, `Complete Findings Index`, `Block`, `Discuss`, `Watch`, `Intentional Changes`, `Coverage Ledger`, `Evidence Appendix`, and `Report Self-Check` when present.
2. Confirm the report still applies to the current diff, branch, baseline, and user-requested scope.
3. Build a disposition ledger before changing code:
   - Add every `F#` from `Complete Findings Index`.
   - Add every finding card from `Block`, `Discuss`, and `Watch`.
   - Add every `I#` from `Intentional Changes`.
   - Add every `Coverage Ledger` row whose status is `Not covered`, `Finding F#`, `Intentional I#`, or unknown.
   - Add any mismatch between the index, action sections, and coverage ledger as an intake problem.
4. Stop and regenerate or clarify the report before implementing when scope, baseline, report completion, or finding enumeration is stale or inconsistent.
5. Restate each `F#` as a user-visible outcome, not as a code edit.
6. Verify each item against current code, outputs, tests, fixtures, logs, or runtime behavior.
7. Decide each disposition: fix, disprove, narrow, downgrade, confirm intentional, close coverage gap, keep coverage gap open, or ask for clarification.
8. Before editing code, state the intended change plan and a regression-risk self-assessment.
9. Address items in gate order and verify each affected user surface before moving on.
10. End with a short disposition ledger that accounts for every item consumed from the report.
11. Refresh the gate by rerunning `regression-review` or updating the reviewer with concrete evidence when changes materially alter user-visible behavior or coverage.

## Intake Checklist

Before changing code, confirm:

- Which scope was reviewed: working tree, staged diff, commit range, branch diff, or PR.
- Which baseline the report compares against.
- Whether the current checkout still matches that scope and baseline.
- Whether `Completion` is `Complete within reviewed scope` or `Incomplete`.
- Whether every `F#` in `Complete Findings Index` has a matching card in `Block`, `Discuss`, or `Watch`.
- Whether every `Finding F#` in `Coverage Ledger` maps to a known finding.
- Whether every `Intentional I#` in `Coverage Ledger` maps to an intentional change entry.
- Which `Not covered` rows affect user-visible or unknown-impact surfaces.
- Which blind spots limit confidence.

If scope, baseline, completion status, or item enumeration is stale or unclear, stop and regenerate or clarify the report before implementing.

## Handle Each Item Type

### `Block`

Treat `Block` as "stop the change from shipping until fixed or disproven."

For each `Block` item:

- Reproduce the user-visible breakage, or trace the current code path strongly enough to show the report is still correct.
- Fix the behavior or disprove the finding with stronger evidence than the report currently has.
- Do not skip ahead to lower-severity cleanup while a real `Block` item remains unresolved.

Valid outcomes:

- Fix the regression.
- Prove an equivalent guard or output path still exists.
- Downgrade to `Discuss`, but only with concrete evidence.

### `Discuss`

Treat `Discuss` as "resolve uncertainty before approval."

- Clarify product intent when the change may be deliberate.
- Gather the missing proof the report asked for.
- Prefer focused verification over speculative fixes.
- Promote to `Block` if verification proves a serious user-visible break.
- Downgrade to `Watch` or `Intentional` only with concrete evidence.

### `Watch`

Treat `Watch` as "note it, then decide whether cheap mitigation is worth it."

- Add a targeted test, monitor, or follow-up when the caveat matters.
- Avoid unnecessary churn when the risk is minor and already understood.
- Keep the item in the final disposition even when no code change is made.

### `Intentional Changes`

Treat `Intentional Changes` as protected product deltas unless evidence says otherwise.

- Confirm intent against the spec, issue, PR description, or user instruction.
- Leave the change alone if it is deliberate.
- Move it back into `Discuss` only when intent is unclear or contradictory.
- Do not make user-visible behavior match the old baseline merely to silence the report.

### `Coverage Ledger`

Treat coverage rows as gate evidence, not background notes.

- For `Finding F#`, verify that the referenced finding is in the disposition ledger.
- For `Intentional I#`, verify that the intentional change has been confirmed or challenged.
- For `Reviewed - no user-visible regression found`, leave the row alone unless current code or new evidence contradicts it.
- For `Not user-visible`, challenge the classification if the touched path can affect routes, commands, outputs, persistence, scheduled jobs, or externally consumed data.
- For `Not covered`, either perform the missing verification, regenerate the gate for that surface, or leave it as an open coverage gap with a concrete next step.

## When to Push Back

Push back when:

- The report was generated for a different scope or stale branch.
- The report is incomplete but presents the gate as resolved.
- The `Complete Findings Index`, action sections, and `Coverage Ledger` disagree.
- The finding describes an intended product change, not a regression.
- Current runtime or output evidence contradicts the report.
- The user-visible path is no longer reachable.
- The report misses a guard, fallback, or idempotency control that now lives elsewhere.
- A `Not covered` row requires credentials, data, platform access, or runtime setup that is not available in the current environment.

Push back with evidence, not tone:

- Cite the current code path, output, test, log, screenshot, or runtime result.
- State what the report got right and what no longer applies.
- Say what additional verification would settle the disagreement if proof is still incomplete.

## Implementation Order

For multi-item reports:

1. Clarify stale or unclear scope first.
2. Build the disposition ledger from `Complete Findings Index`, action sections, `Intentional Changes`, and `Coverage Ledger`.
3. Resolve report inconsistencies or stale coverage before code changes.
4. Present the code-change plan and regression-risk self-assessment before editing.
5. Fix or disprove every unresolved `Block` item.
6. Resolve `Discuss` items with proof or intent clarification.
7. Decide whether `Watch` items need mitigation now.
8. Confirm or challenge `Intentional Changes`.
9. Close or explicitly carry forward `Not covered` user-visible or unknown-impact surfaces.
10. Re-run targeted verification for every touched user surface.
11. Refresh the regression gate if your changes materially altered user-visible behavior or coverage.

## Disposition Ledger Format

Use this shape in the final response or report update when multiple items were consumed:

```md
| ID / surface | Original status | Disposition | Evidence | Next action |
| --- | --- | --- | --- | --- |
| F1 | Block | Fixed | Targeted test now passes; checkout guard restored. | None |
| F2 | Discuss | Disproved | Current serializer still emits legacy field. | Note in review |
| I1 | Intentional | Confirmed | Matches issue acceptance criteria. | Leave unchanged |
| Settings export | Not covered | Closed | Verified CLI output fixture. | None |
```

Keep it concise, but account for every report item.

## Response Style

Do not use performative agreement. Use short technical acknowledgments.

Good:

- `F1 reproduces on the current diff. Restoring the pending-state guard.`
- `F2 does not reproduce on this branch; the empty-state fallback moved to [file].`
- `I1 appears intentional per the spec. Leaving behavior unchanged.`
- `The billing export row was marked Not covered; I verified the generated CSV fixture and closed that gap.`

Bad:

- `You're absolutely right.`
- `Great catch, I'll fix all of this now.`
- `Thanks for the detailed report.`

## Common Mistakes

- Treat the report title as the bug instead of the user-visible outcome.
- Process only the top items in `Gate Snapshot` and ignore `Complete Findings Index`.
- Fix `Intentional Changes` back to the old behavior.
- Treat `Not covered` rows as harmless notes.
- Downgrade a `Block` item without stronger evidence.
- Claim a finding is false because lint, typecheck, or unrelated tests passed.
- Keep implementing while scope, baseline, completion status, or finding enumeration is unclear.
- Stop after code changes without rerunning the affected flow or output check.
- Claim the gate is clean without accounting for every `F#`, `I#`, and open coverage row.

## Bottom Line

A regression review report is a coverage-led gate artifact. Consume it the same way a strong reviewer would: verify the current behavior, preserve the severity semantics, account for every finding and coverage row, then fix, challenge, confirm, or carry forward each item with evidence.
