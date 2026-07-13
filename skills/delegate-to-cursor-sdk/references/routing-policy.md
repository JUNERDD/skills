# Routing Policy

Use this reference before delegating implementation. The upstream agent chooses the lightest safe route and remains the acceptance reviewer.

## Contents

- Routing decision template
- Cursor SDK runtime and model policy
- Authorization policy
- Cursor internal subagent policy
- Mode selection rules
- Hierarchical scheduling policy
- Support subagent brief
- Escalation and downgrade

## Routing Decision Template

```markdown
## Routing Decision
Mode: <direct_cursor | planned_single_stream | hierarchical_orchestration | blocked>
Support subagents: <none | list of bounded support tasks>
Reason: <why this mode is enough and not over- or under-delegated>
Risk level: <low | medium | high>
Risk gates: <what must be true before acceptance>
Workspace strategy: <same branch | new branch | worktree per workstream | no apply mode>
Cursor SDK runtime: <local | cloud>
Cursor mode: <inspect-only | proposal | apply>
Cursor SDK conversation mode: <plan | agent>
Cursor model: <Grok 4.5 High with speed left to Cursor's default unless the user explicitly directed Cursor to use a different model>
Cursor internal subagents: <disabled | read-only-analysis | verification | bounded-implementation>
Authorization: <authorized | needs Cursor API-key authorization>
Live monitor: <none | status.json path | log-dir/latest>
Hierarchical graph: <n/a | workstream ids, dependencies, and ready conditions>
Effective Cursor concurrency: <n/a | limit and binding constraint>
```

## Cursor SDK Runtime Policy

Prefer local runtime for repository work already available in the current workspace. Use cloud runtime only when the user explicitly wants cloud execution, the repository URL/ref is known, and the Cursor account/team has repository access configured.

For local runtime:

- Use SDK `local.cwd` pointing at the active workspace.
- Keep `local.sandboxOptions.enabled` true unless the user explicitly accepts the risk and the wrapper receives `--override-reason`.
- Load project settings by default; do not load user, team, plugin, or all setting sources unless required and risk-reviewed.
- Use a read-only workspace copy for inspect-only and proposal runs whenever possible.

For cloud runtime:

- Pass explicit `--repo-url <url[#ref]>` entries.
- Keep PR creation explicit with `--auto-create-pr`; do not assume apply implies PR creation.
- Do not pass secrets as cloud env vars unless the user explicitly authorizes that credential scope.

## Cursor Model Policy

Use the wrapper's logical default profile `grok-4.5-high` for every top-level Cursor dispatch unless the user explicitly directed Cursor to use a different model. The profile means Grok 4.5 with High reasoning and Cursor-default speed; it is not an SDK model id. Resolve the canonical id and one unambiguous High effort parameter through the authenticated `Cursor.models.list()` catalog. Send only the High parameter and omit speed. During result verification, accept only catalog-supported speed parameters and values that Cursor reports in addition to the requested High parameter; reject unknown parameters, extra effort parameters, and unsupported speed values. Fail closed if High cannot be represented or verified. Do not silently fall back to Auto or another model. Do not infer Cursor model authorization from permission to use support subagents, planning subagents, workstream orchestrators, Cursor internal subagents, outer-agent model choices, or general "use subagents" wording.

For Cursor internal task/Agent-tool subagents, `@cursor/sdk` 1.0.23 exposes only a string model request rather than the structured parameter selection. Request the Grok 4.5 High label by default, but mark the exact High parameter unverified. Keep internal subagents `disabled` whenever exact High is an acceptance requirement.

## Authorization Policy

Use `references/cursor-sdk-authorization.md` whenever `CURSOR_API_KEY` is missing, invalid, expired, disabled, lacks access, or the SDK returns an authentication/integration error. Do not ask the user to paste API keys into chat. Ask the user to authorize the environment or run the wrapper in an interactive terminal so it can request hidden input.

Choose `blocked` until authorization is available when the task requires Cursor SDK execution and no safe non-Cursor alternative is authorized.

## Cursor Internal Subagent Policy

