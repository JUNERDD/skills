# Live Cursor SDK Monitoring

Read this reference when the upstream agent or a workstream orchestrator needs in-flight visibility into a Cursor SDK run.

## Artifacts

`cursor-delegate` writes one run directory under `<workspace>/.agent/delegations/<timestamp>` by default for standalone direct CLI use. A skill-managed invocation instead creates the private session described in `owned-artifact-cleanup.md` and runs `delegation_session.py run --session-file ... --log-name <unique> -- cursor-delegate ...`. The wrapper injects a log base below the session and holds a foreground lease; the trailing command must not pass raw `--log-dir`.

- `latest`: file in the log parent that contains the newest run directory path.
- `status.json`: mode-`0600` rolling status for parent-agent monitoring; fields are redacted except for the explicitly transient authorization capability described below.
- `metadata.json`: run configuration, safety overrides, SDK runtime/model summary, and result metadata.
- `prompt.txt`: exact prompt sent to Cursor SDK. Treat it as sensitive task context.
- `stream.ndjson`: mode-`0600`, sanitized, monotonically sequenced schema-v2 events used for dashboard audit and replay.
- `snapshot.v2.json`: latest schema-v2 dispatch, frontend, topology, control-capability, usage, artifact, and terminal projection.
- `events.ndjson`: raw SDK stream events, written only with `--include-raw-events` and `--override-reason`.

Prefer `status.json` for normal parent updates and the packaged dashboard for interactive observation/control. Raw SDK events can include file contents, internal subagent prompts, or proposed write text in tool results; they never enter the browser transport.

Keep the session logs until upstream has reviewed the diff, verification, model/terminal evidence, and every bounded follow-up. They are lifecycle evidence, not an acceptance signal. After an accepted or explicitly reconciled/user-authorized abandonment gate, the root cleanup owner removes them with the session helper. For durable audit evidence, the wrapper receives `--retained-log-dir /absolute/caller-owned/log-base` before `--`; that external directory is never cleaned.

## Monitor Workflow

1. Run the CLI through the session wrapper with the exact marker and a unique `--log-name`. Low-latency `onDelta`/`onStep` callbacks and the single consumed SDK `run.stream()` feed separate compatibility status and normalized dashboard observations without consuming the stream twice.
2. Capture the printed `Live status:` path. If the caller only knows the effective log base, read `<log-base>/latest`.
3. Poll `status.json` for low-noise progress: state, runtime, SDK mode, model, agent id, run id, request id, authorization state, last assistant text, current tool call, active/recent internal subagents, recent tool calls, usage, and result.
4. For a normal live dispatch, let the CLI open `frontend.dashboard_url` automatically only after the API key and model preflight both succeed. Use `--no-open-dashboard` solely when the current user explicitly requested no opening; never infer opt-out from CI, headless execution, background work, parallelism, or unavailable browser tooling. If opening fails, treat it as non-fatal and offer the protected status URL only to the current user. After an explicit opt-out, do not proactively hand off the URL; provide it only if the current user later asks for dashboard access. It is a one-time local capability: after a confirmed automatic or manual exchange, assume the original URL is spent, never present it again as fresh, and never copy it into durable output or use it as a health check.
5. If a non-root invocation becomes `needs_authorization`, it must be using `--auth-mode fail`; wait for that invocation's owned frontend cleanup and return control without an authorization capability. Establish the root-owned global barrier from `cursor-sdk-authorization.md`: stop new scheduling, recursively snapshot and interrupt the full descendant tree, re-enumerate to confirm nothing remains running, and only then let root start the loopback browser-authorization invocation. Do not keep other workstreams or owned subprocesses running while merely polling the blocked run.
6. Use raw events only when debugging event-level behavior is worth the noise and sensitivity risk.
7. Treat live status and dashboard rendering as observation, not approval. Cursor still must obey packet stop conditions, CLI failures, explicit Stop outcomes, and upstream/user scope authority.

## Status Semantics

Expected `status.json` fields:

- `state`: `starting`, `running`, `needs_input`, `needs_authorization`, `succeeded`, `failed`, `cancelled`, `interrupted`, or another terminal SDK run status. `cancelled` means SDK cancellation was confirmed; `interrupted` means the client stopped but run cancellation was not confirmed.
- `implementation`: `@cursor/sdk`.
- `runtime`: `local` or `cloud`.
- `sdk_mode`: SDK conversation mode, usually `plan` for inspect/proposal and `agent` for apply.
- `workspace_copy_cleanup`: whether a read-only copy is removed on process exit or intentionally kept by override.
- `model`: CLI model label such as `Grok 4.5 High`.
- `model_selection`: catalog-resolved requested SDK `{ id, params }` after authorization. For the default profile, it is the complete High, non-Fast preset returned by the catalog. A pure resume leaves this unset because it preserves the conversation's sticky model instead of creating a new requested selection.
- `system_model_selection`: structured model selection reported by the SDK system event; this is the runtime corroboration used by the CLI.
- `result.model`: completed run's model value. In the current SDK this mirrors the requested selection, so it is a consistency check rather than independent runtime proof.
- `result.model_verification`: `matched`, `mismatched`, `not_reported`, or `sticky_resume_not_overridden`. For a new selection, each structured system-event or result selection that is present must exactly match the catalog selection. The SDK types make both fields optional, so their absence is recorded without converting an otherwise finished run into a model mismatch. A pure resume uses `sticky_resume_not_overridden` because the CLI deliberately supplies no new model baseline.
- `result.model_verification_scope`: `exact` for a new catalog preset or explicit model selection, or `resume_sticky` for a pure resume.
- `workstream_id`, `delegation_owner`: sanitized hierarchical correlation fields when supplied.
- `task_packet_sha256`, `idempotency_key_sha256`: stable hashes for correlating packets and retries without logging raw idempotency keys.
- `sandbox_enabled`: local runtime sandbox state.
- `agent_id`, `run_id`, `request_id`: safe run identifiers for correlation.
- `current_tool_call`: sanitized active tool call, or `null`.
- `recent_tool_calls`: bounded list of recent tool events with safe args and result metadata.
- `active_subagents`: sanitized active Cursor internal task/subagent entries keyed by call id.
- `recent_subagents`: bounded list of completed or failed internal subagent calls with description, requested model, timing, and safe result metadata. The requested model is not proof of exact internal High parameters.
- `frontend`: packaged frontend state. When ready it includes the one-time `frontend.dashboard_url`, exact loopback origin, owned child PID, production build ID, `frontend.default_close`, and `frontend.retention_seconds`. Authorization is opened only on demand and its transient capability appears exclusively as `authorization.local_url`. A URL recorded after shutdown may be stale, and a URL retained after confirmed auto-open may already be spent, but it remains sensitive local capability data.
- `dashboard_auto_open`: browser-launch audit. `enabled` records the CLI choice; `state` progresses from `waiting_for_authorization` or `disabled` to `launch_requested` or `failed`, with bounded attempt/request timestamps and a safe failure category. A dry run reports `skipped_dry_run` in its console summary instead of starting the frontend.
- `cancellation`, `client_disposal`: signal-handling outcomes. Disposing the SDK client or stream is not evidence that a cloud run was cancelled.
- `last_assistant_text`: latest assistant text, truncated.
- `last_usage` or `result.usage`: token usage when the SDK reports it.
- `authorization`: authorization state. Expect `authorization.state` (`waiting`, `submitted`, `verified`, `cancelled`, or `failed`), `authorization.method` (`browser` or `fail`), `authorization.page_state` (`open` or `closed`), `authorization.local_url` while authorization is available, fixed `authorization.dashboard_url`, and request/resolution timestamps. It always omits the submitted key and removes `authorization.local_url` after verification, cancellation, timeout, or failure.
- `result`: result summary, truncated, after `run.wait()` completes.
- `events_seen`: parsed SDK event count.

The status file intentionally omits full file contents, internal subagent prompts, write payloads, and long assistant output.

Authorization transitions:

- Non-root fail-only handoff: final top-level `needs_authorization`, `authorization.method=fail`, and `page_state=closed`; the process exits `2` without enabling an authorization capability and closes its owned packaged frontend so root can establish the barrier.
- Root loopback wait: top-level `needs_authorization`, `authorization.method=browser`, `authorization.state=waiting`, `authorization.page_state=open`, and both `authorization.local_url` and `authorization.dashboard_url` present. The root agent reads and presents both links in one user handoff; neither authorization link nor the local dashboard is opened automatically.
- Invalid submission: briefly `submitted`, then back to `waiting`; the page and global barrier remain open.
- Verified submission: `authorization.state=verified`, `page_state=closed`, and `authorization.local_url` absent. The CLI then completes model preflight and, only after both preflights succeed, opens the local dashboard by default before top-level state proceeds through normal live dispatch. The authorization page reports verification and can be closed; the same child remains as the live dashboard. Resume only agents recorded by the barrier and only if the invocation did not immediately fail closed while reconciling an ambiguous already-started dispatch.
- Decline/cancellation, timeout, owning CLI stop, or packaged-frontend failure: top-level `failed`, exit `2`, `authorization.state=cancelled` or `failed`, and `page_state=closed`. Do not resume paused agents.

## Dashboard Stream And Control

