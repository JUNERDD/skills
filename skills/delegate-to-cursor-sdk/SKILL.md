---
name: delegate-to-cursor-sdk
description: Opt-in Cursor SDK delegation workflow for bounded coding tasks, reviewed implementation packets, Cursor internal subagents, hierarchical workstreams, follow-up packets, live Cursor SDK monitoring, and proactive Cursor API-key authorization. Use only when the user explicitly injects or names `$delegate-to-cursor-sdk` / `delegate-to-cursor-sdk`; otherwise do not select it proactively.
---
# Delegate to Cursor via Cursor SDK

Route software engineering work to Cursor's coding agent through the official `@cursor/sdk` package. The upstream agent remains accountable for user intent, scope, architecture, risk decisions, verification gates, and acceptance.

Core invariant:

```text
Choose the lightest delegation path that can produce a safe, bounded, reviewable result.
```

## Roles

- **Upstream agent**: interpret the user goal, choose the route, define scope and risk gates, authorize Cursor SDK runtime/model/auth, approve any plan before implementation, review downstream output, and decide acceptance.
- **Support subagent**: perform bounded read-only or advisory work such as repository survey, test triage, security review, API review, documentation review, or independent diff review. It does not edit files, dispatch Cursor, or approve quality.
- **Planning subagent**: produce a read-only plan for one coherent workstream. The upstream agent must review and edit the plan before Cursor receives it.
- **Workstream orchestrator subagent**: own one bounded workstream in hierarchical delegation. It may create a local plan, dispatch Cursor SDK if authorized, review local output, run limited follow-up loops, and report evidence. It does not own global architecture, cross-workstream interfaces, merge, deployment, or user-facing acceptance.
- **Cursor SDK agent**: execute the approved task packet using `@cursor/sdk`. Cursor may inspect, propose, apply changes, or launch bounded internal subagents according to the packet, but it must not broaden scope or become the acceptance reviewer.
- **Cursor internal subagent**: a Cursor task/tool child agent launched inside one Cursor SDK run. It works under Cursor's packet and returns evidence to Cursor. In `@cursor/sdk` 1.0.23 the task/Agent tool accepts only a string model request, so an internal subagent can request the default label but cannot prove the exact High effort parameter.

## Routing Modes

Read `references/routing-policy.md` before delegating. Emit a short routing decision:

```markdown
## Routing Decision
Mode: <direct_cursor | planned_single_stream | hierarchical_orchestration | blocked>
Support subagents: <none | bounded tasks>
Reason: <why this route is sufficient>
Risk level: <low | medium | high>
Risk gates: <checks required before acceptance>
Workspace strategy: <same branch | new branch | worktree per workstream | no apply mode>
Cursor SDK runtime: <local | cloud>
Cursor mode: <inspect-only | proposal | apply>
Cursor SDK conversation mode: <plan | agent>
Cursor model: <Grok 4.5 High with speed left to Cursor's default unless the user explicitly directed Cursor to use a different model>
Cursor internal subagents: <disabled | read-only-analysis | verification | bounded-implementation>
Authorization: <authorized | needs Cursor API-key authorization>
Live monitor: <none | status.json path | log-dir/latest>
```

Choose:

- `direct_cursor` for small, clear, low-risk implementation slices.
- `planned_single_stream` when one coherent stream benefits from a reviewed plan.
- `hierarchical_orchestration` only when independent workstreams have clear ownership and local review loops reduce risk or context load.
- `blocked` when missing context, unsafe action, unavailable permissions, missing Cursor API-key authorization, or required user decisions prevent safe delegation.

## Workflow

