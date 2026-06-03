# Runtime Debugging Reference

Use this reference when the debugging task needs exact logging, local collector bootstrap, or response details.

## Table of contents

- Host capability checklist
- Active logging session
- Reusing or restarting the logging process
- Preferred local collector bootstrap
- Location state file
- IDE config and source opening
- Refreshing stale collector ports in existing log code
- Dashboard and operator APIs
- Dashboard frontend open record
- CORS behavior
- Clearing the active log file
- Session artifact cleanup
- Log format
- JavaScript / TypeScript template
- Non-JavaScript template
- Reading evidence
- Reproduction request
- Log analysis standard
- Fix and verification rules

## Host capability checklist

Adapt the debugging infrastructure to the current host before running commands. Do not preflight the target app unless startup failure is part of the bug you are investigating:

1. Confirm where temporary debug artifacts should live. Reuse an existing host-specific scratch directory when one exists; otherwise default to `$PWD/.debug-logs/`. Scratch directories such as `.debug-logs/` may be ignored by Git, so do not use `git status`, `git diff`, or untracked-file scans as the cleanup source of truth for collector artifacts.
2. Confirm how the host keeps long-lived processes alive: persistent PTY, detached job, task runner, or another supported mechanism.
3. If no authoritative logging configuration already exists, resolve a local Python 3 interpreter for the bundled collector. Prefer `python3`; otherwise allow `python` only when it resolves to Python 3. If neither is available, stop and tell the user you need either an existing logging session or Python 3 for this evidence-first mode.
4. Confirm whether the host can open or automate browser pages. If not, rely on the ready file and HTTP APIs. When it can, reserve page opening for the collector dashboard unless the user explicitly asked to open the target project. Before the first reproduction handoff, the bundled collector dashboard should have `dashboardFrontendOpenRecorded: true`; if not, open `dashboardUrl` and re-check state. Record failed fallback opens through `dashboardFrontendOpenFailedUrl`, and stop after two fallback failures.
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
- Opening the collector dashboard before the first reproduction handoff when `GET /api/state` reports `dashboardFrontendOpenRecorded: false`, stopping after two recorded fallback failures

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
   - Location-state file
2. Otherwise resolve a local Python 3 interpreter and start the bundled local collector service first. It should own the current session's NDJSON log file plus the sidecar location-state JSON file, expose the dashboard and operator APIs from the same origin, and its ready file becomes the source of truth for endpoint, log path, location-state file path, dashboard URL, session ID, workspace root, config file path, and owned temporary artifacts.
3. If no Python 3 interpreter is available, if the logging system is explicitly unavailable, or if the local collector failed to start, stop and tell the user you cannot proceed with evidence-first debugging in the configured mode unless they provide an authoritative logging session or a local Python 3 runtime.

If a reused authoritative session does not expose `syncLocationsUrl` or another writable location-state mechanism, keep debugging with log evidence only. Do not block the task on dashboard `Locations` browsing or IDE-opening features that session cannot support.

When the bundled collector provides dashboard auto-open fields in the ready file, treat them as authoritative:

- If `dashboardOpenSucceeded` is `true`, do not call MCP or browser automation to open the same dashboard again during startup.
- If `dashboardOpenSucceeded` is `false`, or `dashboardOpenAttempted` is `false` because auto-open was disabled, then and only then consider MCP or an embedded browser fallback for the collector dashboard.

Dashboard auto-open success only means the host accepted the browser open request. The dashboard frontend records its first actual page load through `POST /api/dashboard-opened`, exposed in ready/state payloads as `dashboardFrontendOpenRecorded` and `dashboardFrontendOpenedAt`. Before the first reproduction handoff, query `stateUrl`; if `dashboardFrontendOpenRecorded` is false and browser access exists, open `dashboardUrl`, then re-query state. If that fallback open fails, record it through `dashboardFrontendOpenFailedUrl` with the session token. Make at most two fallback open attempts before continuing with ready/state HTTP APIs. Do not repeat this after the record exists.

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
  --location-state-file "$PWD/.debug-logs/<SESSION_ID>.locations.json" \
  --ready-file "$PWD/.debug-logs/<SESSION_ID>.json" \
  --session-id "<SESSION_ID>" \
  --workspace-root "$PWD" \
  --default-ide "<IDE_ID>" \
  --service-log-file "$PWD/.debug-logs/<SESSION_ID>.service.log" \
  > "$PWD/.debug-logs/<SESSION_ID>.service.log" 2>&1
