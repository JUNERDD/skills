# Runtime Debugging Reference

Use this reference for exact collector, instrumentation, evidence-reading, and cleanup operations.

## Table of contents

- Session selection
- Resolve Python and skill root
- Start a local session
- Ready-file contract
- Session commands
- Health, clear, and restart rules
- Location synchronization
- Structured log format
- JavaScript and TypeScript template
- Non-JavaScript guidance
- Volume controls
- Evidence summarization
- Reading raw evidence
- Optional dashboard
- CORS and security
- Reproduction handoff
- Fix verification
- Final cleanup

## Session selection

Prefer this order:

1. Reuse an authoritative session supplied by the host or user. Preserve its endpoint, session ID, log path, token, ready file, and cleanup ownership exactly.
2. Otherwise use the bundled `scripts/debug_session.py` CLI to start the local collector.
3. Use direct file append only when HTTP ingestion is unavailable and the runtime has no lightweight HTTP client.

The collector and lifecycle CLI are self-contained and use Python standard-library code.

Only delete artifacts created by the current skill invocation. Never delete files owned by a host-provided session.

## Resolve Python and skill root

Resolve `<SKILL_ROOT>` to the installed `debug` skill directory. Resolve Python 3 before using bundled scripts:

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

If Python 3 is unavailable and no authoritative session exists, explain that evidence collection cannot start in the configured mode.

## Start a local session

Use a unique session ID. The CLI starts the collector detached, waits for the ready file, and prints the ready payload as JSON.

```bash
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py start \
  --workspace-root "$PWD" \
  --session-id "checkout-$(date +%s)"
```

The default is headless. Add `--open-dashboard` only when the user wants the live dashboard. Add `--ide <IDE_ID>` only when source-opening from the dashboard is useful.

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
  "stateUrl": "http://127.0.0.1:43125/api/state",
  "logsUrl": "http://127.0.0.1:43125/api/logs",
  "syncLocationsUrl": "http://127.0.0.1:43125/api/locations/sync",
  "clearUrl": "http://127.0.0.1:43125/api/clear",
  "shutdownUrl": "http://127.0.0.1:43125/api/shutdown",
  "healthUrl": "http://127.0.0.1:43125/health",
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

# Replace the complete active instrumentation-location set
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py sync-locations \
  --ready-file <READY_FILE> \
  --locations-file <LOCATIONS_JSON>

# Stop and remove collector-owned artifacts
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py stop \
  --ready-file <READY_FILE>
