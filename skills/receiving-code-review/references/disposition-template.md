# Code Review Resolution Report

## Contents

1. [Report Contract](#report-contract)
2. [Source Review](#source-review)
3. [Current Scope](#current-scope)
4. [Re-Review Orchestration](#re-review-orchestration)
5. [Intake Integrity](#intake-integrity)
6. [Disposition Ledger](#disposition-ledger)
7. [Challenges to Source Review](#challenges-to-source-review)
8. [Implementation Plan and Delegation](#implementation-plan-and-delegation)
9. [Code Changes](#code-changes)
10. [Verification](#verification)
11. [Review Refresh](#review-refresh)
12. [Residual Risks](#residual-risks)
13. [Final State](#final-state)
14. [Resolution Self-Check](#resolution-self-check)

## Report Contract

- Schema: `receiving-code-review/v2`
- Resolution ID: `rr-YYYYMMDD-<random-id>`
- Generated at: `YYYY-MM-DDTHH:MM:SSZ`
- Resolution path: `[absolute or repository-relative path]`
- Source skill: `receiving-code-review`
- Lifecycle: `[Re-reviewing | Implementation in progress | Verification in progress | Resolved | Partially resolved]`
- Git index mutation by this workflow: `None`

This report is a companion to the immutable source review. It records current evidence, challenges, dispositions, implementation, and verification without rewriting the original claim history.

## Source Review

- Source schema: `[code-review/v2 | legacy/unstructured]`
- Source report ID: `[cr-YYYYMMDD-<id> | synthetic-source-<id>]`
- Source report path: `[path | Not available]`
- Source recommendation: `[Block | Changes requested | Discuss | Pass with caveat | Pass | Not stated]`
- Source completion: `[Complete within reviewed scope | Incomplete - reason | Not stated]`
- Source scope fingerprint: `[sha256:<digest> | Unavailable - reason]`
- Source item counts: `F [n] | T [n] | unresolved A [n] | intake I [n]`

## Current Scope

- Scope kind: `[working tree | staged diff | commit range | branch diff | pull request | file set | pasted code]`
- Scope description: `[precise current scope]`
- Baseline: `[ref and SHA or context]`
- Target: `[ref and SHA | working tree | staged index | provided code]`
- Current scope fingerprint: `[sha256:<digest> | Unavailable - reason]`
- Scope match: `[Exact | Drifted | Stale | Unknown]`
- Git state at intake: `[staged paths, unstaged paths, untracked paths, or clean]`
- Pre-existing staged paths: `[paths | None]`
- Environment limits: `[credentials, runtime, platform, tools, or None]`

## Re-Review Orchestration

- Assessment subagent: `[V0 launched | Subagent unavailable - coordinator fallback]`
- Orchestration decision: `[Single verifier | Parallel specialists]`
- Decision confidence: `[high | medium | low]`
- Decision rationale: `[why this mode fits current scope and source review results]`
- Coordinator override: `[None | decision changed and reason]`

### Verifier Assignments

| Verifier | Angle | Owned item IDs | Owned surfaces | Adversarial role | Status |
| --- | --- | --- | --- | --- | --- |
| `V1` | `[current behavior/contracts/security/tests/etc.]` | `[F1, T1, A3]` | `[paths or behavior paths]` | `[yes | no]` | `[Complete | Partial | Failed | Fallback]` |

### Re-Review Synthesis

`[State how the coordinator independently verified final dispositions, how conflicts were resolved, and what remains uncertain.]`

## Intake Integrity

- Index/card agreement: `[yes | no - I#]`
- Test-gap enumeration agreement: `[yes | no - I#]`
- Coverage/handoff agreement: `[yes | no - I#]`
- Source/current scope agreement: `[yes | no - I#]`
- Source report structurally valid: `[yes | no | not applicable]`

### Intake Issues

If none exist, write `None.` Otherwise list every synthetic `I#` item.

| ID | Integrity problem | Approval or implementation risk | Evidence | Required resolution |
| --- | --- | --- | --- | --- |
| `I1` | `[mismatch or stale identity]` | `[why it matters]` | `[source/current evidence]` | `[regenerate, re-review, normalize, or carry]` |

## Disposition Ledger

Include exactly one row for every source `F#`, standalone `T#`, source `A#` marked `Not covered`, and intake `I#`.

Allowed verdicts: `Confirmed`, `Narrowed`, `Reclassified`, `Disproved`, `Stale`, `Duplicate`, `Intentional`, `Unverifiable`, `Open`.

Allowed action states: `No change needed`, `Fix required`, `Test required`, `Evidence/answer required`, `Coverage verification required`, `Carried forward`.

Allowed implementation states: `Not needed`, `Not started`, `Implemented`, `Verified`, `Blocked`, `Carried forward`.

| Item ID | Source status | Re-review verdict | Action state | Implementation state | Challenge | Evidence | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `F1` | `[Blocker | Major | Minor | Question]` | `[verdict]` | `[action state]` | `[implementation state]` | `[C# | None]` | `[current code/test/runtime/contract evidence]` | `[specific next action | None]` |
| `T1` | `[Blocker | Major | Minor test gap]` | `[verdict]` | `[action state]` | `[implementation state]` | `[C# | None]` | `[evidence]` | `[next action | None]` |
| `A3` | `Not covered` | `[verdict]` | `[action state]` | `[implementation state]` | `[C# | None]` | `[coverage evidence]` | `[next action | None]` |
| `I1` | `Intake integrity` | `[verdict]` | `[action state]` | `[implementation state]` | `[C# | None]` | `[evidence]` | `[next action | None]` |

## Challenges to Source Review

If no source claim is challenged, write `None.` Otherwise repeat this card for every material challenge.

### C1 - Challenge to F1

Source claim:
`[accurate restatement of the source claim]`

Source evidence:
- `[evidence the source relied on]`

Counterclaim:
`[what current evidence supports instead]`

Argument:
`[why the evidence supports the counterclaim and where the source reasoning fails, narrows, or became stale]`

Counter-evidence:
- `[current code path, focused test, runtime output, contract, history, or other concrete evidence]`

Evidence supporting the source:
- `[remaining evidence for the original concern | None]`

Limits and residual uncertainty:
- `[what remains unproven | None]`

Settlement criterion:
- `[specific evidence that would conclusively settle any remaining dispute]`

Verdict effect:
- Re-review verdict: `[Narrowed | Reclassified | Disproved | Stale | Duplicate | Intentional | Unverifiable | Open]`
- Severity/action effect: `[change or no change]`
- Independent adversarial verifier: `[V# | Not required | Unavailable]`

## Implementation Plan and Delegation

- Actionable IDs: `[F1, T1 | None]`
- Coding stage: `[Required | Not required - reason]`
- Coding subagent: `[D1 launched | Subagent unavailable - coordinator fallback | Not required]`
- Coding mode: `[Single coding agent | Multiple disjoint agents | Not applicable]`
- Allowed files or surfaces: `[paths/surfaces | Not applicable]`
- Prohibited scope: `[unrelated refactors, staging, commit, etc.]`
- Regression/security/contract risk assessment: `[risks and why plan is scoped]`
- Required verification: `[focused tests, runtime checks, review refresh]`
- Staging rule: `Preserve pre-existing staged state; leave new changes unstaged.`

### Coding Assignments

If coding is not required, write `None.`

| Coding agent | Actionable item IDs | File ownership | Expected result | Required verification | Status |
| --- | --- | --- | --- | --- | --- |
| `D1` | `[F1, T1]` | `[paths or subsystem]` | `[behavior/test outcome]` | `[commands/checks]` | `[Complete | Partial | Failed | Fallback]` |

## Code Changes

If no code or tests changed, write `None.`

| Item ID | Coding agent | Changed files | Focused change | Unrelated churn check |
| --- | --- | --- | --- | --- |
| `F1` | `D1` | `[paths]` | `[what changed and why]` | `[clean | rejected/removed details]` |

## Verification

### Coordinator Verification

| Item ID / surface | Command or method | Result | Confidence | Remaining gap |
| --- | --- | --- | --- | --- |
| `F1` | `[focused test, runtime repro, static trace, contract check]` | `[pass/fail and key output]` | `[high | medium | low]` | `[None | gap]` |

### Coding Subagent Verification

| Coding agent | Command or method | Result |
| --- | --- | --- |
| `D1` | `[command]` | `[outcome]` |

### Git State Verification

- Pre-existing staged paths unchanged: `[yes | no - incident details]`
- New changes staged: `No`
- Final unstaged changed paths: `[paths | None]`
- Final untracked paths: `[paths | None]`

## Review Refresh

- Refresh required: `[yes | no - reason]`
- Refreshed report ID: `[cr-YYYYMMDD-<id> | None]`
- Refreshed report path: `[path | None]`
- Refreshed recommendation: `[Block | Changes requested | Discuss | Pass with caveat | Pass | Not applicable]`
- Refreshed scope fingerprint: `[sha256:<digest> | None]`
- Remaining review items after refresh: `[IDs | None]`

## Residual Risks

| ID / area | Residual risk | Why unresolved | Concrete next step | Owner |
| --- | --- | --- | --- | --- |
| `[F#, T#, A#, I#, or area]` | `[risk]` | `[reason]` | `[verification or follow-up]` | `[owner or unknown]` |

If none exist, write `None.`

## Final State

- Completion: `[Resolved | Partially resolved | Blocked]`
- Resolved item IDs: `[IDs | None]`
- Challenged item IDs: `[IDs | None]`
- Implemented item IDs: `[IDs | None]`
- Verified item IDs: `[IDs | None]`
- Carried-forward item IDs: `[IDs | None]`
- Open item IDs: `[IDs | None]`
- Final source recommendation effect: `[unchanged | strengthened | weakened | superseded by refreshed report]`
- Git index mutation by this workflow: `None`

## Resolution Self-Check

- `[yes | no]` Every source `F#`, standalone `T#`, unresolved `A#`, and intake `I#` appears exactly once in `Disposition Ledger`.
- `[yes | no]` Every challenge includes claim, counterclaim, argument, evidence, limits, settlement criterion, and verdict effect.
- `[yes | no]` Every `Fix required` or `Test required` item was assigned to a coding subagent or unavailable fallback is disclosed.
- `[yes | no]` Every implemented item has coordinator verification.
- `[yes | no]` Scope drift and source inconsistencies are explicit.
- `[yes | no]` A material code change has a linked refreshed review, or a reason refresh was unnecessary.
- `[yes | no]` Pre-existing staged state is unchanged and new changes remain unstaged.
- `[yes | no]` `python scripts/validate_disposition_report.py <resolution> --source-report <source>` passes.