```

In a normal terminal that preserves detached children, you can still daemonize it if you prefer:

```bash
mkdir -p .debug-logs
nohup "$PYTHON_BIN" <SKILL_ROOT>/scripts/local_log_collector/main.py \
  --log-file "$PWD/.debug-logs/<SESSION_ID>.ndjson" \
  --location-state-file "$PWD/.debug-logs/<SESSION_ID>.locations.json" \
  --ready-file "$PWD/.debug-logs/<SESSION_ID>.json" \
  --session-id "<SESSION_ID>" \
  --workspace-root "$PWD" \
  --default-ide "<IDE_ID>" \
  --service-log-file "$PWD/.debug-logs/<SESSION_ID>.service.log" \
  > "$PWD/.debug-logs/<SESSION_ID>.service.log" 2>&1 &
```

Resolve `<SKILL_ROOT>` to the installed debug skill directory before running the command. Generate `<SESSION_ID>` from the task plus a timestamp, for example `checkout-bug-1733456789000`. Set `--workspace-root` to the repository root that relative `location` fields should resolve against. If you omit `--location-state-file`, the collector derives `<SESSION_ID>.locations.json` next to the ready file when a ready file exists, otherwise next to the NDJSON log file. Use `--default-ide` only as a fallback when `~/.junerdd/config.json` does not already specify one. The collector attempts to open the dashboard in the default browser automatically unless you pass `--no-open-dashboard`. After the service starts, read the ready file and reuse the returned values exactly, including the dashboard auto-open result, dashboard frontend open record fields, `locationStateFile`, `serviceLogFile`, and `ownedArtifacts`.

If you are operating inside an agent runtime that has its own browser automation or embedded browser, do not open `dashboardUrl` there immediately when the ready file reports `dashboardOpenSucceeded: true`, because that would duplicate the same page open. Only fall back to MCP or an embedded browser at startup when the ready file reports `dashboardOpenSucceeded: false` or `dashboardOpenAttempted: false`. Before the first reproduction handoff, query `GET /api/state`; if the bundled collector still reports `dashboardFrontendOpenRecorded: false`, open `dashboardUrl` even if the startup auto-open succeeded, then re-query state. For failed fallback attempts, call `POST /api/dashboard-open-failed` with the token, error, and attempted URL. Do not exceed two fallback open attempts. Do not open target-app pages unless the user explicitly asked you to open the project. If the host has no browser access, continue with the ready file values plus `GET /api/state`, `GET /health`, `POST /api/clear`, and `POST /api/shutdown`.

Ready file example:

```json
{
  "endpoint": "http://127.0.0.1:43125/ingest",
  "dashboardUrl": "http://127.0.0.1:43125/",
  "dashboardToken": "<SESSION_SCOPED_TOKEN>",
  "stateUrl": "http://127.0.0.1:43125/api/state",
  "syncLocationsUrl": "http://127.0.0.1:43125/api/locations/sync",
  "dashboardFrontendOpenedUrl": "http://127.0.0.1:43125/api/dashboard-opened",
  "dashboardFrontendOpenFailedUrl": "http://127.0.0.1:43125/api/dashboard-open-failed",
  "dashboardFrontendOpenRecorded": false,
  "dashboardFrontendOpenedAt": null,
  "dashboardFrontendOpenFailureCount": 0,
  "dashboardFrontendOpenLastFailureAt": null,
  "dashboardFrontendOpenLastError": "",
  "dashboardFrontendOpenLastFailedUrl": "",
  "clearUrl": "http://127.0.0.1:43125/api/clear",
  "shutdownUrl": "http://127.0.0.1:43125/api/shutdown",
  "healthUrl": "http://127.0.0.1:43125/health",
  "dashboardOpenAttempted": true,
  "dashboardOpenSucceeded": true,
  "dashboardOpenError": "",
  "host": "127.0.0.1",
  "port": 43125,
  "logFile": "/abs/path/.debug-logs/checkout-bug-1733456789000.ndjson",
  "locationStateFile": "/abs/path/.debug-logs/checkout-bug-1733456789000.locations.json",
  "serviceLogFile": "/abs/path/.debug-logs/checkout-bug-1733456789000.service.log",
  "readyFile": "/abs/path/.debug-logs/checkout-bug-1733456789000.json",
  "ownedArtifacts": [
    "/abs/path/.debug-logs/checkout-bug-1733456789000.ndjson",
    "/abs/path/.debug-logs/checkout-bug-1733456789000.locations.json",
    "/abs/path/.debug-logs/checkout-bug-1733456789000.json",
    "/abs/path/.debug-logs/checkout-bug-1733456789000.service.log"
  ],
  "sessionId": "checkout-bug-1733456789000",
  "workspaceRoot": "/abs/path/to/workspace",
  "configFile": "/Users/example/.junerdd/config.json",
  "pid": 12345,
  "startedAt": 1733456789000
}
```

Keep the collector running through the initial reproduction and the post-fix verification run. Stop it only after the debugging session is complete.

## Location state file

The bundled collector maintains a sidecar JSON file that mirrors the current instrumentation locations in real time. Update expectations:

- Treat explicitly synced instrumentation locations as the source of truth for which temporary log points are currently active.
- Merge runtime evidence from accepted ingest events onto those tracked locations so counts and last-seen metadata stay useful.
- Refresh it on startup after hydrating an existing NDJSON log and reloading any previously synced tracked locations.
- Refresh it after every accepted ingest.
- Refresh it after every location sync.
- Refresh it after every clear operation so runtime counters reset without losing the active source locations.
- Treat the file path in `locationStateFile` as authoritative when the session provides one.

The file is intended to answer "which temporary log points are currently active?" without rescanning the whole NDJSON file. `trackedLocations` is the authoritative active set that the agent syncs after instrumentation edits. `locations` is the per-location view for that same active set, with runtime counts from the NDJSON session merged onto the currently tracked rows. Removed log points should disappear from `locations` as soon as the next sync replaces the active set, even if older NDJSON entries still mention them. Use this shape:

```json
{
  "sessionId": "checkout-bug-1733456789000",
  "logFile": "/abs/path/.debug-logs/checkout-bug-1733456789000.ndjson",
  "locationStateFile": "/abs/path/.debug-logs/checkout-bug-1733456789000.locations.json",
  "fileUpdatedAt": 1733456789000,
  "invalidLines": 0,
  "updatedAt": 1733456789001,
  "totalEntries": 3,
  "uniqueLocations": 2,
  "trackedLocationCount": 2,
  "lastEntry": {
    "entryIndex": 2,
    "lineNumber": 3,
    "runId": "initial",
    "hypothesisId": "B",
    "location": "src/cart.ts:118",
    "message": "after response",
    "sessionId": "checkout-bug-1733456789000",
    "timestamp": 1733456789000
  },
  "trackedLocations": [
    {
      "location": "src/cart.ts:118",
      "hypothesisIds": ["A", "B"],
      "registeredAt": 1733456788000,
      "updatedAt": 1733456789000
    }
  ],
  "locations": [
    {
      "location": "src/cart.ts:118",
      "count": 2,
      "lastTimestamp": 1733456789000,
      "lastEntryIndex": 2,
      "lastLineNumber": 3,
      "runIds": ["initial"],
      "hypothesisIds": ["A", "B"],
      "tracked": true,
      "registeredAt": 1733456788000,
      "updatedAt": 1733456789000
    }
  ]
}
```

The dashboard's `Locations` tab should read this data through `GET /api/locations`, not by opening the JSON file directly in frontend code. The API enriches each record with resolved absolute paths, existence checks, and whether the location is currently openable.

When the current session exposes `syncLocationsUrl`, sync the collector immediately with the full active source-location set after inserting, moving, or deleting temporary logs and before asking for reproduction:

```bash
curl -X POST "<SYNC_LOCATIONS_URL>" \
  -H 'Content-Type: application/json' \
  -H 'X-Debug-Dashboard-Token: <DASHBOARD_TOKEN>' \
  --data '{
    "locations": [
      {"location": "src/cart.ts:118", "hypothesisIds": ["A"]},
      {"location": "src/cart.ts:141", "hypothesisIds": ["B"]}
    ]
  }'
