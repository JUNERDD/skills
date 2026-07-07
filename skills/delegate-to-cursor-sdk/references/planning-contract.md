# Planning Contract

Use this reference when the route is `planned_single_stream`. The planning subagent is read-only and produces a plan for upstream review. It does not dispatch Cursor or edit files.

## Planning Subagent Brief

````markdown
# Planning Subagent Brief

## Role
You are a non-Cursor planning subagent. Inspect the repository and produce a bounded implementation plan. Do not edit files, invoke Cursor, commit, push, deploy, or approve quality.

## User Goal
<user goal summary>

## Repository Context
- Workspace: <path or repo name>
- Relevant paths or unknowns: <paths>
- Runtime/package manager: <known details>

## Planning Task
Produce a plan for one coherent implementation stream. Identify assumptions, risks, stop conditions, verification commands, and exact scope boundaries.

## Output Format
Return:
1. Summary
2. Repository observations
3. Proposed implementation steps
4. In-scope and out-of-scope items
5. Files likely touched
6. Acceptance criteria
7. Verification commands
8. Stop conditions
9. Cursor readiness: yes/no and why
10. Open questions
````

## Upstream Plan Review

Before Cursor receives the plan, the upstream agent must check:

- the plan matches user intent;
- the plan fits one coherent workstream;
- scope boundaries are explicit;
- stop conditions cover dependencies, migrations, destructive commands, credentials, public APIs, billing, deployment, and scope expansion;
- verification commands are realistic;
- the Cursor packet uses `## Approved Upstream Plan` and contains no unresolved template placeholders.

## Approved Plan Summary Template

Use this summary inside the task packet copied from `references/task-planned.md` after upstream review:

```markdown
## Approved Upstream Plan

### Summary
<approved implementation target>

### Steps
1. <approved step>
2. <approved step>
3. <approved step>

### Stop Conditions
- Stop and report back if <condition>.

### Verification Required
```bash
<command>
```
```
