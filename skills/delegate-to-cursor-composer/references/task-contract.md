# Cursor Task Contract

Use this reference whenever the upstream agent or an authorized workstream orchestrator dispatches Cursor Composer. Cursor is the implementation executor, not the final reviewer. Read `cursor-internal-subagents.md` when a packet allows Cursor to launch `Task()` / `taskToolCall` subagents.

## Required Authority Section

Every Cursor task packet must contain one of these sections:

- `## Master Direct Implementation Instructions` for direct Cursor mode;
- `## Approved Upstream Plan` for planned single-stream mode;
- `## Approved Local Plan` for hierarchical workstream implementation;
- `## User-Provided Approved Plan` when the user supplied a plan and the upstream agent accepted it.

## Cursor Model Policy

Dispatch Cursor and Cursor internal subagents with model `composer-2.5-fast` unless the user explicitly instructed Cursor to use a different model. Permission to use support subagents, planning subagents, workstream orchestrators, Cursor internal subagents, outer-agent model choices, or general subagent delegation is not Cursor model authorization. If a user-authorized override exists, quote or summarize that explicit user instruction in the task packet and wrapper invocation.

## Direct Cursor Task Packet Template

Use this for small, clear, low-risk tasks where no subagent planning or workstream orchestration is needed.

````markdown
# Cursor Direct Implementation Task Packet

## Role
You are Cursor Composer acting as the downstream implementation executor. The upstream agent has determined this task is small and clear enough for direct Cursor execution. Follow this packet exactly. Do not broaden scope, commit, push, deploy, or modify unrelated files.

## Repository / Workspace
- Repo/workspace: <path or repo name>
- Base branch/ref: <branch/ref if known>
- Current task branch/worktree: <branch/worktree if known>
- Runtime/package manager: <npm/pnpm/yarn/python/go/rust/etc. if known>

## Cursor Model
- Model: composer-2.5-fast
- Override authority: none unless an explicit user Cursor-model instruction is quoted here.

## Cursor Internal Subagent Policy
- Allowed: <disabled | read-only-analysis | verification | bounded-implementation>
- Default model: composer-2.5-fast
- Model override authority: none unless an explicit user Cursor-model instruction is quoted here.
- Max concurrent internal subagents: <0-4>
- Allowed purposes:
  - <purpose or none>
- Write policy: <forbidden | parent-only | owned-files-only>
- Background mode: <forbidden | allowed with joined final report>
- Required evidence: description, model requested, scope, files read or touched, result, risks

## Cursor Run Monitoring
- Wrapper: `scripts/cursor_delegate.py`
- Output format: `stream-json`
- Partial output: <yes | no>
- Log directory: <path or default `.agent/delegations`>
- Live status: <status.json path if known, otherwise read `<log-dir>/latest` after launch>

## User Goal
<one paragraph describing the user-visible outcome>

## Master Direct Implementation Instructions

### Summary
<upstream-defined implementation target>

### Steps
1. <step>
2. <step>
3. <step>

### Stop Conditions
- Stop and report back if <condition>.
- Stop and report back if implementation requires a new dependency, breaking API change, migration, destructive command, credential access, external service change, billing change, deployment action, or scope expansion not listed below.

### Verification Required
```bash
<command 1>
<command 2>
```

## In Scope
- <concrete change 1>
- <concrete change 2>

## Out of Scope
- <explicit non-goal 1>
- <explicit non-goal 2>

## Constraints
- Keep changes minimal and idiomatic for this repository.
- Preserve existing public APIs unless explicitly listed.
- Do not introduce new dependencies unless explicitly allowed.
- Do not alter formatting, generated files, migrations, or lockfiles unless necessary and explained.
- Do not read, print, store, or expose secrets.
- Do not launch Cursor internal subagents unless allowed by `## Cursor Internal Subagent Policy`.
- Leave changes unstaged for upstream review.

## Likely Files / Areas
- `<path>`: <why it may be relevant>

