# Workstream Orchestrator Contract

Use this reference when the route is `hierarchical_orchestration`. A workstream orchestrator subagent owns one bounded workstream. It may perform local planning, delegate implementation to Cursor when authorized, review Cursor output and Cursor internal subagent evidence, run limited repair loops, and report evidence upstream.

The workstream orchestrator owns local completion, not global acceptance.

## Workstream Contract Template

````markdown
# Workstream Orchestrator Contract

## Role
You are a bounded workstream orchestrator subagent. You own this workstream only. You may create a local plan, dispatch Cursor Composer if authorized, allow Cursor internal subagents only within this contract, review its output, run focused repair loops, and report evidence. You do not own global architecture, cross-workstream interfaces, final merge, deployment, or final user-facing approval.

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

## File Ownership / Locks
### Owned files or areas
- `<path or glob>`: <ownership reason>

### Shared or locked files
- `<path>`: <who owns it, whether edits are forbidden or require escalation>

## Interface Contracts
- <API, schema, event, UX, or test contract that must remain consistent across workstreams>

## Dependencies / Ordering
- Before starting: <preconditions>
- Before reporting pass: <dependencies to verify>

## Allowed Delegations
- Support subagents: <allowed | not allowed; allowed purposes>
- Cursor inspect-only mode: <allowed | not allowed>
- Cursor proposal mode: <allowed | not allowed>
- Cursor apply mode: <allowed | not allowed>
- Cursor model: composer-2.5-fast unless the upstream contract quotes an explicit user Cursor-model instruction
- Cursor internal subagents: <disabled | read-only-analysis | verification | bounded-implementation>
- Cursor internal subagent model: composer-2.5-fast unless the upstream contract quotes an explicit user Cursor-model instruction
- Max concurrent internal subagents: <number>
- Live monitoring: <required | optional | not needed; who reads status.json>
- Max Cursor runs: <number>
- Max local repair loops: <number>

## Local Planning Requirements
Create an `## Approved Local Plan` before Cursor apply-mode dispatch. The local plan must fit this contract and must not change global scope.

## Acceptance Criteria
- [ ] <criterion>

## Verification Commands
```bash
<command>
```

## Escalation Conditions
Stop and report upstream if:
- implementation requires editing a locked or shared file beyond permission;
- the local plan conflicts with repository reality or another workstream contract;
- a dependency, migration, public API change, security or privacy decision, destructive command, credential access, or scope expansion is needed;
- verification cannot be run or fails after allowed repair loops;
- local risk remains above workstream tolerance.

## Required Completion Report
Return the completion report template from this reference.
````

## Cursor Packet for Local Implementation

When the workstream orchestrator dispatches Cursor, the packet must include:

````markdown
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
- Background mode: <forbidden | allowed with joined final report>
- Required evidence: description, model requested, scope, files read or touched, result, risks

## Cursor Run Monitoring
- Wrapper: `scripts/cursor_delegate.py`
- Output format: `stream-json`
- Live status: <status.json path if known, otherwise read `<log-dir>/latest` after launch>

## Approved Local Plan

### Workstream ID
<id>

### Master Contract Summary
<scope, boundaries, file ownership, interface constraints>

### Local Implementation Steps
1. <step>
2. <step>
3. <step>

### Cursor Stop Conditions
- <condition>

### Verification Required
```bash
<command>
```
````

The local plan is subordinate to the workstream contract. If they conflict, escalate instead of letting Cursor improvise.

## Local Review / Repair Loop

Before reporting upstream:

1. Read Cursor's final report.
2. Inspect the diff for this workstream.
3. Run or verify required commands.
4. Check scope, file ownership, interface contracts, and non-goals.
5. Check that Cursor and Cursor internal subagents requested model `composer-2.5-fast` unless the upstream contract quoted an explicit user Cursor-model instruction.
6. Check that internal subagents stayed within the `Cursor Internal Subagent Policy`.
7. If findings are `blocker` or `required`, create a focused repair packet and dispatch Cursor again only within the allowed repair-loop count.
8. If still failing, report `FAIL` with evidence instead of hiding the failure.

## Completion Report Template

```markdown
# Workstream Completion Report

## Workstream ID
<id>

## Local Verdict
<PASS | PASS_WITH_RISKS | FAIL | BLOCKED>

## Scope Implemented
- <what was implemented>

## Files Changed
- `<path>`: <purpose>

## Cursor Runs
- Run: <id/log path if available>
  - Mode: <inspect-only | proposal | apply>
  - Model: <composer-2.5-fast or explicit user-authorized override>
  - Packet: <path or summary>
  - Live status: <status.json path or none>
  - Result: <success | failed | blocked>

## Cursor Internal Subagents
- <none or description + model requested + scope + result + files read/touched + risk>

## Support Subagents Used
- <none or task + conclusion>

## Review Performed
- Diff reviewed: <yes/no + notes>
- Scope checked: <yes/no + notes>
- Interface contracts checked: <yes/no + notes>
- File ownership checked: <yes/no + notes>

## Verification
- `<command>`: <passed | failed | not run + reason>

## Repair Loops
- Attempt 1: <issue -> fix -> verification>
- Attempt 2: <issue -> fix -> verification>

## Deviations From Contract
- <none or exact deviation + why it was necessary>

## Risks / Open Questions
- <risk or none>

## Upstream Attention Required
- <what must be inspected before final acceptance>
```
