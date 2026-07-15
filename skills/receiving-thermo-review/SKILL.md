---
name: receiving-thermo-review
description: Consume a `thermo-review` Markdown report, PR feedback derived from one, or structural quality-gate feedback involving `Blocker`, `Major`, `Minor`, `Question`, `Complete Findings Index`, `Decomposition Gaps`, recursive coverage, line-count ledgers, candidate sweep logs, `Not covered` rows, or 350-line thresholds. Use when Codex must verify every structural item against the current checkout, build disposition and behavior-parity ledgers before editing, resolve oversized maintained-source findings through cohesive responsibility boundaries rather than count-only edits, fix, disprove, narrow, waive, or carry forward each item with evidence, avoid user-visible regressions, and leave Git staging untouched unless explicitly asked to stage, commit, or publish.
---

# Receiving Thermo Review

## Purpose

Use this skill after `thermo-review` has produced a report or equivalent structural quality feedback. Treat the report as an evidence-backed gate, not as an instruction list.

Account for every finding, decomposition gap, 350-line threshold item, recursive coverage row, candidate sweep row, and uncovered structural area before claiming the gate is resolved.

## Boundary

- Use `thermo-review` to create or refresh the structural report.
- Use `receiving-thermo-review` to consume the report and decide what to fix, disprove, narrow, waive, or carry forward.
- Use `receiving-code-review` for general correctness, security, contract, or test feedback.
- Use `receiving-hack-review` for hack-risk ownership gates.
- Use `regression-review` when a planned or completed structural fix has material or uncertain user-visible behavior impact.
- Use `exhaustive-code-slimmer` when the user wants a fresh deletion-first slimming pass instead of a response to an existing thermo report.

## Non-Negotiables

- Build a disposition ledger before editing code.
- Verify harsh review language against current code, current diff, line counts, call sites, ownership boundaries, canonical helpers, tests, configs, and project constraints.
- Prefer the narrowest behavior-preserving simplification that resolves the structural risk.
- Resolve size-pressure findings by reducing the file's responsibility span or dependency burden. Do not accept a lower line count as sufficient evidence.
- Treat a cohesive extraction that stays inside both the current package and architectural layer as scoped cleanup when behavior and public contracts stay unchanged. Pause before crossing either boundary, changing a public API/type/state model, replacing a framework, reshaping the project layout, or collapsing a large abstraction unless the user has approved that scope.
- Preserve Git staging. Do not run `git add`, `git add -A`, `git add -p`, `git add -N`, `git commit`, `git commit --amend`, or index-mutating equivalents unless the current request explicitly asks for staging, committing, or PR publication.
- If staged changes already exist, preserve them exactly. Keep new fixes unstaged.

## Intake Workflow

1. Read the full report, including `Scope`, `Review Snapshot`, `Complete Findings Index`, severity sections, `Questions`, `Decomposition Gaps`, recursive ledgers, line-count ledgers, sweep logs, blind spots, evidence, and self-checks.
2. Confirm the report still applies to the current checkout, branch, diff, baseline, and user-requested scope.
3. Stop and regenerate or clarify before editing when scope, baseline, completion status, line counts, or item enumeration is stale or inconsistent.
4. Build the disposition ledger:
   - every `F#` in `Complete Findings Index`
   - every finding card in `Blocker`, `Major`, `Minor`, and `Questions`
   - every standalone `D#` in `Decomposition Gaps`
   - every recursive coverage row marked `Finding F#`, `Not covered`, unknown, or ambiguous
   - every line-count row marked `crossed 350`, `already over 350`, `Finding F#`, `not covered`, or `waived with reason`, including any boundary diagnosis or its absence
   - every candidate sweep row marked `Finding F#`, `merged into F#`, `not covered`, or ambiguous
   - any mismatch between indexes, cards, ledgers, sweep logs, line counts, and self-checks
5. Restate each item as a concrete structural risk: maintainability, future-change cost, ownership drift, type-contract muddiness, oversized-file pressure, duplicated concept, or unnecessary reasoning load.
6. Verify each item before deciding its disposition: fix, disprove, narrow, downgrade, justify waiver, answer question, close gap, keep open, or ask for clarification.

## Regression Guard

Before editing, build a small behavior-parity ledger for every file or module the fix may touch.

Classify each touched surface as:

- `User-visible`: route, component, command, API response, persisted write, email/export/output, job, config default, flag path, or permission/session behavior.
- `User-visible dependency`: helper, adapter, type, parser, formatter, query, cache key, retry path, or state transform feeding a visible surface.
- `Not user-visible`: tests, docs, generated-only, fixture-only, or dead code with evidence.
- `Unknown impact`: any path whose visible effect cannot be traced locally.

