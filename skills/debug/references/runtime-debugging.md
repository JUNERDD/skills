# Runtime Debugging Reference

Use this reference when the debugging task needs exact logging, local collector bootstrap, or response details.

## Table of contents

- Host capability checklist
- Active logging session
- Reusing or restarting the logging process
- Preferred local collector bootstrap
- Refreshing stale collector ports in existing log code
- Dashboard and operator APIs
- CORS behavior
- Clearing the active log file
- Log format
- JavaScript / TypeScript template
- Non-JavaScript template
- Reading evidence
- Reproduction block
- Log analysis standard
- Fix and verification rules

## Host capability checklist

Adapt the debugging infrastructure to the current host before running commands. Do not preflight the target app unless startup failure is part of the bug you are investigating:

1. Confirm where temporary debug artifacts should live. Reuse an existing host-specific scratch directory when one exists; otherwise default to `$PWD/.debug-logs/`.
2. Confirm how the host keeps long-lived processes alive: persistent PTY, detached job, task runner, or another supported mechanism.
3. If no authoritative logging configuration already exists, resolve a local Python 3 interpreter for the bundled collector. Prefer `python3`; otherwise allow `python` only when it resolves to Python 3. If neither is available, stop and tell the user you need either an existing logging session or Python 3 for this evidence-first mode.
4. Confirm whether the host can open or automate browser pages. If not, rely on the ready file and HTTP APIs. When it can, reserve page opening for the collector dashboard unless the user explicitly asked to open the target project.
5. Confirm whether planned instrumentation runs in browser/client code, server/runtime code, or both. For browser/client code, prefer direct posts to the active collector endpoint and do not assume an app-local proxy is required.
6. Confirm how the user signals that reproduction is complete. Use the host's real action label or request a short reply if no action exists.
7. Do not proactively start the target app, hit app health endpoints, probe routes, or run compile/build checks as setup unless the user explicitly asked to debug startup behavior or a current hypothesis depends on that evidence.

## App preflight limits

The default opening move is collector or session setup plus temporary instrumentation, not target-app validation.

Allowed before the first reproduction:

- Preparing the log session, ready file, temp artifact location, and host capability assumptions
- Deciding where instrumentation will run and how the user will signal reproduction completion

Not allowed as default setup:

- `pnpm dev`, `npm run dev`, or equivalent commands just to see whether the app boots
- Requests to target-app health endpoints or status routes
- Route reachability probes, page probes, or "does this URL load" checks
- Build, compile, or bundle checks whose only purpose is to confirm the app is healthy

Only do those app-level checks when the user explicitly asks to debug startup or availability, or when a specific hypothesis would otherwise remain untestable.

## Browser opening limits

The collector dashboard is the only page the skill may open by default.

Allowed by default:

- Reusing the collector's ready file and HTTP APIs without opening any target-app page
- Opening the collector dashboard only when its auto-open attempt failed or was intentionally disabled

Not allowed without an explicit user request to open the project:

- MCP or browser-automation navigation to the target app's home page, routes, or preview URLs
- Opening the project just to see whether it loads
- Treating a project page open as generic validation before hypotheses or instrumentation

If the user did not explicitly ask you to open the project, stay on the collector dashboard and the collector's HTTP APIs.

## Active logging session

Prefer this order:

1. If the session gives you any of the following, capture and reuse them exactly:
   - Server endpoint
   - Log path
   - Session ID
   - Ready file
2. Otherwise resolve a local Python 3 interpreter and start the bundled local collector service first. It should own the current session's NDJSON log file, expose the dashboard and operator APIs from the same origin, and its ready file becomes the source of truth for endpoint, log path, dashboard URL, and session ID.
3. If no Python 3 interpreter is available, if the logging system is explicitly unavailable, or if the local collector failed to start, stop and tell the user you cannot proceed with evidence-first debugging in the configured mode unless they provide an authoritative logging session or a local Python 3 runtime.

When the bundled collector provides dashboard auto-open fields in the ready file, treat them as authoritative:

- If `dashboardOpenSucceeded` is `true`, do not call MCP or browser automation to open the same dashboard again.
- If `dashboardOpenSucceeded` is `false`, or `dashboardOpenAttempted` is `false` because auto-open was disabled, then and only then consider MCP or an embedded browser fallback for the collector dashboard.

## Reusing or restarting the logging process

Before each new recording pass, verify that the current logging process is still alive before you clear logs or ask for reproduction again.

Prefer this order:

1. If the current session exposes `healthUrl`, probe it first.
2. Otherwise, if the session exposes `stateUrl`, probe that instead.
3. If the probe fails, times out, or the process has already been closed, start a new collector process for the current task and adopt the new ready file values before continuing.

Probe examples:

```bash
curl -fsS "<HEALTH_URL>"
curl -fsS "<STATE_URL>"
```

Treat connection errors, timeouts, and non-2xx responses as proof that the current process is no longer usable for the next recording round.

## Preferred local collector bootstrap

