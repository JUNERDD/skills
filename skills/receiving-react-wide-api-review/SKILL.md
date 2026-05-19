---
name: receiving-react-wide-api-review
description: >-
  Consume a coverage-led `react-wide-api-review` Markdown report, PR feedback derived from one, or a request to address `Block`, `Discuss`, `Watch`, `Intentional Exceptions`, `Complete Wide-API Index`, `Field-Flow Ledger`, `Recursive Coverage Ledger`, `Not covered`, pass-through, context fan-out, hook return, hook options, form controller, table/grid controller, selector, or coverage-gap items. Use when verifying whether each reported wide React/TypeScript API problem still applies, then fixing, disproving, narrowing, confirming, or carrying forward every item with evidence using AST-first verification when available while leaving Git staging untouched unless the user explicitly asks for staging, committing, or PR publication in the current request.
---

# Receiving React Wide API Review

## Overview

Use this skill after `react-wide-api-review` has produced a recursive coverage-led report.

Treat the report as an evidence-backed API-boundary review artifact, not as a blind instruction list. The primary job is to account for every `F#` finding, every `I#` intentional exception, every `Field-Flow Ledger` row with unresolved status, and every `Recursive Coverage Ledger` row marked `Not covered`, `Finding F#`, `Intentional Exception I#`, or unknown before claiming the wide-API gate is resolved.

## Skill Boundary

- Use `react-wide-api-review` to create or refresh the report.
- Use `receiving-react-wide-api-review` to consume the report and decide what to do next.
- Use a general React refactor skill when there is no report, no enumerated findings, and no wide-field API gate to close.
- Use a general performance skill when the only issue is measured slowness without props/hook/context field-flow concerns.

## Core Principles

Build a disposition ledger before editing code.

Before changing code, state a concrete change plan and self-assess whether the plan can:

- introduce behavioral regressions
- broaden the refactor beyond the reviewed scope
- weaken field ownership boundaries
- convert a bounded exception into a sweeping rewrite
- create a new wide API while removing the old one
- introduce user-visible UI regressions or product-facing behavior changes
- change Git staging state

Name the affected boundaries, why the plan is scoped, what verification will be needed, and that any fixes will remain unstaged unless the user explicitly requested staging or publication.

Never treat a prop-count complaint as automatically correct. Verify the current field-flow and ownership model first. When AST, language-server, parser, or repository code-intelligence capabilities are available, use them before regex or heuristic scanning to verify structural claims and dispositions.

When the agent or environment has AST capability, verify findings with AST before relying on grep-style searches. Prefer type-aware AST for symbol identity, props/hook/context shapes, aliases, and consumers; use syntax AST for reads, destructuring, JSX edges, object spreads, dependency arrays, and returned object literals. Use code search and heuristic scripts as candidate discovery or fallback only. See `references/ast-verification.md`.

## User-Visible UI Behavior Preservation Gate

For React wide-API fixes, the accepted change must narrow ownership while preserving externally observable behavior.

- Before editing code, define the strongest available behavior-preservation oracle for the affected UI surface: build, typecheck, lint when relevant, focused tests, interaction smoke tests, route/API contract checks, visual/snapshot checks, accessibility checks, or manual reproduction steps supported by the repository.
- Treat rendered copy, visible data, routes, loading/empty/error states, form validation semantics, focus behavior, keyboard interaction, accessibility semantics, ordering, filtering, selection state, permissions, and persistence behavior as protected user-visible behavior.
- Do not change protected UI behavior to make a wide-API finding easier to fix unless the user explicitly approves that product-facing change in the current request.
- If the report recommends a boundary change but the UI behavior oracle is weak or missing, keep the fix smaller, add a targeted smoke/characterization check when feasible, or carry the risk forward instead of claiming a clean gate.
- Passing lint or typecheck is not enough to prove user-visible UI behavior is preserved. State what the oracle protects and what remains outside it.

## Git State Hard Gate

Treat the Git index as user-owned state. Consuming a review report is not permission to prepare a commit.

