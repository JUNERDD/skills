---
name: delegate-to-cursor-sdk
description: Opt-in workflow for routing bounded coding tasks through the independent cursor-delegate CLI and Cursor SDK, with reviewed implementation packets, internal subagents, hierarchical workstreams, follow-up packets, a chronological no-regression execution dashboard with Stop controls, agent-guided loopback API-key authorization, a global authorization barrier, and owned temporary-artifact cleanup. Use only when the user explicitly injects or names `$delegate-to-cursor-sdk` / `delegate-to-cursor-sdk`; otherwise do not select it proactively.
---

# Delegate to Cursor via Cursor SDK

Route software engineering work to Cursor's coding agent through the independent `cursor-delegate` CLI. The CLI owns the `@cursor/sdk` integration; this skill owns delegation policy, task packets, review, and acceptance.

Core invariant:

```text
Choose the lightest delegation path that can produce a safe, bounded, reviewable result.
```

## Roles

- **Upstream agent**: interpret the user goal, choose the route, define scope and risk gates, authorize Cursor SDK runtime/model/auth, approve any plan before implementation, own the private delegation session, review downstream output, decide acceptance, and clean only that session's temporary artifacts.
- **Support subagent**: perform bounded read-only or advisory work such as repository survey, test triage, security review, API review, documentation review, or independent diff review. It does not edit files, dispatch Cursor, or approve quality.
- **Planning subagent**: produce a read-only plan for one coherent workstream. The upstream agent must review and edit the plan before Cursor receives it.
- **Workstream orchestrator subagent**: own one bounded workstream in hierarchical delegation. It may create a local plan, dispatch Cursor SDK if authorized, review local output, run limited follow-up loops, and report evidence. It does not own global architecture, cross-workstream interfaces, merge, deployment, or user-facing acceptance.
- **Cursor SDK agent**: execute the approved task packet using `@cursor/sdk`. Cursor may inspect, propose, apply changes, or launch bounded internal subagents according to the packet, but it must not broaden scope or become the acceptance reviewer.
- **Cursor internal subagent**: a Cursor task/tool child agent launched inside one Cursor SDK run. It works under Cursor's packet and returns evidence to Cursor. In `@cursor/sdk` 1.0.23 the task/Agent tool accepts only a string model request, so an internal subagent can request the default label but cannot prove the exact High effort parameter. It is an event-observed descendant with `parent-only` control capability, not a separately retained run; stop its owning parent rather than claiming an independent Stop.

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
Cursor model: <the catalog-resolved Grok 4.5 High non-Fast preset unless the user explicitly directed Cursor to use a different model>
Cursor internal subagents: <disabled | read-only-analysis | verification | bounded-implementation>
Authorization: <authorized | needs_authorization | waiting_for_user | cancelled | failed>
Live monitor: <none | status.json path | default dashboard auto-open with manual fallback>
Dashboard launch: <default-auto-after-key-and-model-preflight | no-open explicitly requested by current user | n/a>
Dashboard lifecycle: <terminal-close-default | bounded-retention N seconds with exceptional reason>
Temporary artifacts: <skill-owned private session | caller-owned packet/logs preserved>
Audit retention: <ephemeral until accepted or reconciled-abandonment cleanup | caller-owned retained path and reason>
```

Choose:

- `direct_cursor` for small, clear, low-risk implementation slices.
- `planned_single_stream` when one coherent stream benefits from a reviewed plan.
- `hierarchical_orchestration` only when independent workstreams have clear ownership and local review loops reduce risk or context load.
- `blocked` when missing context, unsafe action, unavailable permissions, authorization is cancelled/failed/unavailable, or required user decisions prevent safe delegation. A loopback authorization flow that is still waiting is a non-terminal `needs_authorization` state, not a completed block.

## Workflow

1. **Intake**: identify the user goal, definition of done, workspace constraints, likely repository areas, risk class, validation commands, and destructive or irreversible actions. Ask at most one blocking question; otherwise state assumptions and proceed.
2. **Route**: choose the lightest safe mode with `references/routing-policy.md` and record the routing decision.
3. **Establish the owned delegation session**: read `references/owned-artifact-cleanup.md`, run `scripts/delegation_session.py start` from this skill's actual installation directory, and record the exact marker, packet directory, log directory, lease directory, and root cleanup owner. The root upstream agent is the cleanup owner for the entire session lifetime. Do not place copied packets or skill-managed CLI logs in the target repository.
4. **Prepare authority**:
   - Direct mode: materialize the fenced packet body from `references/task-direct.md` below the current session's `packetsDir` and fill `## Master Direct Implementation Instructions`.
   - Planned mode: brief the planning subagent with `references/planning-contract.md`, review the plan, then materialize the fenced body from `references/task-planned.md` below `packetsDir` and fill `## Approved Upstream Plan`.
   - Hierarchical mode: use `references/workstream-contract.md` to build a dependency-aware coordination ledger, compute effective Cursor concurrency, and define workstream contracts; each ready authorized workstream materializes the fenced body from `references/task-local.md` below the root-owned `packetsDir` and fills `## Approved Local Plan`.
   - User-provided plan: preserve the original, accept or edit a copy, then materialize the fenced body from `references/task-user-plan.md` below `packetsDir` with `## User-Provided Approved Plan`.
   - Follow-up loop: materialize the fenced body from `references/task-follow-up.md` below the same `packetsDir` into a new bounded follow-up packet only for specific findings from upstream review.
