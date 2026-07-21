# Cursor SDK Planned Implementation Task Packet

Use this template only after a non-Cursor planning subagent plan has been reviewed upstream. Materialize only the fenced packet body below into the current invocation's marker-owned `packetsDir` from `owned-artifact-cleanup.md`, then replace every placeholder before dispatch. Never copy the explanatory wrapper or edit this source template in place.

````markdown
# Cursor SDK Planned Implementation Task Packet

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
- Setting sources: <project | explicit list>

## Cursor Model

- CLI profile: `grok-4.5-high`
- Model: `Grok 4.5 High`
- Model params: `catalog-resolved-high-non-fast-preset`
- SDK resolution: resolve exactly one High, non-Fast preset through `Cursor.models.list()` and send the preset's complete catalog-defined `{ id, params }` selection.
- Override authority: none unless an explicit user Cursor-model instruction is quoted here. For an authorized override, set CLI profile to `explicit`, Model to the exact SDK id, and Model params to `none` or a comma-separated exact `key=value` list matching the CLI arguments.

## Cursor Internal Subagent Policy

- Allowed: <disabled | read-only-analysis | verification | bounded-implementation>
- Default requested model: Grok 4.5 High
- Model verification: requested label only; exact High parameters are unverified, so use `disabled` when exact pinning is required
- Model override authority: none unless an explicit user Cursor-model instruction is quoted here.
- Max concurrent internal subagents: <0-4>
- Allowed purposes:
  - <purpose or none>
- Write policy: <forbidden | parent-only | owned-files-only>
- Background mode: <forbidden | allowed with joined completion report>
- Required evidence: description, model requested, model observed if supplied otherwise unverified, scope, files read or touched, result, risks

## Cursor SDK Run Monitoring

- Dispatch owner: upstream lease wrapper; the exact session marker and filesystem paths are root-held and not delegated to Cursor
- Safe log name / correlation ID: <unique single-level non-sensitive value>
- Retained logs: <none | caller-owned-retained; exact path withheld and never cleaned>
- Live status: upstream-only; exact status and log paths withheld from Cursor
- Raw events: disabled unless explicitly justified

## Authorization

- Cursor API-key state: <authorized | needs user authorization>
- Secret handling: do not request or expose API keys in this packet, prompts, logs, commits, comments, or chat

## Temporary Artifact Ownership

- Packet and ordinary session logs: upstream-owned; do not edit, relocate, or delete them
- Retained log directory: caller-owned and never cleaned by the session helper
- Cleanup: root upstream agent only, after final review and terminal CLI/frontend shutdown

## User Goal

<one paragraph describing the user-visible outcome>

## Approved Upstream Plan

### Summary

<approved implementation target>

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

## In Scope

- <concrete change 1>
- <concrete change 2>

## Out of Scope

- <explicit non-goal 1>
- <explicit non-goal 2>

## Context

<only implementation-relevant context>

## Acceptance Criteria

- [ ] <criterion 1>
- [ ] <criterion 2>

## Completion Report Required

Return: Summary, Files Changed, Verification, Internal Subagents, Deviations, Risks/Follow-ups, and Notes for Upstream Reviewer.
````
