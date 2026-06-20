---
name: code-review
description: Perform a scoped general code review of a working tree, staged diff, commit range, branch diff, PR, focused file set, or pasted code, prioritizing correctness bugs, behavioral regressions, security and privacy issues, contract violations, and missing tests. Use when the user asks for `/code-review`, a code review, PR review, diff review, branch review, staged-change review, or asks whether code changes are safe to merge. Write a Markdown report file plus a short summary. Do not make code changes unless the user explicitly asks for fixes.
---

# Code Review

## Overview

Treat the requested scope as a general code-review gate. Findings are the primary output; summaries, praise, style notes, and broad refactor ideas are secondary.

Always produce a Markdown report file and a short terminal summary.

The primary job is to enumerate every distinct review finding that can be reasonably identified within the reviewed scope, not only the most severe or easiest findings.

## Skill Boundary

- Use `code-review` to create or refresh a general code-review report.
- Use `receiving-code-review` to consume the report and decide what to do next.
- Use `regression-review` instead when the main question is a coverage-led user-visible behavior gate.
- Use `hack-review` instead when the main question is brittle implementation structure, shortcut ownership, or hidden hack risk.

## Set Scope First

- Prefer an explicit scope from the user: working tree, staged changes, last commit, commit range, branch diff, PR, file set, or pasted code.
- If no scope is named, inspect available Git context and choose the smallest reasonable review scope. Prefer staged changes when they exist; otherwise use the working tree against `HEAD`.
- State the assumed scope and baseline in the report.
- Do not silently review unrelated changes or the whole repository when a narrower scope is implied.
- If the requested scope is too large to cover completely, review the highest-risk areas first, mark the report `Incomplete`, list the exact files or surfaces not covered, and set the recommendation no lower than `Discuss` unless the uncovered area is demonstrably review-irrelevant.
- If requirements, issue text, a PR description, migration notes, or design docs exist, read them before judging intent.

## Completeness Contract

- Output every distinct review finding discovered within the reviewed scope.
- Use `Must-review now` only as a short priority preview. The full findings sections and `Complete Findings Index` must include all findings.
- Maintain a `Review Coverage Ledger` that maps every changed review-relevant area to one of:
  - `Finding F#`
  - `Reviewed - no issue found`
  - `Not review-relevant`
  - `Not covered`
- Treat review-relevant areas broadly: API contracts, data flow, persistence, auth, permissions, security boundaries, external calls, generated output, CLI output, tests, migrations, config, loading and error states, concurrency, caching, and touched shared utilities.
- If a candidate issue is investigated and dismissed, record the dismissal in the evidence appendix when it explains coverage or prevents duplicate review.
- If missing context, runtime setup, credentials, diff size, or token budget prevents complete coverage, say exactly where coverage stopped. A partial review must not be presented as complete.

## Output Rules

- Always write a Markdown file.
- Generate a fresh random id for each report filename, such as 8 lowercase hex characters from `openssl rand -hex 4`, `uuidgen`, or an equivalent local source.
- If the repo already has an obvious location for reviews or reports, follow that directory convention, but still append the random id immediately before `.md` unless the repo's convention already guarantees a unique per-run filename.
- Otherwise write to `tmp/reviews/YYYY-MM-DD-code-review-report-<random-id>.md`.
- Do not overwrite an existing report. If the chosen path already exists, generate a new id and choose a new path before writing.
- End with a short terminal summary that includes the report path, recommendation, completion status, counts by severity, and the top risks.
- Structure the report in this order:
  - `Scope`
  - `Review Snapshot`
  - `Complete Findings Index`
  - `Blocker`
  - `Major`
  - `Minor`
  - `Questions`
  - `Test Gaps`
  - `Review Coverage Ledger`
  - `Evidence Appendix`
- Keep the primary view optimized for review reading speed, but do not omit findings for brevity.
- Do not use wide summary tables as the main presentation shape for finding details. Tables are appropriate for the findings index, coverage ledger, and evidence appendix.

## Severity Labels

Use these severity labels as the primary classification:

- `Blocker`
  - Strong evidence of a correctness, security, data-loss, privacy, migration, availability, or release-blocking regression that should stop the change from merging.
- `Major`
  - A meaningful bug, contract break, security weakness, behavioral regression, or missing test for risky changed behavior that should be fixed or answered before merge.
- `Minor`
  - A lower-impact issue, narrow maintainability risk, or non-blocking test gap worth addressing or carrying forward.
- `Question`
  - Missing context or unclear intent that materially affects approval. Do not use `Question` for curiosity that does not change the review decision.

Do not lead with style, naming, formatting, or broad refactor preferences unless they hide a real bug or review-blocking risk.

## Recommendation Mapping

Use the top-level `Recommendation` field in `Review Snapshot` with this exact mapping:

- If any unresolved finding is `Blocker`, the report recommendation MUST be `Block`.
- Else if any unresolved finding is `Major`, the report recommendation MUST be `Changes requested`.
- Else if any approval-affecting finding is `Question`, the report recommendation MUST be `Discuss`.
- Else if coverage is incomplete for a review-relevant or unknown-impact area, the report recommendation MUST be `Discuss`.
- Else if any unresolved finding is `Minor`, the report recommendation MUST be `Pass with caveat`.
- Else use `Pass`.

Additional rules:

