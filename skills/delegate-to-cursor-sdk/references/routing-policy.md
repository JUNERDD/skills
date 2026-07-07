# Routing Policy

Use this reference before delegating implementation. The upstream agent chooses the lightest safe route and remains the acceptance reviewer.

## Contents

- Routing decision template
- Cursor SDK runtime and model policy
- Authorization policy
- Cursor internal subagent policy
- Mode selection rules
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
Cursor model: <composer-2.5 fast=true unless the user explicitly directed Cursor to use a different model>
Cursor internal subagents: <disabled | read-only-analysis | verification | bounded-implementation>
Authorization: <authorized | needs Cursor API-key authorization>
Live monitor: <none | status.json path | log-dir/latest>
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

Use the default Cursor SDK model alias `composer-2.5-fast`, implemented as `model: { id: "composer-2.5", params: [{ id: "fast", value: "true" }] }`, for every Cursor dispatch and Cursor internal subagent unless the user explicitly directed Cursor to use a different model. Do not infer Cursor model authorization from permission to use support subagents, planning subagents, workstream orchestrators, Cursor internal subagents, outer-agent model choices, or general "use subagents" wording.

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
- Local review and bounded follow-up loops reduce integration risk.
- Different domains benefit from different specialists, such as backend, frontend, migrations, testing, security, or docs.
- File ownership can be isolated by branch, worktree, patch queue, or explicit serialization.
- The upstream agent can define cross-workstream interfaces and integration gates before dispatch.

Do not choose hierarchical mode for a small bug, a single-file edit, a task whose subtasks constantly modify the same files, or an unauthorized Cursor SDK environment.

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