For each `User-visible`, `User-visible dependency`, or `Unknown impact` surface, compare the planned before/after path:

- Source parity: does visible behavior still read from the same input, state slice, request field, serialized form, fixture, env var, or feature flag?
- Guard parity: do auth, permission, validation, debounce, duplicate-submit, confirmation, retry, ordering, empty-state, and error guards still run before the effect?
- Output parity: does the final renderer, API response, CLI text, exporter, email body, request builder, or persisted record still receive the expected shape and format?
- Extension-point parity: if a local override, callback, prop, branch, or special case is removed, what preserves the same behavior?
- Intent split: are structural cleanup and intentional product-visible behavior changes separated and named?

Record each surface as `Preserved`, `Intentional change`, `Potential regression`, or `Not covered`.

Do not hide behavior risk behind passing typecheck, lint, or unrelated tests. If behavior parity is uncertain, either run targeted verification, narrow the structural fix, invoke `regression-review`, or carry the uncertainty forward explicitly.

## Pre-Edit Plan

Before changing code, tell the user:

- which ledger items will be fixed, disproven, narrowed, waived, or carried forward
- the exact files/modules likely to change
- why the fix is behavior-preserving or which visible changes are intentional
- which behavior-parity surfaces need verification
- for each threshold item, the current responsibility map, proposed owner or seam, and before/after dependency direction
- whether each proposed split is contract-preserving local cleanup or an approval-gated boundary change
- which line counts or structural ledgers will be recomputed
- which tests, runtime checks, output inspections, or static traces will be run
- that Git staging will remain untouched unless staging or publishing was requested

## Item Handling

### `Blocker`

Treat as do-not-merge until fixed, disproven, narrowed below blocker severity, or explicitly justified.

- Verify the structural failure and why it blocks maintainable change.
- Prefer behavior-preserving simplification, decomposition, ownership correction, or type-boundary clarification.
- Disprove or downgrade only with stronger evidence than the report has.

### `Major`

Treat as fix or answer before approval.

- Verify maintainability, abstraction, ownership, type-contract, duplication, or decomposition risk.
- Apply focused fixes that delete complexity or clarify ownership.
- Promote to `Blocker` if verification shows serious ongoing delivery risk.

### `Minor`

Treat as decide-and-record.

- Fix when mitigation is cheap and reduces reasoning cost without broad churn.
- Carry forward when impact is low, the fix is noisy, or approved broader work should own it.
- Keep the item in the final ledger either way.

### `Question`

Treat as approval-affecting missing context.

- Answer with local evidence, specs, architecture notes, ownership conventions, or user clarification when possible.
- Convert to a fix, disproof, waiver, or carried-forward open question.

### `Decomposition Gaps`

Treat standalone `D#` rows as structural review items.

- Verify whether extraction, module split, helper reuse, state-model cleanup, or type-boundary clarification reduces net reasoning cost.
- Close a gap only when behavior remains preserved and verification is clear.
- Carry forward broad boundary work with owner, scope, and trigger instead of starting an unapproved architecture refactor.

### Recursive Ledgers And Sweep Logs

Treat recursive coverage and candidate sweep rows as gate evidence.

- Ensure every `Finding F#` and `merged into F#` row maps to the disposition ledger.
- Challenge `Not review-relevant` only when the path affects maintained source structure, ownership, type contracts, duplication, tests, config, generated output, or visible behavior.
- For `Not covered` or ambiguous rows, run the missing trace, refresh the gate, or carry a concrete next step.

### Line Count Ledger

Treat the 350-line threshold as a structural signal, not a mechanical ban.

- Recompute current line counts before fixing or waiving a threshold item.
- Before choosing a remedy, map the file's independent reasons to change, shared state, side effects, callers, callees, dependency clusters, and concepts with an existing canonical owner.
- When responsibilities are mixed, prefer returning a complete concern to its canonical owner or extracting one domain, policy, state, adapter, presentation, or orchestration responsibility behind a narrow contract. Delete code only when current evidence independently proves it redundant.
- Accept a split only when the original file owns less, the destination has a clear domain purpose, dependencies stay one-way without cycles, and the change does not create another mixed-responsibility hotspot.
- Reject dense formatting, compressed control flow, shortened names, removal of useful documentation or types, line-range extractions, thin forwarding modules, and moves into catch-all `utils`, `helpers`, or `common` files. None of these closes a threshold item.
- For `crossed 350`, implement the smallest cohesive, behavior-preserving separation available within scope or document a defensible cohesive-file waiver. Crossing back below the number is supporting evidence, not the acceptance criterion.
- For `already over 350`, avoid adding another responsibility; place new behavior with its rightful owner or narrow an existing responsibility when the approved scope permits it. If a cohesive file still grows, refresh its waiver against the added behavior.
- Perform an extraction without additional approval only when it remains inside both the current package and architectural layer and keeps public contracts and dependency direction stable. Carry forward work that crosses either boundary with its proposed scope, risk, and verification plan when approval is still needed.
- Exclude generated files, lockfiles, vendored artifacts, snapshots, fixtures, and intentionally monolithic external formats unless manually maintained source.

