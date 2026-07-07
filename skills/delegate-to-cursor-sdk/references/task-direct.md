# Cursor SDK Direct Implementation Task Packet

Use this template for small, clear, low-risk tasks where no subagent plan is needed. Copy the template and replace every placeholder before dispatch.

````markdown
# Cursor SDK Direct Implementation Task Packet

## Role
You are Cursor's coding agent acting as the downstream implementation executor through `@cursor/sdk`. Follow this packet exactly. Do not broaden scope, commit, push, deploy, or modify unrelated files.

## Repository / Workspace
- Repo/workspace: <path or repo name>
- Base branch/ref: <branch/ref if known>
- Current task branch/worktree: <branch/worktree if known>
- Runtime/package manager: <npm/pnpm/yarn/python/go/rust/etc. if known>

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
- Model override authority: none unless an explicit user Cursor-model instruction is quoted here.
- Max concurrent internal subagents: <0-4>
- Allowed purposes:
  - <purpose or none>
- Write policy: <forbidden | parent-only | owned-files-only>
- Background mode: <forbidden | allowed with joined completion report>
- Required evidence: description, model requested, scope, files read or touched, result, risks

## Cursor SDK Run Monitoring
- Wrapper: `scripts/cursor_delegate.mjs`
- Log directory: <path or default `.agent/delegations`>
- Live status: <status.json path if known, otherwise read `<log-dir>/latest` after launch>
- Raw events: disabled unless explicitly justified

## Authorization
- Cursor API-key state: <authorized | needs user authorization>
- Secret handling: do not request or expose API keys in this packet, prompts, logs, commits, comments, or chat

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

## Context
<only implementation-relevant context>

## Constraints
- Use the smallest coherent diff that satisfies this packet.
- Leave changes unstaged for upstream review.
- Do not access credentials, alter external services, or run destructive commands.

## Acceptance Criteria
- [ ] <criterion 1>
- [ ] <criterion 2>

## Completion Report Required
Return: Summary, Files Changed, Verification, Internal Subagents, Deviations, Risks/Follow-ups, and Notes for Upstream Reviewer.
````
