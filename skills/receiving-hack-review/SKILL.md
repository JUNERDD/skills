---
name: receiving-hack-review
description: Consume a coverage-led `hack-review` Markdown report, PR feedback derived from one, or a request to address `Block`, `Discuss`, `Watch`, `Intentional Exceptions`, `Complete Hack-Risk Index`, `Ownership Coverage Ledger`, `Not covered`, or coverage-gap items. Use when Codex must verify whether each reported shortcut, ownership problem, intentional exception, and uncovered implementation boundary still applies before changing code, then fix, disprove, narrow, confirm, or carry forward every item with evidence while leaving Git staging untouched unless the user explicitly asks for staging, committing, or PR publication in the current request.
---

# Receiving Hack Review

## Overview

Use this skill after `hack-review` has produced a coverage-led report. Treat the report as an evidence-backed design review artifact, not as an instruction list to execute blindly.

The primary job is to account for every `F#` finding, every `I#` intentional exception, and every uncovered implementation-relevant or unknown boundary before claiming the hack gate is resolved.

## Skill Boundary

- Use `hack-review` to create or refresh the report.
- Use `receiving-hack-review` to consume the report and decide what to do next.
- Use `regression-review` instead when the concern is user-visible behavior rather than implementation shortcuts.
- Use `receiving-code-review` instead when the feedback is general code review rather than a hack-risk gate.

## Core Principles

Build a disposition ledger before editing code.

Before editing code, present a concrete change plan and self-assess whether the plan can introduce regressions, broaden behavior changes, or weaken ownership boundaries. Name the affected boundaries, why the plan is scoped, what verification will be needed, and that any fixes will remain unstaged unless the user explicitly requested staging or a publish flow. If the plan carries material regression or ownership risk, narrow it or ask before editing.

Never stage changes while consuming a review report unless the user explicitly asks for staging or committing in the current request. Do not run `git add`, partial staging commands, or tooling that stages files as a side effect.

## Git State Hard Gate

Treat the Git index as user-owned state. Addressing a hack review report is not permission to prepare a commit.

- Do not run `git add`, `git add -A`, `git add -p`, `git add -N`, `git commit`, `git commit --amend`, or equivalent index-mutating commands unless the user's current request explicitly asks for staging, committing, or PR publication.
- Do not stage files after editing code just to make a follow-up review, `git diff --cached`, commit message, or PR body easier.
- If there are already staged changes when you start, inspect them only as needed and preserve them exactly. Keep any new fixes unstaged so they do not get mixed into the user's staged set.
- If a report was generated from a staged diff and the fix changes code, do not update the staged diff yourself. Explain that the fix is present in the working tree and ask before staging or regenerating a staged-diff gate.
- If a tool would stage files as a side effect, do not use it. Choose an unstaged working-tree diff, branch diff, or explicit file inspection instead.
- If you accidentally stage changes, stop immediately, unstage only your own additions when that can be done without disturbing pre-existing staged work, and report what happened.

Keep gate integrity aligned with evidence:

- Treat `Complete Hack-Risk Index` as the enumeration source for findings.
- Treat `Ownership Coverage Ledger` as the enumeration source for reviewed, intentional, non-relevant, and uncovered implementation boundaries.
- Treat `Not covered` rows on implementation-relevant or unknown boundaries as unresolved gate items until they are covered, regenerated, or explicitly accepted as out of scope.
- Verify the current ownership model before implementing a fix.
- Do not dismiss a `Block` item without stronger counter-evidence.
- Do not "fix" an `Intentional Exceptions` item into a sweeping refactor unless product or architecture intent changed.
- Do not treat lint, typecheck, or unrelated passing tests as proof that a shortcut is gone.
- Do not remove necessary edge guards merely because the report called out a nearby fallback. Confirm which boundary actually owns the invariant first.
- Do not claim completion while any indexed finding, intentional exception, or coverage gap lacks a disposition.

## Response Pattern

WHEN receiving a hack review report:

1. Read the full report, including `Scope`, `Gate Snapshot`, `Complete Hack-Risk Index`, `Block`, `Discuss`, `Watch`, `Intentional Exceptions`, `Ownership Coverage Ledger`, `Evidence Appendix`, and `Report Self-Check` when present.
2. Confirm the report still applies to the exact scoped change set the user asked to review.
3. Build a disposition ledger before changing code:
   - Add every `F#` from `Complete Hack-Risk Index`.
   - Add every finding card from `Block`, `Discuss`, and `Watch`.
   - Add every `I#` from `Intentional Exceptions`.
   - Add every `Ownership Coverage Ledger` row whose status is `Not covered`, `Finding F#`, `Intentional Exception I#`, or unknown.
   - Add any mismatch between the index, action sections, and coverage ledger as an intake problem.
