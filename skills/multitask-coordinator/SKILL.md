---
name: multitask-coordinator
description: Coordinate non-trivial multi-step work with delegation-first subagent scheduling. Use when work can benefit from parallel exploration, implementation, review, verification, queued independent requests, large repositories or monorepos, migrations, dirty worktrees, isolated worktrees or branches; when the user asks to maximize subagent delegation or keep running workers uninterrupted; or when auditing multi-agent orchestration. After triggering, build a dependency graph, dispatch the maximum useful set of ready non-overlapping workers allowed by tools, permissions, isolation, and integration capacity, keep healthy workers running to completion, synthesize evidence, and verify the integrated result. Handle only truly trivial or non-delegable work directly.
---

# Multitask Coordinator

Use the parent agent as scheduler, contract owner, integrator, and final verifier. Delegate execution aggressively without delegating final responsibility. If subagents are unavailable or prohibited, apply the same dependency and ownership model locally.

## Core Invariants

1. **Dispatch first.** Before deep foreground execution, identify ready independent work and dispatch the maximum useful set immediately.
2. **Maximize useful parallelism.** Do not use an arbitrary zero-or-one-worker default. Set effective concurrency to the minimum of available worker slots, ready independent tasks, safe ownership or isolation capacity, and the parent's ability to review and integrate results. Do not leave a safe useful slot idle merely to minimize worker count. If capacity is not exposed, dispatch ready nodes until the tool reports saturation, then retain the remainder in the ready queue.
3. **Do not interrupt healthy workers.** Let a healthy worker reach a terminal result. Do not cancel, terminate, restart, reassign, preempt, or send unsolicited follow-up messages.
4. **Keep one owner per write boundary.** Prevent overlapping edits to shared files, contracts, schemas, lockfiles, generated artifacts, global configuration, or public APIs unless workers use isolated branches or worktrees and the parent owns the merge plan.
5. **Do not duplicate delegated work.** The parent may inspect interfaces, prepare integration, or verify results, but must not independently redo a healthy worker's assigned task.
6. **Require evidence.** Treat worker summaries as claims until supported by diffs, changed paths, logs, test output, screenshots, or concrete artifacts.
7. **Retain final ownership.** The parent owns objective interpretation, shared contracts, sequencing, conflict resolution, integration, validation, and user communication.

## Scheduling Workflow

1. **Frame the task.** Define the objective, acceptance criteria, non-goals, constraints, validation, and rollback boundary when relevant.
2. **Read local rules.** Inspect applicable repository instructions, package scripts, protected paths, test guidance, and `git status --short`. Treat unrelated existing changes as user-owned.
3. **Build a task graph.** Represent work as nodes with dependencies, read and write scope, expected evidence, and completion criteria. Keep product tradeoffs, compatibility and rollout policy, irreversible architecture choices, and final acceptance parent-owned; mark shared contracts parent-owned unless one worker is explicitly the sole owner. Workers may produce proposals when requested, but the parent decides.
4. **Classify nodes.** Mark each node as parent-only, delegable read-only, delegable write, review, or verification. A node is ready only when its dependencies and required contracts are stable.
5. **Dispatch ready nodes.** Fill every useful safe worker slot. Start critical-path, long-running, uncertainty-reducing, and dependency-unblocking nodes first; then backfill with other ready nodes.
6. **Continue event-driven scheduling.** When any worker completes or a dependency becomes ready, dispatch the next useful node immediately. Do not wait for an entire wave unless a real consistency barrier requires it. Rebalance queued or unassigned work only; never load-balance by preempting a healthy running worker.
7. **Work the coordinator path.** While workers run, refine shared contracts, prepare integration and validation, inspect non-overlapping interfaces, and resolve coordinator-only decisions.
8. **Integrate incrementally.** Review completed evidence and artifacts as they arrive. Unlock dependent work without waiting for unrelated workers.
9. **Verify the whole result.** Run the narrowest credible repository-specific checks, then broader checks when risk warrants them. State any skipped validation and residual risk.

## Delegation Rules

Delegate every bounded leaf whose expected latency, coverage, or risk-reduction benefit exceeds its dispatch, context, synthesis, and merge cost.

Handle a node directly only when one of these conditions applies:

- It is a truly small single operation and dispatch overhead would exceed the work.
- It requires immediate user interaction, credentials, approval, or a continuous single-context exchange.
- Delegation is unavailable or prohibited by higher-priority instructions or tools.
- It changes a shared contract, public API, destructive boundary, or sensitive external surface that the parent must control.
- No safe independent ownership boundary exists.

Even when the parent keeps a central contract or destructive step, delegate adjacent audits, call-site discovery, isolated consumer updates, review, or verification when useful.

When decomposition is uncertain, dispatch one explorer per distinct uncertainty domain up to effective concurrency, then fan out implementation as soon as the map stabilizes. Do not use multiple generic explorers that repeat the same investigation.