5. **Resolve Cursor SDK model**: use the CLI's logical default profile `grok-4.5-high`. The CLI discovers the current canonical model and exactly one High, non-Fast preset through `Cursor.models.list()`, then sends that preset's complete `{ id, params }` selection as the SDK catalog defines it. It fails closed rather than splitting preset parameters, guessing High, selecting a Fast variant, or falling back to Auto. Pass a different `--model` and any accompanying `--model-param` only when the user explicitly directed Cursor to use that model; include `--user-authorized-model` and `--override-reason`.
6. **Resolve authorization and enforce the global barrier**: before any Cursor dispatch or parallel implementation wave, read `references/cursor-sdk-authorization.md`. Prefer `CURSOR_API_KEY` in the local process environment. A non-root workstream must use `--auth-mode fail`; if it reports `needs_authorization`, it returns control without owning an authorization capability. The root stops new dispatches, snapshots the entire live descendant tree and continuation points under one barrier generation, interrupts every descendant, and re-enumerates until none is running. Only then may the root rerun the same bounded packet with `--auth-mode browser`. The CLI starts its packaged Next.js frontend on an isolated loopback port without opening any URL. While the key is missing or rejected, do not open `frontend.dashboard_url`, `authorization.local_url`, or the external Cursor API Keys page automatically. The same app serves `/authorize/[sessionId]` and `/dashboard/[dispatchId]`; it publishes the transient `authorization.local_url` plus fixed `authorization.dashboard_url` in mode-`0600` status and publishes the local dashboard entry as `frontend.dashboard_url`. The root manually presents the two authorization links together in one user handoff. Resume each recorded canonical agent at most once only after key verification; on cancellation, failure, or an unconfirmed pause, keep implementation stopped and move to `blocked`. Never collect the key in chat, task packets, logs, prompts, or continuation records.
7. **Dispatch Cursor SDK through the owned lease wrapper**: use inspect-only, proposal, or apply mode according to the routing decision. Every skill-managed dispatch must use `scripts/delegation_session.py run --session-file <exact-marker> --log-name <unique-single-level-name> -- cursor-delegate ...`; never invoke a task dispatch directly and never pass `--log-dir` inside the trailing CLI command. By default the wrapper maps the name to the current session's `logsDir` and holds a foreground lease that blocks premature cleanup. For explicitly durable audit logs, add `--retained-log-dir /absolute/caller-owned/log-base` before `--`; the absolute path must not already exist, the wrapper creates it outside the session, and this skill never cleans it. Never install SDK dependencies in this skill. Let a normal live invocation automatically open the local dashboard only after the API key is valid and model preflight succeeds. Pass `--no-open-dashboard` only when the current user explicitly requested that the dashboard not open; never infer opt-out from CI, headless execution, background work, parallel dispatch, unavailable browser tooling, or any other environment signal. Treat opener failure as non-fatal, report it, and use protected status for a manual fallback without retrying Cursor dispatch.
8. **Monitor and control when useful**: when live visibility helps, read `references/live-monitoring.md`. Prefer the default post-preflight dashboard auto-open for interactive observation and `status.json` for low-noise programmatic checks; never tail raw events by default. If the system opener fails, offer `frontend.dashboard_url` only to the current user as a manual fallback. If the current user explicitly suppressed opening, do not proactively hand them the dashboard capability; provide it only if they later ask to access the dashboard. After a confirmed automatic open, assume its one-time status URL may be spent and never re-present it as a fresh entry. The dashboard may stop an independently controllable retained agent or issue Stop All. Treat each control outcome as evidence and continue upstream review; a click is not proof of cancellation until the CLI reports success or terminal state.
9. **Review**: use `references/review-checklist.md` to inspect reports, diffs, verification evidence, scope boundaries, lockfiles, generated files, SDK metadata, authorization state, and integration risks.
10. **Narrow follow-up or stop**: send bounded follow-up packets only for specific findings. Keep their packets and logs in the same owned session. Stop and escalate when the implementation needs new product scope, architecture, dependencies, migrations, security posture, public APIs, credentials, destructive commands, billing changes, or deployment actions.
11. **Finalize and clean up**: after the final upstream verdict and only when no authorization, resume, follow-up, active lease, active workstream, or ambiguous remote run remains, preserve the bounded review evidence and invoke `scripts/delegation_session.py cleanup` with the exact marker. Delete only the skill-owned session; a caller-owned path passed with `--retained-log-dir` is never a cleanup target. Cleanup succeeds once. A later call is refused because the removed marker can no longer prove ownership; do not report that refusal as success. Retain and report caller-owned files or any session whose cleanup gate is not met.