## Acceptance Criteria
- [ ] <observable criterion 1>
- [ ] <observable criterion 2>
- [ ] <tests or checks pass>

## Required Final Report
Return this exact structure:

```markdown
## Summary
<what changed in 3-6 bullets>

## Files Changed
- `<path>`: <purpose>

## Verification
- `<command>`: <passed | failed | not run + reason>

## Internal Subagents
- <none, or description + model requested + scope + result + files read/touched + risks>

## Deviations
- <none, or exact deviation + why it was necessary>

## Risks / Follow-ups
- <remaining risk, tradeoff, or none>

## Notes for Upstream Reviewer
- <anything the reviewer should inspect carefully>
```
````

## Reviewed Plan Task Packet Template

Use this after a planning subagent, workstream orchestrator, or user-provided plan has been reviewed by the responsible upstream agent.

````markdown
# Cursor Reviewed Implementation Task Packet

## Role
You are Cursor Composer acting as the downstream implementation executor. The upstream agent has reviewed the plan and owns final review. Do not generate a competing architecture plan. Do not broaden scope. Do not commit, push, deploy, or modify unrelated files.

## Repository / Workspace
- Repo/workspace: <path or repo name>
- Base branch/ref: <branch/ref if known>
- Current task branch/worktree: <branch/worktree if known>
- Runtime/package manager: <npm/pnpm/yarn/python/go/rust/etc. if known>

## Cursor Model
- Model: composer-2.5-fast
- Override authority: none unless an explicit user Cursor-model instruction is quoted here.

## Cursor Internal Subagent Policy
- Allowed: <disabled | read-only-analysis | verification | bounded-implementation>
- Default model: composer-2.5-fast
- Model override authority: none unless an explicit user Cursor-model instruction is quoted here.
- Max concurrent internal subagents: <0-4>
- Allowed purposes:
  - <purpose or none>
- Write policy: <forbidden | parent-only | owned-files-only>
- Background mode: <forbidden | allowed with joined final report>
- Required evidence: description, model requested, scope, files read or touched, result, risks

## Cursor Run Monitoring
- Wrapper: `scripts/cursor_delegate.py`
- Output format: `stream-json`
- Partial output: <yes | no>
- Log directory: <path or default `.agent/delegations`>
- Live status: <status.json path if known, otherwise read `<log-dir>/latest` after launch>

## Planning Provenance
- Source: <non-Cursor planning subagent | workstream orchestrator subagent | user-provided plan>
- Upstream reviewer: <upstream agent | workstream orchestrator under upstream contract>
- Review verdict: <approved | approved with edits>
- Parent workstream ID, if any: <id or none>

## User Goal
<one paragraph describing the user-visible outcome>

## Approved Upstream Plan
<use this heading for upstream-approved planned single-stream work; omit if using Approved Local Plan or User-Provided Approved Plan>

## Approved Local Plan
<use this heading for hierarchical workstream implementation; omit if using Approved Upstream Plan or User-Provided Approved Plan>

## User-Provided Approved Plan
<use this heading when the user supplied the plan and the upstream agent accepted it; omit otherwise>

### Summary
<approved approach>

### Implementation Slice
<exact slice Cursor should implement>

### Steps
1. <approved step 1>
2. <approved step 2>
3. <approved step 3>

### Stop Conditions
- Stop and report back if <condition>.
- Stop and report back if implementation requires a new dependency, breaking API change, migration, destructive command, credential access, external service change, billing change, deployment action, or scope expansion not listed below.

### Verification Required
```bash
<command 1>
<command 2>
```

## Context
<only the context required for implementation: current behavior, bug symptoms, design decision, API contract, linked issue summary, or product requirement>

## In Scope
- <concrete change 1>
- <concrete change 2>

## Out of Scope
- <explicit non-goal 1>
- <explicit non-goal 2>

