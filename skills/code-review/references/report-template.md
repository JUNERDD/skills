# Code Review Report

## Scope

- Review date: `YYYY-MM-DD`
- Scope reviewed: `[working tree | staged diff | commit range | branch diff | PR | file set | pasted code]`
- Baseline: `[HEAD | commit SHA | branch | PR base | provided snippet context]`
- Completion: `[Complete within reviewed scope | Incomplete - reason]`
- Assumptions: `[state defaults if scope, runtime setup, credentials, product intent, or environment was inferred]`

## Review Snapshot

- Recommendation: `[Block | Changes requested | Discuss | Pass with caveat | Pass]`
- Completion: `[Complete within reviewed scope | Incomplete - exact uncovered area]`
- Why now: `[one sentence that explains the review decision]`
- Must-review now: `[top 1-3 items only; full list is in Complete Findings Index]`
  1. `F#` `[short title]`
  2. `F#` `[short title]`
  3. `F#` `[short title]`
- Findings count: `Blocker [n] | Major [n] | Minor [n] | Question [n]`
- Coverage confidence: `[high | medium | low]`
- Biggest blind spot: `[short phrase, or None identified]`

## Complete Findings Index

If no findings exist, write `No code-review findings identified in the reviewed scope.`
Otherwise add one row for every `F#` finding in the report.

| ID | Severity | Surface | Review risk | Confidence |
| --- | --- | --- | --- | --- |
| `F1` | `[Blocker | Major | Minor | Question]` | `[route, command, API, helper, config, test, etc.]` | `[one-line risk or open approval question]` | `[high | medium | low]` |

## Blocker

If none exist, write `None.`
Otherwise repeat this card for every `Blocker` finding. Continue numbering across all finding sections as needed.

### F1 Blocker - [Short title]

Impact: `[user, security, data, contract, availability, or release impact]`
Review reason: `[why this should block merge]`
Surface: `[route, feature, command, API, migration, security boundary, output, etc.]`
Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`
- `[secondary](/abs/path/file.tsx#L42)`

Failure mode:
- Expected: `[required behavior, invariant, contract, or coverage]`
- Current: `[what the reviewed change does instead]`

Evidence:
- `[runtime repro, targeted test, log, fixture, output inspection, code-path trace, or missing-test evidence]`

Reviewer action:
`[block until fixed | block until disproven | request targeted test | request runtime verification]`

## Major

If none exist, write `None.`
Otherwise repeat this card for every `Major` finding. Continue numbering across all finding sections as needed.

### F2 Major - [Short title]

Impact: `[meaningful bug, regression, security, contract, or coverage impact]`
Review reason: `[why this should be fixed or answered before merge]`
Surface: `[route, feature, command, API, migration, security boundary, output, etc.]`
Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`
- `[secondary](/abs/path/file.tsx#L42)`

Failure mode:
- Expected: `[required behavior, invariant, contract, or coverage]`
- Current: `[what the reviewed change does instead]`

Evidence:
- `[what supports the concern and what is still missing]`

Reviewer action:
`[request fix | request proof | request test | raise before approval]`

## Minor

If none exist, write `None.`
Otherwise repeat this card for every `Minor` finding. Continue numbering across all finding sections as needed.

### F3 Minor - [Short title]

Impact: `[lower-impact bug, narrow debt, or non-blocking coverage risk]`
Review reason: `[why it is worth noting but not blocking]`
Surface: `[route, feature, command, API, helper, test, output, etc.]`
Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`

Failure mode:
- Expected: `[preferred behavior, coverage, or constraint]`
- Current: `[current lower-risk gap]`

Evidence:
- `[what was checked]`

Reviewer action:
`[approve with caveat | add follow-up test | monitor | note for later]`

## Questions

If none exist, write `None.`
Otherwise repeat this card for every approval-affecting `Question` finding. Continue numbering across all finding sections as needed.

### F4 Question - [Short title]

Approval impact: `[what cannot be approved or classified without this context]`
Needed context: `[specific product, contract, migration, security, or test information needed]`
Surface: `[route, feature, command, API, migration, security boundary, output, etc.]`
Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`

Evidence:
- `[what is known, what is unknown, and why it affects approval]`

Reviewer action:
`[ask owner | confirm intent | request spec | request proof]`

## Test Gaps

If none exist, write `None.`
Otherwise list focused missing or weak tests that are not already fully covered by a finding card.

- `T1` `[changed behavior or risk]` - `[missing assertion, fixture, integration path, or regression test]` - `[link](/abs/path/file.ts#L10)`

## Review Coverage Ledger

Every changed review-relevant or unknown-impact area must appear here, including areas with no findings.

| Area / path | Touched files or entry points | Status | Result | Evidence |
| --- | --- | --- | --- | --- |
| `[area]` | `[file or entry point links]` | `[Finding F# | Reviewed - no issue found | Not review-relevant | Not covered]` | `[short result]` | `[static trace, search, runtime check, fixture, test, or reason not covered]` |

## Evidence Appendix

### Diff Inventory

| File or area | Classification | Review area considered |
| --- | --- | --- |
| `[path]` | `[surface | dependency | config | test-only | docs-only | generated | unknown]` | `[API, persistence, auth, output, tests, none, or unknown]` |

### Candidate Sweep Log

Use this section for meaningful candidates that were investigated and dismissed, or for duplicate candidates merged into another finding. Omit trivial unchanged paths.

| Candidate | Decision | Reason |
| --- | --- | --- |
| `[candidate issue]` | `[dismissed | merged into F# | covered by T#]` | `[evidence or reasoning]` |

### Verification Commands

- `[command and key outcome]`
- `[command and key outcome]`

### Supporting Code Links

| ID | Role | Link | Why it matters |
| --- | --- | --- | --- |
| `F1` | `entry` | `[handler](/abs/path/file.ts#L10)` | `[where the path starts]` |
| `F1` | `risk` | `[changed branch](/abs/path/file.ts#L42)` | `[where the failure enters]` |
| `F1` | `test` | `[coverage gap](/abs/path/file.test.ts#L88)` | `[what does or does not cover it]` |

### Blind Spots

| Area | Risk introduced by the blind spot | What would resolve it |
| --- | --- | --- |
| `[unverified path]` | `[how this limits the review decision]` | `[specific next verification step]` |

### Report Self-Check

- `[yes | no]` Every changed review-relevant or unknown-impact area appears in `Review Coverage Ledger`.
- `[yes | no]` Every finding in a severity section appears in `Complete Findings Index`.
- `[yes | no]` Every `Finding F#` ledger row has a matching card.
- `[yes | no]` Every `Not covered` row has a reason and next verification step.
- `[yes | no]` Recommendation follows the mapping rules from the skill.
