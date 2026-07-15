# Thermo Review Report

## Scope

- Review date: `YYYY-MM-DD`
- Scope reviewed: `[working tree | staged diff | commit range | branch diff | PR | file set | pasted code]`
- Baseline: `[HEAD | commit SHA | branch | PR base | provided snippet context]`
- Completion: `[Complete within reviewed scope | Incomplete - reason]`
- Assumptions: `[state defaults if scope, runtime setup, product intent, or environment was inferred]`

## Review Snapshot

- Recommendation: `[Block | Changes requested | Discuss | Pass with caveat | Pass]`
- Completion: `[Complete within reviewed scope | Incomplete - exact uncovered area]`
- Why now: `[one sentence explaining the structural quality decision]`
- Must-review now: `[top 1-3 items only; full list is in Complete Findings Index]`
  1. `F#` `[short title]`
  2. `F#` `[short title]`
  3. `F#` `[short title]`
- Findings count: `Blocker [n] | Major [n] | Minor [n] | Question [n]`
- Coverage confidence: `[high | medium | low]`
- Biggest blind spot: `[short phrase, or None identified]`

## Complete Findings Index

If no findings exist, write `No thermo-nuclear code quality findings identified in the reviewed scope.`
Otherwise add one row for every `F#` finding in the report.

| ID | Severity | Surface | Structural risk | Confidence |
| --- | --- | --- | --- | --- |
| `F1` | `[Blocker | Major | Minor | Question]` | `[file, module, component, API, helper, config, test, etc.]` | `[one-line risk or open quality-gate question]` | `[high | medium | low]` |

## Blocker

If none exist, write `None.`
Otherwise repeat this card for every `Blocker` finding. Continue numbering across all finding sections as needed.

### F1 Blocker - [Short title]

