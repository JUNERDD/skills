# Runtime Debugging Reference

Use this reference for exact collector, instrumentation, evidence-reading, and cleanup operations.

## Table of contents

- Session selection
- Resolve Python and skill root
- Validate the coverage plan
- Start a local session
- Ready-file contract
- Session commands
- Health, clear, and restart rules
- Location synchronization
- Structured log format
- Browser routing
- Non-JavaScript guidance
- Volume controls
- Evidence summarization
- Reading raw evidence
- Dashboard startup and recovery
- CORS and security
- Reproduction handoff
- Root-cause repair verification
- Final cleanup

## Session selection

Prefer this order:

1. Reuse an authoritative session supplied by the host or user. Preserve its endpoint, session ID, log path, token, ready file, and cleanup ownership exactly.
2. Otherwise use the bundled `scripts/debug_session.py` CLI to start the local collector.
3. Use direct file append only when HTTP ingestion is unavailable and the runtime has no lightweight HTTP client.

The collector and lifecycle CLI are self-contained and use Python standard-library code.

Only delete artifacts created by the current skill invocation. Never delete files owned by a host-provided session.

## Resolve Python and skill root

Resolve `<SKILL_ROOT>` to the installed `debug` skill directory. Resolve Python 3 before validating the coverage plan or using other bundled Python scripts:

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

If Python 3 is unavailable, do not claim that the bundled coverage-plan gate passed. Use a host-provided equivalent only when it validates the coverage-plan requirements. If neither validator nor an authoritative evidence session exists, explain which gate cannot start.

## Validate the coverage plan

Validate before adding temporary probes and again after their final locations and mappings are current:

```bash
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_plan.py validate \
  <PLAN_FILE> \
  --format markdown
```

Treat exit code `0` as a passed structural gate, `1` as plan validation failure, and `2` as an unreadable or malformed JSON artifact. Runtime checks still need to prove source locations, collector health, delivery, and observer capacity.

## Start a local session

Use a unique session ID. The CLI starts the collector detached, waits for the ready file, and prints the ready payload as JSON.

```bash
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py start \
  --workspace-root "$PWD" \
  --session-id "checkout-$(date +%s)"
```

The default is to open the live dashboard automatically. The collector publishes its ready file, starts serving HTTP, verifies the health endpoint, and only then asks the operating system to open the dashboard. Use `--no-open-dashboard` or its `--headless` alias for headless, CI, container-only, remote, or CLI-only operation. Add `--ide <IDE_ID>` only when source-opening from the dashboard is useful.

Automatic browser opening is non-fatal and never part of the evidence gate. Inspect `dashboardOpenPending`, `dashboardOpenSucceeded`, `dashboardOpenError`, and `dashboardFrontendOpenRecorded` only when dashboard availability matters. `dashboardOpenSucceeded` means an opener accepted the request; `dashboardFrontendOpenRecorded` confirms that the page loaded, not that instrumentation coverage is sufficient.

The CLI writes session artifacts under `<workspace>/.debug-logs/` unless `--artifact-dir` is supplied. Capture the returned `readyFile` path and use it for every later command.

Do not manually start a second collector for the same ready file. If `start` reports an active healthy session, reuse or stop it first.

## Ready-file contract

Treat the ready file as authoritative. It includes at least:

```json
{
  "endpoint": "http://127.0.0.1:43125/ingest",
  "batchEndpoint": "http://127.0.0.1:43125/ingest/batch",
  "dashboardUrl": "http://127.0.0.1:43125/",
  "dashboardToken": "<SESSION_TOKEN>",
  "dashboardAutoOpenEnabled": true,
  "dashboardOpenPending": false,
  "dashboardOpenAttempted": true,
  "dashboardOpenSucceeded": true,
  "dashboardFrontendOpenRecorded": true,
  "stateUrl": "http://127.0.0.1:43125/api/state",
  "logsUrl": "http://127.0.0.1:43125/api/logs",
  "syncLocationsUrl": "http://127.0.0.1:43125/api/locations/sync",
  "clearUrl": "http://127.0.0.1:43125/api/clear",
  "shutdownUrl": "http://127.0.0.1:43125/api/shutdown",
  "healthUrl": "http://127.0.0.1:43125/health",
  "ingestEventCountLimited": false,
  "ingestMaxJsonBodyBytes": 4194304,
  "ingestAcceptedEventCount": 0,
  "indexLagBytes": 0,
  "logFile": "/workspace/.debug-logs/checkout-1733456789.ndjson",
  "locationStateFile": "/workspace/.debug-logs/checkout-1733456789.locations.json",
  "serviceLogFile": "/workspace/.debug-logs/checkout-1733456789.service.log",
  "readyFile": "/workspace/.debug-logs/checkout-1733456789.json",
  "ownedArtifacts": ["..."],
  "sessionId": "checkout-1733456789",
  "workspaceRoot": "/workspace",
  "pid": 12345
}
```