```

Use replace semantics: send the entire current set of active temporary log locations each time so removed log points disappear from the sidecar state as soon as the code changes. Do not trim a valid active set just because it is larger than the usual instrumentation budget; the collector state should reflect the temporary log points that actually exist in source. Each synced location must stay relative to `workspaceRoot`, include a line number, and resolve to an existing source file inside the workspace; the collector rejects invalid, absolute, missing-file, or out-of-root records at sync time.

If the current session does not expose `syncLocationsUrl` or another writable location-state mechanism, keep `location` populated in the log payloads and continue without collector-managed active-location state for that session.

## IDE config and source opening

The collector stores IDE preferences in `~/.junerdd/config.json`. Keep the file extensible by nesting debug-collector settings under their own object instead of using flat top-level keys. Use this shape:

```json
{
  "debug": {
    "collector": {
      "ide": {
        "selected": "cursor"
      }
    }
  }
}
```

Rules:

- Preserve unrelated keys in `~/.junerdd/config.json` when updating the selected IDE.
- If `~/.junerdd/config.json` is unreadable, invalid JSON, or not a JSON object, surface that error and refuse writes until the file is repaired. Do not overwrite a broken config with partial data.
- Treat `debug.collector.ide.selected` as the authoritative stored preference when it exists.
- Use the collector's `--default-ide` only when that config key is absent.
- If the configured `--default-ide` is unavailable, fall back to the first available IDE instead of exposing a dead default choice.
- Expose the config path and supported IDE options from `GET /api/config` so the dashboard can render the current selection without touching the filesystem directly.
- Update the config through `POST /api/config` by writing only `debug.collector.ide.selected`. Do not accept arbitrary root-level merge patches from the dashboard.
- Route dashboard clicks through `POST /api/open-location` so the browser never needs to know the local editor command line.
- If the stored IDE is unsupported or unavailable, show that state in the dashboard and disable source-opening actions until the selection is fixed.

`POST /api/open-location` should parse `location`, resolve relative paths against `workspaceRoot`, and open the file in the configured IDE at the logged source line. Reject absolute paths or `..` traversals that resolve outside `workspaceRoot`. Prefer editor CLI launchers when available. For VS Code-family editors and JetBrains apps on macOS, allow an application-bundle fallback when the shell launcher is missing. When the launcher exits `0` during the synchronous handoff, return `launchStatus: "confirmed"`; when the process is still running after the short handoff window, return `launchStatus: "requested"` so the caller does not mistake a best-effort launch request for confirmed editor success.

## Refreshing stale collector ports in existing log code

When a restarted collector comes back on a different port, update the existing temporary logging code before the next reproduction run so the logs do not keep posting to the dead endpoint.

Prefer this order:

1. Read the new ready file and capture the new `endpoint` exactly.
2. Check the current `locationStateFile` first when it exists so you can restrict the search to files that still contain active temporary logs.
3. Search only the active debug instrumentation for stale collector URLs or endpoint constants.
4. Patch those temporary logging regions to use the new endpoint before asking for the next reproduction.

Useful search patterns:

```bash
rg -n "http://127\\.0\\.0\\.1:[0-9]+/ingest|#region agent log|X-Debug-Session-Id" <target-paths>
```

Keep the update narrow:

- Prefer updating one file-local debug endpoint constant when you created one.
- Otherwise replace only the stale URLs inside the temporary logging regions for the current task.
- Do not rewrite unrelated docs, examples, or committed production code just because they mention another port.

## Dashboard and operator APIs

The bundled service attempts to open `dashboardUrl` in a browser by default. Pass `--no-open-dashboard` only when you explicitly need a headless run. When the ready file reports a successful auto-open, do not immediately reopen the same page with MCP; wait for the pre-reproduction frontend-open-record check. Do not open target-app pages from MCP or browser automation unless the user explicitly asked to open the project. The bundled UI shows:

- Total recorded entries
- Invalid NDJSON line count
- File size and last update time
- Count breakdowns by `runId` and `hypothesisId`
- The latest parsed log event
- A `Locations` tab that lists active temporary log points and opens them through the configured IDE

The same service also exposes:

- `GET /api/state` for live summary data
- `POST /api/locations/sync` to replace the active temporary log-point list
- `POST /api/dashboard-open-failed` to record a failed dashboard open attempt before the frontend has loaded
- `POST /api/dashboard-opened` for the dashboard frontend to record its first real page load
- `POST /api/clear` to truncate the current session log file
- `POST /api/shutdown` to stop the collector after the response returns

Both the ready file and `GET /api/state` include `locationStateFile`, `serviceLogFile`, an `ownedArtifacts` list, a session-scoped `dashboardToken`, active-location URLs, and dashboard frontend open-record fields. When you started the bundled collector yourself, treat that artifact list as the authoritative cleanup target after the debug session succeeds, and use the returned `dashboardToken` for mutating operator calls. Browser-initiated dashboard calls must stay same-origin. Local agent or CLI calls may omit `Origin` when they already hold the session token.

## Dashboard frontend open record

The dashboard page sends one same-origin `POST /api/dashboard-opened` request after it first reads collector state and obtains the session token. The collector records only the first successful request for the session by setting `dashboardFrontendOpenRecorded: true` and `dashboardFrontendOpenedAt` in both ready-file and state payloads; later dashboard reloads or duplicate tabs must not update that timestamp.

The agent records failed fallback opens by calling:

```bash
curl -X POST "<DASHBOARD_FRONTEND_OPEN_FAILED_URL>" \
  -H 'Content-Type: application/json' \
  -H 'X-Debug-Dashboard-Token: <DASHBOARD_TOKEN>' \
  --data '{"error":"<OPEN_ERROR>","attemptedUrl":"<DASHBOARD_URL>"}'
