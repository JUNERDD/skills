---
name: react-wide-api-review
description: Perform a scoped, coverage-led, deep recursive review of React and TypeScript APIs whose field counts are too large, including oversized component props, hook parameters, hook return objects, context values, form controllers, table/grid configs, view models, callback surfaces, and domain-model pass-through chains. Use when users ask for deep recursive inspection, repo-level review, field-flow tracing, pass-through tracing, component tree analysis, hook consumption analysis, context fan-out analysis, selector opportunities, or an AST-first Markdown gate report for excessive React API field counts.
---
# React Wide API Review

## Overview

Treat the target code as a scoped wide-API architecture audit. The primary job is to recursively trace how fields move through React components, custom hooks, contexts, form controllers, view models, and child boundaries, then write a Markdown report that accounts for every reviewed wide API surface, every distinct field-flow liability, every intentional exception, and every coverage gap.

This skill is for producing or refreshing the review report. Use `receiving-react-wide-api-review` to consume the report, verify each finding, and implement or challenge fixes.

The focus is field-count explosion, not object byte size. When AST, language-server, parser, or repository code-intelligence capabilities are available, use them before regex or heuristic scanning for structural claims. Do not treat a large object as a problem merely because it is large. Treat it as a problem when too many fields cross a boundary, too many consumers can observe unrelated changes, ownership is unclear, React memoization boundaries are defeated, hook dependencies become unmanageable, context fan-out grows, or leaf components receive domain objects they do not own.

## Skill Boundary

- Use `react-wide-api-review` to create or refresh a scoped review report.
- Use `receiving-react-wide-api-review` to consume an existing report and decide what to change.
- Do not edit production code while producing the review report unless the user explicitly asks for a patch as part of the same request. Prefer a report-only audit.
- Do not use this skill for general React performance review unless the performance concern is tied to excessive API field counts, wide subscriptions, context fan-out, or hook return breadth.
- Do not use this skill for purely cosmetic prop naming complaints. Findings must be tied to ownership, field-flow, maintainability, or measurable review risk.

## Set Scope First

Prefer an explicit scope from the user: working tree, staged diff, commit range, branch diff, pull request, named component, named hook, named context, named module/package, or whole repository.

Strictly honor the user-specified scope. Do not silently widen a component-level request to the whole repository. If no scope is provided and the environment is a git repository, default to the staged diff. If there is no staged diff and no explicit scope, ask whether to review the working tree, last commit, branch diff, named component/hook/context, or whole repository.

If the requested scope is too large to review completely in one pass, do not silently sample it. Review the highest-risk entry surfaces first, mark the report `Incomplete`, list the exact files, components, hooks, contexts, or flow boundaries not covered, and set the recommendation no lower than `Discuss` unless the uncovered area is demonstrably not React API relevant.

## Completeness Contract

The report must account for every implementation-relevant or unknown wide-API boundary in the reviewed scope.

Maintain two ledgers:

- `Field-Flow Ledger`: maps every relevant field or field group to its source, flow category, direct consumer, pass-through path, proposed owner, and status. Use flow categories such as `Directly consumed`, `Passed through`, `Spread propagated`, `Derived`, `Effect-bound`, `Memo-bound`, `Context-propagated`, `Hook-return propagated`, `Callback/action`, `Selector candidate`, `Unused or unverified`, and `Out of scope`.
- `Recursive Coverage Ledger`: maps every reviewed component, hook, context, form controller, table/grid config, view model, reducer state surface, callback surface, provider value, selector boundary, adapter, and recurring pass-through path to one of `Finding F#`, `Intentional Exception I#`, `Reviewed - no wide-api risk found`, `Not wide-api relevant`, or `Not covered`.

Do not stop after the top three findings. The `Must-review now` list is only a priority preview. The `Complete Wide-API Index` and the action sections must include every distinct finding discovered within the reviewed scope.

If a candidate issue is investigated and dismissed, record the dismissal in the evidence appendix when it explains coverage or prevents duplicate review.

If token budget, missing files, parser limitations, unavailable runtime context, or repository size prevents complete coverage, state exactly where coverage stopped. A partial review must not be presented as complete.

## Review Actions

Use these action labels as the primary classification.

### `Block`

Strong evidence that the API surface creates a structural liability that should stop the change before merge or release.

Typical examples:

