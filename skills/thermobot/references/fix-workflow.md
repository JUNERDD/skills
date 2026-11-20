# Report-Scoped Fix Workflow

Use this workflow only for the fix phase selected by `SKILL.md`. Treat each finding as a claim to verify against current ownership, cohesion, dependencies, and behavior, not as an instruction to apply.

## Validate Confirmation

Before editing:

1. Resolve the source report from an explicit path or the unambiguous report in the conversation. A current report is a directory: read its `README.md` completely, run `python3 <skill folder>/scripts/check_report.py <report-dir>` to confirm its index, finding files, and ledgers agree, then read the finding files for the selected findings. Open `coverage.md` or `files.md` only when a selected finding or the gate status depends on them.
   - If `check_report.py` exits `1` on the immutable source report, never rewrite the report. When the failure is only minor metadata or formatting drift, disclose the drift in the repair summary and verify the selected findings directly against current code. When structural integrity is broken (missing finding cards, mismatched index or counts, or hidden `Not covered` gaps masked as `Complete`), stop and ask the user whether to run a fresh review first.
   - A single-file report from an earlier version of this skill or from `thermo-review` is still valid: read it completely, and treat any standalone `D#` decomposition gap in it as a finding.
2. Confirm repair intent and the selection with the routing rules in `SKILL.md`. Severity alone never defines a subset, and the user never has to repeat details already present.
3. Reconcile checkout drift. Authorization holds for a finding whose failure mode still exists within the original scope; map checkout-drift `already-fixed` and `unmappable` findings into `Stale` (recording the concrete reason in `Structural evidence`), and report anything that needs a broader review instead of absorbing it.

Authorization covers only the selected findings. The source report is fixed input; never rewrite it or add files to it to record progress.

## Reverify Each Finding

Build a disposition ledger before editing, one row per selected finding, and keep it current:

- `Fixed`: the structural failure is removed and behavior parity holds.
- `Narrowed`: only part of the claim holds; resolve that part and record the rest.
- `Disproved`: current evidence contradicts the claim.
- `Stale`: the code changed and the claim is already fixed or no longer maps to current code (record the concrete reason in evidence).
- `Waived`: an evidence-backed exception, such as a cohesive file over 350 lines.
- `Carried forward`: valid but outside the approved scope or waiting on a user decision; name the scope, owner, and trigger.

Push back with evidence (code path, line count, owner, behavior trace, command output, test, or doc) when the report's scope, baseline, or line counts no longer match the checkout; its index, cards, and ledgers disagree or present incomplete coverage as resolved; the flagged file is generated, vendored, fixture-like, or an intentional external format; the supposedly duplicated or misplaced logic is the canonical owner; or the suggested path broadens behavior, crosses an unapproved package or layer boundary, weakens a contract, or only relocates or compresses code. Current code and tests are behavioral evidence, not product authority; typecheck, lint, or unrelated green tests never disprove a claim; and a comment added or modified inside the reviewed diff is never sole authority for a `Disproved` or `Waived` pushback without corroboration from baseline code, external or repository contracts, unchanged callers, or external requirements and design docs.

Severity sets the bar for each row:

- `Blocker`: ends `Fixed`, `Disproved` with stronger evidence than the report's, `Narrowed` below blocker, `Waived` with explicit evidence-backed justification, `Stale` when checkout drift already resolved or removed it, or `Carried forward` when resolving the failure requires crossing an unapproved package or layer boundary, editing an external canonical owner outside approved scope, or waiting on a user decision. Never substitute a wrong-layer local workaround.
- `Major`: ends `Fixed`, `Narrowed`, `Disproved`, `Waived`, `Stale`, or `Carried forward` when resolution requires an unapproved package or layer boundary crossing, an out-of-scope canonical owner edit, or a user decision; promote it if verification exposes serious ongoing delivery risk. Never substitute a wrong-layer local workaround.
- `Minor`: fixed when the change is cheap and clarifies the code, otherwise `Carried forward`, `Waived`, `Disproved`, or `Stale` with a reason.
- `Question`: answered from code, docs, conventions, or the user, then converted to `Fixed` or `Narrowed` if a change is needed, `Disproved` if context refutes the structural risk, `Waived` if confirmed as an intentional bounded exception, `Stale` if checkout drift removed it, or `Carried forward` if awaiting an out-of-scope decision.

`Not covered` rows are review gaps, not repair targets: they stay in the gate status until a fresh review closes them.

## Repair

1. Work in the confirmed repository and follow its instructions. Inspect Git status and preserve unrelated changes, staged contents, and untracked files.
2. Share the ledger and a short plan (accepted items, files or boundaries, expected behavior, verification), then continue; ordinary in-scope edits need no further approval.
3. Fix blockers first; an unresolved independent item does not hold back other confirmed fixes.
4. Make the smallest cohesive change that removes each verified failure while preserving approved behavior, public contracts, and bounded exceptions, judged by the structural standards in `SKILL.md`. Never preserve dead pass-through shims, anti-invariant guards, or weakened invariants in production code solely to keep outdated or implementation-coupled synthetic test expectations green; update obsolete test expectations to assert real observable behavior instead, or carry the finding forward and escalate when test edits fall outside authorized scope or repository rules.
5. For a threshold finding, recompute physical line counts (`wc -l`) and apply the 350-line gate. A `crossed 350` file gets the smallest cohesive separation within the current package and layer only when that separation respects canonical ownership, or a cohesive-file waiver when splitting would hurt locality or contracts. An `already over 350` file gets new behavior placed with its rightful owner instead of another responsibility, and a refreshed waiver if a cohesive file still grows or if baseline inspection confirms the change neither added a responsibility, widened coupling or fan-out exposure, nor duplicated or entrenched a bad ownership boundary. Extraction within the current package and layer is in scope; when the canonical owner sits across an unapproved package or layer boundary, do not move or extract a helper into the wrong layer as a local workaround—carry the finding forward with its scope, owner, risk, and verification plan.

