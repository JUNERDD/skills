# Report Directory Template

A Thermobot report is a directory, so a large review stays navigable and the fix phase can open only the files it needs. Keep the fixed Markdown headings (`## Report Contract`, `## Scope`, `## Review Snapshot`, `## Findings Index`, `## Ledgers`), bullet keys (`Report type`, `Report ID`, `Reviewed HEAD`, `Input fingerprint`, `Snapshot consistency`, `Completion`, `Recommendation`, `Findings count`, `Must-review now`), card H1 format (`# F<n> <Severity> - <Title>`), card field labels (`Surface`, `Look here first`, `Confidence`, `Impact`, `Structural failure`, `Simpler path`, `Needed context`, `Evidence`), and fixed status/threshold tokens verbatim in English, because `scripts/check_report.py` parses them; prose descriptions may follow the user's language.

## Layout

```text
<report-dir>/
├── README.md     entry point: contract, scope, snapshot, findings index, ledgers, verification
├── findings/
│   └── F<n>.md   one card per finding; omit the folder when there are no findings
├── coverage.md   recursive coverage ledger
└── files.md      file inventory with 350-line diagnoses
```

When a ledger would run to several hundred rows, split it by top-level area into `coverage/<area>.md` or `files/<area>.md` in place of the single file, and link every split part from `README.md`.

## README.md

Replace every placeholder token (`<random-id>`, `[...]`, `/abs/path/...`) before running the checker. Place `Complete` or `Incomplete` at the very start of the `Completion` value rather than relying on mid-line backticks for completion status. `Parent report` and `Inherited settlements` are optional on standalone reviews (set to `None` or omit) and required for `post-fix delta of report ID` reports.

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
- Baseline: `[HEAD | merge-base commit SHA | commit SHA | branch | PR base | provided snippet context]`
- Reviewed HEAD: `[commit SHA | N/A for pasted code]`
- Input fingerprint: `[sha256-... | N/A for pasted code]`
- Snapshot consistency: `[Matches reviewed snapshot | Drifted - details]`
- Parent report: `[None | tb-YYYYMMDD-<id>]`
- Inherited settlements: `[None | settled intent and disproved claims carried forward]`
- Intent sources: `[None found | requirements, issue, PR description, design or migration notes]`
- Completion: `[Complete within reviewed scope | Incomplete - exact uncovered areas]`
- Assumptions: `[None | inferred scope, baseline, unreviewed branch commits or unstaged changes notice, environment, or product intent]`

## Review Snapshot

- Recommendation: `[Block | Changes requested | Discuss | Pass with caveat | Pass]`
- Why now: `[one sentence explaining the structural quality decision]`
- Findings count: `Blocker [n] | Major [n] | Minor [n] | Question [n]`
- Must-review now: `[top 1-3 F# findings, or None]`
- Coverage confidence: `[high | medium | low]`
- Biggest blind spot: `[short phrase, or None identified]`

## Findings Index

[If no findings exist, write `No structural findings identified in the reviewed scope.` Otherwise add one row per finding, ordered by severity with consecutive IDs `F1`, `F2`, ..., each linking its matching card.]

| ID | Severity | Surface | Structural risk | Confidence |
| --- | --- | --- | --- | --- |
| [`F1`](findings/F1.md) | `[Blocker, Major, Minor, or Question]` | `[file, module, component, API, helper, ownership boundary, state model, type boundary, test, or config]` | `[one-line risk or open question]` | `[high, medium, or low]` |

## Ledgers

- [Recursive coverage ledger](coverage.md): `[candidate count by status]`
- [File inventory](files.md): `[file count; files >= 350 lines]`

## Verification Commands

- `[read-only command and key outcome]`
```

Do not pre-assert `check_report.py` `-> OK` inside `README.md` before the check has run; run `python3 <skill-folder>/scripts/check_report.py <report-dir>` after writing the directory, confirm `OK` before handoff, and report that result in chat.

## findings/F<n>.md

Write one file per finding, named by its ID. Keep the heading severity plain (`# F1 Blocker - ...`, replacing `Blocker` with `Major`, `Minor`, or `Question`; the checker also tolerates backticked or bracketed severity). For a `Question`, replace `Simpler path` with `Needed context: [the intent, ownership, or constraint that decides the gate]`. When a diff newly relies on, duplicates, or exposes a structural or ownership flaw in an unchanged helper or shared contract, anchor `primary` in `Look here first` on the changed diff boundary and `secondary` on the unchanged helper or canonical owner.

