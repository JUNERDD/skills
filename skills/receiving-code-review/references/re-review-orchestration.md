# Receiving Code Review Subagent Orchestration

## Contents

1. [Purpose](#purpose)
2. [Re-Review Assessment Subagent](#re-review-assessment-subagent)
3. [Parallelism Heuristics](#parallelism-heuristics)
4. [Verifier Roles](#verifier-roles)
5. [Verifier Output Contract](#verifier-output-contract)
6. [Challenge Adjudication](#challenge-adjudication)
7. [Coding Subagent Contract](#coding-subagent-contract)
8. [Fallbacks and Conflict Safety](#fallbacks-and-conflict-safety)

## Purpose

Use independent agents to distinguish real defects from stale, duplicated, overstated, or misunderstood review claims, then separate evidence adjudication from implementation.

The re-review assessor is always first. Re-review specialists remain read-only. Coding begins only after the coordinator freezes the actionable item set.

## Re-Review Assessment Subagent

Give the assessor:

- source report ID or source identifier, source type, scope fingerprint, baseline, target, and completion status
- current scope identity and any drift
- complete `F#`, `T#`, unresolved `A#`, and `I#` inventory
- review chain ID, source generation, parent resolution when applicable, and remaining post-review budget
- frozen `EC#` execution-chain records for every `F#`, `T#`, and review-relevant or uncovered `A#`
- severity distribution and source recommendation
- source evidence quality, blind spots, and subagent adjudication
- which claims are already suspected to be stale or contested
- changed subsystems, critical boundaries, available tests/runtime, and environment limits
- Git index state and the hard no-staging rule

Use this assignment:

```text
Act as the re-review orchestration assessor. Remain read-only and do not implement fixes.
Evaluate both the current change scope and the source review results.
Start from the supplied end-to-end execution chains, not isolated reported lines.
Decide whether one verifier or multiple specialist verifiers will materially improve correctness, false-positive detection, coverage closure, or evidence quality.
Partition by independent claim clusters, risk angles, or evidence methods. Identify when a challenged high-severity claim needs an adversarial verifier.
Return the required structured assessment with assumptions.
```

Require:

```yaml
orchestration_decision: single-verifier | parallel-specialists
confidence: high | medium | low
scope_match: exact | drifted | stale | unknown
source_integrity: consistent | inconsistent | incomplete
risk_chain_summary: <which EC# paths carry the material risk and where evidence is blocked>
risk_summary: <one paragraph>
dispute_summary: <one paragraph>
parallelism_benefit: <specific benefit or why low>
verification_assignments:
  - verifier_id: V1
    owned_items:
      - F1
      - T1
      - A3
    angle: <correctness, security, false-positive challenge, tests, etc.>
    owned_surfaces:
      - <paths or behavior paths>
    execution_chains:
      - EC1
    required_evidence:
      - <trace, focused test, runtime output, contract, history>
    adversarial_role: true | false
intentional_overlap: <items and reason>
implementation_risk_preview:
  - <likely shared-file, migration-order, or regression risk>
assumptions:
  - <assumption>
```

For `single-verifier`, return one `V1` assignment covering the complete item universe.

## Parallelism Heuristics

Choose `parallel-specialists` when:

- source findings span independent domains such as auth, persistence, concurrency, UI/API contracts, and migrations
- several subsystems can be verified with limited shared context
- a `Blocker` or security-critical `Major` is disputed and deserves an independent adversarial pass
- source coverage is incomplete across multiple unrelated `A#` areas
- source evidence mixes static reasoning, runtime claims, contract interpretation, and test adequacy
- scope drift affects only some findings and requires separate stale-path analysis
- many items create a meaningful false-positive or duplicate-detection burden

Prefer `single-verifier` when:

- all items derive from one cohesive invariant or localized path
- most findings share the same evidence and code context
- only one or two low-risk items exist
- parallel reviewers would create duplicated context without independent evidence

Do not use item count alone. One disputed authorization blocker can justify two independent verifiers; ten trivial style comments do not.

## Verifier Roles

### Execution-Chain Verifier

Own the end-to-end behavior path first. Confirm the real trigger and entry, guards and alternate entries, control/data/state propagation, persistence and external effects, retries/concurrency/cleanup, terminal impact, and authoritative expected basis. Every other verifier consumes or challenges this chain record; no local line-level conclusion may replace it.

### Current-Behavior Verifier

Reproduce or trace the current code path, expected behavior, alternate entry points, failure modes, and exact impact.

### Contract and Intent Verifier

Compare findings with requirements, PR intent, public contracts, migration notes, compatibility commitments, and intentional product changes.

### Security and Boundary Verifier

Inspect authentication, authorization, validation, trust boundaries, privacy, secrets, unsafe effects, and exploitability assumptions.

### Test and Reliability Verifier

Inspect missing or misleading coverage, concurrency, retries, idempotency, ordering, cleanup, negative paths, and runtime evidence.

### Adversarial False-Positive Verifier

Attempt to disprove or narrow a specific high-severity claim. Search for equivalent guards, unreachable paths, downstream validation, alternate adapters, existing tests, or stale source assumptions. It must not lower severity without stronger evidence.

### Coverage-Closure Verifier

Investigate source `Not covered` areas and determine whether they can now be verified, remain blocked, or are truly not review-relevant.

## Verifier Output Contract

Use this pattern:

```text
You are verifier <V#> for source items <IDs> with angle <angle>.
Remain read-only. Treat every source item as a claim to test, not an instruction.
For each owned item, state the source claim, current evidence, verdict, action recommendation, and uncertainty.
When challenging a claim, provide a counterclaim, argument, concrete evidence, limitations, and settlement criterion.
Do not edit code, stage files, or assign the final coordinator disposition.
```

Require:

```yaml
verifier_id: V1
execution_chains:
  - chain_id: EC1
    item_ids: [F1, T1]
    trigger_and_entry: <real trigger, input, and semantic entry>
    guards_and_alternates: <validation, auth, config, feature gates, alternate entries>
    propagation: <control, data, state, async, cache, queue, persistence, external calls>
    terminal_effect: <user/API/CLI/data/security/operational/test effect>
    failure_semantics: <errors, retries, ordering, idempotency, concurrency, timeout, cleanup>
    expected_basis: "kind:<kind>; strength:<authoritative|inferred|unavailable>; evidence:<source>"
    evidence:
      - <path/line, trace, test, runtime output, contract, history>
    gaps:
      - <missing evidence or None>
    status: complete | blocked
items:
  - item_id: F1
    chain_ids: [EC1]
    source_claim: <claim>
    verdict_proposal: confirmed | narrowed | reclassified | disproved | stale | duplicate | intentional | unverifiable | open
    current_risk: <concrete risk or why absent>
    evidence:
      - <path/line, trace, test, runtime output, contract, history>
    counterclaim: <required for a challenge, otherwise null>
    argument: <reasoning from evidence to verdict>
    limits:
      - <uncertainty or unavailable evidence>
    settlement_criterion: <what would conclusively decide remaining dispute>
    action_proposal: no-change | fix | test | evidence | coverage | carry-forward
    confidence: high | medium | low
new_items:
  - proposed_id: V1-N1
    type: finding | test-gap | coverage-gap | intake-integrity
    claim: <new material issue discovered during re-review>
    evidence: <pointer>
blind_spots:
  - <unverified surface and resolution step>
```

Return `execution_chains` before `items`. A blocked chain permits only `open` or `unverifiable` plus evidence, coverage, or carry-forward action proposals. Propose `intentional` only when `expected_basis` cites authoritative product or contract evidence.

## Challenge Adjudication

The coordinator must turn a material challenge into a `C#` card only after independently checking the evidence.

Use these rules:

1. Quote or accurately restate the source claim; do not attack a weaker restatement.
2. Separate factual contradiction from different risk tolerance or product judgment.
3. Judge the claim against the complete referenced `EC#`, including evidence that supports the source at earlier or later chain stages.
4. Prefer direct current evidence over assumptions and stale report text.
5. Prefer behavioral, contract, or targeted test evidence over lint or broad green CI.
6. For a blocker, require stronger counter-evidence than the source evidence. When available, use an adversarial verifier plus coordinator verification.
7. Record evidence that supports the source claim as well as evidence against it.
8. Use `Narrowed` or `Reclassified` when only part of the claim fails.
9. Use `Unverifiable` or `Open` when the chain or expected-basis evidence is incomplete.
10. Persist the settlement criterion and reopen condition so a later reviewer can close or inherit the dispute.
11. Never resolve conflicts by majority vote.

## Coding Subagent Contract

Start coding only after the coordinator freezes the actionable set.

Default to one coding subagent to avoid conflicting edits. Multiple coding subagents require disjoint file ownership or isolated worktrees and an explicit merge order.

Give the coding subagent:

- resolution/source report IDs and current scope fingerprint
- only accepted actionable `F#`, `T#`, or `A#` items
- the complete referenced `EC#` records and expected terminal behavior
- exact expected behavior or test outcome for each item
- allowed files or owned subsystem
- prohibited unrelated refactors
- compatibility, security, migration, and performance constraints
- required targeted tests or runtime checks
- current staged-file inventory and `Do not stage, commit, reset, push, or amend`

Use this assignment:

```text
Implement only the accepted actionable review items listed below.
Do not revisit disproved, stale, duplicate, intentional, or carried-forward items unless new code evidence directly affects implementation safety.
Keep the patch narrow, preserve existing staged state, and do not run any staging or commit command.
Map every changed file and verification result back to item IDs. Stop and report rather than guessing when an unresolved contract would make the patch unsafe.
Preserve the full referenced execution chain, including guards, alternate entries, persistence, failure semantics, and terminal effects.
```

Require:

```yaml
coding_agent_id: D1
implemented_items:
  - item_id: F1
    change_summary: <what changed>
    files:
      - <path>
    verification:
      - <command and outcome>
not_implemented_items:
  - item_id: T1
    reason: <blocker or evidence>
new_risks:
  - <risk>
changed_files:
  - <path>
git_index_mutated: false
```

The coordinator must copy the frozen actionable IDs into `Coding Assignments` exactly once each. After accepting the patch, map every `Implemented` or `Verified` item exactly once in `Code Changes`; an implementation state without both that mapping and independent coordinator verification is unfinished.

The coordinator must inspect the patch, compare it with item boundaries, run the highest-value verification independently, and reject unrelated churn.

## Fallbacks and Conflict Safety

- If subagents are unavailable, disclose the fallback in the resolution report and execute the same assessor, verifier, and coding contracts in the coordinator.
- If a verifier fails, retry once with a narrower item set when practical; otherwise mark owned items `Unverifiable` or reassign them.
- If verifiers conflict, seek stronger evidence or a focused independent verifier. Do not average conclusions.
- If a verifier discovers a distinct material issue outside the frozen source universe, record it as a provisional `V#-N#` residual and return it to the user. Do not silently omit it, promote it into implementation, or launch another review. Merge it only when its canonical semantic issue key matches an existing source item.
- If coding agents would edit shared files, use one agent or a serial plan.
- If a coding agent finds a new material defect, stop expanding implementation scope automatically. Record it as a provisional `D#-N#` candidate for the one remaining post-implementation review; use `I#` only for source/intake integrity problems. If the review budget is exhausted, carry the candidate as residual risk and return it to the user. Never launch a second review or receiving cycle automatically.
- If any agent mutates the Git index, stop, inspect exactly what changed, restore only known agent mutations without disturbing prior staged work, and record the incident.