## Push Back When

- The report was generated for a different scope, stale branch, stale baseline, or stale line count.
- Completion is incomplete but presented as resolved.
- Indexes, severity sections, decomposition gaps, ledgers, sweep logs, and self-checks disagree.
- The suggested simpler path broadens behavior, moves architecture boundaries, weakens contracts, or merely relocates or compresses code without reducing structural load.
- The alleged oversized file is generated, vendored, fixture-like, or intentionally external-format code.
- The alleged duplicated or misplaced logic is actually the canonical owner.
- Current code, call sites, tests, docs, project conventions, or behavior-parity tracing contradict the report.
- A `Not covered` row requires credentials, data, platform access, or runtime setup that is unavailable.

Push back with evidence: code path, line count, owner, canonical helper, behavior trace, command output, test, fixture, or doc.

## Implementation Order

1. Clarify stale or unclear scope.
2. Build the disposition ledger and behavior-parity ledger.
3. Resolve report inconsistencies and stale line counts.
4. For every threshold item, map responsibilities and dependency seams and classify the remedy as local or approval-gated.
5. Present the pre-edit plan.
6. Fix or disprove unresolved `Blocker` items.
7. Resolve `Major` items with focused fixes, proof, waiver, or carry-forward decisions.
8. Decide `Minor` and `Question` items.
9. Close or carry forward standalone `D#` gaps and open coverage rows.
10. Recompute affected line counts.
11. Run targeted structural and behavior verification for every touched surface.
12. Refresh the thermo gate or update the reviewer with concrete evidence when structure, coverage, line counts, or decomposition materially changed.

## Final Ledger

Use this shape when multiple items were consumed:

```md
| ID / area | Original status | Disposition | Structural evidence | Behavior / regression evidence | Next action |
| --- | --- | --- | --- | --- | --- |
| F1 | Blocker | Fixed | Moved discount policy into a cohesive domain owner; checkout now owns orchestration only, dependencies remain one-way, and the file dropped from 382 to 319 lines. | Submit source, duplicate-submit guard, and persisted payment payload are unchanged; checkout tests pass. | None |
| F2 | Major | Narrowed | Shared adapter is the canonical owner; only the local wrapper was unnecessary. | API response shape is unchanged by static trace. | Remove wrapper |
| D1 | Decomposition gap | Carried forward | Requires approved boundary change across three packages. | Not edited, so no behavior delta. | Propose scoped refactor |
| app/page.tsx | Crossed 350 | Waived | Generated route table; not manually maintained source. | Not user-visible source logic. | Keep excluded |
| Payment state candidates | Not covered | Open | Requires staging event logs not available locally. | Behavior parity not covered; risk remains unknown. | Regenerate with logs |
```

Mention changed files are left unstaged unless the user asked otherwise.

## Response Style

Use short technical acknowledgments:

- `F1 still applies. The new branch duplicates the existing policy path, so I am deleting the wrapper and reusing the canonical helper.`
- `F2 is narrower than reported. The file remains over 350 lines, but this diff returns formatting policy to its canonical owner and leaves the route with one fewer reason to change.`
- `D1 requires a cross-package boundary move. I am carrying it forward instead of starting an unapproved architecture refactor.`
- `The state-machine candidate was Not covered; local fixtures do not exercise it, so I am leaving a concrete verification step.`
- `The planned extraction touches checkout output formatting, so I am adding it to the behavior-parity ledger before editing.`

## Common Mistakes

- Processing only `Must-review now` and ignoring the complete findings index.
- Treating `D#`, line-count rows, sweep rows, or open coverage rows as background.
- Starting broad architecture refactors without approved scope.
- Treating a denser layout, compressed control flow, or a lower count as proof that structural pressure is gone.
- Moving code into an arbitrary dumping ground or thin forwarding layer instead of extracting a coherent responsibility.
- Dismissing structural findings only because tests pass.
- Ignoring source, guard, output, or extension-point parity during structural cleanup.
- Staging fixes without an explicit current staging, commit, or PR request.
- Claiming the thermo gate is resolved without accounting for every structural item and every behavior-parity risk.
