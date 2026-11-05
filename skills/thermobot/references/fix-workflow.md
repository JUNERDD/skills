# Report-Scoped Fix Workflow

Use this workflow only for the fix phase selected by `SKILL.md`. Treat each finding as a claim to verify against current ownership, cohesion, dependencies, and behavior, not as an instruction to apply.

## Validate Confirmation

Before editing:

1. Resolve the source report from an explicit path or the unambiguous report in the conversation, confirm that it is a Thermobot report or one written by the earlier `thermo-review` skill, and read it completely. Reports without a `Report Contract` section are still valid; treat any standalone `D#` decomposition gap in them as a finding.
2. Confirm repair intent and the selection with the routing rules in `SKILL.md`. Severity alone never defines a subset, and the user never has to repeat details already present.
3. Reconcile checkout drift. Authorization holds for a finding whose failure mode still exists within the original scope; mark stale, already-fixed, or unmappable findings explicitly, and report anything that needs a broader review instead of absorbing it.

Authorization covers only the selected findings. The source report is fixed input; never rewrite it to record progress.

## Reverify Each Finding

Build a disposition ledger before editing, one row per selected finding, and keep it current:

- `Fixed`: the structural failure is removed and behavior parity holds.
- `Narrowed`: only part of the claim holds; resolve that part and record the rest.
- `Disproved`: current evidence contradicts the claim.
- `Stale`: the code changed and the claim no longer maps to it.
- `Waived`: an evidence-backed exception, such as a cohesive file over 350 lines.
- `Carried forward`: valid but outside the approved scope or waiting on a user decision; name the scope, owner, and trigger.

Push back with evidence (code path, line count, owner, behavior trace, command output, test, or doc) when the report's scope, baseline, or line counts no longer match the checkout; its index, cards, and ledgers disagree or present incomplete coverage as resolved; the flagged file is generated, vendored, fixture-like, or an intentional external format; the supposedly duplicated or misplaced logic is the canonical owner; or the suggested path broadens behavior, crosses an unapproved package or layer boundary, weakens a contract, or only relocates or compresses code. Current code and tests are behavioral evidence, not product authority, and typecheck, lint, or unrelated green tests never disprove a claim.

Severity sets the bar for each row:

- `Blocker`: ends fixed, disproved with stronger evidence than the report's, narrowed below blocker, or explicitly justified.
- `Major`: fixed or answered; promote it if verification exposes serious ongoing delivery risk.
- `Minor`: fixed when the change is cheap and clarifies the code, otherwise carried forward with a reason.
- `Question`: answered from code, docs, conventions, or the user, then converted to another disposition.

`Not covered` rows are review gaps, not repair targets: they stay in the gate status until a fresh review closes them.

## Repair

1. Work in the confirmed repository and follow its instructions. Inspect Git status and preserve unrelated changes, staged contents, and untracked files.
2. Share the ledger and a short plan (accepted items, files or boundaries, expected behavior, verification), then continue; ordinary in-scope edits need no further approval.
3. Fix blockers first; an unresolved independent item does not hold back other confirmed fixes.
4. Make the smallest cohesive change that removes each verified failure while preserving approved behavior, public contracts, and bounded exceptions, judged by the structural standards in `SKILL.md`.
5. For a threshold finding, recompute line counts and apply the 350-line gate. A `crossed 350` file gets the smallest cohesive separation available within scope or a cohesive-file waiver. An `already over 350` file gets new behavior placed with its rightful owner instead of another responsibility, and a refreshed waiver if a cohesive file still grows. Extraction within the current package and layer is in scope; a move across either needs approved scope, otherwise carry it forward with its scope, risk, and verification plan.

Ask again before dependency changes, destructive actions, external mutations, or scope expansion.

## Behavior Parity

Structural fixes preserve behavior unless a product change is separately approved. Before editing, list the user-visible surfaces the change can reach (routes, components, commands, API responses, persisted writes, exports, jobs, defaults, flags, permissions) and the helpers, types, or transforms that feed them. After editing, confirm that each one still:

- reads the same inputs, state, flags, and serialized forms;
- runs the same guards (auth, validation, duplicate-submit, ordering, retry, empty and error states) before its effects;
- emits the same output shape and format;
- keeps the behavior of any removed override, callback, or special case.

Settle each surface with the cheapest sufficient evidence: a static trace when code only moved, the existing tests that exercise it, or one targeted test or small before-and-after comparison of representative inputs where logic was rewritten. Verification is where this phase spends most of its time, so stop once each surface is settled. Exhaustive input matrices and throwaway differential harnesses rarely prove more than a trace and the tests already do; reserve them for rewritten logic whose behavior the tests cannot pin down. Add a test only where it closes a gap a regression could slip through.

Record each surface as `Preserved`, `Intentional change`, `Potential regression`, or `Not covered`. When parity stays uncertain, add a targeted check, narrow the fix, or carry the risk forward; use `regression-review` when the user wants that gate.

## Verify

Run targeted tests, type checks, lint, builds, or non-destructive runtime checks in proportion to the change, plus the repository's required gates. Reuse an earlier result only when it covers the final code, and say that it was reused. If a check fails, correct it only with evidence-backed, in-scope changes; stop and report when the next attempt would broaden behavior or need new authority. Finish by inspecting the diff: each selected failure is resolved, nothing unrelated changed, and the index, branches, and remotes are untouched.

Leave fixes unstaged, and take no Git or external action, such as staging, committing, pushing, switching branches, or deploying, that the user did not separately request. When the review covered the staged diff, note that the staged snapshot still contains the original issues. If a tool changes the index, restore only that delta and disclose it.

## New Findings

Do not repair a newly discovered issue unless it shares a selected root cause and cannot be separated from the confirmed repair. Report each distinct new issue as unconfirmed work; a later message intending to address it is enough.

## Output

Return a concise Markdown summary containing:

- the source report ID and path
- the disposition ledger:

  | ID | Severity | Disposition | Structural evidence | Behavior parity | Next action |
  | --- | --- | --- | --- | --- | --- |

- changed files, plus verification commands and outcomes
- the overall gate status: unselected findings and open `Not covered` rows still count, so a resolved subset does not clear the gate
- distinct new issues awaiting confirmation
- Git state: fixes left unstaged, and the index, commits, branches, remotes, and external systems unchanged
