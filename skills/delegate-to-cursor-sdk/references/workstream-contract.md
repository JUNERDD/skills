# Workstream Contract

Use this reference when the route is `hierarchical_orchestration`. A workstream orchestrator subagent owns one bounded workstream and reports evidence upstream. It does not own global architecture, cross-workstream interfaces, merge, deployment, or user-facing acceptance.

## Contents

- Contract template
- Coordination ledger and scheduling rules
- Completion report template
- Escalation conditions

## Coordination Ledger

Before dispatching hierarchical work, keep one upstream-owned ledger row per workstream:

```text
id | depends_on | ready_when | unblocks | owner | owned_paths | locked_contracts | Cursor_mode | validation | status | status_json
```

The wrapper still dispatches one Cursor SDK run per invocation. The upstream agent owns this ledger and launches ready invocations; do not describe the wrapper as a persistent scheduler or queue service.

Use `queued -> ready -> running -> awaiting_review -> accepted -> integrated` for the normal path. Use `needs_input`, `needs_authorization`, `blocked`, or `failed` for exception states. Only upstream acceptance may move a workstream to `accepted` and unlock dependents; a Cursor SDK `succeeded` state is evidence, not acceptance.

Compute effective concurrency with the formula in `routing-policy.md`. Start critical-path and dependency-unblocking work first, then backfill ready workstreams as accepted results free capacity. Never create concurrent apply-mode writers in one worktree. Give every parallel run a unique log directory or record its concrete `status.json` path.

Treat a Cursor run as healthy while it reports no failure, authorization/input need, scope or ownership violation, safety conflict, or predeclared no-progress threshold breach. Observe it through `status.json` without launching a duplicate implementation, changing its contract, or cancelling it. Use the least disruptive intervention when an exception occurs.

## Workstream Contract Template

````markdown
# Workstream Contract

## Role
You are a bounded workstream orchestrator subagent. Own this workstream only. You may create a local plan, dispatch Cursor SDK if authorized, allow Cursor internal subagents only within this contract, review output, run bounded follow-up loops, and report evidence. Do not change global scope, cross-workstream interfaces, commit, push, deploy, or claim acceptance.

## Workstream ID
<stable id>

## Coordination State
- Depends on: <workstream ids or none>
- Ready when: <accepted dependencies and stable contracts>
- Unblocks: <workstream ids or none>
- Priority: <critical-path | dependency-unblocking | long-running | normal>
- Status: <queued | ready | running | awaiting_review | accepted | integrated | needs_input | needs_authorization | blocked | failed>
- Dedicated log directory or status path: <path>

## Global User Goal
<user goal summary>

## Decomposition Context
<why this workstream exists and how it fits other workstreams>

## Owned Scope
- <item>

## Explicitly Out of Scope
- <item>

## File Ownership
### Owned files or areas
- `<path or glob>`: <ownership reason>

### Shared or locked files
- `<path>`: <owner and editing rule>

## Interface Contracts
- <API, schema, event, UX, or test contract that must remain consistent>

## Allowed Delegations
- Support subagents: <allowed | not allowed; allowed purposes>
- Cursor SDK inspect-only mode: <allowed | not allowed>
- Cursor SDK proposal mode: <allowed | not allowed>
- Cursor SDK apply mode: <allowed | not allowed>
- Cursor SDK runtime: <local | cloud>
- Cursor SDK conversation mode: <plan | agent>
- Cursor model: Grok 4.5 High with speed left to Cursor's default unless the upstream contract quotes an explicit user Cursor-model instruction
- Cursor internal subagents: <disabled | read-only-analysis | verification | bounded-implementation>
- Cursor internal subagent requested model: Grok 4.5 High unless the upstream contract quotes an explicit user Cursor-model instruction
- Cursor internal subagent model verification: string request only; exact High parameters are unverified, so use `disabled` when exact pinning is required
- Authorization: <authorized | workstream must request upstream/user authorization before dispatch>
- Max Cursor runs: <number>
- Max follow-up loops: <number>

## Local Planning Requirements
Create an `## Approved Local Plan` before Cursor apply-mode dispatch. The local plan must fit this contract and must not change global scope.

## Acceptance Criteria
- [ ] <criterion>

## Verification Commands
```bash
<command>
```

## Escalation Conditions
Stop and report upstream if implementation requires locked files, conflicting contracts, dependencies, migrations, public API changes, security or privacy decisions, destructive commands, credentials, authorization changes, billing changes, deployment, or scope expansion.
````

## Completion Report Template

````markdown
# Workstream Completion Report

## Workstream ID
<id>

## Coordination State
- Previous status: <running | awaiting_review>
- Proposed status: <awaiting_review | blocked | failed>
- Dependencies or dependents affected: <none or ids>

## Scope Delivered
- <item>

## Cursor SDK Runs
- <runtime, mode, SDK conversation mode, requested and catalog-resolved model, structured system model, model-verification status, task packet, status path, result, authorization state>

## Internal Subagents
- <description, model requested, model observed if supplied otherwise unverified, scope, result, files read/touched>

## Files Touched
- `<path>`: <reason>

## Verification
```bash
<command>
# result summary
```

## Deviations
- <none or details>

## Risks and Open Questions
- <none or details>

## Verdict
<pass | pass with notes | blocked>
````

After upstream review, update the ledger to `accepted` or an exception state. Dispatch newly ready dependents immediately when capacity exists. Move a workstream to `integrated` only after cross-workstream contracts and integration-level verification pass.