When the collector restarts on another port, replace stale endpoint constants in all active temporary probes before reproduction.

The dashboard state response keeps high-cardinality count lists small so polling does not compete with ingestion. Read `summary.countCardinality`, `summary.countListLimit`, and `summary.countListsTruncated` when a list such as `correlationCounts` is abbreviated. This is a presentation bound only: `summary.totalEntries`, the paginated logs API, and the NDJSON evidence file still represent every accepted event.

`ingestEventCountLimited: false` means the collector does not reject a batch because it contains more than an arbitrary number of events. `ingestMaxJsonBodyBytes` is a network-frame byte boundary, not a total log-count boundary. Continue with subsequent acknowledged frames until the page-local queue is empty. During high-volume capture, inspect `ingestAcceptedEventCount`, `ingestRequestCount`, `indexLagBytes`, `indexErrorCount`, and `indexLastError`; ingestion acknowledgement is intentionally independent from dashboard indexing.

## Session commands

Use the lifecycle CLI rather than reimplementing token handling and cleanup in shell snippets.

```bash
# Health only
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py health \
  --ready-file <READY_FILE>

# Full state summary
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py state \
  --ready-file <READY_FILE>

# Clear the current session log and in-memory counters
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py clear \
  --ready-file <READY_FILE>

# Retry browser opening for a healthy session and print the URL/status
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py open-dashboard \
  --ready-file <READY_FILE>

# Replace the complete active instrumentation-location set
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py sync-locations \
  --ready-file <READY_FILE> \
  --locations-file <PLAN_FILE>

# Stop and remove collector-owned artifacts
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py stop \
  --ready-file <READY_FILE>
```

Use `--keep-artifacts` on `stop` only when the user asks to retain raw evidence. Use `--delete-root-cause-document <PATH>` only after a terminal diagnosis or successful repair verification and after updating the document's cleanup status.

## Health, clear, and restart rules

Before every deliberate recording pass:

1. Run `health` or `state`.
2. If the collector is unreachable, start a new session and adopt the new ready file.
3. Patch every temporary endpoint constant when the port changed.
4. Preserve needed evidence from the previous run.
5. Run `clear`.
6. Use a fresh `runId`.

Do not clear another session's log. Do not use collector stdout as application evidence; read the NDJSON file.

Useful endpoint search:

```bash
rg -n "http://127\\.0\\.0\\.1:[0-9]+/ingest|#region agent log|probeId" <instrumented-paths>
```

## Location synchronization

Use the validated coverage plan as the location source whenever possible. `sync-locations` accepts its top-level `probes` array and projects only `location`, `hypothesisIds`, and `probeId`. It also accepts a direct `locations` payload for cleanup and host-provided operator input:

```json
{
  "locations": [
    {
      "location": "src/cart.ts:118",
      "hypothesisIds": ["H-cache-stale", "H-race-overwrite"],
      "probeId": "cart.commit.before"
    },
    {
      "location": "src/cart.ts:141",
      "hypothesisIds": ["H-race-overwrite"],
      "probeId": "cart.commit.after"
    }
  ]
}
```

The collector accepts and validates `location`, `hypothesisIds`, and `probeId` or `probeIds`; the location sidecar retains those mappings. Use replace semantics: send the full active set after adding, moving, or deleting probes. Sync an empty `locations` list after removing all instrumentation. Validate a coverage plan with `scripts/debug_plan.py` before syncing it.

Each location must be relative to `workspaceRoot`, include a line number, resolve to an existing file, and remain inside the workspace.

