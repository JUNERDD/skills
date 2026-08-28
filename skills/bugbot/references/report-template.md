# Bugbot Report

## Report Contract

- Report type: `bugbot`
- Report ID: `bb-YYYYMMDD-<random-id>`
- Review date: `YYYY-MM-DD`
- Report path: `[absolute or repository-relative path]`
- Repository root: `[absolute path]`
- Artifact status: `Fixed review input; do not rewrite during repair`

## Scope

- Diff mode: `[branch changes | uncommitted changes]`
- Requested base: `[branch or None]`
- Resolved baseline: `[merge-base commit | HEAD commit]`
- Reviewed target: `[current working tree plus untracked non-ignored files]`
- Changed files: `[count]`
- Completion: `[Complete within reviewed scope | Incomplete - exact reason]`
- Custom instructions: `[None | concise summary]`
- Assumptions: `[None | scope, baseline, environment, or intent assumptions]`

## Detection Snapshot

- Recommendation: `[Block | Changes requested | Discuss | Pass with caveat | Pass]`
- Completion: `[Complete within reviewed scope | Incomplete - exact uncovered candidates]`
- Why now: `[one sentence explaining the decision]`
- Findings count: `high [n] | medium [n] | low [n]`
- Must-review now: `[top 1-3 B# findings, or None]`
- Coverage confidence: `[high | medium | low]`
- Biggest blind spot: `[short phrase, or None identified]`

## Complete Findings Index

If no findings exist, write `No introduced production bugs identified in the reviewed scope.` Otherwise add one row for every finding.

| ID | Severity | Category | Location | Title |
| --- | --- | --- | --- | --- |
| `B1` | `[high | medium | low]` | `[category]` | `[path:start-end](/absolute/path#Lstart)` | `[title]` |

## Findings

If no findings exist, write `None.` Otherwise repeat this card for every finding.

### B1 [severity] - [Title]

- Category: `[category]`
- Location: `[repository-relative path:start-end](/absolute/path#Lstart)`
- Confirmation selector: `B1`

Description: `[concise root cause and production impact]`

Rationale: `[why the reviewed change introduced a production bug]`

Evidence:

- `[changed-line evidence]`
- `[caller, callee, contract, state, test, or runtime evidence proving the causal path]`

## Detection Coverage Ledger

Account for every changed area and every meaningful candidate added by the recursive sweep.

| Area / candidate | Changed entry point | Status | Result | Evidence / next step |
| --- | --- | --- | --- | --- |
| `[candidate]` | `[repository-relative path:start-end]` | `[Finding B# | Reviewed - no bug found | Not production-relevant | Not covered]` | `[short conclusion]` | `[evidence, or blocker plus concrete next step]` |

## Evidence Appendix

### Diff Inventory

| Path | Change status | Production surfaces considered |
| --- | --- | --- |
| `[repository-relative path]` | `[modified | added | deleted | renamed | untracked]` | `[contracts, callers, persistence, async effects, tests, none, or unknown]` |

### Verification Commands

- `[read-only command and key outcome]`
- `[read-only command and key outcome]`

### Dismissed Or Merged Candidates

If none exist, write `None.`

| Candidate | Decision | Reason |
| --- | --- | --- |
| `[candidate]` | `[dismissed | merged into B# | not production-relevant]` | `[evidence]` |

### Blind Spots

If none exist, write `None identified.`

| Area | Why it remains unverified | What would resolve it |
| --- | --- | --- |
| `[candidate or surface]` | `[missing context, unavailable tool, credentials, runtime, or other blocker]` | `[specific next step]` |

## Report Self-Check

- `[yes | no]` Every finding appears in both `Complete Findings Index` and `Findings`.
- `[yes | no]` Every meaningful recursive candidate appears in `Detection Coverage Ledger`.
- `[yes | no]` Every `Finding B#` ledger row maps to a finding card.
- `[yes | no]` Every `Not covered` row names a blocker and next step, and completion is `Incomplete`.
- `[yes | no]` Severity counts match the finding cards.
- `[yes | no]` Recommendation follows the skill's mechanical mapping.
