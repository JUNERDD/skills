---
name: regression-review
description: Perform a scoped, coverage-led review of working tree, staged, commit-range, branch, or PR changes to find user-visible behavioral regressions. Use when Codex must audit code changes for broken or degraded user journeys, changed defaults, loading/error/permission/session behavior, stale data, ordering, retries, duplicate/destructive actions, exported output, emails, CLI output, or other visible behavior, and must write a Markdown report that enumerates all distinct findings discovered within the reviewed scope plus coverage gaps, intentional visible changes, and scoped behavior-graph deltas when they clarify the affected path.
---

# Regression Review

## Overview

Treat the change set as a scoped user-visible regression audit with a gate recommendation. The primary job is to enumerate every distinct user-visible regression finding that can be reasonably identified within the reviewed scope, not only the most severe or easiest findings.

Always produce a Markdown report file and a short terminal summary.

Keep the overall recommendation mechanically aligned with the highest-severity unresolved finding and the coverage state. Do not let prose tone drift the gate up or down.

Use behavior graphs as lightweight review artifacts for touched user-visible or unknown-impact surfaces, not as whole-repo call graphs.

## Set Scope First

- Prefer an explicit scope from the user: working tree, staged changes, last commit, commit range, branch diff, or PR.
- If the user does not specify scope, default to staged changes when they exist; otherwise compare the current working tree against `HEAD` and state that assumption in the report.
- If the requested scope is too large to review completely in one pass, do not silently sample it. Review the highest-risk surfaces first, mark the report `Incomplete`, list the exact files or surfaces not covered, and set the recommendation no lower than `Discuss` unless the uncovered area is demonstrably non-user-visible.
- If requirements, issue text, a PR description, or a design doc exist, read them before judging regressions.
- Separate intended product changes from accidental regressions.

## Completeness Contract

- Output every distinct regression finding discovered within the reviewed scope. Do not stop after the top 3.
- Use `Must-review now` only as a short priority preview. The full findings sections and `Complete Findings Index` must include all findings.
- Maintain a `Coverage Ledger` that maps every touched user-visible surface to one of:
  - `Finding F#`
  - `Intentional I#`
  - `Reviewed - no user-visible regression found`
  - `Not user-visible`
  - `Not covered`
- Do not drop lower-severity user-visible changes. Put them in `Watch` or `Intentional Changes` when they are real but not blocking.
- If a candidate issue is investigated and dismissed, record the dismissal in the evidence appendix when it explains coverage or prevents duplicate review.
- If token budget, runtime setup, missing credentials, or diff size prevents complete coverage, say exactly where coverage stopped. A partial review must not be presented as complete.

## Output Rules

- Always write a Markdown file.
- Generate a fresh random id for each report filename, such as 8 lowercase hex characters from `openssl rand -hex 4`, `uuidgen`, or an equivalent local source.
- If the repo already has an obvious location for reviews or reports, follow that directory convention, but still append the random id immediately before `.md` unless the repo's convention already guarantees a unique per-run filename.
- Otherwise write to `tmp/reviews/YYYY-MM-DD-user-visible-regression-report-<random-id>.md`.
- Do not overwrite an existing report. If the chosen path already exists, generate a new id and choose a new path before writing.
- End with a short terminal summary that includes the report path, the gate recommendation, completion status, counts by action, and the top risks.
- Structure the report in this order:
  - `Scope`
  - `Gate Snapshot`
  - `Complete Findings Index`
  - `Block`
  - `Discuss`
  - `Watch`
  - `Intentional Changes`
  - `Coverage Ledger`
  - `Evidence Appendix`
- Keep the primary view optimized for review reading speed, but do not omit findings for brevity.
- Do not use wide summary tables as the main presentation shape for finding details. Tables are appropriate for the findings index, coverage ledger, and evidence appendix.

## Review Actions

Use these action labels as the primary classification:

- `Block`
  - Strong evidence or strong risk that a user-visible behavior is broken, degraded, or dangerously changed.
  - A reviewer should stop the change from shipping until the issue is fixed or disproven.
- `Discuss`
  - The user-visible impact may be meaningful, but severity, intent, or actual runtime effect is still unclear.
  - A reviewer should raise it in review and resolve the uncertainty before approval.
- `Watch`
  - The behavior change is worth noticing, but does not justify blocking by itself.
  - A reviewer may approve with caveat, added test, follow-up, or monitoring.
- `Intentional`
  - The user-visible change appears deliberate and should not be framed as a regression.

Do not use `confirmed`, `probable`, or `possible` as top-level groupings. Keep them as evidence language inside the card when useful.

## Recommendation Mapping

Use the top-level `Recommendation` field in `Gate Snapshot` with this exact mapping:

- If any unresolved finding is `Block`, the report recommendation MUST be `Block`.
- Else if any unresolved finding is `Discuss`, the report recommendation MUST be `Discuss`.
- Else if coverage is incomplete for a user-visible or unknown-impact surface, the report recommendation MUST be `Discuss`.
- Else if any unresolved finding is `Watch`, the report recommendation MUST be `Pass with caveat`.
- Else use `Pass`.