The collector is a small folderized app under `scripts/local_log_collector/`, resolved relative to the skill root. In agent runners that kill the child process tree when a command exits, launch it in a persistent PTY session or the host's equivalent long-lived execution mode and keep that session open for the whole debugging cycle:

Before running the bootstrap command, resolve `<PYTHON_BIN>` to a Python 3 interpreter. Prefer `python3`; otherwise allow `python` only when it resolves to Python 3:

```bash
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1 && python -c 'import sys; raise SystemExit(0 if sys.version_info.major == 3 else 1)'; then
  PYTHON_BIN=python
else
  echo "Python 3 interpreter not found" >&2
  exit 1
fi
```

If this check fails, stop and tell the user you need either an authoritative logging session or a local Python 3 runtime for the bundled collector.

```bash
mkdir -p .debug-logs
"$PYTHON_BIN" <SKILL_ROOT>/scripts/local_log_collector/main.py \
  --log-file "$PWD/.debug-logs/<SESSION_ID>.ndjson" \
  --ready-file "$PWD/.debug-logs/<SESSION_ID>.json" \
  --session-id "<SESSION_ID>" \
  > "$PWD/.debug-logs/<SESSION_ID>.service.log" 2>&1
```

In a normal terminal that preserves detached children, you can still daemonize it if you prefer:

```bash
mkdir -p .debug-logs
nohup "$PYTHON_BIN" <SKILL_ROOT>/scripts/local_log_collector/main.py \
  --log-file "$PWD/.debug-logs/<SESSION_ID>.ndjson" \
  --ready-file "$PWD/.debug-logs/<SESSION_ID>.json" \
  --session-id "<SESSION_ID>" \
  > "$PWD/.debug-logs/<SESSION_ID>.service.log" 2>&1 &
```

Resolve `<SKILL_ROOT>` to the installed debug skill directory before running the command. Generate `<SESSION_ID>` from the task plus a timestamp, for example `checkout-bug-1733456789000`. The collector attempts to open the dashboard in the default browser automatically unless you pass `--no-open-dashboard`. After the service starts, read the ready file and reuse the returned values exactly, including the dashboard auto-open result.

If you are operating inside an agent runtime that has its own browser automation or embedded browser, do not open `dashboardUrl` there when the ready file reports `dashboardOpenSucceeded: true`, because that would duplicate the same page open. Only fall back to MCP or an embedded browser for the collector dashboard when the ready file reports `dashboardOpenSucceeded: false` or `dashboardOpenAttempted: false`. Do not open target-app pages unless the user explicitly asked you to open the project. If the host has no browser access, continue with the ready file values plus `GET /api/state`, `GET /health`, `POST /api/clear`, and `POST /api/shutdown`.

Ready file example:

```json
{
  "endpoint": "http://127.0.0.1:43125/ingest",
  "dashboardUrl": "http://127.0.0.1:43125/",
  "stateUrl": "http://127.0.0.1:43125/api/state",
  "clearUrl": "http://127.0.0.1:43125/api/clear",
  "shutdownUrl": "http://127.0.0.1:43125/api/shutdown",
  "healthUrl": "http://127.0.0.1:43125/health",
  "dashboardOpenAttempted": true,
  "dashboardOpenSucceeded": true,
  "dashboardOpenError": "",
  "host": "127.0.0.1",
  "port": 43125,
  "logFile": "/abs/path/.debug-logs/checkout-bug-1733456789000.ndjson",
  "readyFile": "/abs/path/.debug-logs/checkout-bug-1733456789000.json",
  "sessionId": "checkout-bug-1733456789000",
  "pid": 12345,
  "startedAt": 1733456789000
}
```

Keep the collector running through the initial reproduction and the post-fix verification run. Stop it only after the debugging session is complete.

## Refreshing stale collector ports in existing log code

When a restarted collector comes back on a different port, update the existing temporary logging code before the next reproduction run so the logs do not keep posting to the dead endpoint.

Prefer this order:

1. Read the new ready file and capture the new `endpoint` exactly.
2. Search only the active debug instrumentation for stale collector URLs or endpoint constants.
3. Patch those temporary logging regions to use the new endpoint before asking for the next reproduction.

Useful search patterns:

```bash
rg -n "http://127\\.0\\.0\\.1:[0-9]+/ingest|#region agent log|X-Debug-Session-Id" <target-paths>
```

Keep the update narrow:

- Prefer updating one file-local debug endpoint constant when you created one.
- Otherwise replace only the stale URLs inside the temporary logging regions for the current task.
- Do not rewrite unrelated docs, examples, or committed production code just because they mention another port.

## Dashboard and operator APIs

The bundled service attempts to open `dashboardUrl` in a browser by default. Pass `--no-open-dashboard` only when you explicitly need a headless run. When the ready file reports a successful auto-open, do not reopen the same page with MCP. Do not open target-app pages from MCP or browser automation unless the user explicitly asked to open the project. The bundled UI shows:

- Total recorded entries
- Invalid NDJSON line count
- File size and last update time
- Count breakdowns by `runId` and `hypothesisId`
- The latest parsed log event