Use redundant workers only for intentionally independent hypotheses, high-risk review, or verification. Do not assign duplicate implementation merely to occupy worker slots.

## Worker Shapes

- **Explorer:** Read-only mapping of requirements, code paths, dependencies, failure modes, or ownership boundaries.
- **Contract owner:** Sole owner of a shared type, schema, API, migration boundary, or cross-worker interface.
- **Implementation worker:** Exclusive ownership of one coherent package, feature, layer, adapter, or isolated branch or worktree.
- **Reviewer:** Read-only independent scrutiny for correctness, regressions, security, accessibility, consistency, or test gaps.
- **Verifier:** Runs or designs targeted validation and returns reproducible evidence.

Prefer one coherent worker over microtasks when a continuous context or single design owner is necessary. Split work when boundaries are independent and synthesis cost is lower than the latency or coverage gain.

## Healthy Worker Continuity

Treat a worker as healthy when it has not reported an error or blocker, has not exceeded a harness-defined or pre-dispatch task-specific stall or timeout policy, has no confirmed scope or ownership violation, and is not creating a safety or destructive-action risk. Normal queueing or a long-running bounded task is not an exception by itself. Do not invent a retrospective timeout merely because execution is slower than expected.

While a worker is healthy:

- Do not cancel, stop, restart, reassign, or preempt it.
- Do not send unsolicited follow-up messages; queue noncritical context until completion.
- Do not send instructions that change its objective, scope, ownership, or validation contract.
- Do not duplicate its task in the foreground or give the same task to another implementation worker.
- Do not discard it merely because another result arrived first; use the result as additional evidence when it completes.
- Use only non-disruptive status observation when the harness supports it.

Intervene only when at least one condition is present:

- The worker reports failure, exception, blocker, or a required decision.
- The worker exceeds a platform-defined or pre-dispatch no-progress or timeout threshold.
- A confirmed scope, ownership, contract, safety, or destructive-action conflict appears.
- A user, system, or developer instruction changes and makes continuation invalid.
- A hard resource limit or tool requirement forces intervention.

Use the least disruptive response: collect status, provide one narrow correction or missing fact, pause dependent work, and cancel only when continuation is unsafe, invalid, or unable to recover. Restart only after identifying the cause and issuing a materially improved prompt.

## Ownership And Isolation

- Assign exactly one writer to each shared file or contract in a shared workspace.
- Use isolated worktrees, branches, remote workspaces, or tool-native sandboxes for competing patches, overlapping modules, dependency changes, generated artifacts, or broad migrations.
- If isolation is unavailable, reduce write concurrency rather than weakening ownership boundaries. Keep overlapping workers read-only.
- Pass relevant dirty-worktree context to every write worker and require preservation of unrelated changes.
- For multi-root or cross-repository work, scope workers by root, package, app, or service. Keep compatibility, release order, and integrated validation with the parent.
- Review diffs before adopting or merging worker output.

## Worker Prompt Contract

Give each worker the smallest self-contained prompt that preserves correctness:

```text
Objective:
Complete only this bounded result: ...

Done when:
- Observable acceptance criteria: ...

Dependencies and context:
- Stable inputs or contracts: ...
- Repository rules that apply: ...
- Workspace, branch, worktree, and dirty-state context: ...

Scope:
- You may read: ...
- You may edit: ...
- Do not edit: ...

Coordination constraints:
- You are not alone in this codebase. Do not revert or overwrite edits you did not make. Adjust around existing changes and report conflicts.
- Do not change shared contracts unless you are their explicit sole owner.
- Report out-of-scope conflicts instead of resolving them.

Validation:
- Run: ...
- If validation cannot run, explain why and identify the residual risk.

Output:
- Status: COMPLETED, BLOCKED, or FAILED.
- Summary and changed paths.
- Evidence and exact command results.
- Blockers, assumptions, and residual risks.
```

## Collection, Synthesis, And Closeout

For each completed worker, inspect the returned artifacts and evidence rather than relying on the summary alone. Reject or follow up on unsupported critical claims.

For multiple workers, synthesize by:

- **Agreement:** mutually reinforcing findings or compatible changes.
- **Conflict:** incompatible facts, contracts, or edits that require a named owner.
- **Coverage gap:** required work no worker completed.
- **Blocker:** missing permission, input, dependency, or decision.
- **Residual risk:** behavior that remains unverified.

Send a focused follow-up only after completion or when an intervention condition exists. Resolve shared-contract conflicts in the parent or through one explicitly assigned owner. Run final integrated validation and report what was delegated, adopted, rejected, verified, and left at risk.

## Performance Audit

When the user asks to evaluate the scheduler, or when orchestration shows avoidable delay, conflict, retries, or idle capacity, read [references/scheduler-audit.md](references/scheduler-audit.md). Use its metrics, diagnostic tests, and optimization loop to identify hidden serialization, poor granularity, context waste, merge risk, unnecessary interruption, and verification gaps.
