# Scheduler Performance Audit

## Contents

[Measure](#measure) · [Capacity Model](#capacity-model) · [Diagnose](#diagnose) · [Optimize](#optimize) · [Scenario Tests](#scenario-tests) · [Audit Output](#audit-output)

Use this reference to evaluate or tune multi-agent scheduling. Prefer evidence from real runs; when telemetry is unavailable, label conclusions as qualitative.

## Measure

Capture the smallest useful set of observations:

- Time from task framing to first useful dispatch.
- Potential useful parallelism versus actual active workers.
- Critical-path latency and dependency-unblock delay.
- Ready-queue wait after a worker slot becomes available.
- Parent idle time while delegable work exists.
- Duplicate investigation or implementation rate.
- Overlapping-write, merge-conflict, and rework rate.
- Prompt and context volume per worker.
- Completion, blocker, failure, cancellation, restart, and retry rates.
- Synthesis effort and delay between worker completion and integration.
- Verification coverage for changed behavior and high-risk paths.

Do not optimize worker count in isolation. Optimize end-to-end latency, correctness, coverage, and coordination cost.

## Capacity Model

Use this upper bound for effective concurrency:

```text
effective_parallelism = min(
  available_worker_slots,
  ready_independent_nodes,
  safe_ownership_or_isolation_capacity,
  parent_review_and_integration_capacity
)
```

A worker is useful when its expected benefit is positive:

```text
benefit = latency_saved + coverage_gain + risk_reduction
          - dispatch_overhead - context_cost - synthesis_cost - merge_risk
```

Relative comparison is sufficient; exact numeric scoring is optional.

## Diagnose

Check for these bottlenecks in order:

1. **Late dispatch:** The parent performs substantial delegable work before launching workers.
2. **Hidden serialization:** Ready independent nodes wait despite safe capacity.
3. **Wave barriers:** The scheduler waits for all workers instead of unlocking dependencies from completed results.
4. **Poor granularity:** Tasks are either too small for dispatch overhead or too broad for clear ownership and evidence.
5. **Critical-path neglect:** Long or dependency-unblocking work starts after low-impact tasks.
6. **Context waste:** Workers receive broad repository or conversation context unrelated to their boundary.
7. **Ownership ambiguity:** Multiple writers touch shared files, contracts, lockfiles, or generated artifacts.
8. **Duplicate work:** The parent or sibling workers repeat healthy delegated work without an explicit review purpose.
9. **Excess intervention:** Healthy workers are polled with scope changes, cancelled, or restarted without an exception condition.
10. **Slow synthesis:** Completed evidence waits unreviewed, delaying dependent dispatch and final integration.
11. **Weak result contracts:** Workers return summaries without paths, commands, logs, or reproducible evidence.
12. **Verification gaps:** Parallel implementation increases throughput but leaves integrated behavior untested.

## Optimize

Apply only changes that address an observed bottleneck:

- Build an explicit DAG and maintain an event-driven ready queue.
- Dispatch all useful ready nodes in the first burst; backfill immediately when slots open. Rebalance only queued work, never by preempting a healthy running worker.
- Start critical-path, long-running, and uncertainty-reducing tasks first.
- Split by package, feature, layer, root, or exclusive write boundary rather than arbitrary file count.
- Combine microtasks into one coherent deliverable when dispatch and synthesis dominate execution.
- Split oversized workers when independent results can unlock downstream work earlier.
- Send task-local context, stable contracts, exact paths, and validation commands; omit unrelated history. Reuse one compact canonical contract block across sibling prompts, then append only task-local scope.
- Assign one contract owner and one writer per shared boundary, or use isolated worktrees or branches.
- Integrate completed results incrementally instead of waiting for unrelated workers.
- Use independent review or verification workers for high-risk changes, not duplicate implementation by default.
- Preserve healthy workers; use the least disruptive recovery action for blockers or failures.
- Standardize worker output so the parent can verify and synthesize quickly.
- Match verification breadth to risk and run integrated checks after merging worker output.

## Scenario Tests

Use these static tests after changing the policy:

- **Single trivial action:** Handle directly because dispatch overhead is larger than the task.
- **Several independent modules:** Dispatch up to the effective concurrency limit without a zero-or-one default.
- **Dependent migration:** Assign one contract owner first, then dispatch ready consumer updates as soon as the contract stabilizes.
- **Shared file without isolation:** Permit one writer; use other workers for read-only audit or verification.
- **Healthy long-running worker:** Continue non-overlapping coordinator work and do not cancel, restart, reassign, or change scope.
- **Blocked or failed worker:** Collect the blocker, apply the least disruptive correction, and cancel or restart only when recovery requires it.
- **Completed worker unlocks downstream work:** Dispatch the dependent node immediately without waiting for the rest of the wave.
- **High-risk integrated change:** Add independent review or verification and run final cross-boundary validation.

## Audit Output

Report:

- Observed bottlenecks and supporting evidence.
- The constraint limiting effective parallelism.
- Policy or prompt changes made.
- Expected effect on latency, quality, coverage, and coordination cost.
- Validation performed.
- Remaining uncertainty and the telemetry needed to confirm real-world improvement.
