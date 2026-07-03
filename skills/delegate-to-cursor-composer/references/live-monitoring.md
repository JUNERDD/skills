# Live Cursor Monitoring

Read this reference when the upstream agent or a workstream orchestrator needs in-flight visibility into a Cursor CLI run.

## Artifacts

`scripts/cursor_delegate.py` writes one run directory under `<workspace>/.agent/delegations/<timestamp>` by default. Use `--log-dir` to choose a stable parent directory.

- `latest`: file in the log parent that contains the newest run directory path.
- `status.json`: sanitized rolling status for parent-agent monitoring.
- `events.ndjson`: raw parsed JSON events from Cursor stdout, one event per line.
- `stdout.log`: raw Cursor stdout, including stream-json output.
- `stderr.log`: raw Cursor stderr with wrapper stderr separated from stdout.
- `metadata.json`: run configuration plus final return code.
- `prompt.txt`: exact prompt sent to Cursor.

Prefer `status.json` for normal parent updates. Use `events.ndjson` only when debugging event-level behavior; raw Cursor events can include file contents, internal subagent prompts, or proposed write text in tool results.

## Monitor Workflow

1. Run the wrapper with `--output-format stream-json`; add `--stream-partial-output` when real-time assistant text deltas matter.
2. Capture the printed `Logs:` or `Live status:` path. If the caller only knows the log parent, read `<log-dir>/latest`.
3. Poll `status.json` for low-noise progress: state, model, internal subagent model, session id, last assistant text, current tool call, active/recent internal subagents, recent tool calls, and result.
4. Tail `stdout.log` or `events.ndjson` only when detailed event inspection is worth the noise and sensitivity risk.
5. Treat live status as observation, not approval. Cursor still must stop only on packet stop conditions, wrapper failures, or explicit upstream/user intervention outside the running process.

## Status Semantics

Expected `status.json` fields:

- `state`: `starting`, `running`, `succeeded`, or `failed`.
- `current_tool_call`: sanitized active tool call, or `null`.
- `recent_tool_calls`: bounded list of recent started/completed tool events with safe args and result metadata.
- `active_subagents`: sanitized active Cursor internal `taskToolCall` entries keyed by call id.
- `recent_subagents`: bounded list of completed or failed internal subagent calls with description, requested model, agent id, timing, and safe result metadata.
- `last_assistant_text`: latest assistant text or text delta, truncated.
- `result`: final result summary, truncated, after Cursor emits a result event.
- `events_seen`: parsed JSON event count.

The status file intentionally omits full file contents, internal subagent prompts, write payloads, and long assistant output. Read raw logs only when necessary.

## Limits

- Cursor print mode suppresses thinking events. Monitoring can show messages and tool activity, not private reasoning.
- The Cursor event schema may gain fields over time. Consumers must ignore unknown fields.
- Network reconnects or CLI bugs can affect event completeness; final review must still inspect reports, diffs, and verification.
- The `latest` pointer is convenient for one run. For parallel external wrapper runs, use each printed `status.json` path instead of relying on one shared `latest`.
