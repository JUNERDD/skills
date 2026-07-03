---
name: delegate-to-cursor-composer
description: Opt-in only Cursor Composer delegation workflow for bounded coding tasks, reviewed implementation packets, Cursor internal subagents, hierarchical workstreams, and live Cursor CLI monitoring. Use only when the user explicitly injects or names `$delegate-to-cursor-composer` / `delegate-to-cursor-composer` as the skill to use; otherwise do not select it proactively.
---
# Delegate to Cursor Composer

Use this skill to route software engineering work to Cursor Composer through bounded, reviewable delegation packets. The upstream agent remains accountable for user intent, scope, architecture, risk decisions, verification gates, and final acceptance.

Core rule:

```text
Choose the lightest delegation path that can produce a safe, bounded, reviewable result.
```

## Roles

- **Upstream agent**: interpret the user goal, choose the route, define scope and risk gates, approve any plan before implementation, review all downstream output, and give the final verdict.
- **Support subagent**: perform bounded read-only or advisory work such as repo survey, test triage, security review, API review, documentation review, or independent diff review. Support subagents do not edit files, dispatch Cursor, or approve final quality.
- **Planning subagent**: produce a read-only implementation plan for one coherent workstream. The upstream agent must review and edit the plan before Cursor receives it.
- **Workstream orchestrator subagent**: own one bounded workstream in hierarchical delegation. It may create a local plan, dispatch Cursor if authorized, review local output, run limited repair loops, and report evidence. It does not own global architecture, cross-workstream interfaces, final merge, deployment, or final user-facing approval.
- **Cursor Composer**: execute the approved implementation packet. Cursor may inspect, propose, apply changes, or launch bounded internal subagents according to the packet, but it must not broaden scope or become the final reviewer.
- **Cursor internal subagent**: a Cursor `Task()`/`taskToolCall` child agent launched by Cursor. It works under Cursor's packet, uses `composer-2.5-fast` by default, and returns evidence to Cursor; it is distinct from upstream support/planning/workstream subagents.

## Routing Modes

Use `references/routing-policy.md` before implementation. Emit a short routing decision:

```markdown
## Routing Decision
Mode: <direct_cursor | planned_single_stream | hierarchical_orchestration | blocked>
Support subagents: <none or bounded tasks>
Reason: <why this route is sufficient>
Risk gates: <checks required before acceptance>
Cursor mode: <inspect-only | proposal | apply>
Cursor model: <composer-2.5-fast unless the user explicitly directed Cursor to use a different model>
Cursor internal subagents: <disabled | read-only-analysis | verification | bounded-implementation>
Live monitor: <none | status.json path or expected log-dir/latest>
```

Choose:

- `direct_cursor` for small, clear, low-risk implementation slices.
- `planned_single_stream` when the work is one coherent stream but benefits from a reviewed plan.
- `hierarchical_orchestration` only when multiple independent workstreams have clear ownership and local review loops reduce risk or context load.
- `blocked` when missing context, unsafe action, unavailable permissions, or required user decisions prevent safe delegation.

Support subagents may be used in any mode when their bounded evidence improves quality.

## Workflow

1. **Intake**: identify the user goal, definition of done, workspace constraints, likely repo areas, risk class, validation commands, and any destructive or irreversible actions. Ask at most one blocking question; otherwise state assumptions and proceed.
2. **Route**: choose the lightest safe mode with `references/routing-policy.md` and record the routing decision.
3. **Prepare upstream context**:
   - Direct mode: create a Cursor packet from `references/task-contract.md` using `## Master Direct Implementation Instructions`.
   - Planned mode: brief the planning subagent with `references/planning-contract.md`, review the plan, then create a Cursor packet with `## Approved Upstream Plan`.
   - Hierarchical mode: define workstream contracts with `references/orchestrator-subagent-contract.md`; each authorized workstream creates Cursor packets with `## Approved Local Plan`.
   - User-provided plan: accept or edit the plan before Cursor receives `## User-Provided Approved Plan`.
