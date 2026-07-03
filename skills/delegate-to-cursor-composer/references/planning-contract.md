# Planning Contract

Use this reference when the route is `planned_single_stream`. The planning subagent is read-only and produces a plan for upstream review before any Cursor dispatch.

## Planning Brief Template

````markdown
# Planning Subagent Brief

## Role
You are a non-Cursor planning subagent. You are not the implementer. Do not invoke Cursor, edit files, commit, push, deploy, choose a Cursor model, or approve your own plan. Produce a structured implementation plan for upstream review. Cursor model remains `composer-2.5-fast` unless the original user explicitly directed Cursor to use a different model.

## User Goal
<one paragraph describing the user-visible outcome>

## Repository / Workspace Context
- Repo/workspace: <path or repo name if known>
- Stack/runtime/package manager: <known details>
- Base branch/ref: <if known>
- Existing constraints or architecture notes: <summary>

## Request Details
<symptoms, product requirement, bug report, desired behavior, linked issue summary, or design requirement>

## Constraints
- <technical, product, security, compatibility, API, dependency, timeline, or scope constraint>

## In Scope
- <item>

## Out of Scope
- <item>

## Available Context
- <files, snippets, logs, tests, prior decisions, or repo areas the planner may inspect>

## Assumptions to Validate
- <assumption>

## Requested Output
Return exactly this structure:

### Understanding
<concise interpretation of the task>

### Assumptions
- <assumption and confidence>

### Recommended Plan
1. <step>
2. <step>
3. <step>

### Implementation Slice
- Objective:
- Likely files/areas:
- Concrete changes:
- Acceptance criteria:
- Verification commands:
- Dependencies or ordering:
- Risks:
- Cursor internal subagent recommendation:

### Scope Boundaries
- In scope:
- Out of scope:

### Risk Register
- <risk>: <mitigation or decision needed>

### Cursor Readiness
<ready | not ready>. Explain blockers before Cursor dispatch.
````

## Upstream Plan Review Verdict

````markdown
## Plan Review Verdict
<approved | approved with edits | needs replanning | blocked>

## Approved Upstream Plan

### Summary
<upstream-approved approach>

### Implementation Slice
<exact slice Cursor should implement>

### Steps
1. <approved step>
2. <approved step>
3. <approved step>

### Cursor Stop Conditions
- <condition>

### Verification Required
```bash
<command>
```

## Planning Findings
### blocker
- <finding or none>

### required
- <finding or none>

### notes
- <review notes or none>
````

## Review Criteria

Approve only when:

- the plan directly addresses the user goal;
- scope and non-goals are explicit;
- acceptance criteria are observable;
- verification commands are realistic;
- risks are called out;
- Cursor can implement without re-planning architecture;
- Cursor model remains `composer-2.5-fast` unless an explicit user Cursor-model instruction exists;
- Cursor internal subagent use is disabled, read-only-analysis, verification, or bounded-implementation with clear limits;
- user decisions are escalated before implementation.