- A leaf or section component receives a full domain model and passes it through multiple levels while consuming only a few fields.
- A hook returns a flat bag of dozens of fields, and downstream effects or memoized children depend on the whole object.
- A context provider exposes many unrelated domains, causing broad consumer invalidation.
- A wide form controller is passed to every field, making field-level updates fan out across the whole form.
- A new wide API duplicates an existing selector, adapter, or view-model owner.
- A spread pass-through hides which fields are actually required and prevents safe refactor.

### `Discuss`

The API smells too wide, but intent, ownership, update frequency, migration status, blast radius, or the better boundary is still unclear. A reviewer should resolve uncertainty before approval.

### `Watch`

The field-count problem or pass-through debt is real, but bounded enough that approval may proceed with a caveat, follow-up, targeted test, selector extraction, or TODO with an owner and exit trigger.

### `Intentional Exception`

The wide surface appears deliberate, bounded, and documented enough that it should not be framed as an accidental API problem. Examples include stable public library API compatibility, schema-driven renderer inputs, controlled migration shims, or third-party adapter contracts.

Do not use `confirmed`, `probable`, or `possible` as top-level groupings. Keep confidence as evidence language inside cards.

## Recommendation Mapping

Use the top-level `Recommendation` field in `Gate Snapshot` with this exact mapping:

- If any unresolved finding is `Block`, the report recommendation must be `Block`.
- Else if any unresolved finding is `Discuss`, the report recommendation must be `Discuss`.
- Else if coverage is incomplete for an implementation-relevant or unknown boundary, the report recommendation must be `Discuss`.
- Else if any unresolved finding is `Watch`, the report recommendation must be `Pass with caveat`.
- Else use `Pass`.

Do not write `Pass with caveat` when a `Discuss` item or implementation-relevant coverage gap is still open. Do not write `Discuss` when the body contains no `Discuss` items and no incomplete implementation-relevant coverage.

## What Counts As One Finding

Count one item per distinct field-flow or ownership liability, not per file, component, prop, hook, or repeated syntax pattern.

Merge candidates when they express the same liability across one boundary. Split candidates when different owners, update frequencies, consumer groups, or failure modes are affected.

Examples:

- One wide `UserEditorProps` passed through `UserEditorView` into three sections may be one finding if the liability is a single pass-through boundary.
- The same `UserEditorProps` also placed into a global context is a separate finding because the fan-out and consumer invalidation are different.
- Ten callbacks in one component may be one finding if they can be replaced by one typed command boundary.
- A hook returning 40 fields and a context exposing those same fields are separate findings if each creates independent consumer risk.

## Evidence Standard

Prefer the strongest feasible evidence for the suspected wide-API liability. When AST, language-server, parser, or repository code-intelligence capabilities are available, use them before regex-style tracing. Prefer type-aware AST when practical, then syntax AST, then text search and heuristic scripts.

Use AST or language-server evidence for structural facts such as symbol resolution, props shape, call-site tracing, JSX edges, destructuring, property reads, object spreads, hook calls, hook return consumption, provider values, context consumers, dependency arrays, imports/exports, aliases, and wrappers such as `memo` or `forwardRef`.

Use text search and bundled scripts as candidate generators, cross-checks, and fallback tools. They are not final authority for field-flow conclusions when AST can resolve the same relationship.

Label evidence as `AST-verified`, `AST-inferred`, `Text-fallback`, `Runtime-observed`, or `Unknown / not covered` when confidence depends on the analysis mode. See `references/ast-first-analysis.md`.

Search the codebase for the current owner of the view model, selector, form field subscription, table config, context, or domain adapter before calling something a duplicate or bypass.

Separate verified facts from inferred maintenance or runtime risk. Do not present taste as evidence. Passing lint or typecheck proves syntax and type hygiene, not that the field-flow problem is resolved.

## User-Visible UI Behavior Preservation

For any review recommendation that could become a React UI refactor, the target is narrower field ownership without changing externally observable behavior.

- Treat user-visible UI behavior as protected unless the user explicitly asks for a product behavior change.
- Do not recommend a wide-API fix that would change rendered copy, visible data, routes, loading/empty/error states, form validation semantics, focus behavior, keyboard interaction, accessibility semantics, ordering, filtering, selection state, permissions, or persistence behavior unless that change is called out as product-facing and user-approved.
- When a finding needs implementation work, include the behavior-preservation oracle the receiving agent should use: build, typecheck, lint when relevant, affected tests, interaction smoke tests, visual/snapshot checks, accessibility checks, route/API contract checks, or manual reproduction steps supported by the repository.
- If no UI oracle exists for the affected surface, record that blind spot and keep the recommendation at least `Discuss` when the proposed boundary change could alter visible UI behavior.
- Separate "field ownership should be narrower" from "the UI should behave differently." A correct wide-API finding must be fixable as a behavior-preserving refactor unless the report explicitly frames the visible change as outside the wide-API gate.