- Do not run `git add`, `git add -A`, `git add -p`, `git add -N`, `git commit`, `git commit --amend`, or equivalent index-mutating commands unless the user's current request explicitly asks for staging, committing, or PR publication.
- Do not stage files after editing just to make a follow-up review, `git diff --cached`, commit message, or PR body easier.
- If there are already staged changes when you start, inspect them only as needed and preserve them exactly.
- Keep new fixes unstaged so they do not get mixed into the user's staged set.
- If the report was generated from a staged diff and the fix changes code, do not update the staged diff yourself. Explain that the fix is present in the working tree and ask before staging or regenerating a staged-diff gate.
- If a tool would stage files as a side effect, do not use it.
- If you accidentally stage changes, stop immediately, unstage only your own additions when that can be done without disturbing pre-existing staged work, and report what happened.

## Gate Integrity Rules

- Treat `Complete Wide-API Index` as the enumeration source for findings.
- Treat `Field-Flow Ledger` as the enumeration source for relevant fields, field groups, flow categories, and proposed owners.
- Treat `Recursive Coverage Ledger` as the enumeration source for reviewed, intentional, not-relevant, and uncovered boundaries.
- Treat `Not covered` rows on implementation-relevant or unknown boundaries as unresolved gate items until they are covered, regenerated, or explicitly accepted as out of scope.
- Verify the current field ownership model before implementing a fix.
- Do not dismiss a `Block` item without stronger counter-evidence than the report has.
- Do not refactor an `Intentional Exception` into a broad redesign unless product or architecture intent changed.
- Do not treat lint, typecheck, or unrelated passing tests as proof that a wide API is safe.
- Do not remove necessary external or legacy guards merely because the report called out a nearby wide internal boundary.
- Do not claim completion while any indexed finding, intentional exception, field-flow row, or coverage gap lacks a disposition.

## Response Pattern

When receiving a React wide API review report:

1. Read the full report, including `Scope`, `Gate Snapshot`, `Complete Wide-API Index`, `Block`, `Discuss`, `Watch`, `Intentional Exceptions`, `Field-Flow Ledger`, `Recursive Coverage Ledger`, `Evidence Appendix`, and `Report Self-Check` when present.
2. Confirm the report still applies to the exact scoped change set or codebase slice the user asked to address.
3. Build a disposition ledger before changing code:
   - add every `F#` from `Complete Wide-API Index`
   - add every finding card from `Block`, `Discuss`, and `Watch`
   - add every `I#` from `Intentional Exceptions`
   - add every `Field-Flow Ledger` row whose status is `Finding F#`, `Intentional I#`, `Not covered`, `Unused or unverified`, or unknown
   - add every `Recursive Coverage Ledger` row whose status is `Not covered`, `Finding F#`, `Intentional Exception I#`, or unknown
   - add mismatches between the index, action sections, and ledgers as intake problems
4. Stop and regenerate or clarify the report before implementing when scope, baseline, completion, field ownership, or finding enumeration is stale or inconsistent.
5. Restate each `F#` as a concrete API-boundary liability, not merely as a code edit.
6. Verify each item against current code, field-flow, context consumers, hook callers, tests, runtime behavior, search results, and ownership boundaries. Prefer AST/language-server/parser evidence for symbol references, props shape, field reads, destructuring, spreads, hook calls, provider values, and dependency arrays when available. If AST is available, rebuild the relevant field-flow map with AST before changing code or disproving the item.
7. Decide each disposition:
   - `Fixed`
   - `Disproved`
   - `Narrowed`
   - `Downgraded`
   - `Confirmed intentional exception`
   - `Closed coverage gap`
   - `Carried forward`
   - `Needs clarification`
8. Before editing code, state the intended change plan, regression/ownership-risk self-assessment, UI behavior-preservation oracle, and no-staging intent.
9. Address items in gate order and verify each affected boundary before moving on.
10. End with a concise disposition ledger that accounts for every consumed report item.
11. Refresh the gate by rerunning `react-wide-api-review` or updating the reviewer with concrete evidence when changes materially alter the implementation strategy or coverage.

## Intake Checklist

Before changing code, confirm:

