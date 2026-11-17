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
- Reviewed HEAD: `[commit ID]`
- Reviewed target: `[current working tree plus untracked non-ignored files]`
- Input fingerprint: `[SHA-256 and construction: tracked binary diff plus sorted untracked paths/content hashes; exclude the new report and out-of-scope prior reports, retain explicitly requested review documentation]`
- Snapshot consistency: `[unchanged at handoff | reconciled changes | drift causing incomplete coverage]`
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
| `B1` | `[high / medium / low]` | `[category]` | `[path:start-end](/absolute/path#Lstart)` | `[title]` |

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

Account for every changed area, its affected behaviors, and every meaningful candidate added by the recursive sweep. Use event sequences for stateful behavior and input/output cases for stateless behavior; include relevant intermediate outcomes. Expected behavior needs a source, not just an assertion that the implementation is intended.

| Area / behavior / candidate | Changed entry point | Trigger / event sequence | Expected behavior and source | Status | Evidence / exclusion / next step |
| --- | --- | --- | --- | --- | --- |
| `[candidate]` | `[repository-relative path:start-end]` | `[input or ordered events, relevant identity/scope and intermediate outcome]` | `[contract and its source]` | `[Finding B# / Reviewed - no bug found / Not production-relevant / Not covered]` | `[static causal trace, existing test, or authorized runtime evidence; for dismissal, the invariant excluding failure; for uncovered work, blocker and concrete next step]` |

`Reviewed - no bug found` describes the examined case and its exclusion evidence, not exhaustive safety. A material unresolved dependency or platform assumption belongs in `Not covered`. Runtime absence alone is not a blocker when static evidence resolves the behavior.

## Evidence Appendix

### Diff Inventory

| Path | Change status | Production surfaces considered |
| --- | --- | --- |
| `[repository-relative path]` | `[modified / added / deleted / renamed / untracked]` | `[contracts, callers, persistence, async effects, tests, none, or unknown]` |

### Verification Commands

- `[read-only command and key outcome]`
- `[read-only command and key outcome]`

### Dismissed Or Merged Candidates

If none exist, write `None.`

| Candidate | Decision | Reason / exclusion evidence |
| --- | --- | --- |
| `[candidate]` | `[dismissed / merged into B# / not production-relevant]` | `[evidence]` |

### Blind Spots

If none exist, write `None identified.`

| Area | Why it remains unverified | What would resolve it |
| --- | --- | --- |
| `[candidate or surface]` | `[missing context, unavailable tool, credentials, runtime, or other blocker]` | `[specific next step]` |

## Report Self-Check

- `[yes | no]` Every finding appears in both `Complete Findings Index` and `Findings`.
- `[yes | no]` The reviewed input snapshot is identified and consistent with the evidence.
- `[yes | no]` Every changed area, affected behavior, and meaningful recursive candidate appears in `Detection Coverage Ledger`.
- `[yes | no]` Relevant entry, exit, replacement, intermediate, and terminal behavior is accounted for; inapplicable transitions are not required.
- `[yes | no]` Substantive no-bug conclusions name examined cases and concrete exclusion evidence.
- `[yes | no]` Every `Finding B#` ledger row maps to a finding card.
- `[yes | no]` Every `Not covered` row names a blocker and next step, and completion is `Incomplete`.
- `[yes | no]` Severity counts match the finding cards.
- `[yes | no]` Recommendation follows the skill's mechanical mapping.