The location-state sidecar is a near-real-time operational view. Runtime updates are debounced to avoid rewriting a large JSON file for every event; sync, clear, startup, and shutdown force a current write. Use the NDJSON file as evidence of record.

## Structured log format

Use one JSON object per NDJSON line:

```json
{
  "sessionId": "checkout-1733456789",
  "runId": "initial",
  "parentCorrelationId": "save-flow-8f31",
  "operationId": "save-B",
  "requestId": "req-42",
  "correlationId": "flow-8f31",
  "sequence": 12,
  "probeId": "cart.commit.before",
  "hypothesisIds": ["H-cache-stale", "H-race-overwrite"],
  "location": "src/cart.ts:118",
  "phase": "mutation",
  "event": "before_commit",
  "level": "debug",
  "message": "cart state before persistence",
  "data": {
    "cartVersion": 7,
    "itemCount": 3,
    "payloadHash": "d8f1..."
  },
  "timestamp": 1733456789000,
  "monotonicMs": 4812.4
}
```

Required for planned probes:

- `runId`
- `probeId`
- `hypothesisIds` or backward-compatible `hypothesisId`
- `location`
- `event`
- `timestamp`

Required when work crosses async, concurrent, process, service, queue, persistence, or browser-lifecycle boundaries:

- `parentCorrelationId` or another durable flow identifier when child operations fan out
- `operationId` and `requestId` when those boundaries exist
- `correlationId`
- `sequence`
- attempt/generation/version metadata in `data`

Keep values bounded and JSON-serializable. Log serialization must not throw into product code.

## Browser routing

Read [browser-debugging.md](./browser-debugging.md) before adding client instrumentation, wrapping `fetch`, collecting high-frequency browser streams, or crossing navigation and reload boundaries. Keep browser-specific transport details out of non-browser investigations.

## Non-JavaScript guidance

Use `batchEndpoint` for serialized frames and `endpoint` for a single event. Do not impose an event-count cap when complete request coverage is required. Split only by request bytes or runtime-specific payload constraints, then continue sending subsequent frames until every event is acknowledged.

If the runtime has no lightweight HTTP client, append a compact JSON line to `logFile` using append mode and close promptly. When appending directly:

- Use the same schema.
- Serialize under a process-safe lock when multiple writers share a file.
- Keep each object on one physical line.
- Expect the collector to incrementally index the file on the next state read or background tail pass.
- Do not mix unrelated sessions in one file.

## Volume controls

For general loops or hot paths unrelated to complete `fetch` capture, select and document an information-preserving control:

```text
first 5 per correlation
once per entity/version
only when selected fields change
only when invariant fails
aggregate count and emit at flow end
deterministic sample by correlation ID
```

Emit suppression metadata such as `recordedCount`, `droppedCount`, and `limit` so missing general-purpose probe events are interpretable.

When the failure contract requires complete application-`fetch` coverage, follow the browser reference. Do not apply count-based suppression to required start and terminal lifecycle events.

Keep each event small. Use hashes, lengths, selected fields, and bounded error messages instead of complete payloads or state trees.

## Evidence summarization

Summarize large logs before loading raw entries into model context:

```bash
"$PYTHON_BIN" <SKILL_ROOT>/scripts/summarize_debug_log.py \
  <LOG_FILE> \
  --run-id initial \
  --expected-probes-file <PLAN_FILE> \
  --format markdown \
  --timeline-limit 80 \
  --max-examples 2
```

Useful filters:

```bash
--correlation-id flow-8f31
--parent-correlation-id save-flow-8f31
--operation-id save-B
--request-id req-42
--hypothesis-id H-race-overwrite
--probe-id cart.commit.before
--format json
```

The summarizer reports valid/invalid lines, probe and hypothesis coverage, correlations, event counts, sequence gaps/regressions, error-like events, and a bounded timeline. It does not infer the root cause; use it to select raw evidence.

## Reading raw evidence

After summarization:

1. Verify the expected run and correlation exist.
2. Verify flow start/end sentinels.
3. Check missing planned probes and suppression counters.
4. Identify the earliest invalid value, invariant failure, or invalid ordering.
5. Read the raw NDJSON lines for that causal interval.
6. Cite probe ID, location, run, correlation, sequence, and selected data.
7. Evaluate every hypothesis, including `NOT_REACHED` paths.

