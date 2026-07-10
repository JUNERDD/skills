# Code Review Resolution Report

## Contents

1. [Report Contract](#report-contract)
2. [Source Review](#source-review)
3. [Current Scope](#current-scope)
4. [Re-Review Orchestration](#re-review-orchestration)
5. [Intake Integrity](#intake-integrity)
6. [Disposition Lineage](#disposition-lineage)
7. [Execution Chain Reconstruction](#execution-chain-reconstruction)
8. [Disposition Ledger](#disposition-ledger)
9. [Challenges to Source Review](#challenges-to-source-review)
10. [Implementation Plan and Delegation](#implementation-plan-and-delegation)
11. [Code Changes](#code-changes)
12. [Verification](#verification)
13. [Post-Implementation Review](#post-implementation-review)
14. [Residual Risks](#residual-risks)
15. [Final State](#final-state)
16. [Resolution Self-Check](#resolution-self-check)

## Report Contract

- Report type: `receiving-code-review`
- Resolution ID: `rr-YYYYMMDD-<random-id>`
- Review chain ID: `rc-YYYYMMDD-<id>`
- Generated at: `YYYY-MM-DDTHH:MM:SSZ`
- Resolution path: `[absolute or repository-relative path]`
- Source skill: `receiving-code-review`
- Status: `[Re-reviewing | Implementation in progress | Verification in progress | Resolved | Partially resolved | Blocked]`
- Git index mutation by this workflow: `None`

This report records current evidence, challenges, dispositions, implementation, and verification while leaving the supplied review artifact unchanged. Link the two artifacts by Report ID when the source is a canonical `code-review` report.

## Source Review

- Source type: `[code-review report | PR feedback | review notes]`
- Source report ID: `[cr-YYYYMMDD-<id> | synthetic-source-<id>]`
- Source report path: `[path | Not available]`
- Source recommendation: `[Block | Changes requested | Discuss | Pass with caveat | Pass | Not stated]`
- Source completion: `[Complete within reviewed scope | Incomplete - reason | Not stated]`
- Source scope fingerprint: `[sha256:<digest> | Unavailable - reason]`
- Source review generation: `[0 | 1]`
- Source review trigger: `[initial | post-implementation | unstructured]`
- Source parent resolution ID: `[None | rr-YYYYMMDD-<id>]`
- Source parent resolution path: `[None | path]`
- Continuation authority: `[Initial receiving handoff | Explicit current user instruction]`
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

`[State how the coordinator verified full EC# chains before local dispositions, resolved conflicts, and handled blocked chains.]`

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

## Disposition Lineage

Include every source `F#` and `T#`. For generation `0`, use `New`. For generation `1`, inherit protected parent decisions with the same exact issue key/fingerprint unless changed code, contract, or material evidence justifies `Reopened`.

| Item ID | Issue key | Issue fingerprint | Parent resolution / item / verdict | Chain or evidence delta | Lineage state | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `F1` | `behavior; entry=...; contract=...; effect=...` | `ifp-sha256:<64 lowercase hex>` | `[None | rr-... / F# / Intentional]` | `[None | kind:<code|contract|evidence>; ref:<source>; change:<concrete delta>]` | `[New | Inherited | Reopened]` | `[source identity, parent disposition, changed code/contract/evidence]` |

## Execution Chain Reconstruction

Create an `EC#` before assigning a final disposition. Reuse one chain for multiple items when they share the same real trigger, propagation, expected basis, and terminal effect.

Fill every stage for `Complete`; use `Checked: none - <reason>` for an explicitly inspected but inapplicable stage. Use `Blocked` when evidence is unavailable.

| Chain ID | Item IDs | Trigger / entry | Guards / alternate paths | Propagation / dependencies | Terminal effect | Failure semantics | Expected basis | Evidence / gaps | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `EC1` | `[F1, T1]` | `[real trigger, input, semantic entry]` | `[validation, auth, config, feature gates, alternate entries]` | `[control/data/state, async, cache, queue, persistence, external calls]` | `[user/API/CLI/data/security/operations/test effect]` | `[errors, retries, ordering, idempotency, concurrency, timeout, cleanup]` | `kind:<kind>; strength:<authoritative|inferred|unavailable>; evidence:<source>` | `[code/test/runtime/contract evidence and exact gaps]` | `[Complete | Blocked]` |

## Disposition Ledger

Include exactly one row for every source `F#`, standalone `T#`, source `A#` marked `Not covered`, and intake `I#`.

Allowed verdicts: `Confirmed`, `Narrowed`, `Reclassified`, `Disproved`, `Stale`, `Duplicate`, `Intentional`, `Unverifiable`, `Open`.

Allowed action states: `No change needed`, `Fix required`, `Test required`, `Evidence/answer required`, `Coverage verification required`, `Carried forward`.

Allowed implementation states: `Not needed`, `Not started`, `Implemented`, `Verified`, `Blocked`, `Carried forward`.

| Item ID | Issue fingerprint | Execution chain(s) | Source status | Re-review verdict | Action state | Implementation state | Challenge | Evidence | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `F1` | `ifp-sha256:<64 lowercase hex>` | `EC1` | `[Blocker | Major | Minor | Question]` | `[verdict]` | `[action state]` | `[implementation state]` | `[C# | None]` | `[whole-chain code/test/runtime/contract evidence]` | `[specific next action | None]` |
| `T1` | `ifp-sha256:<64 lowercase hex>` | `EC1` | `[Blocker | Major | Minor test gap]` | `[verdict]` | `[action state]` | `[implementation state]` | `[C# | None]` | `[whole-chain evidence]` | `[next action | None]` |
| `A3` | `N/A` | `EC2` | `Not covered` | `[verdict]` | `[action state]` | `[implementation state]` | `[C# | None]` | `[coverage evidence]` | `[next action | None]` |
| `I1` | `N/A` | `N/A` | `Intake integrity` | `[verdict]` | `[action state]` | `[implementation state]` | `[C# | None]` | `[evidence]` | `[next action | None]` |

## Challenges to Source Review

If no source claim is challenged, write `None.` Otherwise repeat this card for every material challenge.

### C1 - Challenge to F1

Execution chains:
- `EC1`

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

Decision authority:
- `[user/product owner/requirement/contract/invariant | Not applicable]`

Reopen condition:
- `[specific code, contract, or evidence change required to revisit this decision]`

Verdict effect:
- Re-review verdict: `[Narrowed | Reclassified | Disproved | Stale | Duplicate | Intentional | Unverifiable | Open]`
- Severity/action effect: `[No change needed | Fix required | Test required | Evidence/answer required | Coverage verification required | Carried forward]`
- Independent adversarial verifier: `[V# | Not required | Unavailable]`

## Implementation Plan and Delegation

- Actionable IDs: `[F1, T1 | None]`
- Coding stage: `[Required | Not required - reason]`
- Coding subagent: `[D1 launched | Subagent unavailable - coordinator fallback | Not required]`
- Coding mode: `[Single coding agent | Multiple disjoint agents | Not applicable]`
- Allowed files or surfaces: `[paths/surfaces | Not applicable]`
- Affected execution chains: `[EC1, EC2 | None]`
- Prohibited scope: `[unrelated refactors, staging, commit, etc.]`
- Regression/security/contract risk assessment: `[risks and why plan is scoped]`
- Required verification: `[focused tests, runtime checks, post-implementation review]`
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

## Post-Implementation Review

- Post-review budget at intake: `[0 | 1]`
- Post-review runs used: `[0 | 1]`
- Post-implementation review required: `[yes | no - reason]`
- Post-review generation: `[1 | None]`
- Post-review scope: `[implementation delta plus affected EC# chains | None]`
- Post-review report ID: `[cr-YYYYMMDD-<id> | None]`
- Post-review report path: `[path | None]`
- Post-review recommendation: `[Block | Changes requested | Discuss | Pass with caveat | Pass | Not applicable]`
- Post-review scope fingerprint: `[sha256:<digest> | None]`
- Remaining review items after post-review: `[IDs | None]`
- Automatic follow-on receiving: `No`
- Terminal handoff: `Return remaining findings to the user or product owner; do not invoke receiving-code-review automatically.`
- Termination reason: `[no post-review needed | terminal generation completed | review budget exhausted | explicit user decision required]`

## Residual Risks

| ID / area | Residual risk | Why unresolved | Concrete next step | Owner |
| --- | --- | --- | --- | --- |
| `[F#, T#, A#, I#, V#-N#, D#-N#, or area]` | `[risk]` | `[reason]` | `[verification or follow-up]` | `[owner or unknown]` |

If none exist, write `None.`

## Final State

These IDs describe the current source disposition ledger only; post-review findings remain in the terminal handoff.

- Completion: `[Resolved | Partially resolved | Blocked]`
- Resolved item IDs: `[IDs | None]`
- Challenged item IDs: `[IDs | None]`
- Implemented item IDs: `[IDs | None]`
- Verified item IDs: `[IDs | None]`
- Carried-forward item IDs: `[IDs | None]`
- Open item IDs: `[IDs | None]`
- Final source recommendation effect: `[unchanged | strengthened | weakened | superseded by post-review report]`
- Review-chain completion: `[Terminal | Awaiting explicit user decision]`
- Git index mutation by this workflow: `None`

## Resolution Self-Check

- `[yes | no]` Every source `F#`, standalone `T#`, unresolved `A#`, and intake `I#` appears exactly once in `Disposition Ledger`.
- `[yes | no]` Every source `F#`, standalone `T#`, and unresolved `A#` references a complete or explicitly blocked `EC#` covering its whole execution chain.
- `[yes | no]` Every source `F#` and `T#` has lineage with an exact issue key and verified fingerprint; protected parent decisions are inherited or reopened with concrete delta evidence.
- `[yes | no]` Blocked execution chains produce only `Open` or `Unverifiable` and never actionable fixes/tests.
- `[yes | no]` Verdict, action, and implementation states satisfy the compatibility matrix.
- `[yes | no]` Every challenge includes claim, counterclaim, argument, evidence, limits, settlement criterion, and verdict/action effects that exactly match its disposition row.
- `[yes | no]` Every `Fix required` or `Test required` item appears exactly once in `Coding Assignments`, and unavailable fallback is disclosed when used.
- `[yes | no]` Every `Implemented` or `Verified` item appears exactly once in `Code Changes` and has coordinator verification.
- `[yes | no]` Report-contract `Status` exactly matches final `Completion`.
- `[yes | no]` Every distinct material verifier/coding discovery outside the source universe is recorded as a provisional residual candidate and did not trigger automatic scope expansion.
- `[yes | no]` Scope drift and source inconsistencies are explicit.
- `[yes | no]` Post-review use is within the 0/1 budget; any generation `1` report is terminal and automatic follow-on receiving is `No`.
- `[yes | no]` Pre-existing staged state is unchanged and new changes remain unstaged.
- `[yes | no]` The validator passes; a generation `1` source includes `--parent-resolution <parent-resolution>`.