## Deep Recursive Workflow

1. Define the scope and baseline.
   - Record the exact user-provided scope.
   - For git scopes, record the exact command or comparison baseline.
   - For component/hook/context scopes, record the entry symbol and files inspected.

2. Build a wide-surface inventory.
   - If AST is available, start with an AST inventory instead of regex scanning. Resolve component declarations, prop types, hook signatures, hook return shapes, context values, JSX call sites, object spreads, dependency arrays, imports, exports, and wrappers such as `memo` and `forwardRef`.
   - Identify components with many props.
   - Identify prop types, options types, config types, form controllers, table configs, view models, reducer states, and hook return types with many top-level fields.
   - Identify custom hooks with many positional parameters or wide object parameters.
   - Identify hooks that return large flat objects.
   - Identify contexts and provider values with multiple unrelated domains.
   - Identify JSX call sites with many explicit props or spreads.
   - Identify recurring callback surfaces.

3. Build the initial field-flow graph.
   - If AST is available, map symbols rather than strings: declaration -> local binding -> field read/destructure -> JSX outbound edge -> downstream declaration.
   - For each candidate boundary, list fields or field groups.
   - Classify each field as direct read, derived, effect-bound, memo-bound, callback/action, context-propagated, passed to child, spread through, selector candidate, unused, or unknown.
   - Record the file and line evidence where practical, and record parser/type-resolution gaps where AST cannot prove a path.

4. Recurse through pass-through paths.
   - Descend into child components when a field group, object, or spread is passed onward.
   - Descend into custom hooks when a wide object is passed as hook input.
   - Descend into hook consumers when a wide return object is passed onward or used as one dependency.
   - Descend into context consumers when a wide provider value is read.
   - Descend into field components when a form/controller object is passed.
   - Stop only at a documented stop condition.

5. Apply stop conditions explicitly.
   Stop recursion at primitive fields directly rendered by a leaf component, third-party components outside the project scope, generated files, stable public API compatibility boundaries, intentionally opaque schema renderers with documented field contracts, files outside the requested scope, or max-depth/tool-budget limits. Budget stops must be marked `Not covered`.

6. Classify boundaries as Container, View, Section, Leaf, Custom Hook, Hook Consumer, Context Provider, Context Consumer, Form Controller, Form Field, Table/Grid Config, Row/Cell Renderer, Selector/Store Boundary, Domain Adapter, View Model Builder, or Unknown.

7. Score and prioritize using `references/scoring-model.md`.

8. De-duplicate and write findings. Use one finding for one structural liability. Include a compact field-flow tree in the finding card or evidence appendix.

9. Write the report from `references/report-template.md`.

10. Run the report self-check.

## Analysis Tool Preference

Use this preference order when code is available:

1. Type-aware AST analysis when the agent or environment can build a TypeScript program for the scope.
2. Syntax AST analysis when type-aware resolution is unavailable.
3. The bundled heuristic scripts and targeted code search for candidate discovery or fallback.
4. Manual local inspection and runtime/profiler evidence for dynamic or parser-inaccessible paths.

Record which mode was used in the report. If AST is unavailable or incomplete, identify the limitation and its confidence impact instead of implying full recursive coverage.

## Script Usage

When AST tooling is not available, or when a quick candidate inventory is useful before AST/manual tracing, use scripts as candidate generators, not as final authority:

```bash
python skills/react-wide-api-review/scripts/react_wide_api_inventory.py ./src --format markdown
python skills/react-wide-api-review/scripts/react_wide_api_trace.py ./src --symbol UserEditor --symbol useUserEditor --field form
```

The scripts are intentionally heuristic. They can help identify wide types, component props from file-local types, inline object parameter types, destructuring, direct property reads, JSX call sites, hook parameters, hook return bags, provider values, simple pass-through edges, and symbol/field references. They do not replace AST field-flow tracing when AST is available, TypeScript ownership reasoning, or call-site inspection.

## Output Rules

Always write a Markdown report file.

Generate a fresh random id for each report filename, for example with `openssl rand -hex 4`, `uuidgen`, or an equivalent local source.