The packaged Next.js app exchanges the one-time access ticket for a target-bound in-memory session with an HttpOnly, SameSite `strict` cookie and CSRF token. It requires the exact owned loopback `Host`; control and authorization POSTs additionally require the exact `Origin`, matching CSRF header, bounded body, and matching dispatch/session target.

`/api/stream` uses AI SDK v7 UI-message data parts for replay metadata, `RunSnapshot`, and ordered `RunEvent` values. The journal normalizes all supported Cursor SDK callback/stream families, including assistant/thinking deltas, step/turn boundaries, request observation, tool lifecycle/update, task/subagent lifecycle, summaries, shell output, usage deltas, model, artifacts, and terminal state. The middle execution tape renders the user-relevant temporal milestones rather than claiming every normalized event is a visible card.

The execution tape is ordered by `RunEvent.sequence`. `stepId`, `callId`, and `modelCallId` correlate the UI projection; none substitutes for sequence ordering. `requestId` remains a journal/status audit field and is not promised as a rendered UI association. Tool entries update in place by `callId`; step/turn/request/summary/task events remain visible around them so the user can reconstruct when work happened.

Assistant and thinking deltas append to accumulated text. Completion or conversation text may fill missing portions, but empty, shorter, or stale payloads cannot erase richer streamed content. Completed thinking remains visible and expandable. Segment text is bounded to 500,000 characters, so describe this as non-regressing within the retained projection rather than infinite transcript storage.

The server subscribes the live listener before replaying backlog, closing the replay/live race. A reconnect sends its last sequence, and the browser advances that cursor only after actual receipt. React publication is coalesced by animation frame so event ingestion stays loss-auditable without forcing one render per delta. The browser and server each retain a bounded 2,000-event window. If the server ring cannot satisfy the cursor or local trimming exposes a sequence gap, the UI displays a watermark and restores aggregate assistant/reasoning/tool state from the latest authoritative snapshot instead of silently claiming a gap-free full timeline. Events older than the window are not reconstructed from `stream.ndjson` in the browser. Slow or disconnected browsers never backpressure SDK ingestion.

Dashboard agent rows expose explicit control capability:

- `independent`: active top-level run retained by the CLI; per-agent Stop is allowed.
- `parent-only`: internal task/Agent-tool descendant; stop the owning parent to cancel its subtree.
- `none`: terminal, unsupported, or no retained run; no Stop action.

Stop is successful only after correlated SDK cancellation or terminal evidence. Stop All closes dispatch admission first, cancels independent active runs, rechecks through a bounded drain, and returns per-agent outcomes. Record `partially-failed` and every remaining active/unsupported/failed outcome instead of claiming global success.

Dashboard opening is best effort and independent of retention. Report an opener failure without blocking Cursor dispatch, then use the protected one-time status entry as the manual fallback. `--no-open-dashboard` does not stop the packaged frontend and does not change terminal cleanup.

At dispatch terminal, the packaged frontend closes immediately by default. `--dashboard-retention-seconds 1..300` is permitted only when the upstream agent invoking this skill recorded an exceptional review reason. The CLI remains attached and owns cleanup during retention; never detach it or delegate this choice to Cursor/workstreams.

Do not run the skill's session cleanup until the foreground wrapper/CLI has returned, its lease has been released, and any dashboard retention interval has ended. A live or unresolved lease, live frontend PID, active status, authorization wait, pending follow-up, or unreconciled interruption keeps the session in `retained` state. An external path supplied with `--retained-log-dir` is never a cleanup target.

## Limits

- SDK streaming exposes normalized events, not private reasoning beyond SDK-provided thinking summaries.
- Tool call `args` and `result` payloads are internal and may change; consumers must parse defensively and ignore unknown fields.
- Cursor internal task/Agent-tool calls expose a string model request in `@cursor/sdk` 1.0.23, not a structured parameter selection. Report exact High as unverified unless the SDK later supplies independent structured evidence.
- Cursor SDK 1.0.23 does not expose a pause operation. The global authorization barrier pauses/interrupts outer collaboration agents before Cursor dispatch; never infer a lossless Cursor pause from client disposal or cancellation.
- Local proposal/inspect runs use a permission-hardened copy by default and refuse escaping symlinks. Treat this as defense in depth, keep the SDK sandbox enabled, and still inspect reports and diffs.
- Cloud agents persist state server-side; local agents persist through the SDK's local store. Capture `agent_id` if continuation is required.
- The `latest` pointer is convenient for one run. For parallel skill-managed runs, assign a dedicated wrapper `--log-name` per workstream or use each printed `status.json` path instead of relying on one shared `latest`.
- Direct CLI logs are durable by default. Skill-owned logs become temporary only because the root explicitly placed them in a private session and accepted responsibility for the terminal cleanup gate. A path passed with `--retained-log-dir` is caller-owned and never cleaned.
