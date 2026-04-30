---
name: debug
description: Evidence-first runtime debugging for application bugs, regressions, flaky behavior, and unclear failures, with an optional MCP server for exposing the workflow to MCP-compatible agents. Use when an agent is asked to debug an issue and should avoid speculative fixes by forming hypotheses, attaching to or starting a logging session, instrumenting code, collecting runtime logs, tracking active log locations in a sidecar JSON file, using the collector dashboard to inspect those locations and open source through the configured IDE, analyzing the recorded log file, applying only proven fixes, and verifying the result before removing instrumentation, especially for browser or frontend issues where logs should go directly to the active collector endpoint instead of app-local proxy APIs. Also use when configuring, running, or troubleshooting the debug MCP server in Cursor, Windsurf, Claude Code, or another MCP client.
---

# Debug

Use runtime evidence before changing behavior. Treat code reading as context building, not proof.

## MCP Server

This skill is also available as an MCP server, so any MCP-compatible agent (Cursor, Windsurf, Claude Code, etc.) can use the debug workflow through standard tool calls.

### Install

From the installed `debug` skill directory:

```bash
cd mcp_server
uv sync
```

### Run

```bash
uv run server.py
```

### Configure in Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "debug": {
      "command": "uv",
      "args": [
        "--project",
        "/path/to/debug/mcp_server",
        "run",
        "/path/to/debug/mcp_server/server.py"
      ],
      "cwd": "/path/to/project"
    }
  }
}
```

### Available MCP Tools

The session writes `.debug-logs` under `workspace_root` when provided, then
`JUNERDD_DEBUG_WORKSPACE_ROOT`/`DEBUG_WORKSPACE_ROOT`, then a single MCP client
root when available, and otherwise the MCP server's current working directory.
Configure the MCP server with the target project as `cwd` when you want the
fallback to match the original current-directory behavior.

| Tool | Description |
|---|---|
| `start_debug_session` | Start a collector session, returns endpoint + dashboard URL |
| `stop_debug_session` | Stop collector, clean up all artifacts |
| `check_collector_health` | Verify collector is alive |
| `ingest_log` | Send a log entry (observation, variable state, control flow evidence) |
| `get_debug_state` | Full state: entry/run/hypothesis counts |
| `get_debug_logs` | Paginated log entries |
| `clear_debug_logs` | Clear logs for next run |
| `sync_instrumentation_locations` | Register active instrumentation points |
| `open_location_in_ide` | Open source file in configured IDE |

### MCP Resources

- `debug://workflow` — full SKILL.md workflow
- `debug://reference` — runtime debugging reference

### MCP Prompts

- `debug_workflow` — load the 16-step debugging methodology
- `hypothesis_template` — structured hypothesis tracking template

## Host adaptation

Before starting, normalize the current debugging environment without preflighting the target app:

- Determine whether the session already exposes a logging endpoint, log path, session ID, ready file, location-state file, or other authoritative debug configuration.
- Determine whether the active session also exposes location-sync support such as `syncLocationsUrl` or a writable location-state file. If it does not, keep collecting runtime evidence and treat dashboard `Locations` browsing plus IDE-opening features as unavailable for that session instead of blocking the debug pass.
- If no authoritative logging configuration exists, determine whether a local Python 3 interpreter is available for the bundled collector. Prefer `python3`; otherwise allow `python` only when it resolves to Python 3. If no Python 3 interpreter is available, stop and tell the user you need either an existing logging session or a local Python 3 runtime before continuing in evidence-first mode.
- Determine how the host keeps long-lived processes alive: persistent PTY, detached shell, task runner, or no background support.
- Determine whether the host can open or automate browser pages. If not, rely on the collector's ready file and HTTP APIs instead of UI inspection. When browser access exists, reserve page opening for the collector dashboard by default; do not open target-app pages unless the user explicitly asked you to open the project.
- Determine whether each planned log point runs in browser/client code, server/runtime code, or both. For browser/client code, prefer direct requests to the active collector endpoint instead of adding project-local proxy routes.
- Determine how the user signals that reproduction is complete: explicit UI button, task-state action, or a short chat reply.
- Do not treat target-app startup, health checks, route probes, or compile/build checks as default preflight. Only inspect them when the user explicitly asked to debug startup behavior or when a current hypothesis is about app boot, compilation, or endpoint availability.
- Store temporary artifacts in an existing host-specific scratch directory when one already exists. Otherwise default to a workspace-local hidden directory such as `.debug-logs/`. If you start the bundled collector yourself, use its `ownedArtifacts` list as the cleanup source of truth because `.debug-logs/` is often ignored by Git.

## Workflow

