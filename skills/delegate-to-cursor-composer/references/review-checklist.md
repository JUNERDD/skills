# Review Checklist

Use this reference for routing review, subagent-output review, Cursor-output review, repair review, and final integration review.

## Phase 0: Routing Review

Before delegating implementation, confirm:

- The routing mode is the lightest safe mode.
- Direct Cursor mode is limited to clear, bounded, low-risk work.
- Planned single-stream mode is used when independent planning is valuable.
- Hierarchical mode is used only for decomposable multi-workstream tasks.
- Support subagents, if used, have bounded non-orchestrating tasks.
- Branch, worktree, or file-ownership strategy prevents write conflicts.
- Cursor model is `composer-2.5-fast` unless the original user explicitly directed Cursor to use a different model.
- Cursor internal subagent policy is explicit: disabled, read-only-analysis, verification, or bounded-implementation.
- Live monitoring requirements are stated when Cursor may run long or under a workstream orchestrator.
- Risk gates are explicit.

```markdown
## Routing Review
Mode: <direct_cursor | planned_single_stream | hierarchical_orchestration | blocked>
Approved: <yes | no>
Rationale: <why>
Required gates: <list>
```

## Phase 1: Support Subagent Output Review

Support subagents provide evidence, not authority. Check:

- The subagent stayed within the bounded task.
- Findings are backed by file paths, logs, snippets, or clearly stated reasoning.
- Recommendations do not silently expand scope.
- Confidence and uncertainty are stated.
- The upstream agent decides how to use the findings.

## Phase 2: Planning Subagent Review

Inputs:

- original user request and assumptions;
- repository/context facts provided to the planner;
- planning subagent report;
- user constraints, non-goals, and risk tolerance.

Review gates:

1. Goal and scope alignment.
2. Technical plausibility.
3. Observable acceptance criteria.
4. Realistic verification commands.
5. Explicit stop conditions for Cursor.
6. Risk handling for data, auth, privacy, migrations, dependencies, performance, compatibility, rollback, and user decisions.

````markdown
## Plan Review Verdict
<approved | approved with edits | needs replanning | blocked>

## Approved Upstream Plan

### Summary
<upstream-approved approach>

### Implementation Slice
<exact slice Cursor should implement>

### Steps
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

## Phase 3: Workstream Report Review

For each workstream report, verify:

- The workstream stayed within its contract.
- File ownership and shared-file locks were respected.
- Interface contracts were preserved.
- The workstream did not make global architecture, product, dependency, migration, or deployment decisions.
- Cursor runs stayed within authorized mode and run count.
- Cursor runs used model `composer-2.5-fast` unless an explicit user Cursor-model instruction authorized a different model.
- Cursor internal subagents stayed within policy, max concurrency, model, purpose, write limits, and background-mode limits.
- Live monitoring artifacts, if required, are present and consistent with the final report.
- Verification evidence is credible.
- Reported deviations are acceptable or require escalation.

```markdown
## Workstream Review
Workstream ID: <id>
Verdict: <accepted | accepted_with_notes | needs_repair | rejected | blocked>
Findings:
- <severity>: <finding>
Integration impact:
- <impact or none>
```

## Phase 4: Cursor Output Review

Review:

- Cursor final report.
- `metadata.json`, `status.json`, and log paths when the wrapper was used.
- Git diff, including generated files and lockfiles.
- Scope boundaries, non-goals, and stop conditions.
- Cursor model evidence; subagent permissions or outer-agent model choices do not count as Cursor model authorization.
- Cursor internal subagent evidence: `taskToolCall` descriptions, requested models, started/completed events, result status, and reported files read/touched.
- Whether Cursor waited for foreground internal subagent results and incorporated them before finalizing.
- Tests, lint, typecheck, build, and manual verification evidence.
- Error handling, edge cases, security, privacy, performance, accessibility, compatibility, and rollback concerns.
- Whether any new dependency, migration, public API change, billing change, deployment action, destructive command, or credential access occurred.

Finding severities:

- `blocker`: unsafe, incorrect, failing, or scope-breaking issue that prevents acceptance.
- `required`: issue that must be fixed before final approval.
- `suggestion`: improvement that is not necessary for acceptance.
- `nit`: minor style or wording issue.

```markdown
## Cursor Review
Verdict: <approved | approved_with_notes | needs_repair | blocked>

### blocker
- <finding or none>

### required
- <finding or none>

### suggestion
- <finding or none>

### nit
- <finding or none>

### Verification Assessment
- <command>: <credible | insufficient | failed | not run + reason>
```

## Phase 5: Repair Review

Repair packets must be narrower than the original packet and tied to specific findings.

Accept a repair only when:

- all listed blocker and required findings are resolved;
- no unrelated changes were introduced;
- verification is at least as strong as the original verification requirement, or limitations are explicit;
- remaining risks are acceptable for the user goal.

## Phase 6: Final Integration Review

Before the final user response, confirm:

- The result satisfies the original user goal and definition of done.
- Subagent outputs, Cursor reports, and diffs agree.
- Workstream outputs compose into the user goal.
- Shared interfaces and file ownership conflicts are resolved.
- Verification evidence is sufficient or limitations are explicitly stated.
- Remaining risks and user decisions are clear.

```markdown
## Final Review Verdict
<approved | approved_with_notes | needs_repair | blocked>

## Evidence Reviewed
- <routing decision>
- <subagent reports>
- <Cursor packets and reports>
- <Cursor monitor artifacts, if used>
- <diffs>
- <verification output>

## Remaining Risks
- <risk or none>
```