```

Use `--keep-artifacts` on `stop` only when the user asks to retain raw evidence. Use `--delete-root-cause-document <PATH>` only after final verification and after updating the document's cleanup status.

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

Create a JSON file containing the complete current set of temporary probe locations:

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

The collector accepts and validates `location`, `hypothesisIds`, and `probeId` or `probeIds`; the location sidecar retains those mappings. Use replace semantics: send the full active set after adding, moving, or deleting probes. Sync an empty list after removing all instrumentation.

Each location must be relative to `workspaceRoot`, include a line number, resolve to an existing file, and remain inside the workspace.

The location-state sidecar is a near-real-time operational view. Runtime updates are debounced to avoid rewriting a large JSON file for every event; sync, clear, startup, and shutdown force a current write. Use the NDJSON file as evidence of record.

## Structured log format

Use one JSON object per NDJSON line:

```json
{
  "sessionId": "checkout-1733456789",
  "runId": "initial",
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

Required for one-shot probes:

- `runId`
- `probeId`
- `hypothesisIds` or backward-compatible `hypothesisId`
- `location`
- `event`
- `timestamp`

Required when concurrency or fan-out is possible:

- `correlationId`
- `sequence`
- attempt/generation/version metadata in `data`

Keep values bounded and JSON-serializable. Log serialization must not throw into product code.

## JavaScript and TypeScript template

Prefer one small file-local helper per runtime boundary instead of repeating a large `fetch` block at every probe. Use the endpoint, batch endpoint, and session values from the ready file. The helper below micro-batches probes emitted in the same turn, bounds each request, and never throws into product code.

```ts
// #region agent log config
const debugEndpoint = '<ENDPOINT>'
const debugBatchEndpoint = '<BATCH_ENDPOINT>'
const debugSessionId = '<SESSION_ID>'
const debugBatchSize = 20
let debugSequence = 0
let debugFlushScheduled = false
const debugQueue: Array<Record<string, unknown>> = []
const scheduleDebugFlush = typeof queueMicrotask === 'function'
  ? queueMicrotask
  : (callback: () => void) => { void Promise.resolve().then(callback) }

function flushDebugProbes() {
  debugFlushScheduled = false
  const events = debugQueue.splice(0, debugBatchSize)
  if (events.length === 0) return

  try {
    const requests = debugBatchEndpoint
      ? [{ url: debugBatchEndpoint, body: JSON.stringify({ events }) }]
      : events.map((event) => ({ url: debugEndpoint, body: JSON.stringify(event) }))
    for (const request of requests) {
      void fetch(request.url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Debug-Session-Id': debugSessionId,
        },
        body: request.body,
        keepalive: true,
      }).catch(() => {})
    }
  } catch {
    // Temporary debugging must never affect product behavior.
  }

  if (debugQueue.length > 0 && !debugFlushScheduled) {
    debugFlushScheduled = true
    scheduleDebugFlush(flushDebugProbes)
  }
}

function debugProbe(input: {
  probeId: string
  hypothesisIds: string[]
  location: string
  phase: string
  event: string
  correlationId: string
  message: string
  data?: Record<string, unknown>
}) {
  try {
    debugQueue.push({
      sessionId: debugSessionId,
      runId: 'initial',
      correlationId: input.correlationId,
      sequence: ++debugSequence,
      probeId: input.probeId,
      hypothesisIds: input.hypothesisIds,
      location: input.location,
      phase: input.phase,
      event: input.event,
      message: input.message,
      data: input.data ?? {},
      timestamp: Date.now(),
      monotonicMs: typeof performance !== 'undefined' ? performance.now() : undefined,
    })
    if (!debugFlushScheduled) {
      debugFlushScheduled = true
      scheduleDebugFlush(flushDebugProbes)
    }
  } catch {
    // Temporary debugging must never affect product behavior.
  }
}
// #endregion
```

For runtimes without `queueMicrotask`, use a resolved Promise or send a single event to `endpoint`. Keep batches below 200 events and comfortably below browser `keepalive` payload limits; 20 small bounded events is the default. Do not allow an unbounded client queue.

Call the helper inside collapsible temporary regions when the language supports them. Remove the helper, endpoint constants, and calls after successful verification.

For concurrent flows, use a sequence counter scoped to a correlation rather than one global counter when practical. Emit a terminal sentinel before navigation or teardown so the last batch is scheduled.

## Non-JavaScript guidance

Prefer `batchEndpoint` when the runtime can buffer a small bounded burst; otherwise use the single-event `endpoint`. If the runtime has no lightweight HTTP client, append a compact JSON line to `logFile` using append mode and close immediately.

When appending directly:

- Use the same schema.
- Serialize under a process-safe lock when multiple writers share a file.
- Keep each object on one physical line.
- Expect the collector to rehydrate the file on the next state read.
- Do not mix unrelated sessions in one file.

## Volume controls

Before instrumenting a loop or hot path, select and document a control:

```text
first 5 per correlation
once per entity/version
only when selected fields change
only when invariant fails
aggregate count and emit at flow end
deterministic sample by correlation ID
```

Emit suppression metadata such as `recordedCount`, `droppedCount`, and `limit` so missing events are interpretable.

Keep each event small. Use hashes, lengths, selected fields, and bounded error messages instead of complete payloads or state trees. Batch transport reduces request and file-open overhead but does not justify larger payloads or an unbounded queue.

## Evidence summarization

Summarize large logs before loading raw entries into model context:

```bash
"$PYTHON_BIN" <SKILL_ROOT>/scripts/summarize_debug_log.py \
  <LOG_FILE> \
  --run-id initial \
  --format markdown \
  --timeline-limit 80 \
  --max-examples 2
```

Useful filters:

```bash
--correlation-id flow-8f31
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

## Optional dashboard

The collector can serve a same-origin dashboard with state, log windows, and active source locations. It is optional and must not block evidence collection.

Start with `--open-dashboard` only when the user wants it. Otherwise use ready-file values, CLI commands, and the NDJSON file. Do not spend reproduction time proving that the dashboard frontend opened.

## CORS and security

The collector binds to `127.0.0.1` by default.

- Browser instrumentation may post directly to `/ingest`; the collector supplies ingest CORS headers.
- Mutating operator APIs require the session-scoped `X-Debug-Dashboard-Token`.
- Browser operator calls must be same-origin.
- The lifecycle CLI reads the token from the ready file.
- Do not expose the collector publicly or log its token into product telemetry.
- Do not create a project-local proxy unless direct browser-to-collector delivery is proven impossible.

## Reproduction handoff

Before the first reproduction request, present:

1. A concise hypothesis-family summary
2. Probe count, shared-probe count, mapped-hypothesis coverage, causal-boundary coverage, and volume controls
3. Residual ambiguities
4. Exact reproduction steps

Make the reproduction request the final visible section and stop. Use the host's real completion action when available; otherwise ask for a short reply such as `done`.

Use one `runId` for the clean initial reproduction. Do not mix setup activity with the failing flow.

## Fix verification

- Keep discriminating probes active while applying the fix.
- Use the smallest change that addresses the proven origin, not only the downstream symptom.
- Use a new `runId`, such as `post-fix`.
- Reproduce the same flow and compare the same probe IDs and invariants.
- Treat a missing post-fix symptom as insufficient when the flow itself did not complete.
- If verification fails, preserve the failed-fix evidence and update the same investigation document.

## Final cleanup

After verification succeeds:

1. Remove every temporary probe, helper, endpoint constant, header, and debug-only import.
2. Sync `{"locations": []}`.
3. Update the investigation document with verification and cleanup status.
4. Run `debug_session.py stop --ready-file <READY_FILE>`.
5. Verify every `ownedArtifacts` path is absent unless `--keep-artifacts` was requested.
6. Remove an empty `.debug-logs/` directory.
7. Delete or retain the investigation document according to [root-cause-document.md](./root-cause-document.md).

Do not use Git status as cleanup proof because `.debug-logs/` is commonly ignored.