## CLI Availability

Before any dispatch, check:

```bash
command -v cursor-delegate
```

If the command is missing, do not recreate the SDK call with ad hoc code and do not install packages in the skill directory. If the user has a `cursor-delegate` source checkout and explicitly asks to install it, follow that project's local-install instructions. Otherwise report that the independent CLI is required and stop before dispatch.

Read `references/cursor-delegate-cli-reference.md` before invoking unfamiliar flags or troubleshooting installation, authorization, logging, resume, or override behavior.

## Cursor SDK Dispatch

Use the CLI only after creating a task packet with exactly one valid authority section and no unresolved template placeholders. Every dispatch is a foreground child of the session wrapper.

```bash
python3 <skill-root>/scripts/delegation_session.py run \
  --session-file /private/session/.cursor-delegate-skill-session.json \
  --log-name root-01 \
  -- cursor-delegate \
  --workspace /path/to/repo \
  --task-file /private/session/packets/cursor-task.md \
  --planning-source auto \
  --inspect-only
```

Apply mode:

```bash
CURSOR_API_KEY="$CURSOR_API_KEY" python3 <skill-root>/scripts/delegation_session.py run \
  --session-file /private/session/.cursor-delegate-skill-session.json \
  --log-name root-apply-01 \
  -- cursor-delegate \
  --workspace /path/to/repo \
  --task-file /private/session/packets/cursor-task.md \
  --apply
```

For an explicitly retained audit log, add `--retained-log-dir /absolute/caller-owned/root-apply-01` between `--log-name` and `--`. Keep `--log-name` unique for lease and correlation records. The retained path must be absolute, caller-owned, outside the private session, and not already exist; the wrapper creates it and excludes it from every cleanup attempt.

The CLI defaults to local Cursor SDK runtime, SDK conversation mode `plan` for inspect/proposal and `agent` for apply, local sandbox enabled, project setting source enabled, and logical model profile `grok-4.5-high`. Live dispatch resolves the complete catalog-defined High, non-Fast Grok 4.5 preset; dry-run reports the intended profile without claiming a resolved SDK selection.

Keep the task packet's `## Cursor Model` section aligned with the CLI arguments. The CLI requires exactly one section and exactly one each of `CLI profile`, `Model`, and `Model params`; it rejects stale or conflicting defaults and explicit overrides whose exact id or parameters do not match the CLI arguments. Validation ignores fenced examples and HTML comments, and rejects ambiguous raw HTML blocks or multiline inline-code spans; fence such examples explicitly.

Authorization behavior:

- If `CURSOR_API_KEY` is set, the CLI verifies it before creating or sending a Cursor run and passes it as `apiKey` to the SDK.
- Every live dispatch supervises one isolated child process that starts only the packaged production Next.js build on `127.0.0.1:0`; the installed CLI never runs `next dev`, `next build`, npm, or another package manager. The same frontend project serves the authorization and dashboard routes under different capability-bound paths.
- The dashboard receives a random one-time ticket that remains redeemable for the owned frontend lifetime; a separate short-lived authorization ticket is created only while authorization is active. Ticket exchange creates an in-memory target-bound session with an HttpOnly, SameSite `strict` cookie. Protected requests require the exact owned loopback Host; mutations additionally require exact Origin, an atomically consumed/rotated CSRF token, bounded body, and matching dispatch/session target.
- With the default `--auth-mode browser`, a missing or rejected key writes `needs_authorization` and publishes the transient `authorization.local_url` capability together with the fixed [Cursor API Keys](https://cursor.com/dashboard/api) `authorization.dashboard_url` in mode-`0600` status. The local dashboard entry is separately published as `frontend.dashboard_url`. The CLI opens none of them while authorization is unresolved and removes `authorization.local_url` after verification, cancellation, timeout, or failure.
- The local Next.js page sends the user's transient key input over its exact loopback origin and the owned parent/child IPC channel. The parent CLI verifies it with Cursor, keeps invalid submissions on the page for correction, and never saves the key or places it in argv, URLs, child environment, a client bundle or response, logs, status, metadata, prompts, or the dashboard event journal.
- The root agent reads both authorization status URLs and presents the local authorization page and Cursor API Keys link together. The user opens those links manually; neither the CLI nor the agent auto-opens an authorization URL.
- A verified submission closes the authorization capability in status. After model preflight also succeeds, the CLI opens the local dashboard by default and dispatch continues. The authorization page reports verification and can be closed by the user; the same owned frontend process continues serving the dashboard until the dispatch lifecycle closes it. `--auth-mode fail` controls only missing or rejected key handling: it never enables or opens an authorization capability and exits `2` when authorization is required. With a valid environment key and successful model preflight, it follows the same default dashboard auto-open policy as browser mode unless the current user explicitly requested `--no-open-dashboard`.
- `--no-open-dashboard` suppresses the default post-preflight local dashboard launch. Pass it only for an explicit current-user request, not because the caller believes CI, headless, background, parallel, or browser-tool-free execution should be quiet.
- Dashboard opening is best effort. Report an opener failure without blocking dispatch, then use the protected `frontend.dashboard_url` as the current user's manual fallback.
- `needs_authorization` is a global scheduling barrier for this skill: no support, planning, workstream, follow-up, or Cursor agent may continue or start until the barrier is released.

Dashboard behavior:

- `frontend.dashboard_url` is a one-time local capability. A normal live invocation opens it automatically after key and model preflight unless the current user explicitly requested `--no-open-dashboard`. Use manual handoff after an opener failure, or after an explicit opt-out only if the current user later asks to access the dashboard; do not proactively countermand their opt-out. Never place the URL in task packets, prompts, continuation records, durable reports, or unrelated logs. After confirmed automatic opening, treat the original status URL as consumed and never hand it off again as fresh.
- The dashboard's middle region is a chronological execution tape ordered by `RunEvent.sequence`. Step/turn boundaries, requests, task/subagent lifecycle, summaries, assistant/reasoning updates, and tool lifecycle appear in their actual temporal flow; tools update in place by `callId`, while `stepId` and `modelCallId` preserve UI correlation. `requestId` remains a journal/status audit field and is not promised as a rendered UI association.
- Assistant and thinking deltas append. Completion and conversation snapshots may fill missing text but cannot replace richer streamed text with empty, shorter, or stale content. Completed thinking remains visible and expandable instead of disappearing.
- Replay subscribes before reading backlog, advances the cursor only for events the browser actually receives, and batches React publication by animation frame. The browser retains a bounded 2,000-event execution window; a gap or rollover surfaces a watermark and restores aggregate text/state from the authoritative snapshot. Do not claim an unlimited historical timeline or full-text recovery beyond the snapshot's bounded text projection.
- The browser transport remains sanitized and replayable through AI SDK v7, current shadcn chat primitives, and AI Elements. It never receives opt-in raw SDK events.
- Stop is available only for a CLI-retained active Cursor run with `independent` capability. A Cursor internal task subagent is visible but `parent-only`; stop the owning parent to cancel its subtree. A terminal or unsupported agent must not be described as independently stoppable.
- Stop All first closes admission for that dispatch, then cancels independently controllable active runs and rechecks through a bounded drain. Report per-agent outcomes and any partial failure; never claim all agents stopped while the CLI reports an active, unsupported, timed-out, or failed outcome.
- Stop and Stop All are lifecycle controls for the current dispatch. They do not authorize a retry, replacement run, broader task packet, destructive action, commit, push, deployment, or any other scope expansion.

Use `--runtime cloud --repo-url <repo-url[#ref]>` only when cloud execution is explicitly desired and repository access is configured for the Cursor account/team. Keep apply-mode cloud PR behavior explicit with `--auto-create-pr` rather than implicit.

CLI runs write `status.json`, `metadata.json`, `prompt.txt`, sanitized `stream.ndjson`, `snapshot.v2.json`, and a `<log-base>/latest` pointer. Direct CLI callers may treat these as durable audit evidence. This skill instead routes every invocation through the session wrapper: ordinary log names resolve below the private session and are removed only at an accepted or explicitly reconciled-abandonment cleanup gate, while an explicit `--retained-log-dir` is caller-owned and never cleaned. Read-only workspace copies are removed on process exit by default; preserving them requires `--keep-workspace-copy` plus `--override-reason`. The CLI refuses symlinks that escape a copy, but permission hardening remains defense in depth rather than a security boundary; keep the SDK sandbox enabled. Raw `events.ndjson` is written only with `--include-raw-events`, which requires `--override-reason`. Prefer `status.json` or the packaged dashboard for monitoring.

Dashboard lifecycle is decided only by the upstream agent currently invoking this skill:

- Default: do not pass `--dashboard-retention-seconds`; its default value `0` closes the frontend child, listener, and port when dispatch becomes terminal.
- Exceptional bounded review: the invoking upstream agent may pass `--dashboard-retention-seconds N` only after recording a concrete special-case reason in the routing decision, where `1 <= N <= 300`. Do not choose retention by habit, do not delegate this decision to Cursor or a workstream, and do not create a detached/orphan dashboard.
- The CLI remains the process owner and foreground command during retention, waits for at most `N` seconds, then closes the frontend. Parent disconnect, SIGINT, SIGTERM, startup failure, and authorization failure also trigger owned cleanup.

Dashboard launch and retention are independent. Default auto-open does not authorize retention, and `--no-open-dashboard` does not prevent the packaged frontend from running or change terminal-close-default cleanup.

## Guardrails

- Keep delegated context minimal, relevant, and role-specific.
- Resolve the complete catalog-defined Grok 4.5 High, non-Fast preset for every new top-level Cursor dispatch unless an explicit user Cursor-model instruction exists. Validate every model value the SDK reports, but record optional model evidence as unreported rather than inventing it.
- Treat an internal subagent's Grok 4.5 High label as a request, not a verified parameter selection. Keep internal subagents `disabled` when exact High execution is acceptance-critical.
- Treat every Cursor internal task subagent as `parent-only` unless the CLI has separately registered a real top-level run handle. Never fabricate an independent Stop action from stream-only IDs or tool-call metadata.
- Do not pass secrets, private keys, tokens, production credentials, or unrelated proprietary context to Cursor SDK or subagents.
- Do not ask the user to paste a Cursor API key into chat. Use the CLI-owned local authorization page or a pre-authorized environment.
- Treat `authorization.local_url` as a short-lived capability even though it contains no API key: show it only to the current user during the authorization handoff, and do not copy it into task packets, continuation records, durable reports, or unrelated logs.
- Treat `frontend.dashboard_url` as the same class of short-lived local capability. Do not print or persist it outside the CLI's protected status file and the current user handoff.
- Keep the default post-preflight dashboard auto-open. Pass `--no-open-dashboard` only after the current user explicitly asks not to open it; never derive that choice from CI, headless mode, background execution, concurrency, or missing browser-control tooling.
- Before both API-key validation and model preflight succeed, the CLI and invoking agent must not automatically open any authorization or dashboard URL. The root may still present authorization links to the current user, who opens them manually to complete the missing-key flow.
- Treat dashboard opener failure as non-fatal and report the protected manual fallback. After confirmed auto-open, never re-hand the original one-time status URL as if it were unused.
- Treat `needs_authorization` as a real global barrier: stop new scheduling, pause/interrupt every live child agent, and record its continuation before waiting. Merely stopping status polling while agents continue is not a pause.
- Cover the complete descendant tree, including support/planning agents without workstream rows. Re-enumerate after interruption; if any descendant or owned subprocess is still running, mark the barrier failed instead of claiming it is waiting safely.
- Keep the unified loopback Next.js frontend and its `cursor-delegate` process root-owned. Non-root agents use `--auth-mode fail` and hand authorization back to root, so interrupting a child cannot orphan the local page or silently leave a Cursor dispatch running.
- Resume only the recorded pre-barrier agent set, exactly once, after the CLI reports a verified key. Do not resume implementation after authorization cancellation or failure.
- Allow Cursor internal subagents only when the task packet includes `## Cursor Internal Subagent Policy`; otherwise keep Cursor as a single executor.
- Keep terminal dashboard cleanup at its default `0` seconds. Only the upstream agent that invoked this skill may choose an exceptional `1..300` second retention window, must state why, and must let the owning CLI remain attached until cleanup completes.
- Start one private delegation session before copying packets. Place every skill-owned packet and ordinary per-dispatch log base under it; an explicit newly created `--retained-log-dir` stays outside and is never cleaned. Never use the target repository's default `.agent/delegations` for a skill-managed run.
- Keep the session through authorization barriers, retries, resumes, bounded follow-ups, and hierarchical integration review. Non-root agents never clean it and hand only marker/path evidence plus live-process disposition to root; cleanup ownership never leaves root.
- At final acceptance or explicitly reconciled/user-authorized abandonment, use the bundled helper to validate ownership, allowlisted contents, terminal statuses, frontend shutdown, and path containment before deletion. Never substitute a broad recursive delete, glob, `latest` target, shared directory, or unresolved environment variable.
- Never delete a caller-provided task/plan, explicit audit-retention directory, repository change, branch/worktree, `--keep-workspace-copy` result, symlink, unknown artifact, or session that still needs continuation. Preserve and report a blocked cleanup rather than widening scope.
- Use Stop All when the user or upstream agent intends to halt the whole current dispatch; use per-agent Stop only for a registered independently controllable run. Preserve and report partial-failure evidence instead of treating a submitted command as success.
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
- `references/cursor-delegate-cli-reference.md`: independent CLI availability, command surface, defaults, safety overrides, and project-maintenance contract.
- `references/owned-artifact-cleanup.md`: private session creation, ownership boundary, cleanup gate, helper usage, and retained-artifact rules.
- `scripts/delegation_session.py`: standard-library session creation, leased foreground dispatch with optional never-cleaned retained logs, and one-time allowlisted cleanup for the exact marker-owned packet/log session.

## Response

Report:

- routing mode and reason;
- subagents used, if any;
- Cursor SDK runtime and mode: inspect-only, proposal, or apply;
- Cursor SDK conversation mode;
- top-level resolved Cursor model and verification status, plus internal subagent model requested or observed without overstating parameter verification;
- authorization state, link handoff and page-lifecycle outcome, and whether user action was needed;
- dashboard launch outcome: default post-preflight auto-open, explicit current-user opt-out, or non-fatal opener failure with manual handoff, without reproducing the capability URL in a durable report;
- dashboard lifecycle choice: default terminal close, or the exceptional bounded retention duration and reason selected by the invoking upstream agent;
- per-agent Stop or Stop All commands used, their correlated outcomes, and any remaining parent-only, unsupported, timed-out, failed, or active agents;
- number of agents paused for the authorization barrier and number resumed after verification;
- Cursor internal subagents used, if any;
- changes made or downstream findings;
- verification performed and results;
- upstream review verdict: accepted, accepted with notes, needs bounded follow-up, or blocked;
- temporary-artifact outcome: cleaned, retained with reason, or cleanup blocked/refused with reason, plus whether any caller-owned audit directory was preserved;
- remaining risks or user decisions.
