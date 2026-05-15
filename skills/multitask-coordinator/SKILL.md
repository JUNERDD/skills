---
name: multitask-coordinator
description: Coordinate non-trivial multi-step work with background subagents when delegation is allowed. Use for complex tasks, long-running execution, large repositories, monorepos, dirty worktrees, independent exploration or implementation slices, atomic migrations, review passes, or verification work where the parent agent must decide whether to delegate, define worker ownership boundaries, avoid duplicate foreground/background work, synthesize outputs, handle blockers, and still handle trivial requests directly.
---

# Multitask Coordinator

Use the parent agent as the coordinator. Keep responsibility for task framing, delegation decisions, worker prompts, shared contracts, integration, verification, and user communication with the parent. Use background subagents only when the current system, developer, user, and tool constraints allow delegation.

If subagents are unavailable or not allowed, apply the same workflow locally as a task-decomposition checklist.

## Coordination Invariants

Before dispatching work, stabilize the coordination surface:

- Restate the objective, completion criteria, non-goals, validation requirements, and rollback boundary when they affect implementation choices.
- Keep the parent as owner of shared contracts, package exports, public APIs, cross-worker sequencing, deletion of old entrypoints, and final acceptance.
- Delegate only bounded work that can finish independently and return evidence.
- Avoid using workers to decide product tradeoffs, compatibility policy, rollout strategy, or irreversible architecture boundaries unless the user explicitly asked for proposals.
- Treat the task as incomplete until the parent has integrated outputs and run or explicitly skipped the agreed validation.

For atomic or destructive migrations, prefer workers for audits, isolated implementation slices, or review passes. Do not let workers independently remove old paths before the parent has mapped every in-scope call site and assigned one owner for the replacement contract.

## Fast Decision

Handle work directly when:

- The task is one command, one known file read, one small edit, or one direct answer.
- The next step depends on immediate user interaction, approval, credentials, or a continuous single-context exchange.
- The task touches a sensitive or externally visible surface where the parent must stay in the loop.
- The next critical-path step is defining or changing a shared contract that other work depends on.

Delegate only when all are true:

- Delegation is allowed and the task is non-trivial.
- The worker can receive a clear objective, scope, constraints, ownership boundary, expected output, and validation expectation.
- The parent has useful non-overlapping work to do while the worker runs, or the worker result can arrive later without blocking the immediate critical path.
- The result can be reviewed or verified from evidence, changed files, commands, logs, or concrete artifacts.

Prefer zero or one worker unless parallelism clearly reduces risk or latency. Use two to four workers for large independent boundaries. Avoid five or more workers unless there is a written plan, disjoint ownership, and a clear synthesis path.

Before any dispatch, explicitly choose the parent's immediate local task. Do not delegate the work that blocks the parent's next step.

## Choose Worker Shape

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

## Before Dispatch

1. Read current instructions and workspace rules.
   - Check applicable repository instructions such as `AGENTS.md`, `CLAUDE.md`, package scripts, test guidance, protected files, and style rules.
   - Summarize only the rules each worker must follow.

2. Map the work.
   - Define success criteria, affected systems, likely owner files, shared contracts, and verification commands.
   - Check the dirty worktree before assigning write scopes. Treat existing changes as user-owned unless proven otherwise.
   - Decide the parent's immediate next local task before delegating.
   - Mark shared files and contracts as parent-owned unless one worker is explicitly assigned as the sole owner.

3. Dispatch the smallest useful worker set.
   - Give each worker a disjoint objective and ownership boundary.
   - Make edit ownership explicit for implementation workers.
   - Ask for evidence, paths, command results, blockers, and residual risks, not only conclusions.

## Large Repository Mode

For large applications or monorepos, define worker scopes by ownership boundary, not by arbitrary file count:

- Package or app boundary, such as `web`, `web-extension`, or one package under `packages/*`.
- Feature boundary, such as one chat surface, preview system, billing flow, or upload pipeline.
- Layer boundary, such as schema/contract, runtime/store, UI consumer, server API, or verification.
- Read-only review boundary, such as regression risk, duplication search, accessibility, or test coverage.

Do not let sibling workers edit the same files, shared helper, schema, generated artifact, lockfile, environment file, or global config. When a shared contract must change, assign exactly one owner for the contract and only then assign consumer updates.

For dirty worktrees, pass the relevant `git status --short` context to workers and instruct them to preserve unrelated changes. If the dirty state makes ownership ambiguous, keep edits local or ask the user.

For one-shot migrations, use this default split:

- Parent: shared API/contract, execution order, integration, old-entry deletion, final validation.
- Explorer: call-site and risk audit.
- Worker: one package, feature boundary, or adapter boundary with exclusive write ownership.
- Reviewer: focused regression or consistency pass after integration.

## Worker Prompt Contract

Every worker prompt should include:

- Objective: the specific result the worker owns.
- Context: task-local facts, relevant paths, and repo rules it must follow.
- Scope: allowed read areas and allowed write areas.
- Constraints: forbidden files, forbidden actions, style rules, and coordination expectations.
- Validation: commands to run or explain why they cannot be run.
- Output: changed paths, evidence, command results, blockers, and residual risks.

For implementation workers, also state: "You are not alone in this codebase. Do not revert or overwrite edits you did not make. Adjust your work around existing changes and report conflicts."

## While Workers Run

- Keep the parent on adjacent non-overlapping work: refine requirements, inspect interfaces, prepare validation, or organize synthesis questions.
- Do not redo a delegated investigation or implementation in the foreground.
- Wait only when the next critical-path step requires the worker result, the system requires waiting, or the user asks for it.
- If a worker uncovers a contract conflict, pause dependent implementation and resolve the contract in the parent before continuing.

## Synthesis

For one worker, check whether the evidence covers the objective and minimally verify critical claims.

For multiple workers, synthesize by:

- Agreement: conclusions or changes that reinforce each other.
- Conflict: incompatible facts, edits, or recommendations.
- Coverage gap: required area nobody checked.
- Blocker: missing permission, context, dependency, or decision.
- Residual risk: what remains unverified.

When results conflict, locate the source of disagreement before editing. Use a narrow local check or focused follow-up worker only when it materially reduces uncertainty.

## Verification And Final Output

- Review changed files and artifacts, not just worker summaries.
- Run the narrowest credible verification that matches the risk: targeted tests, typecheck, lint, build, browser check, or manual inspection.
- Prefer repository-specific verification commands over generic ones.
- If verification is impossible or intentionally skipped, state why and name the residual risk.
- In the final answer, state what was delegated, what was adopted, what verification ran, and what risk remains.

## Guardrails

- Treat subagents as extra attention, not replacement ownership.
- Do not delegate trivial requests.
- Do not assign the same work to both the parent and a worker.
- Do not split shared contract design across sibling workers.
- Do not create vague worker prompts; vague prompts produce duplication, conflict, and unverifiable output.
- Do not over-split work. Use one coherent worker when synthesis cost would exceed parallel benefit.
- Do not accept worker output as fact without review. Verify critical behavior, patches, and test claims.
- Stop and ask the user when progress requires credentials, production permissions, destructive actions, or product tradeoffs.