Impact: `[developer experience, maintainability, future-change, ownership, or defect-risk impact]`
Review reason: `[why this should block merge]`
Surface: `[file, module, component, API, ownership boundary, state model, type boundary, etc.]`
Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`
- `[secondary](/abs/path/file.tsx#L42)`

Structural failure:
- Expected: `[simple model, canonical ownership, decomposition, invariant, or threshold]`
- Current: `[what the reviewed change does instead]`

Simpler path:
- `[specific responsibility split, ownership move, branch deletion, type model, helper reuse, or code-judo reframing; for a threshold finding, explain how the dependency surface narrows]`

Evidence:
- `[line count, diff trace, call-site trace, duplicate search, canonical helper search, test/context evidence, or missing proof]`

Reviewer action:
`[block until restructured | block until justified | request simpler design | request decomposition]`

## Major

If none exist, write `None.`
Otherwise repeat this card for every `Major` finding. Continue numbering across all finding sections as needed.

### F2 Major - [Short title]

Impact: `[meaningful maintainability, abstraction, ownership, type-contract, duplication, or decomposition impact]`
Review reason: `[why this should be fixed or answered before merge]`
Surface: `[file, module, component, API, ownership boundary, state model, type boundary, etc.]`
Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`
- `[secondary](/abs/path/file.tsx#L42)`

Structural failure:
- Expected: `[simple model, canonical ownership, decomposition, invariant, or threshold]`
- Current: `[what the reviewed change does instead]`

Simpler path:
- `[specific responsibility split, ownership move, branch deletion, type model, helper reuse, or code-judo reframing; for a threshold finding, explain how the dependency surface narrows]`

Evidence:
- `[what supports the concern and what is still missing]`

Reviewer action:
`[request restructure | request proof | request decomposition | raise before approval]`

## Minor

If none exist, write `None.`
Otherwise repeat this card for every `Minor` finding. Continue numbering across all finding sections as needed.

### F3 Minor - [Short title]

Impact: `[lower-impact maintainability risk or non-blocking decomposition gap]`
Review reason: `[why it is worth noting but not blocking]`
Surface: `[file, module, component, API, helper, test, output, etc.]`
Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`

Structural failure:
- Expected: `[preferred structure, threshold, ownership, or clarity]`
- Current: `[current lower-risk gap]`

Simpler path:
- `[specific follow-up or small cleanup]`

Evidence:
- `[what was checked]`

Reviewer action:
`[approve with caveat | track follow-up | simplify opportunistically]`

## Questions

If none exist, write `None.`
Otherwise repeat this card for every approval-affecting `Question` finding. Continue numbering across all finding sections as needed.

### F4 Question - [Short title]

Approval impact: `[what cannot be approved or classified without this context]`
Needed context: `[specific product, ownership, architecture, migration, or constraint information needed]`
Surface: `[file, module, component, API, ownership boundary, state model, type boundary, etc.]`
Confidence: `[high | medium | low]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`

Evidence:
- `[what is known, what is unknown, and why it affects the quality gate]`

Reviewer action:
`[ask owner | confirm intent | request architecture rationale | request proof]`

## Decomposition Gaps

If none exist, write `None.`
Otherwise list focused responsibility splits, ownership moves, extractions, or simplification gaps not already fully covered by a finding card.

- `D1` `[changed surface or risk]` - `[missing decomposition, helper reuse, state model, or type boundary]` - `[link](/abs/path/file.ts#L10)`

## Recursive Coverage Ledger

Every changed structural or unknown-impact area and every discovered candidate frontier item must appear here.

| Area / candidate | Touched files or entry points | Status | Result | Evidence |
| --- | --- | --- | --- | --- |
| `[area or candidate]` | `[file or entry point links]` | `[Finding F# | Reviewed - no issue found | Not review-relevant | Not covered]` | `[short result]` | `[static trace, search, line count, test/context check, or reason not covered]` |

## Evidence Appendix

### Diff Inventory

| File or area | Classification | Structural area considered |
| --- | --- | --- |
| `[path]` | `[source | test | config | docs-only | generated | vendored | unknown]` | `[file size, ownership, abstraction, type boundary, orchestration, duplication, tests, none, or unknown]` |

### Line Count Ledger

For every `crossed 350` or `already over 350` row, diagnose cohesion, dependency direction, and canonical ownership. A lower physical line count alone is not a valid resolution.

| File | Baseline lines | Current lines | Threshold status | Boundary diagnosis | Decision |
| --- | ---: | ---: | --- | --- | --- |
| `[path]` | `[n]` | `[n]` | `[under 350 | crossed 350 | already over 350 | excluded]` | `[responsibilities, dependency seam, canonical owner, or cohesive-file evidence]` | `[reviewed no issue (under 350 only) | Finding F# | waived with reason | excluded | not covered]` |

### Recursive Candidate Sweep Log

Use this section for reviewed candidates, candidates added during recursion, dismissed candidates, and duplicate candidates merged into another finding.

| Candidate | Source | Decision | Reason |
| --- | --- | --- | --- |
| `[candidate issue]` | `[initial inventory | discovered from F# | discovered from trace]` | `[dismissed | Finding F# | merged into F# | not covered]` | `[evidence or reasoning]` |

### Verification Commands

- `[command and key outcome]`
- `[command and key outcome]`

### Supporting Code Links

| ID | Role | Link | Why it matters |
| --- | --- | --- | --- |
| `F1` | `entry` | `[component](/abs/path/file.ts#L10)` | `[where the path starts]` |
| `F1` | `risk` | `[new branch](/abs/path/file.ts#L42)` | `[where the structural failure enters]` |
| `F1` | `context` | `[canonical helper](/abs/path/helper.ts#L12)` | `[what should own or simplify it]` |

### Blind Spots

| Area | Risk introduced by the blind spot | What would resolve it |
| --- | --- | --- |
| `[unverified path]` | `[how this limits the quality decision]` | `[specific next verification step]` |

### Report Self-Check

- `[yes | no]` Every changed structural or unknown-impact area appears in `Recursive Coverage Ledger`.
- `[yes | no]` Every finding in a severity section appears in `Complete Findings Index`.
- `[yes | no]` Every `Finding F#` ledger row has a matching card.
- `[yes | no]` Every `Not covered` row has a reason and next verification step.
- `[yes | no]` Every maintained source file over `350` lines has a cohesion, dependency, and ownership diagnosis and maps to a finding or evidence-backed waiver.
- `[yes | no]` No threshold decision relies only on formatting density, arbitrary relocation, or another count-only tactic.
- `[yes | no]` Recommendation follows the mapping rules from the skill.
