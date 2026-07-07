# Cursor SDK User-Plan Task Packet

Use this template only after the upstream agent accepts a user-provided plan as safe and bounded. Copy the template and replace every placeholder before dispatch.

````markdown
# Cursor SDK User-Plan Task Packet

## Role
You are Cursor's coding agent acting as the downstream implementation executor through `@cursor/sdk`. Follow this packet exactly. Do not broaden scope, commit, push, deploy, or modify unrelated files.

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
- Model: composer-2.5 fast=true
- SDK selection: `{ "id": "composer-2.5", "params": [{ "id": "fast", "value": "true" }] }`
- Override authority: none unless an explicit user Cursor-model instruction is quoted here.

## Cursor Internal Subagent Policy
- Allowed: <disabled | read-only-analysis | verification | bounded-implementation>
- Default model: composer-2.5 fast=true
- Max concurrent internal subagents: <0-4>
- Allowed purposes:
  - <purpose or none>
- Write policy: <forbidden | parent-only | owned-files-only>
- Required evidence: description, model requested, scope, files read or touched, result, risks

## Authorization
- Cursor API-key state: <authorized | needs user authorization>
- Secret handling: do not request or expose API keys in this packet, prompts, logs, commits, comments, or chat

## User Goal
<one paragraph describing the user-visible outcome>

## User-Provided Approved Plan

### User Plan Summary
<summarize the accepted user plan>

### Upstream Scope Notes
<clarifications, exclusions, and constraints added by the upstream agent>

### Steps
1. <accepted step 1>
2. <accepted step 2>
3. <accepted step 3>

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

## Acceptance Criteria
- [ ] <criterion 1>
- [ ] <criterion 2>

## Completion Report Required
Return: Summary, Files Changed, Verification, Internal Subagents, Deviations, Risks/Follow-ups, and Notes for Upstream Reviewer.
````
