# Cursor SDK Authorization

Use this reference whenever a Cursor SDK dispatch has no valid API key, receives an authentication error, or needs to prepare credentials for an automated run.

## Authorization Order

1. Prefer `CURSOR_API_KEY` in the local process environment.
2. For non-default environments, use `--api-key-env <ENV_NAME>` and keep the secret in that environment variable.
3. Every live invocation supervises one isolated child that starts only the packaged production Next.js build on `127.0.0.1:0` without opening a URL. With the default `--auth-mode browser`, a missing or rejected key makes the CLI write `needs_authorization` and publish a transient `authorization.local_url` capability plus the fixed [Cursor API Keys](https://cursor.com/dashboard/api) `authorization.dashboard_url` in mode-`0600` `status.json`. While the key is unresolved, it opens neither authorization link nor the separate local dashboard. No Cursor `Agent.create()` or `send()` may begin before this preflight succeeds.
4. The user submits the key only to the local page. The parent CLI verifies it with `Cursor.me({ apiKey })`, keeps an invalid submission on the page, and holds a verified key only in process memory for the current invocation.
5. Use `--auth-mode fail` for CI, non-root workstreams, or other non-interactive automation. It never enables an authorization capability and fails when the selected environment variable is missing or rejected. Its unified frontend may start for the dispatch/dashboard lifecycle, but the invocation owns and closes it at terminal.

## Global Authorization Barrier

`needs_authorization` is a global scheduling barrier for every agent participating in the current delegation, not permission to let unrelated workstreams continue.

1. Stop creating support agents, planning agents, workstream agents, follow-ups, and new CLI dispatches.
2. Create a unique barrier generation and recursively enumerate the complete live descendant tree, including agents without workstream ledger rows. Record each canonical task identifier, workstream if any, prior state, owned subprocess/session, and a concise continuation point without secrets.
3. Record the private delegation `sessionFile`, packet path/hash, log base/status path, and cleanup disposition for every affected workstream. Root remains the cleanup owner throughout; before interruption, a non-root agent hands root its cleanup evidence and live-process disposition, never ownership. Authorization waiting is not a cleanup state; no packet or log may be removed or recreated merely because its child invocation exited with `needs_authorization`.
4. Ask each owner to stop or hand off the disposition of any live subprocess/session, then pause or interrupt every recorded descendant with the host's actual orchestration primitive. Re-enumerate the tree and process ownership. If anything remains running or cannot be accounted for, set the barrier to `failed`; do not claim a safe wait.
5. A non-root agent must invoke the session wrapper with a unique `--log-name` and trailing `cursor-delegate ... --auth-mode fail`. It returns the authorization need to root without creating an authorization capability, waits for its CLI-owned frontend cleanup, and then becomes safe to interrupt.
6. After all descendants are confirmed stopped, keep the root active as the sole authorization and artifact-cleanup owner. The root reruns the same reviewed packet from the same private session with trailing `cursor-delegate ... --auth-mode browser`, using a new unique wrapper `--log-name`. It reads `authorization.local_url` and `authorization.dashboard_url` from status and presents both links and their distinct purposes in the same user handoff. Neither the CLI nor the agent opens those authorization links automatically. The root waits for the user/CLI result without starting other work.
7. After the CLI reports `authorization.state=verified`, let it complete model preflight. Only when both preflights succeed does a normal live invocation open the local dashboard automatically. Pass `--no-open-dashboard` only when the current user explicitly asked not to open it; do not infer that request from CI, headless execution, background work, parallel dispatch, or unavailable browser tooling. Treat opener failure as non-fatal, report it, and use the protected status URL as a manual fallback. After an explicit opt-out, do not proactively hand off that URL; provide it only if the current user later asks to access the dashboard. Then resume only records from the same barrier generation whose disposition is still `pending` after top-level state proceeds to `starting`/`running` rather than a fail-closed reconciliation error. Use the host's continuation/follow-up primitive on the same canonical agent, never a replacement agent, then mark that record `resumed` so a repeated observer cannot resume it again.
8. If the user declines authorization, the page times out, the packaged frontend fails, the key cannot be verified, the owning CLI is stopped, or the pause could not be confirmed, do not resume implementation. Mark every pending record `not_resumed_<reason>`, move affected workstreams to `blocked`, retain the private session for reconciliation, and report the authorization and cleanup disposition.

Cursor SDK 1.0.23 has run cancellation but no native pause/resume operation. The CLI therefore completes loopback authorization before creating or sending a Cursor run. The outer agent barrier above is owned by this skill and its upstream orchestrator; never describe SDK cancellation, child interruption, or client disposal as a lossless pause. If the host exposes interruption rather than pause, record `interrupted_for_authorization` and recover it with the same canonical task's continuation primitive.

## User Authorization Request

When authorization is missing, ask for authorization without collecting the secret in chat:

```markdown
Cursor SDK needs authorization before I can delegate this task. I paused the active delegation agents. The CLI does not open either authorization link automatically; please use both links below:

- Local cursor-delegate authorization page (paste the key here only): <authorization.local_url from status.json>
- Cursor API Keys (create a key here if needed):

https://cursor.com/dashboard/api

If you do not have a key, create one on Cursor API Keys. Paste it only into the local authorization page, not into chat. The CLI will verify it and release the delegation barrier. The page will report verification and can then be closed; the same owned local frontend continues as the live dashboard until the dispatch closes it. If you do not want to authorize, tell me to stop the owning CLI instead of pasting a key.
```

Do not use a Team Admin API key; Cursor SDK 1.0.23 supports user and service-account API keys, not Team Admin API keys.

For a local loopback-authorized run:

```bash
python3 <skill-root>/scripts/delegation_session.py run \
  --session-file /path/from-private-session/.cursor-delegate-skill-session.json \
  --log-name root-auth-01 \
  -- cursor-delegate \
  --workspace /path/to/repo \
  --task-file /path/from-private-session/packets/task.md \
  --auth-mode browser
```

If the user explicitly requires durable authorization/run audit logs, add `--retained-log-dir /absolute/caller-owned/root-auth-01` before `--`. The absolute caller-owned path must be outside the session and not already exist; the wrapper creates it and cleanup never deletes it. Do not pass `--log-dir` in the trailing command.

The CLI writes both `authorization.local_url` and `authorization.dashboard_url` to mode-`0600` status once the packaged listener is ready. The root agent must read and present both in the same handoff: the local page is only for submitting the key, while `https://cursor.com/dashboard/api` is where a user without a key creates one. The CLI and agent do not open either authorization URL automatically. Treat `authorization.local_url` as a short-lived capability, show it only to the current user, and do not copy it into task packets, continuation records, durable reports, or unrelated logs; the CLI removes it from status after verification, decline/cancellation, timeout, or failure. The default local-dashboard auto-open happens later, only after successful key and model preflights.

## Unified Loopback Frontend Lifecycle

- The CLI starts only its packaged Next.js production artifact, never frontend source, `next dev`, `next build`, npm, or another package manager. One child, ephemeral port, instance ID, event store, and IPC channel belong to one dispatch.
- The same app serves `/authorize/[sessionId]` and `/dashboard/[dispatchId]`. Its dashboard ticket remains redeemable for the owned frontend lifetime; a separate short-lived authorization ticket exists only while authorization is active. Each is random and one-time, and exchanges for a target-bound in-memory session with an HttpOnly, SameSite `strict` cookie, expiry, and CSRF token.
- `authorization.local_url` and `frontend.dashboard_url` are separate one-time entries into the same child. Hand off the authorization capability manually while waiting. After key and model preflight, let the CLI open the dashboard entry by default. Use a manual dashboard handoff after an opener failure, or after an explicit opt-out only if the current user later asks for dashboard access. Never reproduce either local capability in durable output.
- Protected requests require the exact owned loopback `Host`; mutating requests also require the exact `Origin`, an atomically consumed and rotated CSRF token, bounded body, matching target, and matching dispatch/session ID. No API key or parent control credential is embedded in a URL or client bundle.
- The authorization route carries the user's transient key input to the parent CLI through request-correlated in-memory IPC. It never publishes the key to the dashboard stream, journal, status, or metadata.
- Invalid submissions stay on the page and return to `waiting`; they do not release the barrier.
- A verified submission removes the authorization capability from status and renders a verified page that the user can close. After model preflight also succeeds, the CLI opens the local dashboard by default. The local listener stays alive because the same process serves the dispatch dashboard.
- The dashboard stream uses AI SDK v7 typed data parts and current shadcn/AI Elements to render only sanitized schema-v2 events. It can Stop an independently retained run or issue Stop All; internal task subagents are `parent-only` and stop with their parent.
- Terminal dispatch closes the frontend immediately by default. Only the upstream agent invoking this skill may request `--dashboard-retention-seconds 1..300` for a recorded exceptional review reason; the CLI remains attached, waits at most that interval, and then closes the child/listener/port.
- Dashboard launch and retention are independent. `--no-open-dashboard` changes only the post-preflight browser action; use it solely for an explicit current-user request, and keep terminal-close-default cleanup.
- Timeout, CLI signal, parent disconnect, startup failure, or child failure must also close the owned listener and child process. Never detach the frontend.
- The external Cursor API Keys page is opened only by the user and is not controlled by the CLI; never terminate the user's browser application to close it.

## Invalid Key Handling

If the SDK reports an invalid, expired, unauthorized, or disabled key:

1. Mark the invocation `needs_authorization` and establish the global authorization barrier before any retry.
2. Surface any `helpUrl` emitted by the SDK.
3. Ask the user to create or rotate a user API key, or use a service account key for team automation.
4. Confirm the selected key has permission for the runtime: local SDK run, cloud agent creation, connected repository access, and any requested team resources.
5. Retry only after the parent CLI verifies the submitted key. Never blindly recreate or resend an already identified Cursor run.

## Secret Handling Rules

- Never place a Cursor API key in a task packet, prompt, raw event log, issue comment, commit, PR body, shell history snippet, or chat transcript.
- Do not pass API keys through command-line argv; process listings and logs can expose argv. Use an environment variable or the packaged Next.js authorization route.
- Never put the key in the local authorization URL, dashboard URL, IPC diagnostics, status/metadata, agent continuation records, or browser history.
- Do not write API keys into `.env` files unless the user explicitly requests that storage and understands the repository/secret-management implications.
- Keep raw SDK events disabled unless debugging requires them. Raw events may include prompts, file excerpts, or tool payloads.
- Redact `authorization`, `api_key`, `token`, `secret`, `cookie`, `password`, `credential`, and private-key-like fields in status summaries.

## Automation Pattern

For CI or non-interactive automation:

```bash
CURSOR_API_KEY="$CURSOR_API_KEY" python3 <skill-root>/scripts/delegation_session.py run \
  --session-file /path/from-private-session/.cursor-delegate-skill-session.json \
  --log-name ci-01 \
  -- cursor-delegate \
  --workspace "$GITHUB_WORKSPACE" \
  --task-file /path/from-private-session/packets/ci-task.md \
  --apply \
  --auth-mode fail
```

Use a secret manager or CI secret store to inject `CURSOR_API_KEY`. Prefer a service account key for team-owned automation and a user key for user-owned local runs. If CI intentionally uses a packet committed or provisioned in the repository instead, classify it as caller-owned and never delete it; keep any cleanup limited to the separately marker-owned temporary session.