4. Stop and regenerate or clarify the report before implementing when scope, baseline, report completion, ownership context, or finding enumeration is stale or inconsistent.
5. Restate each `F#` as a concrete design liability, not as a code edit.
6. Verify each item against current code, outputs, tests, runtime behavior, search results, and ownership boundaries.
7. Decide each disposition: fix, disprove, narrow, downgrade, confirm intentional exception, close coverage gap, keep coverage gap open, or ask for clarification.
8. Before editing code, state the intended change plan, a regression or ownership-risk self-assessment, and that Git staging will remain untouched.
9. Address items in gate order and verify each affected boundary before moving on.
10. End with a short disposition ledger that accounts for every item consumed from the report, and mention any files changed are left unstaged unless the user asked otherwise.
11. Refresh the gate by rerunning `hack-review` or updating the reviewer with concrete evidence when changes materially alter the implementation strategy or coverage.

## Intake Checklist

Before changing code, confirm:

- Which scope was reviewed: working tree, staged diff, commit range, branch diff, PR, or a named implementation slice.
- Whether that scope matches the user's requested review range exactly.
- If the user did not specify scope, whether the report was generated from the staged diff.
- Which baseline the report compares against.
- Whether the current checkout still matches that scope and baseline.
- Whether `Completion` is `Complete within reviewed scope` or `Incomplete`.
- Whether every `F#` in `Complete Hack-Risk Index` has a matching card in `Block`, `Discuss`, or `Watch`.
- Whether every `Finding F#` in `Ownership Coverage Ledger` maps to a known finding.
- Whether every `Intentional Exception I#` in `Ownership Coverage Ledger` maps to an intentional exception entry.
- Which `Not covered` rows affect implementation-relevant or unknown boundaries.
- Which incumbent abstraction, invariant owner, or shared boundary the report points to.
- Which blind spots limit confidence.

If scope, baseline, completion status, owning abstraction, or item enumeration is stale or unclear, stop and regenerate or clarify the report before implementing.
If the report was generated from a broader or different range than the user asked for, do not consume it as-is. Regenerate the gate for the correct scope first.

## Handle Each Item Type

### `Block`

Treat `Block` as "stop the change from shipping until fixed or disproven."

For each `Block` item:

- Reproduce the shortcut, or trace the current code path strongly enough to show the report is still correct.
- Fix the ownership problem or disprove the finding with stronger evidence than the report currently has.
- Do not skip ahead to lower-severity cleanup while a real `Block` item remains unresolved.

Valid outcomes:

- Fix the owning layer and remove the shortcut.
- Prove the reported shortcut no longer exists or never owned the cited concern.
- Downgrade to `Discuss`, but only with concrete evidence.

### `Discuss`

Treat `Discuss` as "resolve uncertainty before approval."

- Clarify intent when the change may be a deliberate transition, migration shim, or compatibility layer.
- Gather the missing proof the report asked for.
- Prefer focused verification over speculative rewrites.
- Promote to `Block` if verification proves a serious ownership risk.
- Downgrade to `Watch` or `Intentional Exception` only with concrete evidence.

### `Watch`

Treat `Watch` as "note it, then decide whether cheap mitigation is worth it."

- Add a targeted test, owner note, TODO with exit trigger, or follow-up task when the debt matters.
- Avoid unnecessary churn when the risk is minor and already understood.
- Keep the item in the final disposition even when no code change is made.

### `Intentional Exceptions`

Treat `Intentional Exceptions` as protected shortcuts unless evidence says otherwise.

- Confirm scope, owner, and exit condition against the spec, issue, PR description, migration note, or user instruction.
- Leave the code alone if the exception is deliberate and bounded.
- Move it back into `Discuss` only when intent is unclear, the exception has grown beyond its stated scope, or the exit condition is gone.
- Do not refactor the exception away merely to silence the report.

### `Ownership Coverage Ledger`

Treat coverage rows as gate evidence, not background notes.

- For `Finding F#`, verify that the referenced finding is in the disposition ledger.
- For `Intentional Exception I#`, verify that the intentional exception has been confirmed or challenged.
- For `Reviewed - no hack-risk found`, leave the row alone unless current code or new evidence contradicts it.
- For `Not hack-relevant`, challenge the classification if the touched path owns an invariant, abstraction, lifecycle, cache, serializer, permission boundary, adapter, or extension point.
- For `Not covered`, either perform the missing ownership trace, regenerate the gate for that boundary, or leave it as an open coverage gap with a concrete next step.

## Verify Common Hack Leads Carefully

### Impossible-state fallback findings

- Identify who claims the state is impossible.
- Verify whether current code can still receive that state from a real external or legacy boundary.
- Fix the owner or the contract first. Deleting the fallback alone is not a fix if the invalid state is still produced upstream.

