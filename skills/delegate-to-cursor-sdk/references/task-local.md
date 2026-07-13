# Cursor SDK Local Workstream Task Packet

Use this template only inside an authorized hierarchical workstream. Copy the template and replace every placeholder before dispatch.

````markdown
# Cursor SDK Local Workstream Task Packet

## Role
You are Cursor's coding agent acting as the downstream implementation executor for one bounded workstream through `@cursor/sdk`. Follow this packet exactly. Do not broaden scope, commit, push, deploy, or modify unrelated files.

## Repository / Workspace
- Repo/workspace: <path or repo name>
- Base branch/ref: <branch/ref if known>
- Current task branch/worktree: <branch/worktree if known>
- Runtime/package manager: <known details>

## Cursor SDK Runtime
- Runtime: <local | cloud>
- SDK conversation mode: <plan | agent>
- Local sandbox: <enabled | disabled with explicit upstream reason>
- Setting sources: <project | none | explicit list>

## Cursor Model
- Wrapper profile: `grok-4.5-high`
- Model: `Grok 4.5 High`
- Model params: `catalog-resolved-high-default-speed`
- SDK resolution: resolve the canonical id and one High effort parameter through `Cursor.models.list()`; the speed parameter is omitted so Cursor uses its current default.
- Override authority: none unless an explicit user Cursor-model instruction is quoted here. For an authorized override, set Wrapper profile to `explicit`, Model to the exact SDK id, and Model params to `none` or a comma-separated exact `key=value` list matching the wrapper arguments.

## Cursor Internal Subagent Policy
- Allowed: <disabled | read-only-analysis | verification | bounded-implementation>
- Default requested model: Grok 4.5 High
- Model verification: requested label only; exact High parameters are unverified, so use `disabled` when exact pinning is required
- Max concurrent internal subagents: <0-4>
- Allowed purposes:
  - <purpose or none>
- Write policy: <forbidden | parent-only | owned-files-only>
- Required evidence: description, model requested, model observed if supplied otherwise unverified, scope, files read or touched, result, risks

## Authorization
- Cursor API-key state: <authorized | needs user authorization>
- Secret handling: do not request or expose API keys in this packet, prompts, logs, commits, comments, or chat

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
