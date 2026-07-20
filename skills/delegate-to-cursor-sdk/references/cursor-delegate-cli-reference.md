# cursor-delegate CLI Reference

## Contents

- [Availability](#availability)
- [Core Commands](#core-commands)
- [Modes And Defaults](#modes-and-defaults)
- [Model Contract](#model-contract)
- [Authorization](#authorization)
- [Dashboard And Control](#dashboard-and-control)
- [Workspace Safety](#workspace-safety)
- [Cloud Runtime](#cloud-runtime)
- [Logs And Resume](#logs-and-resume)
- [Skill-Managed Artifact Lifecycle](#skill-managed-artifact-lifecycle)
- [Safety Overrides](#safety-overrides)
- [Exit Behavior](#exit-behavior)
- [Project Maintenance](#project-maintenance)

## Availability

Check the independent CLI before dispatch:

```sh
command -v cursor-delegate
```

This is only an availability probe, not a task dispatch. Verify the installed CLI version according to its install documentation before creating a run; all task invocations below use the session wrapper.

The skill does not contain `@cursor/sdk`, JavaScript/TypeScript runtime code, a package manifest, or an implementation fallback.

Installing the skill does not install this command. Obtain and install `cursor-delegate` from the independent CLI project's documented release or source-install flow, then verify the version before using the skill. This reference deliberately does not embed a machine-specific checkout path.

If the command is missing:

- Do not install dependencies in the skill directory.
- Do not translate the request into ad hoc SDK code.
- If the user explicitly asks to install from an existing `cursor-delegate` source checkout, run that project's documented local installer and verify `cursor-delegate --version`.
- Otherwise stop before dispatch and report that the independent CLI must be installed.

## Core Commands

The standalone CLI accepts direct calls, but this downstream skill must route every task dispatch through the standard-library session wrapper. The wrapper owns `--log-dir`; do not include that raw flag after `-- cursor-delegate`. Use a unique, single-level `--log-name` for every attempt.

Inspect-only:

```sh
python3 <skill-root>/scripts/delegation_session.py run \
  --session-file /exact/session/.cursor-delegate-skill-session.json \
  --log-name inspect-01 \
  -- cursor-delegate \
  --workspace /path/to/repo \
  --task-file /path/to/task.md \
  --inspect-only
```

Proposal mode is the default when neither `--inspect-only` nor `--apply` is present:

```sh
python3 <skill-root>/scripts/delegation_session.py run \
  --session-file /exact/session/.cursor-delegate-skill-session.json \
  --log-name proposal-01 \
  -- cursor-delegate \
  --workspace /path/to/repo \
  --task-file /path/to/task.md
```

Apply:

```sh
python3 <skill-root>/scripts/delegation_session.py run \
  --session-file /exact/session/.cursor-delegate-skill-session.json \
  --log-name apply-01 \
  -- cursor-delegate \
  --workspace /path/to/repo \
  --task-file /path/to/task.md \
  --apply
```

Validate the packet and print the prompt without importing the SDK, requesting authorization, creating logs, or dispatching:

```sh
python3 <skill-root>/scripts/delegation_session.py run \
  --session-file /exact/session/.cursor-delegate-skill-session.json \
  --log-name validate-01 \
  -- cursor-delegate \
  --workspace /path/to/repo \
  --task-file /path/to/task.md \
  --inspect-only \
  --dry-run
```

When the user explicitly requests durable audit logs, add `--retained-log-dir /absolute/caller-owned/log-base` between `--log-name` and `--`. Keep `--log-name` unique because the session still uses it for the lease and correlation record. A retained log path must be absolute, outside the private session, caller-owned, and not already exist; the wrapper creates it and excludes it from cleanup forever.

Relevant options:

```text
--planning-source auto|master-direct|non-cursor-planning-subagent|orchestrator-subagent|user-provided-plan|follow-up
--sdk-mode plan|agent
--model <logical-profile-or-sdk-id>
--model-param <key=value>                    repeatable
--user-authorized-model
--runtime local|cloud
--repo-url <url[#ref]>                       repeatable
--setting-source project|user|team|mdm|plugins|all  repeatable
--workspace-copy auto|always|never
--sandbox enabled|disabled
--log-dir <directory>
--resume-agent-id <agent-id>
--idempotency-key <value>
--delegation-owner <value>
--workstream-id <value>
--extra-instruction <text>                  repeatable
--auth-mode browser|fail
--api-key-env <environment-variable-name>
--no-open-dashboard
--dashboard-retention-seconds <0..300>
--dry-run
--help
--version
```

## Modes And Defaults

- Runtime: `local`.
- Inference: still hosted by Cursor; `local` means the agent loop and filesystem access run locally.
- Delegation mode: proposal unless `--inspect-only` or `--apply` is set.
- SDK conversation mode: `plan` for inspect/proposal and `agent` for apply unless `--sdk-mode` overrides it.
- Sandbox: enabled for local runs.
- Setting source: `project` only.
- Workspace copy: `auto`; local inspect/proposal runs use a permission-hardened read-only copy, while apply runs use the original workspace.
- Planning source: `auto`, which still requires exactly one recognized authority section.
- Model profile: `grok-4.5-high`.
- Log parent: `<workspace>/.agent/delegations` unless `--log-dir` is set.
- Dashboard launch: enabled for a normal live dispatch only after API-key and model preflight both succeed.
- Dashboard terminal retention: `0`; the packaged frontend closes when dispatch becomes terminal.

`--apply` and `--inspect-only` are mutually exclusive. `--workspace-copy always` is incompatible with apply mode. Workspace-copy flags do not apply to cloud runtime.

The log-parent default and raw `--log-dir` option describe standalone direct CLI use. This skill creates one private temporary session and always lets `delegation_session.py run` inject `--log-dir`: normally from a unique `--log-name` below `logsDir`, or from explicit `--retained-log-dir` for caller-owned audit evidence. Never pass raw `--log-dir` in a skill-managed trailing command.

## Model Contract

The logical default `grok-4.5-high` is not an SDK model id. During a live authorized dispatch, the CLI:

1. Calls `Cursor.models.list()`.
2. Resolves one canonical Grok 4.5 entry.
3. Resolves exactly one High preset that is not labeled or parameterized as Fast.
4. Sends the preset's complete catalog-defined `{ id, params }` selection.
5. Verifies each structured system-event or `RunResult.model` selection that the SDK reports.
6. Fails closed on a missing, ambiguous, malformed, Fast, or mismatched preset. Optional result evidence that is absent is recorded as `not_reported`, not fabricated as a successful observation.

The task packet must contain exactly one `## Cursor Model` section and exactly one of each field:

```markdown
## Cursor Model

- CLI profile: `grok-4.5-high`
- Model: `Grok 4.5 High`
- Model params: `catalog-resolved-high-non-fast-preset`
```

Use an explicit SDK id only when the user directly authorizes that Cursor model. Pass `--user-authorized-model` and `--override-reason`, and make the packet declare `CLI profile: explicit` with exactly matching model parameters.

## Authorization

The CLI reads `CURSOR_API_KEY` by default. Select another variable with `--api-key-env`; never pass the key itself as an argument.

- Every live, non-dry invocation supervises one isolated child process that binds `127.0.0.1:0` and starts only the packaged production Next.js build without opening a URL. The installed CLI does not run `next dev`, `next build`, npm, or another package manager. One frontend project serves `/authorize/[sessionId]` and `/dashboard/[dispatchId]` under separate capability-bound routes.
- `--auth-mode browser` (default): verify the environment key before dispatch. If it is missing or rejected, write `needs_authorization` and publish `authorization.local_url` plus the fixed `https://cursor.com/dashboard/api` as `authorization.dashboard_url` in mode-`0600` status. While authorization is unresolved, the CLI opens neither authorization link nor the local dashboard.
- `--auth-mode fail`: controls missing or rejected key handling. In that case it never enables or opens an authorization capability and exits `2` with final top-level `needs_authorization`, `authorization.method=fail`, and a closed page state. The unified frontend may start for the dispatch/dashboard lifecycle, but terminal cleanup remains owned by this CLI invocation. This stable machine-readable state is how a non-root workstream hands authorization ownership to root. If the environment key is valid and model preflight succeeds, fail mode proceeds normally and uses the same default dashboard auto-open policy as browser mode unless `--no-open-dashboard` was explicitly authorized by the current user.

The local page accepts a key through a password field, and the parent CLI verifies it with `Cursor.me({ apiKey })`. An invalid key remains on the page for correction. A verified submission closes the authorization capability in status and lets dispatch continue; the page reports verification and can be closed by the user. The same owned frontend process continues serving the dashboard until terminal cleanup. The CLI holds a submitted key only in memory for the invocation and never writes it to argv, URLs, child environment, client bundles or responses, prompts, status, metadata, raw events, journals, or files.

The child starts with a random one-time dashboard ticket that remains redeemable until the owned frontend exits. It receives a separate short-lived authorization ticket over IPC only while authorization is active. Ticket exchange creates an in-memory target-bound session with an HttpOnly, SameSite `strict` cookie, expiry, and CSRF token. Protected requests require the exact owned loopback `Host`; mutating requests additionally require the exact `Origin`, an atomically consumed and rotated CSRF token, bounded body, matching route target, and dispatch/session identifier. Responses are no-store and use restrictive CSP, frame, MIME, and referrer headers. While authorization is available, mode-`0600` `status.json.authorization` exposes only redacted lifecycle state (`waiting`, `submitted`, `verified`, `cancelled`, or `failed`), page state, the transient `authorization.local_url`, fixed `authorization.dashboard_url`, and timestamps. `authorization.local_url` is removed after verification, cancellation, timeout, or failure.

While authorization is waiting, the skill's upstream agent establishes a global scheduling barrier and pauses/interrupts every live collaboration child agent. Cursor SDK itself has no lossless pause API, so the CLI performs authorization preflight before `Agent.create()`/`send()` and never calls cancellation a pause.

Only the root/upstream agent owns a `--auth-mode browser` invocation. Workstream and other non-root agents use `--auth-mode fail`; if authorization is required, they wait for their CLI-owned frontend cleanup, then hand the same reviewed packet, status path, cleanup evidence, and process disposition to root. Root remains the cleanup owner throughout and starts browser mode only after recursively confirming the recorded descendant tree and its owned subprocesses are stopped or accounted for, then reads `authorization.local_url` and `authorization.dashboard_url` from status and presents both to the user at once. The CLI never launches an authorization URL. Once the API key is valid and model preflight succeeds, the same packaged app launches its local dashboard route by default before normal live dispatch.

## Dashboard And Control

`status.json.frontend` records startup state and, when ready, `frontend.dashboard_url`, the exact loopback origin, child PID, production build ID, default-close policy, and requested retention seconds. `frontend.dashboard_url` is a one-time capability entry. Show it only to the current user; do not copy it into a task packet, prompt, continuation record, durable report, or unrelated log. After ticket exchange, browser refreshes use the HttpOnly session rather than reusing the ticket.

A normal live invocation opens the dashboard automatically only after both API-key validation and model preflight succeed. `--no-open-dashboard` suppresses this browser action; under the delegation skill, pass it only when the current user explicitly asks not to open the dashboard. Do not infer opt-out from CI, headless execution, background work, parallel dispatch, or unavailable browser tooling. The flag does not stop the packaged frontend or change retention.

After an explicit opt-out, do not proactively hand the current user `frontend.dashboard_url`; provide it only if they later ask to access the dashboard. This preserves the opt-out while keeping the packaged frontend available for owned lifecycle and control plumbing.

Dashboard opening is best effort. An opener failure is reported and recorded but does not block Cursor dispatch; use the protected status entry as the current user's manual fallback. After an automatic open is confirmed, the one-time `frontend.dashboard_url` still recorded in status may already be spent and must not be handed off again as a fresh capability.

The dashboard receives only the sanitized schema-v2 journal and snapshot. The `/api/stream` route emits AI SDK v7 UI-message data parts for replay metadata, snapshots, and ordered run events. The middle region is an execution tape ordered by `RunEvent.sequence`: step/turn boundaries, requests, summaries, tasks/subagents, assistant/reasoning updates, and tool lifecycles remain in temporal context. Tools update their existing row by `callId`; top-level `stepId` and `modelCallId` preserve UI correlation. `requestId` remains available in journal/status audit data but is not promised as a rendered UI association. Current shadcn chat primitives and AI Elements render the timeline plus code, topology, usage, artifacts, and terminal evidence. Opt-in raw `events.ndjson` never enters the browser transport.

Streamed assistant and thinking text is append-only at the delta layer. Completion/conversation payloads may fill missing content, but empty, shorter, or stale terminal text cannot erase richer accumulated text. Completed thinking remains visible and expandable. This protects the UI projection; the journal still preserves the normalized events independently.

The SSE coordinator subscribes before replay so events arriving at the backlog/live boundary are not lost. The browser advances its cursor only after actual receipt and coalesces React publication once per animation frame. It retains a bounded 2,000-event execution window. When local trimming or a server ring rollover creates a gap, the UI shows a sequence watermark and restores aggregate assistant/reasoning/tool state from the authoritative snapshot. Do not describe this as an unlimited historical timeline: events older than the browser/server window are not reconstructed from `stream.ndjson`, and snapshot text remains bounded.

Agent control capability is explicit:

- `independent`: the CLI retains an active top-level Cursor `Run`; Stop may call the supported SDK cancellation capability.
- `parent-only`: the item is an internal task/Agent-tool descendant observed inside its parent run. It is visible but cannot be stopped independently; stop the owning parent.
- `none`: the run is terminal, unsupported, or has no retained control handle; no Stop action is valid.

Per-agent Stop is dispatch-bound, correlated, serialized, and idempotent. Success means the SDK cancellation completed or terminal evidence won the race; submitting a request is not success.

Stop All closes dispatch admission before queued control work begins, cancels independent active runs, re-lists agents through a bounded drain, and returns per-agent outcomes. Report `partially-failed` whenever an active, unsupported, timed-out, or failed agent remains. Stop controls never authorize a retry, replacement dispatch, broader task, commit, push, deployment, or destructive action.

The frontend closes at terminal by default. The upstream agent that invoked this skill may pass `--dashboard-retention-seconds N` only for a recorded exceptional review need, where `1 <= N <= 300`. The CLI stays attached and remains process owner during retention, then closes the child, listener, and port. Never delegate this lifecycle choice to Cursor or a workstream, never use retention by habit, and never detach the frontend. Parent disconnect, startup failure, timeout, SIGINT, and SIGTERM also trigger owned cleanup.

## Workspace Safety

Local apply mode requires a Git workspace by default and refuses existing changes, except the current untracked task packet and `.agent/delegations/` logs. That exception exists for direct CLI compatibility; a skill-managed run keeps both outside the workspace. Use `--allow-non-git` or `--allow-dirty` only with a reviewed `--override-reason`.

Read-only copies exclude common repository/runtime output such as `.git`, `.agent`, `node_modules`, virtual environments, caches, `.next`, `dist`, and `build`. The CLI refuses symlinks that can escape the copy and removes the copy on normal exit, errors, authorization failure, and handled signals.

Treat permission hardening as defense in depth, not a security boundary. Keep the SDK sandbox enabled.

## Cloud Runtime

Use cloud runtime only when repository access is already configured for the Cursor account or team:

```sh
python3 <skill-root>/scripts/delegation_session.py run \
  --session-file /exact/session/.cursor-delegate-skill-session.json \
  --log-name cloud-01 \
  -- cursor-delegate \
  --runtime cloud \
  --repo-url 'https://example.com/org/repo.git#main' \
  --task-file /path/to/task.md
```

Cloud-only controls are `--auto-create-pr`, `--work-on-current-branch`, and `--skip-reviewer-request`. Each is a safety override and requires `--override-reason`. Apply mode does not imply PR creation.

## Logs And Resume

Every non-dry run writes:

- `status.json`: mode-`0600` rolling compatibility status; ordinary fields are redacted, an open authorization flow temporarily adds `authorization.local_url`, a ready frontend records its local lease/capability fields, and `dashboard_auto_open` records `waiting_for_authorization`, `disabled`, `launch_requested`, or `failed` with safe timestamps/failure evidence.
- `metadata.json`: configuration, safety overrides, hashes, model evidence, dashboard-open audit, and result metadata.
- `prompt.txt`: exact downstream prompt; treat it as sensitive task context.
- `stream.ndjson`: sanitized, monotonically sequenced schema-v2 events used for audit/replay.
- `snapshot.v2.json`: latest schema-v2 dispatch/agent/frontend projection.
- `events.ndjson`: optional raw events only when explicitly enabled.
- `<log-base>/latest`: path of the newest run directory.

Use a separate wrapper `--log-name` for every parallel workstream rather than coordinating through one shared `latest` file. Use `--retained-log-dir` only for an explicitly declared caller-owned durable audit base.

These files are durable by default for a direct CLI caller. Under this skill, the invoking root instead creates an explicitly owned private session and every dispatch runs through the wrapper's foreground lease. A normal `--log-name` maps below the session and survives through review/resume/follow-up before accepted or reconciled-abandonment cleanup. If the user requests retained audit evidence, pass a separate caller-owned base with `--retained-log-dir`; it is never included in cleanup. `latest` is a convenience pointer only; neither the skill nor its helper follows its contents to choose deletion targets.

Resume with `--resume-agent-id <id>`. The SDK derives runtime from the id (`bc-` means cloud; other ids are local), and the CLI refuses conflicting runtime-only options. A pure follow-up does not resend the CLI's default model or mode because both are sticky conversation state; only explicit, reviewed overrides may change them. Local agent state is workspace-scoped: an agent created in a transient read-only copy is not resumable after that copy is removed. Preserve the copy explicitly before the first run, resume from the same path, or start a new inspect/proposal agent.

Pure-resume metadata uses SDK mode `existing`, model-verification state `sticky_resume_not_overridden`, and scope `resume_sticky`; it does not claim a newly resolved `model_selection`.

The SDK does not persist inline MCP configuration across `Agent.resume()`. This CLI intentionally exposes no inline MCP flag, so tools required after resume must live in persistent Cursor project/team/plugin configuration that the resumed runtime loads; do not assume a task packet makes MCP state sticky.

## Skill-Managed Artifact Lifecycle

The CLI deliberately does not delete `--task-file` or `--log-dir`: both may be valuable caller-owned inputs/evidence, and only the caller knows their lifecycle. The downstream skill supplies that missing ownership context through `references/owned-artifact-cleanup.md` and its standard-library `scripts/delegation_session.py` helper.

- Start the private session before copying a packet.
- Put all copied packets below its `packets` directory and run every invocation with `delegation_session.py run --session-file ... --log-name ... -- cursor-delegate ...`.
- Let the wrapper inject the effective `--log-dir` and hold a lease until the foreground child has exited and been reconciled; never pass raw `--log-dir` in the trailing command.
- For durable logs, pass an absolute caller-owned `--retained-log-dir` before `--`; never delete that path during session cleanup.
- Keep the exact marker through authorization barriers, retry/resume, bounded follow-up, and upstream review.
- Wait for the CLI foreground process and packaged frontend retention to end before cleanup.
- Preserve bounded hashes/identifiers/verdict evidence, then let the helper validate allowlisted files, status states, frontend PID, symlinks, and containment before unlinking files and empty directories.
- Never clean a user-provided packet, retained audit directory, repository change, branch/worktree, or workspace copy kept by override.

## Safety Overrides

The following require a non-empty `--override-reason`:

- `--allow-missing-authority`
- `--allow-placeholders`
- `--allow-dirty`
- `--allow-non-git`
- `--sandbox disabled`
- `--workspace-copy never` for local non-apply runs
- `--include-raw-events`
- `--keep-workspace-copy`
- `--auto-create-pr`
- `--work-on-current-branch`
- `--skip-reviewer-request`
- `--sdk-mode agent` outside apply mode
- any setting source other than `project`
- an explicitly user-authorized non-default model

Unsafe flags never bypass the requirement for upstream review. Store only a sanitized reason in metadata.

## Exit Behavior

- Exit `0`: dry-run validation succeeded, or a live run finished without a model mismatch; optional model evidence may be `not_reported`.
- Exit `1`: Pastel/Zod parser or schema failure (including unknown, missing, or invalid option values), SDK/runtime failure, non-finished result, or failed model verification.
- Exit `2`: a parsed command reached a refused packet/override, loopback authorization was cancelled/failed/timed out, `--auth-mode fail` found missing authorization, or another user-correctable domain preflight failure.
- Exit `130` / `143`: handled `SIGINT` / `SIGTERM`; the CLI checks whether cancellation is supported, records cancellation and client-disposal outcomes, and removes transient workspace copies. It records `cancelled` only when `run.cancel()` confirms; unsupported, timed-out, failed, or not-yet-active cancellation is recorded as `interrupted` rather than claiming the run stopped.
- Exit `129` from the skill wrapper: on platforms with `SIGHUP`, the wrapper forwards it, waits for the child, and reports `128 + SIGHUP`. Treat any missing or interrupted CLI evidence conservatively and reconcile the lease/run before cleanup; this does not imply that the CLI completed SDK cancellation.

Do not infer acceptance from exit `0`; inspect the diff, status, result, verification evidence, and task-packet scope.

## Project Maintenance

The independent `cursor-delegate` project is the canonical owner of SDK imports, CLI parsing, model resolution, the packaged unified Next.js authorization/dashboard frontend, protected capability handoff, AI SDK v7 stream adapter, shadcn/AI Elements integration, workspace copying, event sanitization, control coordination, run lifecycle, install scripts, and tests. This skill must not copy that runtime back into `scripts/` or add a package manifest. Its standard-library session helper owns only the skill's external task-packet/log/foreground-lease lifecycle and must remain independent of `@cursor/sdk`.

When CLI flags, defaults, status fields, install flow, or safety semantics change, update this reference plus the root repository README and website catalog in the same change. Do not record a machine-specific source path in the skill.