## Constraints
- Follow the approved plan unless the codebase proves it impossible; if so, stop and report the mismatch.
- Preserve existing public APIs unless explicitly listed.
- Keep changes minimal and idiomatic for this repository.
- Do not introduce new dependencies unless explicitly allowed.
- Do not alter formatting, generated files, migrations, or lockfiles unless necessary and explained.
- Do not read, print, store, or expose secrets.
- Do not launch Cursor internal subagents unless allowed by `## Cursor Internal Subagent Policy`.
- Leave changes unstaged for upstream review.

## Likely Files / Areas
- `<path>`: <why it may be relevant>

## Implementation Guidance
1. Inspect the relevant files and tests first.
2. If the repository contradicts the approved plan, stop and report the mismatch instead of improvising.
3. Make the smallest coherent change that satisfies the acceptance criteria.
4. Add or update tests for changed behavior when practical.
5. Run the verification commands below, or explain exactly why a command could not run.

## Acceptance Criteria
- [ ] <observable criterion 1>
- [ ] <observable criterion 2>
- [ ] <regression criterion>
- [ ] <tests or checks pass>

## Required Final Report
Return this exact structure:

```markdown
## Summary
<what changed in 3-6 bullets>

## Files Changed
- `<path>`: <purpose>

## Verification
- `<command>`: <passed | failed | not run + reason>

## Internal Subagents
- <none, or description + model requested + scope + result + files read/touched + risks>

## Plan Deviations
- <none, or exact deviation + why it was necessary>

## Risks / Follow-ups
- <remaining risk, tradeoff, or none>

## Notes for Upstream Reviewer
- <anything the reviewer should inspect carefully>
```
````

## Repair Packet Template

Use this after review finds problems. Repairs must be narrower than the original task.

````markdown
# Cursor Repair Task Packet

## Role
You are repairing a previous implementation. The upstream reviewer found specific issues. Fix only the issues listed below; do not redesign or broaden scope.

## Cursor Model
- Model: composer-2.5-fast
- Override authority: none unless an explicit user Cursor-model instruction is quoted here.

## Cursor Internal Subagent Policy
- Allowed: <disabled | verification>
- Default model: composer-2.5-fast
- Max concurrent internal subagents: <0-2>
- Write policy: parent-only
- Required evidence: description, model requested, scope, result, risks

## Cursor Run Monitoring
- Live status: <status.json path or none>
- Logs: <run directory or none>

## Original User Goal
<short summary>

## Original Authority Section
<Master Direct Implementation Instructions | Approved Upstream Plan | Approved Local Plan | User-Provided Approved Plan excerpt>

## Review Findings to Fix
### blocker
- <finding, file/line if known, expected correction>

### required
- <finding, file/line if known, expected correction>

## Keep Unchanged
- <parts of previous implementation that are acceptable>

## Out of Scope
- New features.
- Broad refactors.
- Formatting churn unrelated to the findings.

## Acceptance Criteria
- [ ] All listed findings are resolved.
- [ ] No unrelated changes are introduced.
- [ ] Relevant tests/checks pass.

## Verification Commands
```bash
<command>
```

## Required Final Report
Summarize the repair, list changed files, report verification results, list deviations from the repair packet, and call out unresolved items.
````

## Prompt Patterns

Direct Cursor request:

```text
Use Cursor model `composer-2.5-fast` to implement the direct task packet at <path>. The upstream agent has determined this task does not need upstream subagent planning or orchestration. Use Cursor internal subagents only if the packet allows them. Keep the diff minimal. Do not commit or push. Stop and report if the task needs broader planning.
```

Planned implementation request:

```text
Use Cursor model `composer-2.5-fast` to implement the reviewed task packet at <path>. The packet contains an Approved Upstream Plan. Use Cursor internal subagents only if the packet allows them. Keep the diff minimal. Do not commit or push. Stop and report if the codebase contradicts the approved plan.
```

Workstream implementation request:

```text
Use Cursor model `composer-2.5-fast` to implement the local workstream packet at <path>. The packet contains an Approved Local Plan subordinate to the workstream contract. Use Cursor internal subagents only if the packet allows them. Keep the diff within the workstream. Do not commit or push. Stop and report if the task conflicts with a shared interface or locked file.
```