1. **Intake**: identify the user goal, definition of done, workspace constraints, likely repository areas, risk class, validation commands, and destructive or irreversible actions. Ask at most one blocking question; otherwise state assumptions and proceed.
2. **Route**: choose the lightest safe mode with `references/routing-policy.md` and record the routing decision.
3. **Prepare authority**:
   - Direct mode: copy `references/task-direct.md` into a task packet outside the skill directory and fill `## Master Direct Implementation Instructions`.
   - Planned mode: brief the planning subagent with `references/planning-contract.md`, review the plan, then copy `references/task-planned.md` into a task packet outside the skill directory and fill `## Approved Upstream Plan`.
   - Hierarchical mode: use `references/workstream-contract.md` to build a dependency-aware coordination ledger, compute effective Cursor concurrency, and define workstream contracts; each ready authorized workstream copies `references/task-local.md` into a task packet outside the skill directory and fills `## Approved Local Plan`.
   - User-provided plan: accept or edit the plan before Cursor receives a task packet copied from `references/task-user-plan.md` with `## User-Provided Approved Plan`.
   - Follow-up loop: copy `references/task-follow-up.md` into a new bounded follow-up task packet only for specific findings from upstream review.
4. **Resolve Cursor SDK model**: use the wrapper's logical default profile `grok-4.5-high`, meaning Grok 4.5 with High reasoning while speed remains Cursor's default. The wrapper resolves the current canonical id and one unambiguous High effort parameter through `Cursor.models.list()`, sends only that High parameter, and omits every speed parameter. It fails closed rather than guessing the High parameter or falling back to Auto. Pass a different `--model` and any accompanying `--model-param` only when the user explicitly directed Cursor to use that model; include `--user-authorized-model` and `--override-reason`.
5. **Resolve authorization**: before dispatch, read `references/cursor-sdk-authorization.md`. Prefer `CURSOR_API_KEY` in the local process environment. If the key is missing or rejected, the agent must actively request authorization using the reference workflow; do not ask the user to paste the key into chat, task packets, logs, or prompts.
6. **Dispatch Cursor SDK**: use inspect-only, proposal, or apply mode according to the routing decision. Use `scripts/cursor_delegate.mjs`; install dependencies with `npm install` from the skill directory if `@cursor/sdk` is missing.
7. **Monitor when useful**: when live visibility helps, read `references/live-monitoring.md` and monitor `status.json` rather than raw events by default.
8. **Review**: use `references/review-checklist.md` to inspect reports, diffs, verification evidence, scope boundaries, lockfiles, generated files, SDK metadata, authorization state, and integration risks.
9. **Narrow follow-up or stop**: send bounded follow-up packets only for specific findings. Stop and escalate when the implementation needs new product scope, architecture, dependencies, migrations, security posture, public APIs, credentials, destructive commands, billing changes, or deployment actions.

## Cursor SDK Dispatch Wrapper

Use the wrapper only after creating a task packet with exactly one valid authority section and no unresolved template placeholders.

```bash
node scripts/cursor_delegate.mjs \
  --workspace /path/to/repo \
  --task-file /path/to/cursor-task.md \
  --planning-source auto \
  --inspect-only
```

Apply mode:

```bash
CURSOR_API_KEY="$CURSOR_API_KEY" node scripts/cursor_delegate.mjs \
  --workspace /path/to/repo \
  --task-file /path/to/cursor-task.md \
  --apply
```

The wrapper defaults to local Cursor SDK runtime, SDK conversation mode `plan` for inspect/proposal and `agent` for apply, local sandbox enabled, project setting source enabled, and logical model profile `grok-4.5-high`. Live dispatch resolves Grok 4.5 plus its High effort parameter through the authenticated SDK model catalog and omits the speed parameter; dry-run reports the intended profile without claiming a resolved SDK selection.

Keep the task packet's `## Cursor Model` section aligned with the wrapper arguments. The wrapper requires exactly one section and exactly one each of `Wrapper profile`, `Model`, and `Model params`; it rejects stale or conflicting defaults and explicit overrides whose exact id or parameters do not match the wrapper arguments. Validation ignores fenced examples and HTML comments, and rejects ambiguous raw HTML blocks or multiline inline-code spans; fence such examples explicitly.

Authorization behavior:

- If `CURSOR_API_KEY` is set, the wrapper passes it as `apiKey` to the SDK.
- If no key is present and the process is interactive, `--auth-mode auto` prompts for a hidden key, does not save it, and keeps it out of argv/logs.
- If the SDK rejects the key, the wrapper marks `status.json` as `needs_authorization` and prompts once more by default.
- If the run is non-interactive, the wrapper exits with an authorization request that the upstream agent must surface to the user.