Additional rules:

- Do not write `Pass with caveat` when a `Discuss` item is still open.
- Do not write `Discuss` when the body contains no `Discuss` items and no incomplete user-visible coverage.
- If a suspected issue lacks enough proof to justify `Block`, downgrade the finding to `Discuss` instead of keeping `Block` with hand-wavy evidence.
- If the report contains both `Block` and `Discuss`, keep both sections, but the top-level recommendation remains `Block`.

## What Counts As One Finding

- Count one item per distinct user-facing outcome, not per file, function, root cause, or code smell.
- Merge multiple code changes that lead to the same user-visible symptom.
- Split items when different user journeys are affected in materially different ways.
- Focus on findings that matter during review:
  - broken or degraded task completion
  - changed defaults or fallback behavior
  - loading, empty, or error state changes
  - permission or session behavior changes
  - stale data, cache, retry, polling, or ordering changes
  - destructive, repeated, or duplicate actions
  - accessibility, keyboard, focus, or responsive behavior changes that users can notice
  - output changes in emails, generated files, CLI output, API responses, persisted data, or exports

## Evidence Standard

- Prefer the strongest feasible evidence for the affected surface, not one fixed verification mode.
- Runtime checks are valuable, but they are not mandatory when static path tracing or output inspection already provides strong evidence.
- For frontend behavior, use the evidence that best matches the risk: code-path tracing, generated output inspection, logs, focused tests, screenshots, or runtime repro when needed.
- For non-UI changes, inspect outputs, fixtures, generated files, CLI responses, API responses, logs, and focused tests.
- If evidence is missing, lower confidence and say so plainly.
- Separate verified facts from inferred consequences.
- Do not present speculation as fact.
- Do not treat `eslint`, `typecheck`, or passing unrelated tests as proof that a user-visible regression is disproven. They are hygiene evidence only.
- When a spec, issue, or design doc exists, use it to judge intent, but do not treat it as proof that the runtime or output behavior is still correct.

## Scoped Behavior Graphs

Build a scoped behavior graph after the diff inventory, before classifying findings, when a touched file can affect a user-visible or unknown-impact surface.

Keep each graph focused on one surface and these node types:

- Entry: route, component boundary, command, API handler, job, export, or email path.
- Input: props, request payload, state/store slice, persisted data, env/config, feature flag, or fixture.
- Guards: auth, permission, validation, debounce, duplicate-submit, confirmation, retry, ordering, empty-state, or error handling.
- Transform: mapping, filtering, sorting, serialization, formatting, cache key, adapter, or wrapper.
- Output/effect: rendered UI, API response, CLI text, generated file, email body, persisted write, external request, or scheduled side effect.

For each graph, compare the baseline path from the chosen baseline with the after-change path from the current scope. Record changed nodes, removed or moved guards, changed inputs, and changed final outputs/effects. If a graph cannot be built without runtime data, credentials, or a broader scope, record the gap in the coverage ledger or blind spots instead of inventing precision.

## Workflow

1. Define the comparison baseline.
   - Use the user-specified scope exactly when provided.
   - Otherwise use staged changes if present; if nothing is staged, use working tree against `HEAD`.
   - Record the exact scope and baseline in the report.
2. Build a diff inventory.
   - List touched files and classify each as user-visible surface, user-visible dependency, test-only, docs-only, generated, config, or unknown.
   - Use repository structure, route maps, exports, commands, schedules, feature flags, and call sites to avoid missing indirect user-visible paths.
3. Build scoped behavior graphs for user-visible and unknown-impact surfaces.
   - Do not graph docs-only, generated-only, or test-only paths unless they feed visible output.
   - Include entry, input, guards, transform, and output/effect nodes where applicable.
   - Keep the graph shallow enough to support review; do not attempt a complete static call graph.
4. Build the coverage ledger before writing findings.
   - Identify every route, page, component, API consumer, command, job, config default, flag path, email/export/output, and persisted side effect touched by the diff.
   - Add each surface to the ledger even if it later has no finding.
   - Use graph coverage to catch missing surfaces, but keep the ledger as the authoritative coverage index.
5. Trace behavior deltas for every ledger surface.
   - Compare before and after behavior for each surface.
   - Look for removed guards, changed branching, altered ordering, serialization changes, loading changes, empty states, error paths, retries, cache keys, stale data, session/auth checks, and output formatting.
   - For refactors, wrappers, adapters, shared utilities, or "just telemetry" changes, explicitly trace what now supplies the user-visible input, what still enforces guards, and what produces the final output.
   - Use behavior graph deltas to tie code-path changes to user-visible outputs or side effects.
6. Gather proof and code pointers.
   - Collect the strongest runtime, output, test, log, fixture, screenshot, or code-path evidence available.
   - Trace each finding back to concrete code lines.
7. De-duplicate and classify.
   - Merge candidates with the same user-facing outcome.
   - Rank within each section by user impact first, confidence second.
