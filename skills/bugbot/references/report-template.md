# Bugbot Report

## Report Contract

- Report type: `bugbot`
- Report ID: `bb-YYYYMMDD-<random-id>`
- Review date: `YYYY-MM-DD`
- Report path: `[absolute or repository-relative path]`
- Repository root: `[absolute path]`
- Artifact status: `Fixed review input; do not rewrite during repair`

## Scope

- Diff mode: `[branch changes | commit range | uncommitted changes]`
- Requested base: `[branch, revision range, or None]`
- Resolved baseline: `[merge-base commit | range start commit | HEAD commit]`
- Reviewed HEAD: `[commit ID]`
- Reviewed target: `[current working tree plus untracked non-ignored files | staged index | commit range end]`
- Input fingerprint: `[SHA-256 and construction: tracked binary diff plus sorted untracked paths/content hashes when working tree is in scope; exclude the new report and out-of-scope prior reports, retain explicitly requested review documentation]`
- Snapshot consistency: `[unchanged at handoff | reconciled changes | drift causing incomplete coverage]`
- Changed files: `[count]`
- Completion: `[Complete within reviewed scope | Incomplete - exact reason]`
- Custom instructions: `[None | concise summary]`
- Assumptions: `[None | scope, baseline, unreviewed branch commits outside scan, environment, or intent assumptions]`

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

`Reviewed - no bug found` describes the examined case and its exclusion evidence, not exhaustive safety; verify the exact branch's preconditions and visible state rather than dismissing by analogy to another lifecycle transition or operational mode. Never use a diff-added or diff-modified comment as sole authority that degraded recovery, dropped targets, or broken state is intentional, and never dismiss a candidate as pre-existing without verifying baseline equivalence (confirming the diff neither added a writer or trigger nor widened exposure). For shared or unkeyed mutable state, a `Reviewed - no bug found` dismissal must name both the checked non-normal exit paths (abort, error, empty payload) and the codebase writers checked outside the cited clearing path. Do not rely on added or modified tests as exclusion evidence without checking for synthetic event/wire sequences that omit a real upstream phase (trace the omitted phase statically in production) or vacuous assertions (such as pre-action state already satisfying post-action checks or omitted call-count assertions after resetting mocks or spies); record material test-mirage gaps in `Blind Spots` when production behavior is statically resolved, and record unresolved protocol-divergence gaps, uninspected caller/observer/writer clusters from a shared-invariant sweep, and unresolved dependency/platform assumptions in both `Not covered` and `Blind Spots`. Runtime absence alone is not a blocker when static evidence resolves the behavior.

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
- `[yes | no]` Substantive no-bug conclusions verify the exact branch's preconditions and visible state with concrete exclusion evidence (no superficial lifecycle analogies or mode conflation).
- `[yes | no]` No diff-added or diff-modified comment was used as sole authority to excuse degraded recovery, dropped targets, or broken behavior as intentional.
- `[yes | no]` Every "pre-existing in baseline" dismissal is backed by verified baseline code showing the diff neither added a writer or trigger nor widened exposure.
- `[yes | no]` Any dismissal of a shared or unkeyed mutable-state leak accounts for non-normal exit paths (abort, error, empty payload) and all codebase writers outside the cited clearing path.
- `[yes | no]` Any modified shared lock/focus/ownership controller, delegate/callback wrapper, cancellation/rollback path, event handler, tightened multi-phase gate, or shared mutable state triggered a repository-wide sweep with grep-hit exhaustion (or listed uninspected caller/observer/writer clusters in `Not covered` and `Blind Spots`).
- `[yes | no]` Added or modified tests cited during review were checked for synthetic sequence divergence (omitted upstream phases traced statically in production) and vacuous assertions, and any material test-mirage or helper-reported protocol-divergence warnings were traced or recorded in `Blind Spots`.
- `[yes | no]` Every `Finding B#` ledger row maps to a finding card.
- `[yes | no]` Every `Not covered` row names a blocker and next step, and completion is `Incomplete`.
- `[yes | no]` Severity counts match the finding cards.
- `[yes | no]` Recommendation follows the skill's mechanical mapping.
