# Workstream Contract

Use this reference when the route is `hierarchical_orchestration`. A workstream orchestrator subagent owns one bounded workstream and reports evidence upstream. It does not own global architecture, cross-workstream interfaces, merge, deployment, or user-facing acceptance.

## Contents

- Contract template
- Completion report template
- Escalation conditions

## Workstream Contract Template

````markdown
# Workstream Contract

## Role
You are a bounded workstream orchestrator subagent. Own this workstream only. You may create a local plan, dispatch Cursor SDK if authorized, allow Cursor internal subagents only within this contract, review output, run bounded follow-up loops, and report evidence. Do not change global scope, cross-workstream interfaces, commit, push, deploy, or claim acceptance.

## Workstream ID
<stable id>

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
- Cursor model: composer-2.5 fast=true unless the upstream contract quotes an explicit user Cursor-model instruction
- Cursor internal subagents: <disabled | read-only-analysis | verification | bounded-implementation>
- Cursor internal subagent model: composer-2.5 fast=true unless the upstream contract quotes an explicit user Cursor-model instruction
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

## Scope Delivered
- <item>

## Cursor SDK Runs
- <runtime, mode, SDK conversation mode, model, task packet, status path, result, authorization state>

## Internal Subagents
- <description, model requested, scope, result, files read/touched>

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