- Which scope was reviewed: working tree, staged diff, commit range, branch diff, PR, named component, named hook, named context, directory, or implementation slice.
- Whether that scope matches the user's current request exactly.
- Which baseline the report compares against.
- Whether the current checkout still matches that scope and baseline.
- Whether `Completion` is `Complete within reviewed scope` or `Incomplete`.
- Whether the report used AST-first, mixed AST/text, or heuristic text fallback analysis, and whether that method is strong enough for the dispositions being made.
- Whether every `F#` in `Complete Wide-API Index` has a matching card in `Block`, `Discuss`, or `Watch`.
- Whether every `Finding F#` in the field-flow and recursive coverage ledgers maps to a known finding.
- Whether every `Intentional Exception I#` maps to an intentional exception entry.
- Which `Not covered` rows affect implementation-relevant or unknown boundaries.
- Which broad object, hook return, context value, form controller, table controller, or callback bag the report points to.
- Which incumbent selector, schema, model, context, or hook owns the concern today.
- Which blind spots limit confidence.
- Whether the report used type-aware AST, syntax AST, heuristic search only, or manual inspection.
- Whether current verification can use stronger AST evidence than the original report.

If scope, baseline, completion status, owning abstraction, or item enumeration is stale or unclear, regenerate or clarify the report before implementing.

## Handle Each Item Type

### `Block`

Treat `Block` as "stop the change from shipping until fixed or disproven."

For each `Block` item:

- Reproduce the field-flow problem or trace the current code path strongly enough to show the report is still correct.
- Fix the ownership or subscription problem, or disprove the finding with stronger evidence than the report currently has.
- Do not skip to lower-severity cleanup while a real `Block` item remains unresolved.

Valid outcomes:

- narrow the leaf props or introduce a field-level selector
- split context by domain/update frequency
- split a hook return into `value/meta/status/actions`
- replace whole-object effect dependency with concrete dependencies
- replace callback explosion with a typed command/dispatch
- prove the reported broad surface is a bounded schema adapter or compatibility layer
- prove the current code no longer has the reported pass-through/subscription path

### `Discuss`

Treat `Discuss` as "resolve uncertainty before approval."

- Clarify intent when a wide API may be a deliberate schema adapter, generated type, migration shim, or design-system boundary.
- Gather the missing proof the report asked for.
- Prefer focused verification over speculative rewrites.
- Promote to `Block` if verification proves a serious ownership or subscription risk.
- Downgrade to `Watch` or `Intentional Exception` only with concrete evidence.

### `Watch`

Treat `Watch` as "note it, then decide whether cheap mitigation is worth it."

- Add a targeted test, owner note, TODO with exit trigger, follow-up task, or small local narrowing when useful.
- Avoid unnecessary churn when the risk is minor and already understood.
- Keep the item in the final disposition even when no code change is made.

### `Intentional Exceptions`

Treat intentional exceptions as protected wide surfaces unless evidence says otherwise.

- Confirm scope, owner, and exit condition against design docs, schema contracts, issue text, PR description, migration notes, or user instruction.
- Leave the code alone if the exception is deliberate and bounded.
- Move it back into `Discuss` only when intent is unclear, the exception has grown beyond scope, or the exit condition is gone.
- Do not refactor the exception away merely to silence the report.

### `Field-Flow Ledger`

Treat field-flow rows as gate evidence, not background notes.

- For `Directly consumed`, verify the boundary owns the field.
- For `Passed through`, verify whether the pass-through is necessary or should be narrowed.
- For `Spread propagated`, replace with named props or prove the spread is a bounded adapter.
- For `Effect-bound`, verify exact dependencies and side-effect lifecycle.
- For `Context-propagated`, inspect provider and consumer width.
- For `Hook-return propagated`, inspect destructuring and downstream pass-through.
- For `Callback/action`, determine whether a command boundary is safer.
- For `Selector candidate`, decide whether a selector/field hook can close the issue.
- For `Unused or unverified`, search current code or carry forward as a coverage gap.

### `Recursive Coverage Ledger`

Treat coverage rows as the proof of review completeness.