### Root-cause masking findings

- Trace where the bad state, invalid payload, or failure actually begins.
- Remove symptom patches only after the source is repaired or explicitly re-owned.
- Do not answer one local patch by adding a second patch earlier in the flow unless that earlier layer truly owns the invariant.

### Parallel wheel findings

- Compare the new implementation and the incumbent abstraction side by side.
- Prefer reusing or extending the incumbent boundary when it still owns the concern.
- If the new abstraction is actually better, migrate callers and retire the old one. Do not keep two accidental sources of truth.

## When to Push Back

Push back when:

- The report was generated for a different scope or stale branch.
- The report silently widened beyond the user-requested range.
- The report is incomplete but presents the gate as resolved.
- The `Complete Hack-Risk Index`, action sections, and `Ownership Coverage Ledger` disagree.
- The shortcut is a deliberate migration or compatibility layer with a clear owner and exit condition.
- The alleged impossible-state fallback is actually guarding a real external, legacy, or backward-compatibility boundary.
- The alleged duplicate abstraction owns a materially different boundary.
- Current runtime, output, search, or ownership evidence contradicts the report.
- A `Not covered` row requires context, credentials, data, platform access, or runtime setup that is not available in the current environment.

Push back with evidence, not tone:

- Cite the current code path, runtime result, owning abstraction, or search result.
- State what the report got right and what no longer applies.
- Say what additional verification would settle the disagreement if proof is still incomplete.

## Implementation Order

For multi-item reports:

1. Clarify stale or unclear scope first.
2. Regenerate the report if it does not match the user's exact review range, or if no scope was specified and the report was not based on the staged diff.
3. Build the disposition ledger from `Complete Hack-Risk Index`, action sections, `Intentional Exceptions`, and `Ownership Coverage Ledger`.
4. Resolve report inconsistencies or stale coverage before code changes.
5. Present the code-change plan, regression or ownership-risk self-assessment, and no-staging intent before editing.
6. Fix or disprove every unresolved `Block` item.
7. Resolve `Discuss` items with proof or intent clarification.
8. Decide whether `Watch` items need mitigation now.
9. Confirm or challenge `Intentional Exceptions`.
10. Close or explicitly carry forward `Not covered` implementation-relevant or unknown boundaries.
11. Re-run targeted verification for every touched boundary.
12. Refresh the hack gate if your changes materially altered the implementation strategy or coverage.

## Disposition Ledger Format

Use this shape in the final response or report update when multiple items were consumed:

```md
| ID / boundary | Original status | Disposition | Evidence | Next action |
| --- | --- | --- | --- | --- |
| F1 | Block | Fixed | Invariant now enforced in the normalizer; fallback removed from caller. | None |
| F2 | Discuss | Narrowed | Extra guard protects a legacy input boundary only. | Note in review |
| I1 | Intentional Exception | Confirmed | Migration note lists owner and removal trigger. | Leave unchanged |
| Cache invalidation path | Not covered | Open | Requires integration data not available locally. | Regenerate with staging logs |
```

Keep it concise, but account for every report item.

## Response Style

Do not use performative agreement. Use short technical acknowledgments.

Good:

- `F1 still applies on the current diff. The new fallback is hiding a broken invariant in [file]. Restoring ownership upstream.`
- `F2 is narrower than reported. The extra guard protects legacy input at the boundary, so downgrading from Block to Watch.`
- `I1 is a bounded migration exception with an owner and exit trigger. Leaving it unchanged.`
- `The cache invalidation boundary was marked Not covered; current local data cannot verify it, so I am carrying it forward with a concrete staging-log check.`

Bad:

- `You're absolutely right.`
- `Great catch, I'll refactor all of this now.`
- `Thanks for the detailed report.`

## Common Mistakes

- Treat the report title as the bug instead of the underlying ownership problem.
- Process only the top items in `Gate Snapshot` and ignore `Complete Hack-Risk Index`.
- Delete the fallback without fixing who should have prevented the bad state.
- Keep the symptom patch and add another patch upstream.
- Replace one duplicated wheel with a different duplicated wheel.
- Treat `Not covered` rows as harmless notes.
- Downgrade a `Block` item without stronger evidence.
- Stage fixes after editing code without a current explicit staging, commit, or PR request.
- Fold new fixes into an already staged diff while consuming the review report.
- Stop after code changes without rerunning the affected path, ownership trace, or targeted checks.
- Claim the gate is clean without accounting for every `F#`, `I#`, and open coverage row.

## Bottom Line

A hack review report is a coverage-led gate artifact. Consume it the same way a strong reviewer would: verify the current ownership model, preserve the severity semantics, account for every finding and ownership coverage row, then fix, challenge, narrow, confirm, or carry forward each item with evidence.