1. Generate 3-5 precise hypotheses about why the bug happens. Make them specific enough that a log can confirm or reject each one.
2. Establish the active logging session before editing app code or probing the target app. Reuse any authoritative logging configuration exactly, including whether the current session supports location tracking. If no authoritative session exists, resolve Python 3, start the bundled collector from `scripts/local_log_collector/main.py`, and adopt its ready-file values. For exact bootstrap commands, ready-file fields, dashboard-opening rules, and teardown metadata, read [runtime-debugging.md](./references/runtime-debugging.md).
3. Add the minimum instrumentation needed to test all hypotheses in parallel. Prefer 2-6 logs; never skip instrumentation; do not exceed 10 logs. When instrumenting browser/client JavaScript, send logs directly to the active collector endpoint unless runtime evidence proves direct delivery is blocked in the current host. When the current session supports location tracking, sync the current active source-location set after instrumentation edits and before reproduction. For exact sync payload and validation rules, read [runtime-debugging.md](./references/runtime-debugging.md).
4. Before each reproduction run or deliberate re-recording pass, verify that the current logging process is still alive. Prefer the active `healthUrl` or `stateUrl` when one exists. If the process has been closed or the check fails, start a new collector process and treat its new ready file values as authoritative before continuing.
5. If restarting the collector changed the active ingest endpoint or port, update the existing temporary logging code so it no longer points at the stale port. Apply that refresh before the next reproduction run and keep the edits limited to the active debug instrumentation for the current task.
6. Preserve any evidence you still need from the current run, then clear only the active session's existing logs so the next run starts from a low-noise baseline. Prefer the active clear endpoint when one exists; fall back to truncating the active session log file only when no clear endpoint is available.
7. Ask the user to reproduce the issue using the reproduction handoff in [runtime-debugging.md](./references/runtime-debugging.md). Match the host's real completion mechanic exactly: use the actual button or task action label when one exists, otherwise ask for a short completion reply. Then stop and wait for the user's completion signal before continuing.
8. Read the active session's NDJSON log file and evaluate every hypothesis as `CONFIRMED`, `REJECTED`, or `INCONCLUSIVE`, citing the relevant log evidence.
9. Apply a fix only after the logs prove the root cause. Keep instrumentation in place while implementing the fix.
10. Before the post-fix verification run, verify the current logging process is still alive again. If it has been closed, start a new collector process and adopt its new ready file values before clearing and collecting verification logs.
11. If restarting the collector changed the active ingest endpoint or port again, update the temporary logging code to replace the stale port before the verification run.
12. Clear only the active session's current logs again so before/after evidence does not mix.
13. Ask for a post-fix reproduction run and compare before/after logs. Use the same handoff rules in [runtime-debugging.md](./references/runtime-debugging.md), then wait for the user's completion signal before continuing.
14. Remove all injected temporary logging code only after logs prove the fix worked and the user confirms the issue is gone. This includes the inserted log calls, debug-only endpoint constants, temporary headers, and any other scaffolding added only for this debugging pass.
15. If you started the bundled collector for this task, stop it after the final evidence handoff, delete every path in `ownedArtifacts` unless the user asked to keep evidence, verify those exact paths no longer exist, and remove the scratch directory if it becomes empty. Do not use Git status, diffs, or untracked-file scans to infer cleanup because ignored artifacts may be hidden.
16. If the fix fails, remove code changes that came from rejected hypotheses, keep useful instrumentation, generate new hypotheses from a different subsystem, and repeat.

## Guardrails

- Never claim confidence from code inspection alone.
- Never skip local log session setup when no authoritative logging configuration exists.
- Never attempt bundled collector bootstrap without first resolving a Python 3 interpreter when no authoritative logging configuration exists.
- Never remove instrumentation before post-fix verification succeeds.
- Never keep speculative guards or fallback code once logs reject the hypothesis behind them.
- Never log secrets, tokens, passwords, API keys, or PII.
- Never use `setTimeout`, sleep, or artificial delays as the fix.
- Never hardcode host-specific UI instructions unless the current host actually exposes them.
- Prefer targeted edits that match existing architecture and utilities.
- Never analyze service stdout when the session log file is available; read the NDJSON log file directly.
- Never split the dashboard and ingest API across separate local origins when the bundled collector can serve both from one place.
- Never add a Next.js API route, server action, middleware, or any app-local proxy endpoint just to forward browser debug logs when the collector endpoint is directly reachable.
- Never route browser/client debug traffic through the target app's backend as a first choice. Only use that fallback after proving direct browser-to-collector delivery is blocked in the current host, and record that evidence in the debugging notes.
- Never proactively start the target project, hit app health endpoints, probe routes, or run build/compile checks as default setup. Only do so when the user explicitly wants startup debugging or a live hypothesis requires that evidence.
- Never clear the active session's logs before preserving any evidence you still need from the current run.
- Never assume a previously started logging process is still alive before a new recording pass; verify it or start a new collector first.
- Never open the target project with MCP, browser automation, or an embedded browser unless the user explicitly asked you to open the project. By default, the only page you may open is the collector dashboard.
- Never open the same dashboard twice. If the bundled collector already opened the dashboard successfully, do not call MCP or browser automation just to open that page again.
- Never restart the collector and leave the temporary logging code pointed at a stale ingest port.
- Never leave injected temporary logging code behind after the bug is proven fixed and the user confirms the issue is gone.
- Never leave bundled-collector session artifacts behind after a successful debug session unless the user explicitly asked to keep them.
- Never treat a clean Git status as proof that collector artifacts were removed; ignored `.debug-logs/` files must be checked by path.
- Never delete files that belong to an externally provided logging session you did not create.

