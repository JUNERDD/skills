# Routing Policy

Use this reference before delegating implementation. The upstream agent chooses the lightest safe route and remains the final reviewer.

## Routing Output Template

```markdown
## Routing Decision
Mode: <direct_cursor | planned_single_stream | hierarchical_orchestration | blocked>
Support subagents: <none | list of bounded support tasks>
Reason: <why this mode is enough and not over- or under-delegated>
Risk level: <low | medium | high>
Risk gates: <what must be true before final acceptance>
Workspace strategy: <same branch | new branch | worktree per workstream | no apply mode>
Cursor mode: <inspect-only | proposal | apply>
Cursor model: <composer-2.5-fast unless the user explicitly directed Cursor to use a different model>
Cursor internal subagents: <disabled | read-only-analysis | verification | bounded-implementation>
Live monitor: <none | status.json path | log-dir/latest>
```

## Cursor Model Policy

Use Cursor model `composer-2.5-fast` for every Cursor dispatch and Cursor internal subagent unless the user explicitly directed Cursor to use a different model. Do not infer Cursor model authorization from permission to use support subagents, planning subagents, workstream orchestrators, Cursor internal subagents, outer-agent model choices, or general "use subagents" wording.

## Cursor Internal Subagent Policy

Use `references/cursor-internal-subagents.md` whenever Cursor may launch its own `Task()`/`taskToolCall` subagents. Default to `disabled` for trivial tasks. Prefer `read-only-analysis` or `verification` for codebase survey, test triage, security/accessibility review, and independent diff review. Use `bounded-implementation` only when file ownership is explicit and the packet restricts writes to owned files.

## Choose `direct_cursor` When All Are True

- The user goal is clear.
- The task is one coherent implementation slice.
- The expected diff is small or moderate and easy for the upstream agent to review.
- No unresolved product, architecture, dependency, migration, security, privacy, billing, or destructive-operation decision is required.
- Verification is known or can be stated directly.
- The task does not need parallel agent work.
- File ownership is obvious and not shared with another concurrent workstream.

Direct Cursor still requires a bounded task packet. Use `## Master Direct Implementation Instructions`. Keep Cursor internal subagents `disabled` unless read-only analysis would materially improve confidence.

## Choose `planned_single_stream` When Any Are True

- The task is medium complexity or cross-file.
- An independent implementation plan would reduce risk.
- Acceptance criteria or verification strategy need refinement.
- Technical risk exists, but the work is still one coherent stream.
- Cursor should not be asked to decide the implementation plan.

Use a non-Cursor planning subagent, then upstream review, then Cursor.

## Choose `hierarchical_orchestration` When Most Are True

- The task naturally splits into two or more independent workstreams.
- Each workstream can have clear ownership and acceptance criteria.
- Parallel progress would materially reduce latency or context load.
- Local review and repair loops reduce integration risk.
- Different domains benefit from different specialists, such as backend, frontend, migrations, testing, security, or docs.
- File ownership can be isolated by branch, worktree, patch queue, or explicit serialization.
- The upstream agent can define cross-workstream interfaces and integration gates before dispatch.

Do not choose hierarchical mode for a small bug fix, a single-file edit, or a task whose subtasks constantly modify the same files.

## Choose `blocked` When Any Are True

- The user goal is materially ambiguous and cannot be safely assumed.
- Required credentials, data, workspace access, or permissions are missing.
- The requested action is unsafe, destructive, or outside allowed policy.
- Implementation requires a user decision before safe delegation.

## Support Subagents

Support subagents may be used in any mode when bounded evidence improves quality. They do not own workstreams and do not dispatch Cursor.

```markdown
# Support Subagent Brief

## Role
You are a non-orchestrating support subagent. Do not dispatch Cursor, edit files, commit, push, deploy, or approve final quality.

## Task
<bounded analysis, review, triage, or evidence-gathering task>

## Context
<only the context needed>

## Output Required
Return:
- Findings: <facts with file, path, or line references where possible>
- Risks: <risk and severity>
- Recommendations: <actionable suggestions>
- Confidence: <high | medium | low and why>
- Open Questions: <none or list>
```

Good support tasks:

- Survey likely files for a bug and return a file map.
- Review a diff for security, privacy, performance, accessibility, or compatibility issues.
- Triage a failing test log and identify likely root causes.
- Check whether a planned API contract is internally consistent.
- Review documentation, examples, or migration impact.

## Escalation and Downgrade Rules

Escalate `direct_cursor` to `planned_single_stream` when Cursor would need to make architecture or product decisions.

Escalate `planned_single_stream` to `hierarchical_orchestration` when the reviewed plan decomposes into independent workstreams whose local state would overload the upstream agent.

Downgrade `hierarchical_orchestration` to `planned_single_stream` when workstreams have high file overlap, tight sequencing, or ambiguous ownership.

Downgrade `planned_single_stream` to `direct_cursor` when the planning pass would be mechanical overhead for a trivial fix.

## Required Decisions Before Hierarchical Dispatch

Before launching workstream orchestrator subagents, define:

- workstream IDs and objectives;
- file ownership and shared-file locks;
- cross-workstream interface contracts;
- ordering and dependencies;
- branch or worktree strategy;
- allowed Cursor mode for each workstream: inspect-only, proposal, or apply;
- Cursor model for each workstream: `composer-2.5-fast` unless the upstream contract quotes an explicit user Cursor-model instruction;
- Cursor internal subagent policy for each workstream: disabled, read-only-analysis, verification, or bounded-implementation;
- whether live monitoring is required, and who reads `status.json`;
- max Cursor runs and local repair loops;
- evidence required in reports;
- escalation conditions.