- For `Finding F#`, verify the referenced finding is in the disposition ledger.
- For `Intentional Exception I#`, confirm or challenge the exception.
- For `Reviewed - no wide-API risk found`, leave the row alone unless current code or new evidence contradicts it.
- For `Not wide-relevant`, challenge the classification if the boundary owns field shape, subscription, render state, context, hook options, hook return, form, table, or selector behavior.
- For `Not covered`, either perform the missing trace, regenerate the gate for that boundary, or carry it forward with a concrete next step.

## AST-First Verification

When AST, language-server, parser, or project-owned static-analysis tools are available, use them before text search to verify whether a finding still applies. Confirm definitions, aliases, JSX call sites, spreads, destructuring, property reads, hook arguments, hook return consumption, provider values, context consumers, and dependency arrays structurally. Use `references/ast-verification.md` for the detailed protocol.

If only text search or heuristic scripts are available, keep confidence lower for alias-heavy, spread-heavy, HOC-wrapped, computed-key, generated-schema, or re-export-heavy paths. Do not mark a finding as disproved when the missing proof requires AST resolution.

## Verify Common Wide-API Leads Carefully

### Flat component props, local destructuring, or direct reads

- Treat a large destructuring block, inline props object type, broad file-local props type, or many `props.foo` reads as a candidate boundary, not proof of a defect by itself.
- Verify which fields are rendered locally, which callbacks/actions belong together, and which fields are only passed through to children.
- Prefer grouping by owned UI concern, section view model, status, permissions, and actions when that reflects actual consumption.
- Avoid replacing one long prop list with an opaque `data` or `options` bag that hides the same field-flow problem.
- When grouped props cross memoized children or dependency arrays, verify referential identity or split the group by change frequency.

### Leaf receives whole domain/form/table object

- Identify what the leaf actually reads.
- Check whether a field-level hook, selector, or local view model exists.
- Narrow the leaf boundary first; do not start with a whole-feature rewrite.

### Context fan-out

- Inspect provider value creation.
- Search consumers and classify which fields each consumer reads.
- Split by domain or update frequency only when consumers are over-subscribed.
- Keep stable actions separate from volatile state when appropriate.
- For high-frequency or large state, prefer selector-capable stores, `useSyncExternalStore`, context selectors, or field hooks over plain broad context.

### Hook return bag

- Inspect callers and downstream props.
- Group return values by `value`, `meta`, `status`, `permissions`, and `actions` when that matches usage.
- Pass only the groups each child owns rather than moving the original flat bag into several broad bags.
- Stabilize actions only when identity matters.

### Hook options object

- Inspect effects inside the hook.
- Replace whole-object dependencies with concrete fields or create the object inside the effect.
- Do not require callers to `useMemo` broad options if the hook can depend on narrower fields.

### Callback explosion

- Verify that callbacks share one command boundary.
- Use typed `changeField` or reducer dispatch when the callbacks encode field updates.
- Preserve field/value type correlation in action types.
- Preserve type safety; do not collapse to `string, unknown` unless the field set is truly dynamic.

### Spread pass-through

- Replace broad spread with named props at the boundary where ownership changes.
- Keep spread only when it is a deliberate bounded adapter and does not hide field ownership.

### Duplicate view model or selector

- Search for the incumbent selector, schema, domain model, or store slice.
- Reuse or extend the incumbent owner when it still owns the concern.
- If the new model is better, migrate callers and retire the old one rather than keeping two accidental truths.

## When to Push Back

Push back when:

- The report was generated for a different scope or stale branch.
- The report silently widened beyond the user-requested range.
- The report is incomplete but presents the gate as resolved.
- `Complete Wide-API Index`, action sections, `Field-Flow Ledger`, and `Recursive Coverage Ledger` disagree.
- The alleged wide API is a deliberate generated schema, external adapter, or migration layer with owner and exit condition.
- AST or language-server evidence proves the alleged field-flow no longer exists or was narrower than the report claimed.
- The alleged leaf over-subscription is actually a selector boundary.
- The alleged duplicate model owns a materially different boundary.
- Current runtime, output, search, or ownership evidence contradicts the report.
- A `Not covered` row requires context, credentials, generated code, package access, platform access, or runtime setup that is not available.