Use `--runtime cloud --repo-url <repo-url[#ref]>` only when cloud execution is explicitly desired and repository access is configured for the Cursor account/team. Keep apply-mode cloud PR behavior explicit with `--auto-create-pr` rather than implicit.

Wrapper runs write `status.json`, `metadata.json`, `prompt.txt`, and a `<log-dir>/latest` pointer. Read-only workspace copies are removed on process exit by default; preserving them requires `--keep-workspace-copy` plus `--override-reason`. The wrapper refuses symlinks that escape a copy, but permission hardening remains defense in depth rather than a security boundary; keep the SDK sandbox enabled. Raw `events.ndjson` is written only with `--include-raw-events`, which requires `--override-reason`. Prefer `status.json` for low-noise live monitoring.

## Guardrails

- Keep delegated context minimal, relevant, and role-specific.
- Resolve and verify Grok 4.5 High for every top-level Cursor dispatch unless an explicit user Cursor-model instruction exists; leave speed unspecified so Cursor applies its current default.
- Treat an internal subagent's Grok 4.5 High label as a request, not a verified parameter selection. Keep internal subagents `disabled` when exact High execution is acceptance-critical.
- Do not pass secrets, private keys, tokens, production credentials, or unrelated proprietary context to Cursor SDK or subagents.
- Do not ask the user to paste a Cursor API key into chat. Request environment authorization or use the wrapper's hidden local prompt.
- Allow Cursor internal subagents only when the task packet includes `## Cursor Internal Subagent Policy`; otherwise keep Cursor as a single executor.
- Prefer version control before apply-mode Cursor runs.
- Use separate branches or worktrees for hierarchical or parallel workstreams.
- Avoid concurrent writes to the same files unless the upstream agent serializes ownership.
- Treat downstream outputs as evidence, not authority.
- Preserve user intent over downstream suggestions.
- Do not commit, push, deploy, rotate credentials, alter billing, run destructive commands, or expand scope unless the user explicitly requested the action and the upstream agent reviewed the risk.

## Resources

- `references/routing-policy.md`: mode selection rules, Cursor SDK runtime/model policy, support-subagent brief, escalation and downgrade rules.
- `references/cursor-sdk-authorization.md`: API-key authorization workflow, user request templates, and secret-handling rules.
- `references/planning-contract.md`: planning-subagent brief and upstream plan-review format.
- `references/workstream-contract.md`: hierarchical coordination ledger, scheduling rules, workstream contract, and local completion report.
- `references/task-direct.md`: direct Cursor SDK task packet template.
- `references/task-planned.md`: reviewed upstream plan task packet template.
- `references/task-local.md`: local workstream task packet template.
- `references/task-user-plan.md`: user-provided plan task packet template.
- `references/task-follow-up.md`: bounded follow-up task packet template.
- `references/cursor-internal-subagents.md`: Cursor internal task/subagent policy, requested-model limits, review evidence, and packet block.
- `references/review-checklist.md`: routing, plan, workstream, Cursor, follow-up, authorization, and acceptance gates.
- `references/live-monitoring.md`: live Cursor SDK run status artifacts, usage, and limits.
- `scripts/cursor_delegate.mjs`: optional Cursor SDK wrapper with authority-heading checks, placeholder checks, git safety checks, proactive API-key authorization, sanitized status output, and run metadata.
- `scripts/test_cursor_delegate.mjs`: offline wrapper tests that do not call Cursor SDK.
- `package.json`: Node runtime and `@cursor/sdk` dependency metadata.

## Response

Report:

- routing mode and reason;
- subagents used, if any;
- Cursor SDK runtime and mode: inspect-only, proposal, or apply;
- Cursor SDK conversation mode;
- top-level resolved Cursor model and verification status, plus internal subagent model requested or observed without overstating parameter verification;
- authorization state and whether user action was needed;
- Cursor internal subagents used, if any;
- changes made or downstream findings;
- verification performed and results;
- upstream review verdict: accepted, accepted with notes, needs bounded follow-up, or blocked;
- remaining risks or user decisions.