## Instrumentation Rules

- Map each log to at least one `hypothesisId`.
- Set `location` on every temporary log to the actual source file and line for that injected log. The bundled collector uses that field to maintain the live location-state JSON file.
- When the current session exposes `syncLocationsUrl` or a writable location-state file, sync the collector's active location list using the full set of currently injected log points. Repeat that sync after removing temporary logs so the sidecar state tracks source injections rather than whichever NDJSON file happened to run last. Keep the exact sync payload and validation contract in [runtime-debugging.md](./references/runtime-debugging.md). If that support is unavailable, keep `location` populated in the log payloads and continue without collector-managed active-location state for that session.
- Include enough context to prove control flow and state transitions: parameters, branch choice, before/after values, errors, or return values.
- Wrap each inserted debug log in a collapsible code region when the language supports regions.
- If the session provides a logging endpoint, log path, session ID, ready file, or location-state file, treat those values as authoritative and use them exactly.
- When the session provides no logging configuration, prefer the bundled local collector service over ad hoc console logging or temporary files. If no Python 3 interpreter is available for that collector, stop and tell the user the configured debug mode cannot continue until they provide an authoritative logging session or a local Python 3 runtime.
- For JavaScript or TypeScript running in browser/client code, send logs directly to the active HTTP ingestion endpoint. Default to the local collector endpoint when you started the bundled service.
- For JavaScript or TypeScript running only on the server, use the same active HTTP endpoint from that runtime instead of inventing a second ingest layer.
- For non-JavaScript languages, prefer the active HTTP endpoint when the runtime already has a lightweight HTTP client. Otherwise append NDJSON directly to the active session log file.
- When you started the bundled collector, use its same-origin dashboard for live status and operator actions instead of building a second local UI.
- The bundled collector should auto-open the dashboard unless you intentionally started it with `--no-open-dashboard`.
- When the bundled collector reports a successful dashboard auto-open, treat that as sufficient and do not open the same page again through MCP. Only fall back to MCP or an embedded browser when the auto-open attempt failed or was disabled.
- When browser automation or MCP is available, reserve it for the collector dashboard unless the user explicitly asked you to open the target project. Do not use project page opens as implicit validation.
- When referencing bundled files, resolve paths relative to the skill directory instead of the repo root or shell cwd.
- Before a rerun, verify the current logging process is still reachable. If it is not, re-establish a new active session before clearing logs or asking for reproduction.
- If the active collector endpoint changes after a restart, update the inserted temporary logging code to use the new endpoint before the next run.
- When you insert more than one temporary log in the same file, prefer a single file-local endpoint constant inside the debug region so a collector restart requires one endpoint edit in that file instead of many.
- Do not create project-local logging proxy routes, server actions, middleware, or backend forwarding endpoints for client instrumentation unless direct browser delivery is proven impossible in the current host.
- When you need a clean rerun, clear the current session's existing logs before collecting the next pass so stale entries do not pollute the evidence.
- Prefer calling the active clear endpoint for that reset when one exists. Only truncate the active session log file directly when no clear endpoint is available.
- Read the active session log file itself when analyzing evidence.

Read [runtime-debugging.md](./references/runtime-debugging.md) for local collector bootstrap commands, location-state JSON schema, dashboard `Locations` tab behavior, `~/.junerdd/config.json` IDE settings, CORS behavior, payload fields, logging templates, response shape, and verification rules.

## Response Shape

Use phase-based handoffs, and stop whenever the user needs to act.

Before the first reproduction handoff, structure the visible assistant output in this order:

1. Hypotheses
2. Instrumentation plan or applied log points
3. Reproduction request using the reproduction handoff in [runtime-debugging.md](./references/runtime-debugging.md)

Detailed handoff rules live in [runtime-debugging.md](./references/runtime-debugging.md). Apply them to every reproduction or verification request.

After the user reproduces the issue, continue in this order:

4. Log analysis with `CONFIRMED` / `REJECTED` / `INCONCLUSIVE`
5. Proven fix
6. Post-fix verification request using the same visible-handoff rules
7. Short root-cause explanation and 1-2 line fix summary after success