Push back with evidence, not tone:

- cite the current code path, field-flow trace, provider/consumer search, runtime result, or owning abstraction
- state what the report got right and what no longer applies
- say what verification would settle the disagreement if proof remains incomplete

## Implementation Order

For multi-item reports:

1. Clarify stale or unclear scope first.
2. Regenerate the report if it does not match the user's exact review range.
3. Build the disposition ledger from the index, action sections, intentional exceptions, field-flow ledger, and recursive coverage ledger.
4. Resolve report inconsistencies or stale coverage before code changes.
5. Present the change plan, regression/ownership-risk self-assessment, UI behavior-preservation oracle, and no-staging intent.
6. Fix or disprove every unresolved `Block` item.
7. Resolve `Discuss` items with proof or intent clarification.
8. Decide whether `Watch` items need mitigation now.
9. Confirm or challenge `Intentional Exceptions`.
10. Close or explicitly carry forward `Not covered` implementation-relevant or unknown boundaries.
11. Re-run targeted verification for every touched boundary.
12. Refresh the wide-API gate if your changes materially alter the implementation strategy or coverage.

## Disposition Ledger Format

Use this shape in the final response or report update when multiple items were consumed:

```md
| ID / boundary | Original status | Disposition | Evidence | Next action |
| --- | --- | --- | --- | --- |
| F1 | Block | Fixed | `EmailField` now receives `EmailFieldModel`; whole `form` no longer crosses leaf boundary. | Re-run targeted field trace |
| F2 | Discuss | Narrowed | Provider still combines auth and permissions, but all consumers read both; theme split remains open. | Carry theme split as Watch |
| I1 | Intentional Exception | Confirmed | Generated table schema adapter has owner and migration note. | Leave unchanged |
| `NotificationContext consumers` | Not covered | Closed coverage gap | Searched all `useNotificationContext` consumers; no unrelated domain reads found. | None |
```

Keep it concise, but account for every report item.

## Response Style

Use short technical acknowledgments.

Good:

- `F1 still applies on the current diff. The form object is passed through two layers and the leaf only reads email-specific fields. Narrowing the field boundary.`
- `F2 is narrower than reported. The options object is stable config and is not used as an effect dependency, so downgrading to Watch.`
- `I1 is a bounded generated-schema adapter with an owner and exit trigger. Leaving it unchanged.`
- `The provider consumer boundary was marked Not covered; current local package does not include the consumer app, so carrying it forward with a concrete downstream search.`

Avoid performative agreement or blind execution.

## Common Mistakes

- Treating the report title as the bug instead of the underlying field ownership problem.
- Processing only the top items in `Gate Snapshot` and ignoring `Complete Wide-API Index`.
- Ignoring `Field-Flow Ledger` rows that are not attached to a finding.
- Treating `Not covered` rows as harmless notes.
- Deleting a broad prop without providing the correct narrower owner.
- Replacing one flat bag with another bag named `data` or `options`.
- Adding `useMemo`/`useCallback` everywhere without narrowing the boundary.
- Splitting intentional schema adapters into unmaintainable primitives.
- Changing visible UI behavior while claiming the work is only a field-boundary refactor.
- Downgrading a `Block` item without stronger evidence.
- Staging fixes after editing code without a current explicit staging, commit, or PR request.
- Folding new fixes into an already staged diff while consuming the report.
- Claiming the gate is clean without accounting for every `F#`, `I#`, field-flow row, and open coverage row.

## Bottom Line

A React wide API review report is a recursive coverage-led gate artifact. Consume it like a strong reviewer: verify the current field-flow and ownership model, preserve severity semantics, account for every finding and ledger row, then fix, challenge, narrow, confirm, or carry each item forward with evidence.

## References

- Use `references/disposition-template.md` for final ledger/report updates.
- Use `references/fix-patterns.md` for safe implementation patterns.
- Use `references/ast-verification.md` for AST-first report verification.
- Use `references/verification.md` for targeted verification.
- Use `references/report-intake.md` for report consistency checks.
