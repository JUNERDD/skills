# Report Directory Template

A Thermobot report is a directory, so a large review stays navigable and the fix phase can open only the files it needs. Keep the backticked tokens these templates fix (finding IDs, severities, statuses, thresholds, recommendation, completion) verbatim in English, because `scripts/check_report.py` reads them; prose may follow the user's language.

## Layout

```text
<report-dir>/
├── README.md     entry point: contract, scope, snapshot, findings index, ledgers, verification
├── findings/
│   └── F<n>.md   one card per finding; omit the folder when there are no findings
├── coverage.md   recursive coverage ledger
└── files.md      file inventory with 350-line diagnoses
```

When a ledger would run to several hundred rows, split it by top-level area into `coverage/<area>.md` or `files/<area>.md` in place of the single file, and link every part from the README.

## README.md

```markdown
# Thermobot Report

## Report Contract

- Report type: `thermobot`
- Report ID: `tb-YYYYMMDD-<random-id>`
- Review date: `YYYY-MM-DD`
- Report directory: `[absolute or repository-relative path]`
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

## Findings Index

[If no findings exist, write `No structural findings identified in the reviewed scope.` Otherwise add one row per finding, ordered by severity, each linking its card.]

| ID | Severity | Surface | Structural risk | Confidence |
| --- | --- | --- | --- | --- |
| [`F1`](findings/F1.md) | `[Blocker, Major, Minor, or Question]` | `[file, module, API, helper, state model, type boundary, test, or config]` | `[one-line risk or open question]` | `[high, medium, or low]` |

## Ledgers

- [Recursive coverage ledger](coverage.md): `[candidate count by status]`
- [File inventory](files.md): `[file count; files over 350 lines]`

## Verification Commands

- `[read-only command and key outcome]`
- `python3 <skill-folder>/scripts/check_report.py <report-dir>` -> `OK`
```

## findings/F<n>.md

Write one file per finding, named by its ID. For a `Question`, replace `Simpler path` with `Needed context: [the intent, ownership, or constraint that decides the gate]`.

```markdown
# F1 [Blocker, Major, Minor, or Question] - [Short title]

- Surface: `[file, module, component, API, ownership boundary, state model, or type boundary]`
- Look here first: `[primary](/abs/path/file.ts#L10)`, `[secondary](/abs/path/other.ts#L42)`
- Confidence: `[high, medium, or low]`

Impact: `[one or two sentences: the maintainability, ownership, or future-change cost and why it earns this severity]`

Structural failure:

- Expected: `[simpler model, canonical owner, cohesive decomposition, invariant, or threshold]`
- Current: `[what the reviewed change does instead]`

Simpler path: `[one to three sentences: the responsibility split, ownership move, branch deletion, type model, helper reuse, or reframing; for a threshold finding, how the dependency surface narrows]`

Evidence:

- `[file:line pointers, line counts, search or command results, or the proof still missing]`
```

## coverage.md

Account for every changed structural area and every candidate the sweep added, including dismissed and merged ones. A `Not covered` row names its blocker and next step, and makes the README completion `Incomplete`.

```markdown
# Recursive Coverage Ledger

| Area / candidate | Source | Entry points | Status | Evidence / next step |
| --- | --- | --- | --- | --- |
| `[area or candidate]` | `[initial inventory, discovered from F#, or discovered from trace]` | `[file or entry-point links]` | `[Finding F#, Merged into F#, Reviewed - no issue, Not review-relevant, or Not covered]` | `[short conclusion, or blocker plus concrete next step]` |
```

## files.md

Add one row per changed file. Every `crossed 350` or `already over 350` row needs a boundary diagnosis (responsibilities, dependency direction, canonical owner) and must map to a finding or an evidence-backed waiver; `reviewed - no issue` is valid only under 350 lines.

```markdown
# File Inventory

| Path | Class | Baseline lines | Current lines | Threshold | Boundary diagnosis and decision |
| --- | --- | ---: | ---: | --- | --- |
| `[path]` | `[source, test, config, docs, generated, or vendored]` | `[n]` | `[n]` | `[under 350, crossed 350, already over 350, or excluded]` | `[diagnosis; Finding F#, waived - reason, excluded - reason, reviewed - no issue, or not covered]` |
```

## Consistency Check

After writing the directory, run `python3 <skill-folder>/scripts/check_report.py <report-dir>` and fix every problem it prints. It confirms that the index and finding files match one to one, severity counts and the recommendation follow the cards, ledger rows point at real findings, `Not covered` rows come with an `Incomplete` completion, and every file over 350 lines maps to a finding or waiver. It cannot judge whether the sweep was complete or a waiver is sound; that stays with the reviewer.