```markdown
# F1 Blocker - [Short title]

- Surface: `[file, module, component, API, helper, ownership boundary, state model, type boundary, test, or config]`
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

Account for every changed structural area and every candidate the sweep added, including dismissed and merged ones. Every indexed `F#` must appear in at least one row as `Finding F#` or `Merged into F#`.

- `Source`: `initial inventory`, `discovered from F#` (uppercase `F#` matching an indexed finding), or `discovered from trace`.
- `Status`:
  - `Finding F#` (multiple findings allowed as `Finding F1, F2`; uppercase `F#`)
  - `Merged into F#` (uppercase `F#`)
  - `Reviewed - no issue` (requires concrete, non-empty structural evidence in `Evidence / next step`—never dismiss by superficial analogy to legacy sibling code, mode conflation, or single-path citation on shared mutable state)
  - `Not review-relevant`
  - `Not covered` (requires a concrete, non-empty blocker plus next step in `Evidence / next step`, and forces `Completion` to start with `Incomplete`)

```markdown
# Recursive Coverage Ledger

| Area / candidate | Source | Entry points | Status | Evidence / next step |
| --- | --- | --- | --- | --- |
| `[area or candidate]` | `[initial inventory, discovered from F#, or discovered from trace]` | `[file or entry-point links]` | `[Finding F#, Finding F1, F2, Merged into F#, Reviewed - no issue, Not review-relevant, or Not covered]` | `[concrete structural conclusion, or blocker plus concrete next step]` |
```

## files.md

Add at least one row (one row per changed or untracked file in scope; for pasted code, include one synthetic snippet row). Physical line counts (`wc -l`) use an exact `>= 350` boundary for maintained source:

- `Class`: `source`, `test`, `config`, `docs`, `generated`, or `vendored`.
- `Threshold`:
  - `under 350`: `Current lines < 350`.
  - `crossed 350`: `Baseline lines < 350` and `Current lines >= 350`.
  - `already over 350`: `Baseline lines >= 350` and `Current lines >= 350` (including files that shrank or had minor non-growth touches).
  - `excluded`: non-source classes (`test`, `config`, `docs`, `generated`, `vendored`), lockfiles, snapshots, fixtures, intentionally monolithic external formats, or prior Thermobot reports exempt from the 350-line source gate.
- `Boundary diagnosis and decision`: write `<diagnosis>; <decision>` or `<decision>` directly, using explicit decision clauses (validated across all rows):
  - `Finding F#` (multiple allowed as `Finding F1, F2`) or `Merged into F#` (uppercase `F#`; valid on any threshold).
  - `waived - <reason>` (requires a concrete reason; valid for cohesive `>= 350` files or `already over 350` files with shrinkage or non-growth touches).
  - `excluded - <reason>` (requires a concrete reason; use with `Threshold: excluded`, never with `crossed 350` or `already over 350`).
  - `reviewed - no issue` (valid only with `Threshold: under 350`).
  - `not covered - <blocker and next step>` (valid on any threshold, including `crossed 350` and `already over 350`, and requires `Completion` to start with `Incomplete`).

```markdown
# File Inventory

| Path | Class | Baseline lines | Current lines | Threshold | Boundary diagnosis and decision |
| --- | --- | ---: | ---: | --- | --- |
| `[path]` | `[source, test, config, docs, generated, or vendored]` | `[n]` | `[n]` | `[under 350, crossed 350, already over 350, or excluded]` | `[diagnosis; Finding F#, Merged into F#, waived - reason, excluded - reason, reviewed - no issue, or not covered - blocker and next step]` |
```

## Consistency Check

After writing the directory, run `python3 <skill-folder>/scripts/check_report.py <report-dir>`, fix every problem it prints until it exits `0` with `OK`, and report that result in chat. It validates required headings and contract fields (`Report type`, `Report ID`, snapshot fields, `Completion`), one-to-one index and card matching with consecutive `F#` numbering, card H1 and required body sections, severity counts, `Must-review now` IDs, recommendation mapping, split-ledger links, `coverage.md` statuses and reverse finding coverage, `files.md` classes, numeric line counts against `Threshold`, explicit decision clauses, `Not covered` forcing `Incomplete`, and unfilled template placeholders. It cannot judge whether the sweep was complete or a waiver is sound; that stays with the reviewer.
