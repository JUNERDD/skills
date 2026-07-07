# Cursor SDK Follow-up Task Packet

Use this packet only for bounded findings from upstream review of a prior Cursor SDK run. Do not use it to introduce new product scope or new architecture. Copy the template and replace every placeholder before dispatch.

````markdown
# Cursor Follow-up Task Packet

## Original Authority
- Source: <master-direct | non-cursor-planning-subagent | orchestrator-subagent | user-provided-plan>
- Prior task packet: <path or identifier>
- Prior status path: <status.json path if available>
- Prior Cursor model: composer-2.5 fast=true unless explicitly user-overridden

## Review Findings to Address
- <specific blocker or required finding>

## Allowed Changes
- <exact files, globs, or behaviors allowed>

## Not Allowed
- New dependencies unless already authorized
- Public API changes unless already authorized
- Migrations unless already authorized
- Destructive commands, credentials, billing changes, deployment, commits, pushes, or scope expansion

## Cursor SDK Runtime
- Runtime: <local | cloud>
- SDK conversation mode: <plan | agent>
- Local sandbox: <enabled | disabled with explicit upstream reason>

## Cursor Model
- Model: composer-2.5 fast=true
- SDK selection: `{ "id": "composer-2.5", "params": [{ "id": "fast", "value": "true" }] }`
- Override authority: none unless an explicit user Cursor-model instruction is quoted here.

## Cursor Internal Subagent Policy
- Allowed: <disabled | read-only-analysis | verification | bounded-implementation>
- Default model: composer-2.5 fast=true
- Max concurrent internal subagents: <0-2>
- Write policy: <forbidden | parent-only | owned-files-only>
- Required evidence: description, model requested, scope, files read or touched, result, risks

## Authorization
- Cursor API-key state: <authorized | needs user authorization>
- Secret handling: do not request or expose API keys in this packet, prompts, logs, commits, comments, or chat

## Implementation Instructions
1. Address only the listed findings.
2. Preserve accepted behavior from the prior run.
3. Stop and report if the required change exceeds Allowed Changes.

## Verification Required
```bash
<command 1>
<command 2>
```

## Completion Report Required
Return: Summary, Files Changed, Verification, Internal Subagents, Deviations, Risks/Follow-ups, and Notes for Upstream Reviewer.
````