If the repository has an obvious location for reviews or reports, follow that convention, but append the random id immediately before `.md` unless the convention already guarantees unique filenames. Otherwise write to:

```txt
tmp/reviews/YYYY-MM-DD-react-wide-api-review-report-<id>.md
```

Do not overwrite an existing report. End with a short terminal summary that includes report path, recommendation, completion status, counts by action, top risks, and largest uncovered boundary if any.

## Card Format

Write each risk as a short review card, not as a spreadsheet row.

```md
### F1 Block - Wide form controller fans every field update through the whole editor

Engineering impact: Every field component can observe the whole form controller, so one field update can invalidate unrelated leaves and makes ownership of validation, dirty state, and commands ambiguous.

Review reason: The change passes `form` through `UserEditorView`, `ContactSection`, and `EmailField`, while `EmailField` only reads `values.email`, `errors.email`, and `setValue`.

Surface: User editor form boundary

Confidence: High

Look here first:
- [UserEditorView.tsx](/abs/path/src/UserEditorView.tsx#L42)
- [EmailField.tsx](/abs/path/src/EmailField.tsx#L17)

Field-flow:
```txt
useUserEditorForm() -> form[38 fields]
└─ UserEditorView form={form}
   └─ ContactSection form={form}
      └─ EmailField form={form}
         └─ reads only values.email, errors.email, setValue
```

Current ownership:
- The container owns the full form model.
- The field component only owns one field projection.

Recommended boundary:
- Keep the full controller in the container.
- Expose `useField('email')` or pass `FieldState + FieldActions` to the leaf.

Evidence:
- The leaf consumes three field-level members but receives the whole controller.
- No field-level selector or subscription boundary is present.

Reviewer action: Block until field-level ownership is restored or the wide controller is documented as an intentional schema renderer boundary.
```

## Writing Rules

- Start with the gate decision and completion status.
- Keep `Gate Snapshot` short enough to skim quickly.
- Limit `Must-review now` to the top three items, and point to `Complete Wide-API Index` for the full list.
- In each card, make the first sentence about engineering impact, not code mechanics.
- Use exactly one or two `Look here first` links under each finding when practical.
- Put lengthy recursion traces in `Evidence Appendix`.
- Use absolute file paths when the environment supports clickable local links. Include line anchors when available.
- If no wide-API findings are found, still write the report with an empty index, full field-flow and recursive coverage ledgers, strongest blind spot, and what was verified.
- If the report is based mainly on static reasoning, say that plainly in `Gate Snapshot` and `Field-Flow Ledger` and `Recursive Coverage Ledger`.
- If AST/parser evidence was available, state the parser or analysis source used. If it was not available, state that the report used heuristic text fallback and identify paths where AST would improve confidence.
- For findings that imply UI refactors, state the expected behavior-preservation oracle and any user-visible regression blind spot.

## Common Wide-API Leads

Check these explicitly: wide leaf props, pass-through spine, hook return bag, hook options bag, context fan-out, form controller fan-out, callback explosion, table/grid config sprawl, spread opacity, duplicate projection owner, effect dependency bloat, and memo breakage.

## Guardrails

- Do not call a documented public compatibility API a problem merely because it is wide.
- Do not force every component to receive only primitive props; complex section-level view models are often correct.
- Do not recommend `React.memo`, `useMemo`, or `useCallback` as the primary fix for a boundary ownership problem.
- Do not recommend deep equality as the default answer to wide props.
- Do not flatten a well-grouped API into dozens of primitive props.
- Do not turn an intentional schema-driven renderer into field-level props unless the renderer no longer owns the schema boundary.
- Do not recommend or apply a field-boundary refactor that changes user-visible UI behavior unless the user explicitly approved that visible behavior change.
- Do not claim complete coverage unless the recursive coverage ledger accounts for every implementation-relevant or unknown boundary in scope.

## References

- Use `references/report-template.md` as the default output shape.
- Use `references/ast-first-analysis.md` for AST-first field-flow tracing and evidence labels.
- Use `references/recursive-audit.md` for the detailed recursion method.
- Use `references/field-flow-taxonomy.md` for field classification.
- Use `references/scoring-model.md` for priority scoring.
- Use `references/patterns.md` for recommended refactor shapes.
- Use `references/checklist.md` before writing findings and during the final self-check.
- Use `references/migration.md` when a finding needs a realistic migration path.
