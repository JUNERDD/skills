# Thermobot Report

## Report Contract

- Report type: `thermobot`
- Report ID: `tb-YYYYMMDD-<random-id>`
- Review date: `YYYY-MM-DD`
- Report path: `[absolute or repository-relative path]`
- Repository root: `[absolute path]`
- Artifact status: `Fixed review input; do not rewrite during repair`

## Scope

- Scope reviewed: `[working tree | staged diff | commit range | branch diff | PR | file set | pasted code | post-fix delta of report ID]`
- Baseline: `[HEAD | commit SHA | branch | PR base | provided snippet context]`
- Intent sources: `[None found | requirements, issue, PR description, design or migration notes]`
- Completion: `[Complete within reviewed scope | Incomplete - exact uncovered areas]`
- Assumptions: `[None | inferred scope, baseline, environment, or product intent]`

## Review Snapshot

- Recommendation: `[Block | Changes requested | Discuss | Pass with caveat | Pass]`
- Why now: `[one sentence explaining the structural quality decision]`
- Findings count: `Blocker [n] | Major [n] | Minor [n] | Question [n]`
- Must-review now: `[top 1-3 F# findings, or None]`
- Coverage confidence: `[high | medium | low]`
- Biggest blind spot: `[short phrase, or None identified]`

## Complete Findings Index

If no findings exist, write `No structural findings identified in the reviewed scope.` Otherwise add one row per finding, ordered by severity.

| ID | Severity | Surface | Structural risk | Confidence |
| --- | --- | --- | --- | --- |
| `F1` | `[Blocker | Major | Minor | Question]` | `[file, module, API, helper, state model, type boundary, test, or config]` | `[one-line risk or open question]` | `[high | medium | low]` |

## Findings

If no findings exist, write `None.` Otherwise repeat this card for every finding in the order `Blocker`, `Major`, `Minor`, `Question`.

### F1 [Severity] - [Short title]

- Surface: `[file, module, component, API, ownership boundary, state model, or type boundary]`
- Look here first: `[primary](/abs/path/file.ts#L10)`, `[secondary](/abs/path/other.ts#L42)`
- Confidence: `[high | medium | low]`

Impact: `[one or two sentences: the maintainability, ownership, or future-change cost and why it earns this severity]`

Structural failure:

- Expected: `[simpler model, canonical owner, cohesive decomposition, invariant, or threshold]`
- Current: `[what the reviewed change does instead]`

Simpler path: `[one to three sentences: the responsibility split, ownership move, branch deletion, type model, helper reuse, or reframing; for a threshold finding, how the dependency surface narrows]`

For a `Question`, replace `Simpler path` with `Needed context: [the intent, ownership, or constraint that decides the gate]`.

Evidence:

- `[file:line pointers, line counts, search or command results, or the proof still missing]`

## Recursive Coverage Ledger

Account for every changed structural area and every candidate the sweep added, including dismissed and merged ones.

| Area / candidate | Source | Entry points | Status | Evidence / next step |
| --- | --- | --- | --- | --- |
| `[area or candidate]` | `[initial inventory | discovered from F# | discovered from trace]` | `[file or entry-point links]` | `[Finding F# | Merged into F# | Reviewed - no issue | Not review-relevant | Not covered]` | `[short conclusion, or blocker plus concrete next step]` |

## File Inventory

Add one row per changed file. Every `crossed 350` or `already over 350` row needs a boundary diagnosis (responsibilities, dependency direction, canonical owner) and must map to a finding or an evidence-backed waiver; `reviewed - no issue` is valid only under 350 lines.

| Path | Class | Baseline lines | Current lines | Threshold | Boundary diagnosis and decision |
| --- | --- | ---: | ---: | --- | --- |
| `[path]` | `[source | test | config | docs | generated | vendored]` | `[n]` | `[n]` | `[under 350 | crossed 350 | already over 350 | excluded]` | `[diagnosis; Finding F# | waived - reason | excluded - reason | reviewed - no issue | not covered]` |

## Verification Commands

- `[read-only command and key outcome]`

## Report Self-Check

- `[yes | no]` Every finding appears in both `Complete Findings Index` and `Findings`, and the severity counts match the cards.
- `[yes | no]` Every changed structural area and sweep candidate appears in `Recursive Coverage Ledger`, and every `Finding F#` or `Merged into F#` row resolves to a card.
- `[yes | no]` Every `Not covered` row names a blocker and next step, and completion is `Incomplete`.
- `[yes | no]` Every maintained source file over 350 lines has a boundary diagnosis that maps to a finding or an evidence-backed waiver, and no threshold decision relies on a count-only tactic.
- `[yes | no]` The recommendation follows the skill's mapping.
