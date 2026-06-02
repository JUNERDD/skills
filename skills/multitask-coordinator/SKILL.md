---
name: multitask-coordinator
description: Coordinate non-trivial multi-step work with async/background subagents when delegation is allowed. Use for Cursor-style multitask workflows, queued independent requests, long-running coding tasks, large repositories, monorepos or multi-root workspaces, dirty worktrees, isolated worktree or branch execution, independent exploration or implementation slices, atomic migrations, review passes, and verification work where the parent agent must decide whether to delegate, define worker ownership boundaries, avoid duplicate foreground/background work, synthesize outputs, handle blockers, and still handle trivial requests directly.
---

# Multitask Coordinator

Use the parent agent as the coordinator. Keep responsibility for task framing, decomposition, delegation decisions, worker prompts, shared contracts, integration, verification, and user communication with the parent. Use background subagents only when the current system, developer, user, and tool constraints allow delegation.

If subagents are unavailable or not allowed, apply the same workflow locally as a task-decomposition checklist.

## Operating Model

Treat multitask as a way to reduce latency or increase coverage, not as a way to outsource ownership.

- Restate the objective, completion criteria, non-goals, validation requirements, and rollback boundary when they affect implementation choices.
- Keep the parent as owner of shared contracts, package exports, public APIs, cross-worker sequencing, deletion of old entrypoints, and final acceptance.
- Delegate only bounded leaf work that can finish independently and return evidence.
- Keep workers focused on exploration, isolated implementation, review, or verification. Do not use workers to decide product tradeoffs, compatibility policy, rollout strategy, or irreversible architecture boundaries unless the user explicitly asked for proposals.
- Treat the task as incomplete until the parent has integrated outputs and run or explicitly skipped the agreed validation.

For atomic or destructive migrations, prefer workers for audits, isolated implementation slices, or review passes. Do not let workers independently remove old paths before the parent has mapped every in-scope call site and assigned one owner for the replacement contract.

## Dispatch Decision

Handle work directly when:

- The task is one command, one known file read, one small edit, or one direct answer.
- The next step depends on immediate user interaction, approval, credentials, or a continuous single-context exchange.
- The task touches a sensitive or externally visible surface where the parent must stay in the loop.
- The next critical-path step is defining or changing a shared contract that other work depends on.
- Delegation tools are unavailable and local decomposition is sufficient.

Delegate only when all are true:

- Delegation is allowed and the task is non-trivial.
- The worker can receive a clear objective, scope, constraints, ownership boundary, expected output, and validation expectation.
- The parent has useful non-overlapping work to do while the worker runs, or the worker result can arrive later without blocking the immediate critical path.
- The result can be reviewed or verified from evidence, changed files, commands, logs, or concrete artifacts.

Prefer zero or one worker unless parallelism clearly reduces risk or latency. Use two to four workers for large independent boundaries. Avoid five or more workers unless there is a written plan, disjoint ownership, and a clear synthesis path.

When the user has queued or bundled several independent requests, convert the queue into parallel work packets only after identifying dependencies. Preserve order for dependent tasks and parallelize only independent ones.

Before any dispatch, explicitly choose the parent's immediate local task. Do not delegate the work that blocks the parent's next step.

## Worker Shapes

Use an explorer for read-only questions about code, requirements, contracts, failure modes, or likely implementation boundaries.

Use one coherent worker when:

- The task needs one continuous context, one consistent design, or one shared file ownership boundary.
- The conclusions are tightly coupled and splitting would cause duplicate research, conflicting changes, or semantic drift.
- One owner should deliver a complete plan, patch, or verification report.

Use multiple sibling workers when:

- The subtasks are independent, have clear boundaries, and can be synthesized afterward.
- Multiple approaches, hypotheses, review areas, or non-overlapping modules need parallel coverage.
- Each worker can proceed from its prompt and assigned artifacts without relying on another worker.

Use proposal-only workers when multiple implementation directions are useful but the write boundaries would overlap. Use isolated worktrees when competing patches are valuable and available.

Use review-only workers after a large change when independent scrutiny can find regressions without touching files.

Use implementation workers only after the parent has assigned exclusive write ownership or an isolated execution environment.

## Before Dispatch

1. Read current instructions and workspace rules.
   - Check applicable repository instructions such as `AGENTS.md`, `CLAUDE.md`, package scripts, test guidance, protected files, and style rules.
   - Summarize only the rules each worker must follow.

2. Map the work.
   - Define success criteria, affected systems, likely owner files, shared contracts, and verification commands.
   - Check the dirty worktree before assigning write scopes. Treat existing changes as user-owned unless proven otherwise.
   - Decide the parent's immediate next local task before delegating.
   - Mark shared files and contracts as parent-owned unless one worker is explicitly assigned as the sole owner.

3. Choose the isolation model.
   - Prefer an isolated worktree, branch, remote machine, or tool-native background workspace when multiple workers will write code, when patches may compete, or when generated artifacts and dependency changes are possible.
   - Use a shared workspace only for read-only workers, one write worker, or tightly controlled disjoint edits.
   - If isolation is unavailable, reduce worker count and make ownership boundaries stricter.

4. Dispatch the smallest useful worker set.
   - Give each worker a disjoint objective and ownership boundary.
   - Make edit ownership explicit for implementation workers.
   - Ask for evidence, paths, command results, blockers, and residual risks, not only conclusions.

## Ownership And Isolation

