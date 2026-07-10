# Code Review Report

## Contents

1. [Report Contract](#report-contract)
2. [Scope](#scope)
3. [Review Orchestration](#review-orchestration)
4. [Review Snapshot](#review-snapshot)
5. [Complete Findings Index](#complete-findings-index)
6. [Blocker](#blocker)
7. [Major](#major)
8. [Minor](#minor)
9. [Questions](#questions)
10. [Test Gaps](#test-gaps)
11. [Review Coverage Ledger](#review-coverage-ledger)
12. [Subagent Candidate Adjudication](#subagent-candidate-adjudication)
13. [Evidence Appendix](#evidence-appendix)
14. [Receiving Handoff](#receiving-handoff)
15. [Report Self-Check](#report-self-check)

## Report Contract

- Report type: `code-review`
- Report ID: `cr-YYYYMMDD-<random-id>`
- Generated at: `YYYY-MM-DDTHH:MM:SSZ`
- Report path: `[absolute or repository-relative path]`
- Source skill: `code-review`
- Status: `[Review complete | Review incomplete]`
- Git mutation during review: `None`
- Scope fingerprint: `[sha256:<digest> | Unavailable - reason]`

Treat this completed report as the fixed review input for downstream work. Do not rewrite it during receiving or implementation; record dispositions, challenges, code changes, and verification in a separate `receiving-code-review` resolution report that references this Report ID.

## Scope

- Review date: `YYYY-MM-DD`
- Scope kind: `[working tree | staged diff | commit range | branch diff | pull request | file set | pasted code]`
- Scope description: `[precise human-readable scope]`
- Baseline: `[ref and commit SHA, or provided context]`
- Target: `[ref and commit SHA | working tree | staged index | provided code]`
- Changed paths: `[count]`
- Diff size: `[additions/deletions or Unavailable]`
- Completion: `[Complete within reviewed scope | Incomplete - exact reason]`
- Requirements consulted: `[issue, PR description, design document, contract, or None available]`
- Assumptions: `[scope, environment, credentials, product intent, or None]`
- Excluded as unrelated: `[paths/surfaces or None]`

## Review Orchestration

- Assessment subagent: `[R0 launched | Subagent unavailable - coordinator fallback]`
- Orchestration decision: `[Single reviewer | Parallel specialists]`
- Decision confidence: `[high | medium | low]`
- Decision rationale: `[why this mode is proportionate to semantic scope and risk]`
- Coordinator override: `[None | decision changed and reason]`
- Context or tool limits: `[limits or None]`

### Risk Dimensions

- `[risk dimension and why it matters]`
- `[risk dimension and why it matters]`

### Reviewer Assignments

| Reviewer | Angle | Owned surfaces | Mandatory cross-checks | Status |
| --- | --- | --- | --- | --- |
| `R1` | `[correctness/contracts/etc.]` | `[paths or behavior surfaces]` | `[integration/security/test cross-checks]` | `[Complete | Partial | Failed | Fallback]` |

### Synthesis Statement

`[State that the coordinator independently re-verified every accepted candidate, how conflicts were resolved, and which surfaces remain blind spots.]`

## Review Snapshot

- Recommendation: `[Block | Changes requested | Discuss | Pass with caveat | Pass]`
- Completion: `[Complete within reviewed scope | Incomplete - exact uncovered area]`
- Why now: `[one sentence explaining the decision]`
- Must-review now: `[top one to three IDs only; full list is below]`
  1. `F#` `[short title]`
  2. `F#` `[short title]`
  3. `T# or A#` `[short title]`
- Findings count: `Blocker [n] | Major [n] | Minor [n] | Question [n]`
- Standalone test gaps: `Blocker [n] | Major [n] | Minor [n]`
- Coverage confidence: `[high | medium | low]`
- Biggest blind spot: `[short phrase | None identified]`

## Complete Findings Index

If no findings exist, write `No code-review findings identified in the reviewed scope.`

Otherwise add exactly one row for every final `F#` finding. `Origin` names the proposing reviewer or `Coordinator`; `Verification` states how the coordinator checked it.

| ID | Severity | Surface | Review risk | Confidence | Origin | Verification |
| --- | --- | --- | --- | --- | --- | --- |
| `F1` | `[Blocker | Major | Minor | Question]` | `[route, command, API, helper, config, test, etc.]` | `[one-line risk or approval question]` | `[high | medium | low]` | `[R# | Coordinator | multiple]` | `[static trace | runtime | targeted test | contract evidence]` |

## Blocker

If none exist, write `None.` Otherwise repeat this card for every blocker.

### F1 Blocker - [Short title]

Impact: `[user, security, data, contract, availability, or release impact]`
Review reason: `[why this stops approval]`
Surface: `[route, feature, command, API, migration, security boundary, output, etc.]`
Confidence: `[high | medium | low]`
Origin: `[R# candidate ID, Coordinator, or multiple]`
Coordinator verification: `[what was independently checked]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`
- `[secondary](/abs/path/file.tsx#L42)`

Failure mode:
- Expected: `[required behavior, invariant, contract, or coverage]`
- Current: `[what the reviewed change does instead]`

Evidence:
- `[runtime reproduction, focused test, log, fixture, output, code-path trace, or missing-test evidence]`

Assumptions and limits:
- `[assumption or None]`

Reviewer action:
`[block until fixed | block until disproven | request focused verification]`

## Major

If none exist, write `None.` Otherwise repeat this card for every major finding.

### F2 Major - [Short title]

Impact: `[meaningful bug, regression, security, contract, or coverage impact]`
Review reason: `[why this should be fixed or answered before approval]`
Surface: `[route, feature, command, API, migration, security boundary, output, etc.]`
Confidence: `[high | medium | low]`
Origin: `[R# candidate ID, Coordinator, or multiple]`
Coordinator verification: `[what was independently checked]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`
- `[secondary](/abs/path/file.tsx#L42)`

Failure mode:
- Expected: `[required behavior, invariant, contract, or coverage]`
- Current: `[what the reviewed change does instead]`

Evidence:
- `[what proves the concern and what remains uncertain]`

Assumptions and limits:
- `[assumption or None]`

Reviewer action:
`[request fix | request proof | request test | raise before approval]`

## Minor

If none exist, write `None.` Otherwise repeat this card for every minor finding.

### F3 Minor - [Short title]

Impact: `[lower-impact bug, narrow debt, or non-blocking coverage risk]`
Review reason: `[why it is worth carrying]`
Surface: `[route, feature, command, API, helper, test, output, etc.]`
Confidence: `[high | medium | low]`
Origin: `[R# candidate ID, Coordinator, or multiple]`
Coordinator verification: `[what was independently checked]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`

Failure mode:
- Expected: `[preferred behavior, coverage, or constraint]`
- Current: `[current lower-risk gap]`

Evidence:
- `[what was checked]`

Assumptions and limits:
- `[assumption or None]`

Reviewer action:
`[approve with caveat | add follow-up test | monitor | note for later]`

## Questions

If none exist, write `None.` Otherwise repeat this card for every approval-affecting question.

### F4 Question - [Short title]

Approval impact: `[what cannot be approved or classified without this context]`
Needed context: `[specific product, contract, migration, security, or test information]`
Surface: `[route, feature, command, API, migration, security boundary, output, etc.]`
Confidence: `[high | medium | low]`
Origin: `[R# candidate ID, Coordinator, or multiple]`
Coordinator verification: `[what is known and what remains unknown]`

Look here first:
- `[primary](/abs/path/file.ts#L10)`

Evidence:
- `[why the missing context affects approval]`

Settlement criterion:
- `[specific evidence that would answer the question]`

Reviewer action:
`[confirm intent | request spec | request proof | ask owner]`

## Test Gaps

If none exist, write `None.` Otherwise add every standalone test gap not already fully represented by an `F#` card.

| ID | Severity | Surface | Missing coverage | Risk | Origin | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `T1` | `[Blocker | Major | Minor]` | `[changed behavior]` | `[missing assertion, fixture, integration path, or regression test]` | `[what could escape]` | `[R# | Coordinator]` | `[link or trace]` |

## Review Coverage Ledger

Every changed review-relevant or unknown-impact area must have one stable `A#` row, including areas with no finding.

| Area ID | Area / path | Touched files or entry points | Owner | Depth | Status | Result | Evidence / next step |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `A1` | `[area]` | `[file or entry-point links]` | `[R# | Coordinator]` | `[diff-only | dependency trace | contract trace | runtime verified]` | `[Finding F# | Reviewed - no issue found | Not review-relevant | Not covered]` | `[short result]` | `[evidence, reason, or exact next verification]` |

## Subagent Candidate Adjudication

Record every meaningful accepted, merged, dismissed, contradicted, or unresolved candidate. Omit trivial observations.

| Candidate ID | Proposed by | Decision | Final ID | Coordinator evidence | Reason |
| --- | --- | --- | --- | --- | --- |
| `R1-C1` | `R1` | `[accepted | merged | dismissed | contradicted | unresolved]` | `[F# | T# | None]` | `[independent trace/test/output]` | `[why]` |

## Evidence Appendix

### Diff Inventory

| File or area | Classification | Semantic review area considered |
| --- | --- | --- |
| `[path]` | `[surface | dependency | config | test-only | docs-only | generated | unknown]` | `[API, persistence, auth, output, tests, none, or unknown]` |

### Verification Commands

- `[command]` -> `[key outcome]`
- `[command]` -> `[key outcome]`

### Supporting Code Links

| ID | Role | Link | Why it matters |
| --- | --- | --- | --- |
| `F1` | `entry` | `[handler](/abs/path/file.ts#L10)` | `[where the path starts]` |
| `F1` | `risk` | `[changed branch](/abs/path/file.ts#L42)` | `[where the failure enters]` |
| `F1` | `test` | `[coverage gap](/abs/path/file.test.ts#L88)` | `[what does or does not cover it]` |

### Dismissed Coordinator Candidates

| Candidate | Decision | Evidence |
| --- | --- | --- |
| `[suspected issue]` | `[dismissed | merged into F# | represented by T#]` | `[reason and pointer]` |

### Blind Spots

| Area ID | Blind spot | Decision risk | What would resolve it |
| --- | --- | --- | --- |
| `A#` | `[unverified path]` | `[how this limits approval]` | `[specific next verification]` |

## Receiving Handoff

- Handoff status: `[Ready for receiving-code-review | Regenerate before implementation]`
- Source report ID: `[same Report ID]`
- Scope fingerprint to recheck: `[same fingerprint]`
- Actionable finding IDs: `[F1, F2 | None]`
- Actionable test-gap IDs: `[T1 | None]`
- Open question IDs: `[F4 | None]`
- Open coverage area IDs: `[A3 | None]`
- Highest-risk verification to repeat: `[specific check]`
- Suggested implementation boundaries: `[narrow surfaces or None]`
- Re-review note: `Treat every finding as a claim to verify. Challenges require a counterclaim, argument, evidence, limits, and settlement criterion.`

## Report Self-Check

- `[yes | no]` Assessment subagent ran or unavailable fallback is disclosed.
- `[yes | no]` Every changed review-relevant or unknown-impact area appears once in `Review Coverage Ledger`.
- `[yes | no]` Every final finding appears once in the index and once as a matching card.
- `[yes | no]` Every `Finding F#` area references an existing finding.
- `[yes | no]` Every standalone test gap has a stable ID and severity.
- `[yes | no]` Every meaningful subagent candidate has an adjudication.
- `[yes | no]` Every `Not covered` area has a reason and next step.
- `[yes | no]` Recommendation follows the skill mapping.
- `[yes | no]` `python scripts/validate_review_report.py <report-path>` passes.
- `[yes | no]` Git state was not mutated.
