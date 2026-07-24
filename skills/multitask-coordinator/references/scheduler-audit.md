# Scheduler Performance Audit

## Contents

[Measure](#measure) · [Capacity Model](#capacity-model) · [Diagnose](#diagnose) · [Optimize](#optimize) · [Scenario Tests](#scenario-tests) · [Audit Output](#audit-output)

Use this reference to evaluate or tune hierarchical multi-agent scheduling. Prefer evidence from real runs; when telemetry is unavailable, label conclusions as qualitative.

## Measure

Capture the smallest useful set of observations:

- Time from task framing and safety preflight to first useful dispatch.
- Potential useful parallelism versus actual active workers.
- Critical-path latency, dependency-unblock delay, and ready-queue wait.
- Parent and subplanner review-queue depth and integration delay.
- Parent idle time while delegable work exists.
- Task-tree depth, descendant count, and unauthorized delegation attempts.
- Duplicate investigation or implementation rate.
- Decision-owner collisions, decision revisions, and affected-node propagation.
- Work produced against stale decision or contract versions.
- Overlapping-write, hot-path, merge-conflict, and rework rate.
- Prompt and inherited-context volume per worker.
- Shared-memory entry count, injected memory volume, stale-entry rate, rediscovery rate, and cleanup disposition.
- Completion, blocker, failure, cancellation, restart, and retry rates.
- Reviewer unique findings, duplicate findings, and verification coverage.

Do not optimize worker count in isolation. Optimize intent preservation, end-to-end latency, correctness, coverage, and coordination cost.

## Capacity Model

Use this upper bound for effective concurrency:

```text
effective_parallelism = min(
  available_worker_slots,
  ready_independent_nodes,
  safe_ownership_or_isolation_capacity,
  stable_decision_domain_capacity,
  parent_review_and_integration_capacity
)
```

A worker is useful when its expected benefit is positive:

```text
benefit = latency_saved + coverage_gain + risk_reduction
          - dispatch_overhead - context_cost - synthesis_cost - merge_risk
```

Relative comparison is sufficient. Do not invent precision when inputs are qualitative.

## Diagnose

Check for these bottlenecks:

1. **Unsafe early dispatch:** A writer starts before repository rules, dirty state, and ownership are known.
2. **Late dispatch:** The parent performs substantial delegable work after the safety preflight.
3. **Hidden serialization:** Ready independent nodes wait despite safe capacity.
4. **Wave barriers:** Dependents wait for unrelated workers after their own upstream result is accepted.
5. **Poor granularity:** Nodes are too small for dispatch overhead or too broad for clear ownership and evidence.
6. **Decision split-brain:** More than one planner owns or decides the same material domain.
7. **Stale-contract execution:** A node consumes a superseded decision or contract without review.
8. **Uncontrolled recursion:** A worker creates descendants without planner authority, capacity, or inherited ownership boundaries.
9. **Parent or subplanner saturation:** Accepted results wait unreviewed while more work is dispatched.
10. **Context waste:** Workers inherit conversation or repository context unrelated to their boundary.
11. **Memory pollution:** Shared documents contain unsupported, irrelevant, sensitive, superseded, or broadly injected content.
12. **Memory ownership ambiguity:** Multiple agents write one ledger or a non-root agent changes the session marker or cleanup policy.
13. **Ownership ambiguity:** Multiple writers touch a shared surface without isolation and a merge plan.
14. **Duplicate work:** The parent or siblings repeat healthy delegated work without a review purpose.
15. **Excess intervention:** Healthy workers receive scope changes, cancellation, restart, or unsolicited follow-ups.
16. **Conflict misrouting:** A semantic disagreement is treated as a textual merge, or an acceptance dispute lacks an independent verifier.
17. **Hot-path amplification:** One path repeatedly attracts writers, conflicts, and wait time.
18. **Review correlation:** Reviewers receive the same context and repeatedly produce the same findings.
19. **Weak result contracts:** Results lack paths, commands, versions, logs, or reproducible evidence.
20. **Unsafe memory cleanup:** A live, unowned, unmarked, shared, or caller-owned path is selected for deletion.
21. **Verification gaps:** Parallel implementation completes without integrated behavior checks.

## Optimize

Apply only changes that address an observed bottleneck:

- Make the root specification, task graph, and material decision owners explicit.
- Dispatch ready nodes immediately after the safety preflight; backfill when accepted results free capacity.
- Assign a subplanner only to an exclusive, independently decomposable subtree with clear acceptance and escalation boundaries.
- Forbid ordinary workers from delegating; reserve descendant capacity and ownership for subplanners.
- Freeze decisions and contracts consumed by running workers. Version material changes, identify affected nodes, and reconfirm queued work.
- Route semantic conflicts to decision owners, compatible textual conflicts to a neutral merge path, and acceptance conflicts to independent review or verification.
- Split by decision domain, package, feature, layer, root, or exclusive write boundary rather than arbitrary file count.
- Combine microtasks when dispatch and synthesis dominate; split oversized subtrees when independent results unlock downstream work.
- Send task-local context and the minimum necessary inherited history.
- Use ephemeral shared memory only when it reduces repeated context or preserves cross-level state. Give every document one writer, inject only relevant files, and keep the root as marker and cleanup owner.
- Assign one writer per shared boundary or use isolated workspaces; freeze new writers on repeated hot paths.
- Integrate accepted results incrementally and stop dispatching when review or integration is the binding constraint.
- Use distinct review questions or information views for high-risk changes instead of duplicate review prompts.
- Preserve healthy workers and use the least disruptive recovery action for blockers or failures.
- Match verification breadth to risk and run final cross-boundary checks.

## Scenario Tests

Use these tests after changing the policy:

- **Single trivial action:** Handle directly because delegation overhead is larger than the task.
- **Several independent modules:** Dispatch up to effective capacity after the safety preflight.
- **Dependent migration:** Stabilize one owned contract, then unlock consumers immediately after acceptance.
- **Recursive subtree:** Appoint a subplanner only for an exclusive domain with multiple descendant workstreams and reserved capacity.
- **Unauthorized recursion:** Prevent an ordinary worker from spawning descendants.
- **Ephemeral shared memory:** Create one unique owned run root, give subplanners only relevant exact paths, and prevent concurrent writes to one document.
- **Memory fallback:** Avoid disk-backed memory when workers do not share a filesystem; use bounded handoffs instead.
- **Memory cleanup:** Retain an incomplete or ambiguously owned run; remove only a terminal, marker-validated, exact owned root.
- **Decision change:** Reconfirm queued nodes and review running output against the new version without reflexively cancelling healthy work.
- **Decision split-brain:** Route overlapping architectural decisions to the nearest common ancestor before implementation continues.
- **Shared file without isolation:** Permit one writer and use other workers for read-only audit or verification.
- **Semantic versus textual conflict:** Send incompatible intent to the decision owner and compatible edits to a neutral merge path.
- **Healthy long-running worker:** Continue coordinator work without cancelling, restarting, reassigning, or changing scope.
- **Blocked or failed worker:** Apply one narrow correction and restart only when recovery requires it.
- **Completed worker unlocks downstream:** Dispatch the dependent node without waiting for the rest of the wave.
- **Hot path:** Stop assigning new writers and create one convergence or decomposition node.
- **High-risk integrated change:** Use distinct independent review and reproducible final verification.

## Audit Output

Report:

- Observed bottlenecks and supporting evidence.
- The constraint limiting effective parallelism.
- Decision domains, ownership collisions, stale inputs or memory, and conflict routes observed.
- Shared-memory placement, ownership, injection, retention, and cleanup disposition.
- Policy or prompt changes made.
- Expected effect on latency, correctness, context isolation, and coordination cost.
- Validation performed.
- Remaining uncertainty and the telemetry needed to confirm improvement.