```

The collector increments `dashboardFrontendOpenFailureCount` and updates `dashboardFrontendOpenLastFailureAt`, `dashboardFrontendOpenLastError`, and `dashboardFrontendOpenLastFailedUrl` only while `dashboardFrontendOpenRecorded` is false. If startup auto-open fails, the collector records that as the first failure for visibility; the pre-reproduction retry budget still allows at most two fallback open attempts. Once the frontend load record exists, later failure reports are ignored.

Before asking the user for the first reproduction run, query `stateUrl`. If `dashboardFrontendOpenRecorded` is false and browser access exists, open `dashboardUrl`, then query `stateUrl` again. If the open fails, record the failure and retry at most once more. After two fallback attempts fail, stop opening the dashboard and continue with ready/state HTTP APIs. Do not keep reopening the dashboard after the record exists. If the host cannot open a browser, continue with ready/state HTTP APIs and mention that the dashboard frontend open record could not be created by this host.

## CORS behavior

The bundled collector must not introduce browser CORS issues:

- Serve the dashboard from the same collector origin so UI actions stay same-origin.
- Answer `OPTIONS` preflight requests for `/ingest`.
- Return wildcard CORS headers only for `/ingest`, with `Access-Control-Allow-Headers: Content-Type, X-Debug-Session-Id` and `Access-Control-Allow-Methods: POST, OPTIONS`.
- Keep dashboard/operator APIs same-origin from the browser. Do not return wildcard CORS headers for `POST /api/locations/sync`, `POST /api/dashboard-open-failed`, `POST /api/dashboard-opened`, `POST /api/clear`, `POST /api/shutdown`, `POST /api/config`, or `POST /api/open-location`.
- Require the session-scoped `X-Debug-Dashboard-Token` header on mutating requests so random webpages cannot clear logs, rewrite config, or trigger local IDE opens. When a browser sends an `Origin`, reject it unless it matches the collector origin. Local non-browser callers may omit `Origin`.

This collector behavior exists so browser/client instrumentation can post directly to the collector from frontend apps, including Next.js dev apps. Do not add project-local proxy routes such as `/api/_dev/*` unless you have already proven that direct browser delivery is blocked in the current host.

## Clearing the active log file

Before each reproduction run or any deliberate re-recording pass, clear only the active session's existing logs. Prefer the clear endpoint when one is available because it keeps the collector UI, cache, and file state aligned:

```bash
curl -X POST "<CLEAR_URL>" \
  -H 'Content-Type: application/json' \
  -H 'X-Debug-Dashboard-Token: <DASHBOARD_TOKEN>' \
  --data '{}'
```

When the session does not expose a clear endpoint, fall back to truncating only the current session log file:

```bash
: > "<LOG_FILE>"
```

Never clear a different session's logs, and never clear the active session until you have already captured any evidence you still need from the current run. Intermediate log clears do not delete the root-cause document; delete that document only during final successful cleanup unless the user explicitly asked to keep evidence.

## Session artifact cleanup

Only delete artifacts you own.

- If the logging session was provided by the host, another tool, or the user, do not delete its files.
- If you started the bundled collector for the current task, stop it after post-fix verification succeeds and after any final evidence handoff the user still needs.
- Track the root-cause document path separately because it is not part of the collector's `ownedArtifacts` list.
- Before deleting the root-cause document, update it with final verification status, cleanup status, and whether evidence is being retained by request or the document is scheduled for deletion.
- When using the debug MCP server, pass the final root-cause document path as `root_cause_document_path` to `stop_debug_session` after that document has been updated.
- Capture the ready-file payload, including `dashboardToken`, `shutdownUrl`, and `ownedArtifacts`, before deleting anything.
- Stop the collector with the session-scoped `X-Debug-Dashboard-Token` header and confirm it is no longer reachable before deleting artifacts. If shutdown fails, do not report cleanup as complete.
- Then delete every path listed in `ownedArtifacts`, which should include the session NDJSON log, location-state file, ready file, and service log.
- Do not rely on Git visibility for cleanup verification. `.debug-logs/` is commonly in `.gitignore`, so ignored leftovers will not appear in normal status output.
- After deletion, check every `ownedArtifacts` path directly and fail the cleanup if any owned path still exists.
- If the scratch directory becomes empty after that deletion, remove it too.
- After temporary instrumentation and collector artifacts are removed, delete the root-cause Markdown document unless the user explicitly asked to keep evidence. Verify the document path no longer exists and mention the deletion in the final response.

One safe pattern is:

```bash
python3 - <<'PY' "<READY_FILE>" "<ROOT_CAUSE_DOCUMENT_OR_EMPTY>"
from __future__ import annotations

import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ready_path = Path(sys.argv[1])
root_cause_document = (
    Path(sys.argv[2]).expanduser().resolve()
    if len(sys.argv) > 2 and sys.argv[2]
    else None
)
payload = json.loads(ready_path.read_text(encoding='utf-8'))
artifacts = [Path(path) for path in payload.get('ownedArtifacts', []) if path]
shutdown_url = payload.get('shutdownUrl')
health_url = payload.get('healthUrl')
dashboard_token = payload.get('dashboardToken')

if shutdown_url:
    headers = {'Content-Type': 'application/json'}
    if dashboard_token:
        headers['X-Debug-Dashboard-Token'] = dashboard_token
    request = urllib.request.Request(
        shutdown_url,
        data=b'{}',
        headers=headers,
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status >= 400:
                raise SystemExit(f'[ERROR] Collector shutdown failed: HTTP {response.status}')
    except urllib.error.HTTPError as exc:
        raise SystemExit(f'[ERROR] Collector shutdown failed: HTTP {exc.code}') from exc
    except urllib.error.URLError:
        pass

if health_url:
    for _ in range(30):
        try:
            urllib.request.urlopen(health_url, timeout=0.25).close()
        except Exception:
            break
        time.sleep(0.1)
    else:
        raise SystemExit('[ERROR] Collector is still reachable after shutdown; not deleting artifacts.')

for artifact in artifacts:
    try:
        artifact.unlink()
    except FileNotFoundError:
        pass

remaining = [str(artifact) for artifact in artifacts if artifact.exists()]
if remaining:
    raise SystemExit('[ERROR] Collector cleanup left owned artifacts:\n' + '\n'.join(remaining))

if root_cause_document:
    if root_cause_document.suffix.lower() != '.md':
        raise SystemExit(f'[ERROR] Refusing to delete non-Markdown root-cause document: {root_cause_document}')
    try:
        root_cause_document.unlink()
    except FileNotFoundError:
        pass
    if root_cause_document.exists():
        raise SystemExit(f'[ERROR] Root-cause document still exists after cleanup: {root_cause_document}')

artifact_anchor = payload.get('logFile') or (str(artifacts[0]) if artifacts else '')
if artifact_anchor:
    artifact_dir = Path(artifact_anchor).parent
    try:
        artifact_dir.rmdir()
    except OSError:
        pass
PY
```

If you already captured the artifact list in memory, use that list directly rather than re-reading a ready file you are about to delete. If the user asked to keep evidence, pass an empty root-cause document argument and report that the document was intentionally retained.

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

Populate `location` with the actual file and line for the injected log. The collector uses that field to maintain the sidecar location-state JSON. Omit `sessionId` and any session header only when the session explicitly says no session ID is available.

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

## Reproduction request

Do not depend on custom XML or HTML tags such as `<reproduction_steps>` for Codex UI behavior. The documented Codex form path is the official request-user-input capability; use that when it is available in the current host mode. When that form capability is unavailable, send a plain numbered list in regular message text.

Phase handling:

- Treat `commentary` as interim progress text, not as the durable handoff surface for required user actions.
- Put fallback numbered reproduction or verification steps in the final assistant answer text, not in commentary.
- If you need a progress update before the handoff, keep it separate and restate any required user action only in the final visible handoff.
- Do not emit the same handoff text as both `commentary` and final-answer text, because some Codex clients can render both copies separately.

Visible-handoff requirements:

- The reproduction or verification request must be the last user-visible output in that turn.
- In Codex-style hosts, do not place required user steps in commentary, progress updates, tool narration, edit summaries that can collapse, or any other internal/disclosure-only surface.
- If the official request-user-input form is available in the current host mode, make it the final action and then wait.
- If the host does not support that form in the current mode, send a normal assistant message and make the last section the numbered reproduction or verification steps.
- If you need to show hypotheses, applied log points, or temporary edits, show them before the handoff.
- After sending the handoff, stop. Do not continue into log analysis, implementation, or extra tool work until the user completes the requested action.

Preferred form-based request when supported:

- Use the host's official request-user-input flow for a short reproduction prompt when it is available in the current mode.
- Keep the prompt to 1-3 short questions or confirmation actions because that is the documented form shape.
- Match the host's actual completion mechanic exactly instead of inventing synthetic labels.

Fallback text request when no form capability is available:

```text
1. Reproduce the bug in the smallest realistic flow.
2. Restart any required app or service first if the new logs are not loaded automatically.
3. <HOST_COMPLETION_INSTRUCTION>
```

Examples:

- Button-based host: `Press Proceed when done.`
- Task-based host: `Mark the task as fixed when done.`
- Chat-only host: `Reply with "done" when the reproduction completes.`

Apply the same visible-handoff rules to post-fix verification prompts.

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
- When you started the bundled collector, stop it with the dashboard token, delete every path in `ownedArtifacts`, verify those exact paths no longer exist, then delete the root-cause Markdown document after success unless the user explicitly asked to keep evidence.
- If a hypothesis is rejected, remove the code changes based on that hypothesis instead of letting speculative changes accumulate.
