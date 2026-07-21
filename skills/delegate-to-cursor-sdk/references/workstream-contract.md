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
id | depends_on | ready_when | unblocks | owner | owned_paths | locked_contracts | Cursor_mode | validation | status | session_file | packet_path | packet_sha256 | status_json | cleanup_owner | cleanup_disposition | barrier_generation | paused_from | paused_agent | owned_process | authorization_owner | resume_disposition
```

The `cursor-delegate` CLI still dispatches one Cursor SDK run per invocation. The upstream agent owns this ledger and launches ready invocations; do not describe the CLI as a persistent scheduler or queue service.

Use `queued -> ready -> running -> awaiting_review -> accepted -> integrated` for the normal path. Use `needs_input`, `needs_authorization`, `paused_for_authorization`, `blocked`, or `failed` for exception states. Only upstream acceptance may move a workstream to `accepted` and unlock dependents; a Cursor SDK `succeeded` state is evidence, not acceptance.

Compute effective concurrency with the formula in `routing-policy.md`. Start critical-path and dependency-unblocking work first, then backfill ready workstreams as accepted results free capacity. Never create concurrent apply-mode writers in one worktree. Root creates one private delegation session before dispatch. Run every parallel invocation through `delegation_session.py run --session-file ... --log-name <unique> -- cursor-delegate ...` and record its concrete `status.json` path. The wrapper owns raw `--log-dir`; use `--retained-log-dir` only for an explicit caller-owned audit base that cleanup will never delete.

Root is the sole cleanup owner. Workstream agents copy packets below the shared session's `packets` directory, report packet hashes/status paths, and leave them in place through upstream and integration review. A workstream SDK result, local `pass`, agent exit, or authorization handoff never authorizes local cleanup. Root removes the whole allowlisted session only after every required node is accepted/integrated and no continuation remains.

Treat a Cursor run as healthy while it reports no failure, authorization/input need, scope or ownership violation, safety conflict, or predeclared no-progress threshold breach. Observe it through `status.json` without launching a duplicate implementation, changing its contract, or cancelling it. Use the least disruptive intervention when an exception occurs.

## Global Authorization Barrier

Track one upstream-owned barrier with:

```text
clear -> pausing -> waiting -> releasing -> clear
                          \-> cancelled | failed
```

Non-root workstream agents invoke the wrapper with trailing `cursor-delegate ... --auth-mode fail`. When one reports `needs_authorization`, stop backfill, follow-ups, and new dispatches. Create one `barrier_generation`; recursively snapshot all live descendants, including agents without ledger rows, and record their canonical tasks, `paused_from`, owned process/session, exact delegation `session_file`, packet hash, status path, and cleanup disposition. Root remains the sole cleanup owner throughout; before interruption, non-root agents hand root cleanup evidence and live-process disposition, never ownership. Stop or account for owned processes before interrupting descendants, then re-enumerate. If any descendant/process remains running, fail the barrier instead of starting the root-owned packaged Next.js loopback frontend/control plane. After a confirmed stop, root remains the sole `authorization_owner` and `cleanup_owner`, starts browser mode for the same bounded packet using a new `--log-name` in the same session, and presents `authorization.local_url` with `authorization.dashboard_url` without opening either automatically.

After verification, restore only records in the same generation whose `resume_disposition` is still `pending`; continue the same canonical agent once and then set `resumed`. On cancellation, failure, or an unconfirmed stop, move workstreams to `blocked` with `not_resumed_authorization_cancelled`, `not_resumed_authorization_failed`, or `not_resumed_pause_unconfirmed`. Never replace a paused agent with a duplicate or resend a Cursor run that already has an id.

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
- Status: <queued | ready | running | awaiting_review | accepted | integrated | needs_input | needs_authorization | paused_for_authorization | blocked | failed>
- Barrier generation: <id or not applicable>
- Paused from: <prior state or not applicable>
- Paused agent: <canonical task id or none>
- Owned process or session: <stopped | process disposition handed to root | none | unconfirmed>
- Authorization owner: <root agent or none>
- Resume disposition: <not applicable | pending | resumed | not resumed and reason>
- Session runner/log name/status path: <delegation_session.py run, unique --log-name, and concrete status path>
- Retained log directory: <none | new absolute caller-owned path passed with --retained-log-dir, created by the wrapper, and never cleaned>
- Delegation session marker: <exact root-owned sessionFile>
- Task packet path and SHA-256: <path below packetsDir and hash>
- Cleanup owner: <root upstream agent>
- Cleanup disposition: <active | evidence-handed-to-root | cleanup-pending | cleaned | retained and reason | cleanup-blocked and reason>

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
- Cursor model: the catalog-resolved Grok 4.5 High non-Fast preset unless the upstream contract quotes an explicit user Cursor-model instruction
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

## Temporary Artifact Handoff

- <session marker, packet path/hash, per-run log base/status, root cleanup owner, and current disposition; workstream does not delete>

## Authorization Barrier

- <not used, or barrier generation, link handoff and page-lifecycle outcome, complete descendant set, process-ownership audit, and resume dispositions>

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

After upstream review, update the ledger to `accepted` or an exception state. Dispatch newly ready dependents immediately when capacity exists. Move a workstream to `integrated` only after cross-workstream contracts and integration-level verification pass. When every required node is integrated and no authorization/resume/follow-up remains, root applies `owned-artifact-cleanup.md`, records bounded evidence, invokes the helper once for the shared session, and updates every row to the same terminal cleanup disposition.