8. Write the report from `references/report-template.md`.
   - Include all findings in `Complete Findings Index` and the matching action sections.
   - Put priority highlights in `Must-review now`, but never use that list as the full result.
   - Include behavior graph deltas in the evidence appendix when they materially support coverage or findings.
9. Run the report self-check.
   - Every touched user-visible surface is present in `Coverage Ledger`.
   - Every finding in the action sections appears in `Complete Findings Index`.
   - Every `Finding F#` in `Coverage Ledger` has a matching card.
   - Every `Not covered` row has a reason and a concrete next step.
   - Every graphable user-visible or unknown-impact surface has either a behavior graph delta row or a ledger reason for skipping it.
   - The recommendation matches the mapping rules.

## Card Format

Each risk should be written as a short review card, not a spreadsheet row. Repeat the card format for every finding in the section; do not cap sections at one item.

Use this shape:

```md
### F1 Block - Checkout can submit twice

User impact: Users can trigger duplicate payment attempts during a slow checkout.
Review reason: Direct money-path risk with obvious user-facing failure.
Surface: Checkout submit flow
Confidence: High

Look here first:
- [submit handler](/abs/path/app/checkout.tsx#L128)
- [removed guard](/abs/path/lib/payment.ts#L42)

Behavior delta:
- Before: First submit disabled repeat submission while the request was pending.
- After: Repeat clicks can issue another submission before the first request finishes.

Evidence:
- Reproduced locally in browser with throttled network.
- No remaining test covering duplicate submit protection.

Reviewer action:
Block until the guard is restored or equivalent idempotency is proven elsewhere.
```

## Writing Rules

- Start with the gate decision and completion status.
- `Gate Snapshot` should fit on one screen when possible.
- `Gate Snapshot` should usually include:
  - `Recommendation`
  - `Completion`
  - `Why now`
  - `Must-review now`
  - `Findings count`
  - `Coverage confidence`
  - `Behavior graph coverage`
  - `Biggest blind spot`
- Limit `Must-review now` to the top 3 items, and explicitly point to `Complete Findings Index` for the full list.
- In each review card, keep the first sentence about user impact, not code mechanics.
- Use exactly 1 or 2 links under `Look here first`.
- Put the full causal chain in `Evidence Appendix`, not in the main card.
- Use absolute file paths when the environment supports clickable local links. Include line anchors when available, for example `[checkout.tsx](/abs/path/app/checkout.tsx#L128)` or `[checkout.tsx](/abs/path/app/checkout.tsx:128)`.
- `Intentional Changes` should be compact and easy to skim.
- `Coverage Ledger` must include every reviewed user-visible surface, not just surfaces with findings.
- `Evidence Appendix` may use small tables.
- If no user-visible regressions are found, still write the report:
  - Say the recommendation is `Pass` or `Pass with caveat`
  - Include an empty `Complete Findings Index`
  - Include the full `Coverage Ledger`
  - State the strongest blind spot
  - Document what was verified, including behavior graphs that were built or skipped
- If the report is based mainly on static reasoning, say that plainly in both `Gate Snapshot` and `Coverage Ledger`.
- When evidence is mixed, write the verified code-path facts first, then the inferred user impact second.

## Behavior-Preserving Refactor Checklist

When the diff centralizes behavior behind a shared helper, adapter, wrapper, middleware, base class, hook, or common handler, check these explicitly before deciding it is "just a refactor":

- Source parity: did the user-visible behavior start reading from a different input, field, state slice, request payload, or serialized form?
- Guard parity: did auth, permission, debounce, duplicate-submit, confirmation, retry, ordering, or empty-state guards move, disappear, or become bypassable?
- Output parity: does the final renderer, exporter, request builder, CLI output, email body, or persisted record still consume the expected format and shape?
- Extension-point parity: if a local override, callback, prop, or branch was removed, is there a new path that preserves the same behavior, not just the same UI or API surface?
- Intent split: are telemetry-only, naming-only, or cleanup-only changes actually mixed with behavior changes in the same refactor?

For any user-visible flow, explicitly compare:

- user-visible input source
- transformed or intermediate payload
- final output or side effect
- gates that must still run before the effect happens

If those layers are no longer aligned, treat that as a regression lead even before runtime verification.

## Guardrails

- Do not call a deliberate product change a regression just because users will notice it.
- Do not mistake "tests passed" for "user impact disproven".
- Do not overcount the same symptom across multiple files.
- Do not hide lower-severity issues because stronger issues already exist.
- Do not claim complete coverage unless the coverage ledger accounts for every touched user-visible or unknown-impact surface.
- If a runtime check cannot be performed, say so and downgrade confidence rather than hiding the gap.
- Do not discard a strong static regression lead just because the change was introduced during a refactor or telemetry cleanup.
- Do not promote a finding to `Block` unless the user-visible breakage itself, not just the code smell, is strongly supported.

## Reference

- Use [references/report-template.md](references/report-template.md) as the default output shape.