Do not paste the entire NDJSON file into chat when a compact summary and targeted lines suffice.

## Dashboard startup and recovery

The collector serves a same-origin dashboard with state, bounded log windows, and active source locations. Normal local sessions open it automatically after the HTTP health endpoint responds; this ordering avoids a browser landing on a port before the request loop is ready.

Use this recovery sequence only when the operator wants the dashboard and the console does not appear or `dashboardFrontendOpenRecorded` remains `false`:

1. Read the ready payload and confirm `dashboardAutoOpenEnabled` is `true`.
2. Check `dashboardOpenPending`, `dashboardOpenSucceeded`, `dashboardOpenError`, and `dashboardOpenAttempts`.
3. Run `debug_session.py open-dashboard --ready-file <READY_FILE>`, then re-query state. The command skips reopening when the frontend is already recorded, retries platform and Python browser openers, waits briefly for the page-load callback, and always returns `dashboardUrl`.
4. Make no more than two fallback attempts for one session. Record and surface both opener failures and accepted requests that never produced a frontend callback.
5. If the page still does not load, surface the exact URL and errors. Do not restart a healthy collector merely to open the page.
6. Continue evidence collection through the CLI and NDJSON file.

Dashboard state must not block logging, reproduction, analysis, or cleanup and must not appear in the coverage plan as evidence.

## CORS and security

The collector binds to `127.0.0.1` by default.

- Browser instrumentation may post directly to `/ingest`; the collector supplies ingest CORS headers.
- Mutating operator APIs require the session-scoped `X-Debug-Dashboard-Token`.
- Browser operator calls must be same-origin.
- The lifecycle CLI reads the token from the ready file.
- Do not expose the collector publicly or log its token into product telemetry.
- Do not create a project-local proxy unless direct browser-to-collector delivery is proven impossible.

## Reproduction handoff

When reproduction is user-owned, present:

1. A concise hypothesis-family summary
2. Probe count, shared-probe count, mapped-hypothesis coverage, causal-boundary coverage, and volume controls
3. Residual ambiguities
4. Exact reproduction steps

Make the reproduction request the final visible section and stop. Use the host's real completion action when available; otherwise ask for a short reply such as `done`. When reproduction is agent-owned, execute it directly after the runtime gate instead of asking the user.

Use one `runId` for the clean initial reproduction. Do not mix setup activity with the failing flow.

## Authorized root-cause repair verification

- Apply this section only when repair is authorized. Keep discriminating probes active while applying the repair.
- Eliminate the evidence-proven causal mechanism and restore its violated invariant or contract at the owning boundary.
- Treat change size as a constraint, not the objective. After establishing causal sufficiency, choose the narrowest safe, coherent repair; include every causally necessary file or layer and exclude unrelated cleanup.
- Do not substitute a smaller downstream guard, fallback, or coercion while the proven causal mechanism remains active.
- Use a new `runId`, such as `post-repair`.
- Reproduce the same flow and compare the same probe IDs and invariants.
- Treat a missing post-repair symptom as insufficient when the flow itself did not complete.
- If verification fails, preserve the failed-repair evidence and update the same investigation document.

## Final cleanup

After a diagnosis-only evidence handoff completes, or after an authorized repair verifies:

1. Remove every temporary probe, helper, endpoint constant, header, and debug-only import.
2. For a session owned by this invocation, sync `{"locations": []}`. For a host-provided or shared session, remove or report only this invocation's locations according to host policy; never replace shared location state with an empty set.
3. Update any investigation document with the terminal diagnosis or verification status and cleanup decision.
4. Run `debug_session.py stop --ready-file <READY_FILE>` only when this invocation started and owns the session. Never stop a host-provided or shared collector.
5. For an owned session, verify every `ownedArtifacts` path is absent unless `--keep-artifacts` was requested.
6. Remove an empty `.debug-logs/` directory only when this invocation created it.
7. Delete or retain the coverage plan and investigation document according to [root-cause-document.md](./root-cause-document.md).

Do not use Git status as cleanup proof because `.debug-logs/` is commonly ignored.