4. **Resolve Cursor model**: use `composer-2.5-fast` for every Cursor dispatch and Cursor internal subagent unless the user explicitly instructed Cursor to use a different model. Do not treat permission to use support subagents, planning subagents, workstream orchestrators, Cursor internal subagents, or outer-agent model choices as permission to change Cursor's model.
5. **Dispatch Cursor**: use inspect-only, proposal, or apply mode according to the routing decision. Prefer the wrapper in `scripts/cursor_delegate.py` when a headless Cursor CLI is available.
6. **Monitor when useful**: when Cursor may run long enough that the caller needs live visibility, read `references/live-monitoring.md` and monitor `status.json` rather than raw logs by default.
7. **Review**: use `references/review-checklist.md` to inspect downstream reports, diffs, verification evidence, scope boundaries, lockfiles, generated files, and integration risks.
8. **Repair or stop**: send narrow repair packets only for specific findings. Stop and escalate when implementation needs new product scope, architecture, dependencies, migrations, security posture, public APIs, credentials, destructive commands, billing changes, or deployment actions.

## Cursor Dispatch Wrapper

Use the wrapper only after creating a task packet with a valid authority section.

```bash
python scripts/cursor_delegate.py \
  --workspace /path/to/repo \
  --task-file /path/to/cursor-task.md \
  --planning-source auto \
  --output-format stream-json \
  --stream-partial-output
```

The wrapper defaults to Cursor model `composer-2.5-fast`, and internal Cursor subagents inherit that default. Pass `--model` or `--internal-subagent-model` only when the user explicitly directed Cursor to use a different model, and include `--user-authorized-model` with that override.

Add `--apply` only when file modification is authorized and the workspace is reviewable. Use `--inspect-only` for feasibility checks and blockers. The wrapper refuses apply mode on dirty git workspaces unless explicitly overridden.

Wrapper runs write `stdout.log`, `stderr.log`, `events.ndjson`, `status.json`, `metadata.json`, `prompt.txt`, and a `<log-dir>/latest` pointer. Prefer `status.json` for low-noise live monitoring, including Cursor internal subagent starts/completions. Read `references/live-monitoring.md` before tailing raw events.

## Guardrails

- Keep delegated context minimal, relevant, and role-specific.
- Default every Cursor dispatch and Cursor internal subagent to model `composer-2.5-fast`; a subagent authorization or non-Cursor model preference is not a Cursor model override.
- Do not pass secrets, private keys, tokens, production credentials, or unrelated proprietary context to Cursor or subagents.
- Allow Cursor internal subagents only when the task packet includes `## Cursor Internal Subagent Policy`; otherwise keep Cursor as a single executor.
- Prefer version control before apply-mode Cursor runs.
- Use separate branches or worktrees for hierarchical or parallel workstreams.
- Avoid concurrent writes to the same files unless the upstream agent serializes ownership.
- Treat downstream outputs as evidence, not authority.
- Preserve user intent over downstream suggestions.
- Do not commit, push, deploy, rotate credentials, alter billing, run destructive commands, or expand scope unless the user explicitly requested the action and the upstream agent reviewed the risk.

## Resources

- `references/routing-policy.md`: mode selection rules, support-subagent brief, escalation and downgrade rules.
- `references/planning-contract.md`: planning-subagent brief and upstream plan-review format.
- `references/orchestrator-subagent-contract.md`: hierarchical workstream contract and local completion report.
- `references/task-contract.md`: Cursor direct, reviewed, and repair packet templates.
- `references/cursor-internal-subagents.md`: Cursor `Task()`/`taskToolCall` policy, model defaults, review evidence, and packet block.
- `references/review-checklist.md`: routing, plan, workstream, Cursor, repair, and final review gates.
- `references/live-monitoring.md`: live Cursor run status artifacts, usage, and limits.
- `scripts/cursor_delegate.py`: optional headless Cursor CLI wrapper with authority-marker checks, git safety checks, and run logs.

## Final Response

Report:

- routing mode and reason;
- subagents used, if any;
- Cursor mode: inspect-only, proposal, or apply;
- Cursor model and internal subagent model used;
- Cursor internal subagents used, if any;
- changes made or downstream findings;
- verification performed and results;
- upstream review verdict: approved, approved with notes, needs repair, or blocked;
- remaining risks or user decisions.