The same service also exposes:

- `GET /api/state` for live summary data
- `POST /api/clear` to truncate the current session log file
- `POST /api/shutdown` to stop the collector after the response returns

## CORS behavior

The bundled collector must not introduce browser CORS issues:

- Serve the dashboard from the same collector origin so UI actions stay same-origin.
- Answer `OPTIONS` preflight requests on the ingest and operator endpoints.
- Return `Access-Control-Allow-Origin: *`.
- Return `Access-Control-Allow-Headers: Content-Type, X-Debug-Session-Id`.
- Return `Access-Control-Allow-Methods: GET, POST, OPTIONS`.

This collector behavior exists so browser/client instrumentation can post directly to the collector from frontend apps, including Next.js dev apps. Do not add project-local proxy routes such as `/api/_dev/*` unless you have already proven that direct browser delivery is blocked in the current host.

## Clearing the active log file

Before each reproduction run or any deliberate re-recording pass, clear only the active session's existing logs. Prefer the clear endpoint when one is available because it keeps the collector UI, cache, and file state aligned:

```bash
curl -X POST "<CLEAR_URL>" \
  -H 'Content-Type: application/json' \
  --data '{}'
```

When the session does not expose a clear endpoint, fall back to truncating only the current session log file:

```bash
: > "<LOG_FILE>"
```

Never clear a different session's logs, and never clear the active session until you have already captured any evidence you still need from the current run.

## Log format

Prefer NDJSON with one JSON object per line. Use this payload shape:

```json
{
  "sessionId": "optional-session-id",
  "runId": "initial-or-post-fix",
  "hypothesisId": "A",
  "location": "file.ts:42",
  "message": "branch taken",
  "data": {
    "key": "value"
  },
  "timestamp": 1733456789000
}
```

Omit `sessionId` and any session header only when the session explicitly says no session ID is available.

## JavaScript / TypeScript template

When an active HTTP ingestion endpoint exists, use a compact `fetch` call and swallow failures. If you started the bundled local collector, use its `endpoint` value from the ready file. When the same file contains multiple temporary logs, prefer one file-local endpoint constant inside the debug region so a collector restart only requires one endpoint edit in that file. For browser/client instrumentation, call the collector directly instead of creating a Next.js API route or another app-local proxy unless direct delivery is proven blocked in the current host. The collector responds to browser preflight and includes the CORS headers required for this request:

```ts
// #region agent log config
const debugCollectorEndpoint = '<SERVER_ENDPOINT>'
// #endregion

// #region agent log
fetch(debugCollectorEndpoint, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Debug-Session-Id': '<SESSION_ID>',
  },
  body: JSON.stringify({
    sessionId: '<SESSION_ID>',
    runId: 'initial',
    hypothesisId: 'A',
    location: 'file.ts:42',
    message: 'before request',
    data: { value },
    timestamp: Date.now(),
  }),
}).catch(() => {})
// #endregion
```

Remove `X-Debug-Session-Id` and `sessionId` only when the session ID is explicitly absent.

## Non-JavaScript template

If the target runtime already has a lightweight HTTP client, send the same payload to the active endpoint. Otherwise append one NDJSON line to the active log path with standard-library file I/O. Keep the snippet tiny and close the file immediately after writing.

For JavaScript or TypeScript that runs only on the server, still call the active collector endpoint directly from that runtime instead of adding a second project-local ingest layer unless a proven environment constraint forces it.

## Reading evidence

After the user reproduces the issue, open the active session log file and analyze the recorded NDJSON lines directly. Use the collector's stdout or stderr only when you are debugging the collector itself.

## Reproduction block

Always end the reproduction request with this exact wrapper and keep only a numbered list inside it. Replace the final line with the host's actual completion action or a short reply instruction:

```html
<reproduction_steps>
1. Reproduce the bug in the smallest realistic flow.
2. Restart any required app or service first if the new logs are not loaded automatically.
3. <HOST_COMPLETION_INSTRUCTION>
</reproduction_steps>
```

Examples:

- Button-based host: `Press Proceed when done.`
- Task-based host: `Mark the task as fixed when done.`
- Chat-only host: `Reply with "done" when the reproduction completes.`

## Log analysis standard

For every hypothesis:

- Mark it `CONFIRMED` when logs directly prove it.
- Mark it `REJECTED` when logs contradict it.
- Mark it `INCONCLUSIVE` when the current instrumentation is insufficient.

Quote or cite the specific log entries that support the judgment.

## Fix and verification rules

- Keep instrumentation active while implementing the fix.
- Tag verification runs with a distinct `runId` such as `post-fix`.
- Compare before and after logs before claiming success.
- Remove all injected temporary logging code only after log proof and user confirmation. Remove the inserted log calls and any temporary endpoint constants, headers, or other debug-only scaffolding that was added for the current debugging pass.
- If a hypothesis is rejected, remove the code changes based on that hypothesis instead of letting speculative changes accumulate.