Do not let sibling workers edit the same file, shared helper, schema, generated artifact, lockfile, environment file, global config, branch strategy, or public contract. When a shared contract must change, assign exactly one owner for the contract and only then assign consumer updates.

For dirty worktrees, pass the relevant `git status --short` context to workers and instruct them to preserve unrelated changes. If the dirty state makes ownership ambiguous, keep edits local or ask the user.

For isolated worktrees or branches:

- Assign one objective per worktree or branch.
- Name the expected base branch, target branch, and handoff artifact if the tool exposes them.
- Keep parent-owned contracts out of worker write scopes unless one worker is explicitly the sole owner.
- Review diffs before moving work into the foreground or integrating patches.

For multi-root workspaces or cross-repo changes:

- Let the parent own cross-root contracts, version compatibility, release order, and final validation.
- Scope workers by root, package, app, or service boundary.
- Verify the integrated behavior across every touched root, not only each worker's local boundary.

## Large Repository Patterns

For large applications or monorepos, define worker scopes by ownership boundary, not by arbitrary file count:

- Package or app boundary, such as `web`, `web-extension`, or one package under `packages/*`.
- Feature boundary, such as one chat surface, preview system, billing flow, or upload pipeline.
- Layer boundary, such as schema/contract, runtime/store, UI consumer, server API, or verification.
- Read-only review boundary, such as regression risk, duplication search, accessibility, or test coverage.

For one-shot migrations, use this default split:

- Parent: shared API/contract, execution order, integration, old-entry deletion, final validation.
- Explorer: call-site and risk audit.
- Worker: one package, feature boundary, or adapter boundary with exclusive write ownership.
- Reviewer: focused regression or consistency pass after integration.

For full-stack feature work, use this default split:

- Parent: product interpretation, shared types/API contract, integration order, final acceptance.
- Worker A: backend/API or data boundary.
- Worker B: frontend/UI consumer boundary.
- Worker C, optional: tests, docs, migration audit, or regression review.

## Worker Lifecycle

Dispatch:

- Send the smallest prompt that contains enough context, rules, scope, and validation.
- State whether the worker may edit files or must stay read-only.
- State whether the worker is running in an isolated worktree/branch or the shared workspace.

Monitor:

- Keep the parent on adjacent non-overlapping work: refine requirements, inspect interfaces, prepare validation, or organize synthesis questions.
- Do not redo a delegated investigation or implementation in the foreground.
- Wait only when the next critical-path step requires the worker result, the system requires waiting, or the user asks for it.

Follow up:

- Send a narrow follow-up when evidence is missing, scope drift appears, or the worker hits a blocker that does not require a user decision.
- If a worker uncovers a contract conflict, pause dependent implementation and resolve the contract in the parent before continuing.

Collect:

- Require changed paths, evidence, commands run, command results, blockers, and residual risks.
- Prefer raw diffs, logs, screenshots, test output, or concrete artifacts over summary-only claims.

Integrate:

- Review changed files and artifacts, not just worker summaries.
- Merge or adopt worker output only after checking ownership boundaries and contract consistency.
- Resolve conflicts locally in the parent or assign one focused follow-up worker.

Close:

- Run the narrowest credible verification that matches the risk.
- State what was delegated, what was adopted, what verification ran, and what risk remains.

## Prompt Template

Use this structure for worker prompts:

```text
Objective:
Complete only this bounded result: ...

Context:
- Relevant user request and task-local facts: ...
- Repository rules you must follow: ...
- Current worktree or branch context: ...

Scope:
- You may read: ...
- You may edit: ...
- Do not edit: ...

Constraints:
- Preserve unrelated changes.
- Do not change shared contracts unless explicitly assigned.
- Report conflicts instead of resolving out of scope.

Validation:
- Run: ...
- If you cannot run validation, explain why and name the residual risk.

Output:
- Changed paths, if any.
- Evidence and command results.
- Blockers.
- Residual risks.
```

For implementation workers, include this exact coordination warning: "You are not alone in this codebase. Do not revert or overwrite edits you did not make. Adjust your work around existing changes and report conflicts."

## Synthesis And Verification

For one worker, check whether the evidence covers the objective and minimally verify critical claims.

For multiple workers, synthesize by:

- Agreement: conclusions or changes that reinforce each other.
- Conflict: incompatible facts, edits, or recommendations.
- Coverage gap: required area nobody checked.
- Blocker: missing permission, context, dependency, or decision.
- Residual risk: what remains unverified.

When results conflict, locate the source of disagreement before editing. Use a narrow local check or focused follow-up worker only when it materially reduces uncertainty.

Prefer repository-specific verification commands over generic ones. If verification is impossible or intentionally skipped, state why and name the residual risk.

## Guardrails

- Treat subagents as extra attention, not replacement ownership.
- Do not delegate trivial requests.
- Do not assign the same work to both the parent and a worker.
- Do not split shared contract design across sibling workers.
- Do not let sibling workers write overlapping paths unless each uses an isolated worktree or branch and the parent plans the merge.
- Do not create vague worker prompts; vague prompts produce duplication, conflict, and unverifiable output.
- Do not over-split work. Use one coherent worker when synthesis cost would exceed parallel benefit.
- Do not accept worker output as fact without review. Verify critical behavior, patches, and test claims.
- Stop and ask the user when progress requires credentials, production permissions, destructive actions, or product tradeoffs.
