# Live Cursor SDK Monitoring

Read this reference when the upstream agent or a workstream orchestrator needs in-flight visibility into a Cursor SDK run.

## Artifacts

`scripts/cursor_delegate.mjs` writes one run directory under `<workspace>/.agent/delegations/<timestamp>` by default. Use `--log-dir` to choose a stable parent directory.

- `latest`: file in the log parent that contains the newest run directory path.
- `status.json`: sanitized rolling status for parent-agent monitoring.
- `metadata.json`: run configuration, safety overrides, SDK runtime/model summary, and result metadata.
- `prompt.txt`: exact prompt sent to Cursor SDK. Treat it as sensitive task context.
- `events.ndjson`: raw SDK stream events, written only with `--include-raw-events` and `--override-reason`.

Prefer `status.json` for normal parent updates. Raw SDK events can include file contents, internal subagent prompts, or proposed write text in tool results.

## Monitor Workflow

1. Run the wrapper. It streams via SDK `run.stream()` when the runtime supports streaming.
2. Capture the printed `Live status:` path. If the caller only knows the log parent, read `<log-dir>/latest`.
3. Poll `status.json` for low-noise progress: state, runtime, SDK mode, model, agent id, run id, request id, authorization state, last assistant text, current tool call, active/recent internal subagents, recent tool calls, usage, and result.
4. Use raw events only when debugging event-level behavior is worth the noise and sensitivity risk.
5. Treat live status as observation, not approval. Cursor still must obey packet stop conditions, wrapper failures, or explicit upstream/user intervention outside the running process.

## Status Semantics

Expected `status.json` fields:

- `state`: `starting`, `running`, `needs_input`, `needs_authorization`, `succeeded`, `failed`, `cancelled`, or another terminal SDK run status.
- `implementation`: `@cursor/sdk`.
- `runtime`: `local` or `cloud`.
- `sdk_mode`: SDK conversation mode, usually `plan` for inspect/proposal and `agent` for apply.
- `workspace_copy_cleanup`: whether a read-only copy is removed on process exit or intentionally kept by override.
- `model`: wrapper model label such as `Grok 4.5 High`.
- `model_selection`: catalog-resolved requested SDK `{ id, params }` after authorization. For the default profile, it contains the High effort parameter and omits speed so Cursor applies its current default.
- `system_model_selection`: structured model selection reported by the SDK system event; this is the runtime corroboration used by the wrapper.
- `result.model`: completed run's model value. In the current SDK this mirrors the requested selection, so it is a consistency check rather than independent runtime proof.
- `result.model_verification`: `matched`, `mismatched`, or `unavailable`; a finished run is marked failed unless both the structured system event and result value contain the requested model id and High parameter. Only catalog-supported speed parameters and values may appear in addition for the default profile; explicit overrides remain exact.
- `model_allowed_observed_speed_params`: catalog-supported speed parameters and values that Cursor may report after the wrapper omitted speed. Unknown parameters, extra effort parameters, and unsupported values remain mismatches.
- `result.model_verification_scope`: `requested_high_with_catalog_speed_defaults` for the default profile or `exact` for explicit model overrides.
- `workstream_id`, `delegation_owner`: sanitized hierarchical correlation fields when supplied.
- `task_packet_sha256`, `idempotency_key_sha256`: stable hashes for correlating packets and retries without logging raw idempotency keys.
- `sandbox_enabled`: local runtime sandbox state.
- `agent_id`, `run_id`, `request_id`: safe run identifiers for correlation.
- `current_tool_call`: sanitized active tool call, or `null`.
- `recent_tool_calls`: bounded list of recent tool events with safe args and result metadata.
- `active_subagents`: sanitized active Cursor internal task/subagent entries keyed by call id.
- `recent_subagents`: bounded list of completed or failed internal subagent calls with description, requested model, timing, and safe result metadata. The requested model is not proof of exact internal High parameters.
- `last_assistant_text`: latest assistant text, truncated.
- `last_usage` or `result.usage`: token usage when the SDK reports it.
- `authorization`: present when the run needs API-key authorization.
- `result`: result summary, truncated, after `run.wait()` completes.
- `events_seen`: parsed SDK event count.

The status file intentionally omits full file contents, internal subagent prompts, write payloads, and long assistant output.

## Limits

- SDK streaming exposes normalized events, not private reasoning beyond SDK-provided thinking summaries.
- Tool call `args` and `result` payloads are internal and may change; consumers must parse defensively and ignore unknown fields.
- Cursor internal task/Agent-tool calls expose a string model request in `@cursor/sdk` 1.0.23, not a structured parameter selection. Report exact High as unverified unless the SDK later supplies independent structured evidence.
- Local proposal/inspect runs use a permission-hardened copy by default and refuse escaping symlinks. Treat this as defense in depth, keep the SDK sandbox enabled, and still inspect reports and diffs.
- Cloud agents persist state server-side; local agents persist through the SDK's local store. Capture `agent_id` if continuation is required.
- The `latest` pointer is convenient for one run. For parallel wrapper runs, assign a dedicated `--log-dir` per workstream or use each printed `status.json` path instead of relying on one shared `latest`.