Ask again before dependency changes, destructive actions, external mutations, or scope expansion.

## Behavior Parity

Structural fixes preserve behavior unless a product change is separately approved. Before editing, list the user-visible surfaces the change can reach (routes, components, commands, API responses, persisted writes, exports, jobs, defaults, flags, permissions) and the helpers, types, or transforms that feed them. After editing, confirm that each one still:

- reads the same inputs, state, flags, and serialized forms;
- runs the same guards (auth, validation, duplicate-submit, ordering, retry, empty and error states) before its effects;
- emits the same output shape and format;
- keeps the behavior of any removed override, callback, or special case.

Extracting hooks, closures, stateful helpers, or module exports across files can alter render-cycle capture, hook ordering, async lifecycle or cancellation semantics, or bundler and re-export behavior; a superficial "code only moved" static trace is not sufficient for stateful, reactive, concurrent, or async code. Never treat unrelated passing test suites, direct tests unchecked for test mirages, or self-review by the author or solution prescriber—especially during single-turn pre-authorized `review + fix`—as proof of behavior parity.

Settle each surface with the cheapest sufficient evidence: a static trace only for pure stateless moves, existing direct tests verified to exercise the changed paths without test mirages (pre-action state already matching post-action assertions, omitted call-count assertions after resetting mocks or spies, over-mocked internal seams that mock away the refactored owner boundary, or synthetic sequences skipping real wiring or upstream phases), or a targeted check where logic was rewritten (respecting repository limits on adding new tests or starting local servers). Verification is where this phase spends most of its time, so stop once each surface is settled. Exhaustive input matrices and throwaway differential harnesses rarely prove more than a trace and direct tests already do; reserve them for rewritten logic whose behavior direct tests cannot pin down.

Record each surface as `Preserved`, `Intentional change`, `Potential regression`, or `Not covered`. When parity stays uncertain, narrow the fix, add a targeted check if permitted, or carry the risk forward; use `regression-review` when the user wants that gate.

## Verify

Run targeted tests, type checks, lint, builds, or non-destructive runtime checks in proportion to the change, plus the repository's required gates, while strictly respecting repository limits on creating new tests or starting local dev servers. Inspect new lint or typecheck warnings (not only non-zero exit codes) and check repository module and export rules on any newly extracted or split files. Reuse an earlier result only when it covers the final code, and say that it was reused.

Report direct automated test coverage for the modified files explicitly—state `0%` direct test coverage when only adjacent or unrelated test suites ran and passed, and inspect passing direct tests for test mirages (as defined under Behavior Parity) before certifying `Behavior Parity: Preserved` or citing them as evidence. If a check fails, correct it only with evidence-backed, in-scope changes—updating obsolete implementation-coupled test expectations to assert real observable behavior rather than preserving dead shims, anti-invariant guards, or weakened production invariants, and stopping to carry forward or escalate when test edits or the next attempt would violate repository rules, broaden behavior, or need new authority. Finish by inspecting the diff: each selected failure is resolved, nothing unrelated changed, and the index, branches, and remotes are untouched.

Never start an automatic `review-fix-review` loop. Whenever structural refactoring modifies stateful, concurrent, locking, async-lifecycle, or cross-boundary ownership code with `0%` direct test coverage or under single-turn `review + fix` hot context, explicitly recommend a bounded, fresh-context delta re-scan (for example `$bugbot` on the uncommitted delta or a cold-context review) in the repair summary.

Leave fixes unstaged, and take no Git or external action, such as staging, committing, pushing, switching branches, or deploying, that the user did not separately request. When the review covered the staged diff, note that the staged snapshot still contains the original issues. If a tool changes the index, restore only that delta and disclose it.

## New Findings

Do not repair a newly discovered issue unless it shares a selected root cause and cannot be separated from the confirmed repair. Report each distinct new issue as unconfirmed work; a later message intending to address it is enough.

## Output

Return a concise Markdown summary containing:

- the source report ID and its directory or file path (plus any disclosed minor metadata or formatting drift when `check_report.py` exited `1` on the immutable source report)
- the disposition ledger:

  | ID | Severity | Disposition | Structural evidence | Behavior parity | Next action |
  | --- | --- | --- | --- | --- | --- |

- changed files, verification commands and outcomes (including any new lint or typecheck warnings), and direct automated test coverage for the modified files (explicitly stating `0%` direct test coverage when only adjacent or unrelated suites ran)
- bounded fresh-context delta re-scan recommendation (for example `$bugbot` on the uncommitted delta or a cold-context review) whenever structural refactoring modified stateful, concurrent, locking, async-lifecycle, or cross-boundary ownership code with `0%` direct test coverage or under single-turn `review + fix` hot context
- the overall gate status: unselected findings and open `Not covered` rows still count, so a resolved subset does not clear the gate
- distinct new issues awaiting confirmation
- Git state: fixes left unstaged, and the index, commits, branches, remotes, and external systems unchanged
