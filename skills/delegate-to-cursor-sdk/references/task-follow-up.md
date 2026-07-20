# Cursor SDK Follow-up Task Packet

Use this packet only for bounded findings from upstream review of a prior Cursor SDK run. Do not use it to introduce new product scope or new architecture. Materialize only the fenced packet body below into the same marker-owned `packetsDir` as the prior run, replace every placeholder, and keep the session until the follow-up is reviewed. Never copy the explanatory wrapper or edit this source template in place.

````markdown
# Cursor Follow-up Task Packet

## Original Authority

- Source: <master-direct | non-cursor-planning-subagent | orchestrator-subagent | user-provided-plan>
- Prior task packet: <task_packet_sha256 and safe stable identifier; exact temporary path withheld>
- Prior run correlation: <safe dispatch/agent/run/request identifiers; exact status path withheld>
- Prior Cursor model: the catalog-resolved Grok 4.5 High non-Fast preset unless explicitly user-overridden

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

- CLI profile: `grok-4.5-high`
- Model: `Grok 4.5 High`
- Model params: `catalog-resolved-high-non-fast-preset`
- SDK resolution: resolve exactly one High, non-Fast preset through `Cursor.models.list()` and send the preset's complete catalog-defined `{ id, params }` selection for a new agent. A pure resume does not silently replace the conversation's sticky model.
- Override authority: none unless an explicit user Cursor-model instruction is quoted here. For an authorized override, set CLI profile to `explicit`, Model to the exact SDK id, and Model params to `none` or a comma-separated exact `key=value` list matching the CLI arguments.

## Cursor Internal Subagent Policy

- Allowed: <disabled | read-only-analysis | verification | bounded-implementation>
- Default requested model: Grok 4.5 High
- Model verification: requested label only; exact High parameters are unverified, so use `disabled` when exact pinning is required
- Model override authority: none unless an explicit user Cursor-model instruction is quoted here.
- Max concurrent internal subagents: <0-2>
- Allowed purposes:
  - <specific bounded finding or none>
- Write policy: <forbidden | parent-only | owned-files-only>
- Background mode: <forbidden | allowed with joined completion report>
- Required evidence: description, model requested, model observed if supplied otherwise unverified, scope, files read or touched, result, risks

## Cursor SDK Run Monitoring

- Dispatch owner: upstream lease wrapper; the exact session marker and filesystem paths are root-held and not delegated to Cursor
- Safe log name / correlation ID: <new unique single-level non-sensitive follow-up value>
- Retained logs: <none | caller-owned-retained; exact path withheld and never cleaned>
- Live status: upstream-only; exact status and log paths withheld from Cursor
- Raw events: disabled unless explicitly justified

## Authorization

- Cursor API-key state: <authorized | needs user authorization>
- Secret handling: do not request or expose API keys in this packet, prompts, logs, commits, comments, or chat

## Temporary Artifact Ownership

- Prior and follow-up packets/ordinary session logs: upstream-owned and retained until final follow-up review; do not edit, relocate, or delete them
- Retained log directory: caller-owned and never cleaned by the session helper
- Cleanup: root upstream agent only, after the final accepted verdict and terminal CLI/frontend shutdown

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
