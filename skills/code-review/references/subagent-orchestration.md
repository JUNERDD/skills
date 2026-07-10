# Code Review Subagent Orchestration

## Contents

1. [Purpose](#purpose)
2. [Assessment Subagent](#assessment-subagent)
3. [Decision Heuristics](#decision-heuristics)
4. [Specialist Assignment](#specialist-assignment)
5. [Specialist Output Contract](#specialist-output-contract)
6. [Coordinator Synthesis](#coordinator-synthesis)
7. [Fallbacks and Failure Handling](#fallbacks-and-failure-handling)

## Purpose

Use subagents to increase independent coverage and reduce blind spots, not to manufacture consensus or duplicate the same pass. The coordinator remains accountable for the final report.

The first subagent is always an orchestration assessor. It performs risk decomposition, not the final code review.

## Assessment Subagent

Launch the assessor after collecting only minimal scope metadata. Keep it read-only.

Give it:

- requested scope type and user intent
- baseline and target identifiers
- changed paths, additions/deletions, and diff statistics
- touched languages, frameworks, subsystems, and generated files
- available requirements, issue text, PR description, or design notes
- obvious critical surfaces such as auth, money, privacy, migrations, concurrency, external effects, or deployment
- runtime, credential, platform, and tool limitations
- any explicit review priorities from the user

Use this assignment:

```text
Act as the review orchestration assessor. Do not produce final findings and do not edit files.
Evaluate the semantic scope, risk diversity, subsystem independence, evidence needs, and likely context-sharing cost.
Decide whether the deepest practical review should use one reviewer or parallel specialist reviewers.
Prefer parallelism only when independent angles or separable surfaces materially improve coverage.
Return the required structured assessment and identify any assumptions.
```

Require this output:

```yaml
orchestration_decision: single-reviewer | parallel-specialists
confidence: high | medium | low
scope_summary: <one paragraph>
risk_dimensions:
  - <risk dimension and why it matters>
parallelism_benefit: <specific benefit or why it is low>
context_sharing_cost: <low | medium | high with reason>
review_assignments:
  - reviewer_id: R1
    angle: <bounded angle>
    owned_surfaces:
      - <paths, components, or behavior paths>
    mandatory_cross_checks:
      - <cross-cutting checks>
    expected_evidence:
      - <code trace, test, runtime check, contract, etc.>
overlap_plan: <where intentional overlap is required and why>
verification_plan:
  - <focused non-destructive check>
assumptions:
  - <assumption>
```

For `single-reviewer`, still return one `R1` assignment that defines the deep-review plan.

## Decision Heuristics

Choose `parallel-specialists` when one or more of these conditions creates genuinely independent review work:

- two or more materially different risk dimensions, such as auth plus migration or concurrency plus external API compatibility
- multiple subsystems with limited shared context and distinct failure modes
- a high-criticality surface that benefits from an independent adversarial pass
- a broad cross-layer change spanning API, persistence, UI/CLI, deployment, or generated artifacts
- unfamiliar or specialized domain semantics that warrant a dedicated reviewer
- a large diff whose semantic areas can be partitioned without losing integration reasoning
- a need for different evidence methods, such as static contract analysis plus targeted runtime verification

Prefer `single-reviewer` when:

- the change is local, cohesive, and dominated by one invariant
- specialist partitions would repeatedly reread the same small context
- the diff is mostly mechanical, generated, or low-risk and can be verified with one coherent trace
- parallel edits or tools are unavailable and multiple agents would not add independent evidence

Do not use changed-line count as the sole decision. A one-line authorization change can justify independent security review; a large generated-file change may not.

A practical default is two to four specialist reviewers. Use more only when the assessor identifies disjoint ownership and the coordinator can synthesize them without losing context.

## Specialist Assignment

Give each specialist a bounded angle and owned surfaces. Allow intentional overlap only for high-risk invariants or integration boundaries.

Useful roles include:

### Correctness and Contracts

Trace changed behavior, state transitions, invariants, callers/callees, API contracts, error semantics, compatibility, and alternate entry points.

### Security and Privacy

Inspect authentication, authorization, trust boundaries, validation, data exposure, secrets, filesystem/network effects, injection classes, and privilege changes.

### Reliability and Tests

Inspect retries, idempotency, ordering, races, timeouts, cleanup, failure paths, test adequacy, flaky assumptions, and regression coverage.

### Data, Migration, and Integration

Inspect schema changes, serialization, persistence, migrations, rollback, external APIs, queues, caches, deployment/configuration, and operational compatibility.

### Domain or Framework Specialist

Inspect framework lifecycle, language semantics, protocol rules, numerical/domain invariants, build tooling, or other specialized behavior.

Do not assign generic prompts such as “review everything.” State what the specialist owns and what it may inspect as supporting context.

## Specialist Output Contract

Use this assignment pattern:

```text
You are reviewer <R#> for <angle>.
Remain read-only. Review only the assigned scope as primary ownership, while following dependencies needed to prove or disprove risk.
Do not assign final severities or final F/T/A identifiers.
Return every meaningful candidate, every covered area with no issue found, important dismissed candidates, exact evidence, and unresolved uncertainty.
Do not treat lint or unrelated passing tests as proof of safety.
```

Require:

```yaml
reviewer_id: R1
coverage:
  - area: <surface>
    result: issue-candidate | no-issue-found | not-covered | not-review-relevant
    evidence: <pointer or reason>
candidates:
  - candidate_id: R1-C1
    title: <short title>
    risk: <user, security, data, contract, availability, or test risk>
    expected: <required behavior>
    current: <observed behavior>
    evidence:
      - <path/line, trace, test, output, or command result>
    confidence: high | medium | low
    assumptions:
      - <assumption>
    suggested_class: blocker | major | minor | question | test-gap
dismissed_candidates:
  - candidate: <suspected issue>
    reason: <why dismissed>
    evidence: <pointer>
blind_spots:
  - <unverified area and what would resolve it>
```

## Coordinator Synthesis

The coordinator must:

1. Compare specialist coverage against the semantic diff inventory.
2. Re-open the relevant code for every candidate that could affect approval.
3. Reject claims that rely on stale paths, misunderstood intent, duplicate failure modes, or unsupported assumptions.
4. Merge candidates that describe the same failure mode.
5. Split candidates whose impacts cross different contracts, users, security boundaries, or persisted data.
6. Resolve conflicts with stronger evidence, not majority vote.
7. Add coordinator-discovered findings when specialist partitions missed a cross-cutting issue.
8. Assign final severity and stable IDs only after adjudication.
9. Persist all accepted, merged, dismissed, and unresolved meaningful candidates in `Subagent Candidate Adjudication`.
10. Record intentional overlap and whether it confirmed or contradicted another pass.

A specialist conclusion is input evidence, not an authority. The final report must never say an issue exists only because “a subagent found it.”

## Fallbacks and Failure Handling

- If subagents are unavailable, use the assessor output contract in the coordinator and record the fallback in the report.
- If one specialist fails or returns incomplete output, retry once with a narrower assignment when practical. Otherwise mark its surfaces `Not covered`.
- If specialists conflict on a high-severity claim, run an independent focused verifier when available. If uncertainty remains approval-affecting, classify it as `Question` or lower confidence rather than forcing certainty.
- If a specialist edits files or Git state, stop using its result, inspect the mutation, restore only changes known to belong to that specialist without disturbing user state, and disclose the incident.
- If new evidence changes the orchestration decision, update the plan and persist the reason; do not silently add agents.