- Do not write `Pass with caveat` when a `Major` item or approval-affecting `Question` is still open.
- Do not write `Discuss` when the body contains no approval-affecting `Question` and no incomplete review-relevant coverage.
- If a suspected issue lacks enough proof to justify `Blocker`, downgrade the finding to `Major` or `Question` instead of keeping `Blocker` with hand-wavy evidence.
- If the report contains both `Blocker` and `Major`, keep both sections, but the top-level recommendation remains `Block`.

## What Counts As One Finding

- Count one item per distinct failure mode, user or security impact, or missing coverage risk, not per file, function, syntax pattern, or repeated code smell.
- Merge multiple code changes that lead to the same defect or test gap.
- Split items when different users, contracts, security boundaries, persisted data, or integration paths are affected in materially different ways.
- Focus on findings that matter during review:
  - crashes, data loss, stale data, race conditions, contract violations, and broken edge cases
  - behavioral regressions in UI, API, CLI, generated files, emails, persistence, auth, permissions, retries, ordering, and caching
  - injection, unsafe deserialization, auth bypasses, secret exposure, overbroad access, SSRF, XSS, CSRF, unsafe dependency use, and unsafe filesystem use
  - weak or missing tests for changed behavior, especially around bug fixes, regressions, permissions, migrations, and error paths
  - maintainability concerns only when they create concrete review risk

## Evidence Standard

- Tie every finding to a concrete code location, behavior path, output, missing test, or coverage gap.
- Separate verified facts from inferred risk.
- Use runtime evidence when it materially changes confidence, but do not run broad or destructive commands for review.
- Treat passing lint, typecheck, or unrelated tests as hygiene evidence, not proof that a behavioral risk is safe.
- If a finding depends on assumptions, name the assumption and lower confidence.
- Do not invent defects to satisfy the review request. If no issues are found, say so plainly and mention residual risk or coverage gaps.

## Workflow

1. Define the review scope and comparison baseline.
2. Build a diff inventory and identify changed review-relevant areas.
3. Read the diff plus relevant tests, fixtures, schemas, config, docs, and call sites needed to understand impact.
4. Trace changed data and control flow far enough to verify user-visible, persisted, security, integration, and test effects.
5. Check whether new or existing tests cover the risky behavior.
6. Build the `Review Coverage Ledger` before writing findings.
7. Gather proof and code pointers for each candidate issue.
8. De-duplicate and classify findings by distinct failure mode or approval risk.
9. Write the report from `references/report-template.md`.
10. Run the report self-check:
    - Every changed review-relevant or unknown-impact area appears in `Review Coverage Ledger`.
    - Every finding in a severity section appears in `Complete Findings Index`.
    - Every `Finding F#` ledger row has a matching card.
    - Every `Not covered` row has a reason and a concrete next step.
    - The recommendation matches the mapping rules.

## Card Format

Each finding should be written as a short review card, not a spreadsheet row. Repeat the card format for every finding in the section; do not cap sections at one item.

Use this shape:

```md
### F1 Blocker - Checkout can submit twice

Impact: Users can trigger duplicate payment attempts during a slow checkout.
Review reason: Direct money-path risk with an obvious release-blocking failure mode.
Surface: Checkout submit flow
Confidence: High

Look here first:
- [submit handler](/abs/path/app/checkout.tsx#L128)
- [removed guard](/abs/path/lib/payment.ts#L42)

Failure mode:
- Expected: First submit disables repeat submission while the request is pending.
- Current: Repeat clicks can issue another submission before the first request finishes.

Evidence:
- Reproduced locally in browser with throttled network.
- No remaining test covers duplicate submit protection.

Reviewer action:
Block until the guard is restored or equivalent idempotency is proven elsewhere.
```

## Writing Rules

- Start with the recommendation and completion status.
- `Review Snapshot` should fit on one screen when possible.
- `Review Snapshot` should usually include:
  - `Recommendation`
  - `Completion`
  - `Why now`
  - `Must-review now`
  - `Findings count`
  - `Coverage confidence`
  - `Biggest blind spot`
- Limit `Must-review now` to the top 3 items, and explicitly point to `Complete Findings Index` for the full list.
- In each review card, keep the first sentence about user, security, data, contract, or test impact, not code mechanics.
- Use exactly 1 or 2 links under `Look here first`.
- Put longer causal chains, command output, and candidate dismissals in `Evidence Appendix`, not in the main card.
- Use absolute file paths when the environment supports clickable local links. Include line anchors when available, for example `[normalizer.ts](/abs/path/lib/normalizer.ts#L128)` or `[normalizer.ts](/abs/path/lib/normalizer.ts:128)`.
- If no findings are found, still write the report:
  - Say the recommendation is `Pass` or `Pass with caveat`
  - Include an empty `Complete Findings Index`
  - Include the full `Review Coverage Ledger`
  - State the strongest blind spot
  - Document what was verified
- If the report is based mainly on static reasoning, say that plainly in both `Review Snapshot` and `Review Coverage Ledger`.

## Guardrails

- Do not make code changes during review unless the user explicitly asks for fixes.
- Do not stage, commit, push, or mutate Git state.
- Do not silently widen scope to include unrelated changes.
- Do not bury findings below a summary.
- Do not recommend broad rewrites when a narrow fix or test would address the risk.
- Do not claim complete coverage unless the coverage ledger accounts for every changed review-relevant or unknown-impact area.
- Do not treat style-only comments as review findings unless they create concrete review risk.

## Reference

- Use [references/report-template.md](references/report-template.md) as the default output shape.
