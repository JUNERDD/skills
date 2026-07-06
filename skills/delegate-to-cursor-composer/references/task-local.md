# Cursor Local Workstream Task Packet

Use this template only inside an authorized hierarchical workstream. Copy the template and replace every placeholder before dispatch.

````markdown
# Cursor Local Workstream Task Packet

## Role
You are Cursor Composer acting as the downstream implementation executor for one bounded workstream. Follow this packet exactly. Do not broaden scope, commit, push, deploy, or modify unrelated files.

## Repository / Workspace
- Repo/workspace: <path or repo name>
- Base branch/ref: <branch/ref if known>
- Current task branch/worktree: <branch/worktree if known>
- Runtime/package manager: <known details>

## Cursor Model
- Model: composer-2.5-fast
- Override authority: none unless an explicit user Cursor-model instruction is quoted here.

## Cursor Internal Subagent Policy
- Allowed: <disabled | read-only-analysis | verification | bounded-implementation>
- Default model: composer-2.5-fast
- Max concurrent internal subagents: <0-4>
- Allowed purposes:
  - <purpose or none>
- Write policy: <forbidden | parent-only | owned-files-only>
- Required evidence: description, model requested, scope, files read or touched, result, risks

## Workstream ID
<stable id>

## Upstream Workstream Contract
<summarize owned scope, locked files, interface contracts, and allowed delegations>

## Approved Local Plan

### Summary
<local implementation target>

### Steps
1. <local step 1>
2. <local step 2>
3. <local step 3>

### Stop Conditions
- Stop and report back if <condition>.
- Stop and report back if implementation requires editing locked files, changing global interfaces, adding dependencies, migrations, destructive commands, credential access, external service changes, billing changes, deployment actions, or scope expansion not authorized by the workstream contract.

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

## Acceptance Criteria
- [ ] <criterion 1>
- [ ] <criterion 2>

## Completion Report Required
Return: Summary, Files Changed, Verification, Internal Subagents, Deviations, Risks/Follow-ups, and Notes for Upstream Reviewer.
````