Use `references/cursor-internal-subagents.md` whenever Cursor may launch its own task/tool subagents. Default to `disabled` for trivial tasks. Prefer `read-only-analysis` or `verification` for repository survey, test triage, security/accessibility review, and independent diff review. Use `bounded-implementation` only when file ownership is explicit and the packet restricts writes to owned files.

## Choose `direct_cursor` When All Are True

- The user goal is clear.
- The task is one coherent implementation slice.
- The expected diff is small or moderate and easy for the upstream agent to review.
- No unresolved product, architecture, dependency, migration, security, privacy, billing, credential, repository-access, API-key authorization, or destructive-operation decision is required.
- Verification is known or can be stated directly.
- The task does not need parallel agent work.
- File ownership is obvious and not shared with another concurrent workstream.

Direct Cursor still requires a bounded task packet. Use `## Master Direct Implementation Instructions`. Keep Cursor internal subagents `disabled` unless read-only analysis materially improves confidence.

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
- Expected latency, coverage, or risk-reduction benefit exceeds dispatch, Cursor API usage, context, synthesis, review, and merge costs.
- Local review and bounded follow-up loops reduce integration risk.
- Different domains benefit from different specialists, such as backend, frontend, migrations, testing, security, or docs.
- File ownership can be isolated by branch, worktree, patch queue, or explicit serialization.
- The upstream agent can define cross-workstream interfaces and integration gates before dispatch.
- Cursor authorization, budget or rate capacity, and upstream review capacity support the intended concurrency.

Do not choose hierarchical mode for a small bug, a single-file edit, a task whose subtasks constantly modify the same files, or an unauthorized Cursor SDK environment.

## Hierarchical Scheduling Policy

Before dispatch, create the coordination ledger in `workstream-contract.md`. A workstream becomes ready only after its dependencies and shared contracts are accepted upstream; SDK `succeeded` alone does not unlock dependents.

Use this upper bound:

```text
effective_cursor_parallelism = min(
  available_outer_slots,
  ready_independent_workstreams,
  isolated_write_workspaces,
  Cursor_authorization_budget_and_rate_capacity,
  upstream_review_and_integration_capacity
)
```

- Start critical-path, long-running, uncertainty-reducing, and dependency-unblocking workstreams first.
- Backfill a ready workstream when an accepted result frees capacity; do not wait for an unrelated wave to finish.
- Use a separate worktree or branch for every concurrent apply-mode writer. Without isolation, serialize writes and parallelize only inspect, proposal, review, or verification work.
- Give every parallel run its own `--log-dir` or retain its printed `status.json` path. Do not coordinate parallel work through a shared `latest` pointer.
- Do not duplicate, cancel, resume as a competing implementation, or change the scope of a healthy run. Intervene only for `needs_input`, `needs_authorization`, failure, cancellation, a confirmed ownership or safety conflict, a user-goal change, or a predeclared no-progress threshold.
- Keep outer workstream concurrency and Cursor internal subagent fan-out jointly bounded; do not maximize both layers independently.

## Choose `blocked` When Any Are True

- The user goal is materially ambiguous and cannot be safely assumed.
- Required credentials, data, workspace access, repository integration, API-key authorization, or permissions are missing.
- The requested action is unsafe, destructive, or outside allowed policy.
- Implementation requires a user decision before safe delegation.

## Support Subagent Brief

```markdown
# Support Subagent Brief

## Role
You are a non-orchestrating support subagent. Do not dispatch Cursor, edit files, commit, push, deploy, or approve quality.

## Task
<bounded read-only analysis, review, or triage task>

## Scope
- In scope: <paths, APIs, tests, docs, risks>
- Out of scope: <non-goals and forbidden actions>

## Output
Return findings, evidence, risks, confidence, and open questions. Mark blockers clearly.
```

## Escalation and Downgrade

Escalate from direct to planned when implementation choices are unclear. Escalate from planned to hierarchical when workstreams are independent and ownership can be isolated. Downgrade from hierarchical when file overlap, shared design decisions, unavailable authorization, or limited review bandwidth would increase risk.
