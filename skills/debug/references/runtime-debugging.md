# Runtime Debugging Reference

Use this reference for exact collector, instrumentation, evidence-reading, and cleanup operations.

## Table of contents

- Session selection
- Resolve Python and skill root
- Validate the coverage plan
- Resume the active local session
- Start a local session
- Ready-file contract
- Collector-wide recording gate
- Session commands
- Health, clear, and restart rules
- Location synchronization
- Structured log format
- Browser routing
- Non-JavaScript guidance
- Event cardinality and payload controls
- Evidence summarization
- Reading raw evidence
- Dashboard startup and recovery
- CORS and security
- Reproduction handoff
- In-scope root-cause repair verification
- Final cleanup

## Session selection

Treat lifecycle scope as `investigation > collector session > run`. The investigation is one reported bug tracked by one evolving ledger. A collector session is the concrete process, exact ready file, endpoint, port, dashboard, and evidence file used by that investigation. A run is one failing, blind-spot, or verification pass identified by `runId`. User replies, evidence analysis, context compaction, repair work, and a fresh `runId` do not create a collector-session boundary.

Prefer this order:

1. For a continuing investigation, read its ledger and run `scripts/debug_session.py resume --ready-file <READY_FILE>` with the exact active ready file recorded there. A successful resume must reuse its endpoint, session ID, log path, token, port, dashboard, and cleanup ownership without starting another collector or reopening browser UI.
2. When establishing the investigation's initial session, reuse an authoritative session supplied by the host or user and record it in the ledger.
3. Otherwise use the bundled `scripts/debug_session.py` CLI to start the local collector once.
4. If the runtime cannot use the collector's acknowledged HTTP contract, stop at the instrumentation gate. Do not append planned-probe evidence directly to the NDJSON file or substitute an unacknowledged emitter.

Never scan `.debug-logs/`, the workspace, process lists, or port ranges to guess which session belongs to an investigation. The ledger's exact active ready file is the only automatic continuation source. Start a replacement only when that file is missing or its collector is unreachable, or when the user or host explicitly requires isolation or replacement. Preserve the previous evidence and append both the prior session and the replacement reason to the same investigation ledger.

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

## Resume the active local session

Before any `start` on a continuing investigation, recover the exact active ready file from its ledger:

```bash
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py resume \
  --ready-file <READY_FILE>
```

`resume` validates that exact ready file and checks its collector. It does not discover other sessions, start a process, clear evidence, mutate the session, or open/reopen the dashboard. A successful result reports `sessionAction: "reused"`; its `dashboardRecovery` is a no-op snapshot with zero fallback attempts. `lifecycleMode: "local-cli"` identifies the command path, not cleanup ownership: preserve ownership from the investigation ledger. Use the returned ready payload and the same `<READY_FILE>` for every later command; do not call `start` or `open-dashboard` merely because the user replied, analysis resumed, context was compacted, repair began, or a new `runId` was assigned.

If the recorded ready file is missing or its collector is unreachable, preserve the prior session's evidence reference, mark that session accordingly in the ledger, and only then establish a replacement. An explicit user or host isolation/replacement directive may also establish another session, but must record its reason and resulting active ready file in the same ledger.

## Start a local session

Use `start` only after session selection proves that the investigation has no resumable active session or that replacement is allowed. Use a unique session ID for the newly established or replacement collector, not for each run. The CLI starts the collector detached, waits for the ready file, and prints the ready payload as JSON with `sessionAction: "started"`. `start` remains create-only: if the exact ready file already names a healthy collector, use `resume` explicitly so changed startup flags are never silently ignored.

```bash
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py start \
  --workspace-root "$PWD" \
  --session-id "checkout-$(date +%s)"
```

The default is to open the live dashboard automatically. The collector publishes its ready file, starts serving HTTP, verifies the health endpoint, and only then asks the operating system to open the dashboard. The session CLI waits for `dashboardFrontendOpenRecorded` and, when needed, makes at most two fallback open attempts. Use `--no-open-dashboard` or its `--headless` alias only when the collector host is verified to have no usable local graphical browser, such as CI, container-only, or remote operation. A user-owned run, a wait for user reproduction, missing agent browser control, or a prohibition on agent-operated product browsing does not qualify. Add `--ide <IDE_ID>` only when source-opening from the dashboard is useful.

Automatic browser opening is non-fatal and never part of the evidence gate. The `start` result adds `dashboardRecovery` with `frontendConfirmed`, `fallbackAttemptCount`, `dashboardUrl`, and `error`. Preserve those values and always show the refreshed dashboard status and URL before a user-owned reproduction. For a browser-capable local session, recover an accidental `disabled` state with `open-dashboard` before showing the refreshed line; proceed directly with `disabled` only for a verified no-local-GUI host. `dashboardOpenSucceeded` means an opener accepted the request, while `dashboardFrontendOpenRecorded` confirms that the page loaded. Neither field proves instrumentation coverage or that a tab remains open.

The CLI writes session artifacts under `<workspace>/.debug-logs/` unless `--artifact-dir` is supplied. Capture the returned `readyFile` path, record it as the investigation ledger's active ready file, and use it for every later command and continuation.

Do not manually start a second collector for the same investigation. The CLI rejects a healthy duplicate only when it sees the same ready file, so changing the session ID or ready-file name is not a valid way to bypass the ledger-first resume gate. If `start` reports an active healthy session, reuse or stop it according to its ownership before proceeding.

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
  "freezeRecordingUrl": "http://127.0.0.1:43125/api/recording/freeze",
  "resumeRecordingUrl": "http://127.0.0.1:43125/api/recording/resume",
  "shutdownUrl": "http://127.0.0.1:43125/api/shutdown",
  "healthUrl": "http://127.0.0.1:43125/health",
  "recordingFrozen": false,
  "recordingGeneration": 0,
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

The dashboard state response keeps high-cardinality count lists small so polling does not compete with ingestion. Read `summary.countCardinality`, `summary.countListLimit`, and `summary.countListsTruncated` when a list such as `correlationCounts` is abbreviated. This is a presentation bound only: `summary.totalEntries`, the paginated logs API, and the NDJSON evidence file still represent every persisted event.

`ingestEventCountLimited: false` means the collector does not reject a batch because it contains more than an arbitrary number of events. `ingestMaxJsonBodyBytes` is a network-frame byte boundary, not a total log-count boundary. Split oversized frames by bytes while preserving one independently serialized event for every active-probe occurrence. For a live producer, compare its occurrence and enqueue checkpoint with the transport's acknowledged watermark instead of waiting for the queue to become empty; require a final empty drain only after production stops. During high-volume capture, inspect `ingestAcceptedEventCount`, `ingestRequestCount`, `indexLagBytes`, `indexErrorCount`, and `indexLastError`, but do not use accepted-request counters or index progress as proof of persistence. Successful evidence requires the checkpoint's occurrence count, enqueued event count, and persisted NDJSON record count to agree with zero rejected, discarded, or missing events.

## Collector-wide recording gate

The dashboard's single `Freeze` / `Resume` control operates the collector-wide HTTP-ingest write gate, not a tab-local snapshot. The UI continues polling authoritative state while frozen. Every open dashboard tab, a reloaded dashboard, later user replies, analysis turns, and fresh run IDs observe the same collector recording mode and generation. Freezing does not stop or disconnect the collector: `/health` remains `running`, while dashboard state reports `frozen` and the badge shows `FROZEN`.

`Freeze` is an explicit user-controlled action linearized with `/ingest` and `/ingest/batch` writes. Once it takes effect, events that arrive through those endpoints receive a terminal acknowledgement with `discardedEvents` and a discard disposition, but they are not appended to NDJSON and are not added to the index. Legacy `accepted` / `acceptedEvents` counts mean terminally resolved, not necessarily persisted; classify evidence with `persistedEvents` and `discardedEvents`. For a generation-aware frame with a stable `batchId`, a terminal discard resolves the transport frame so it cannot be delayed and replayed as evidence. Any discarded active-probe event makes the run incomplete, sets or implies `continuityBroken`, and can never count as successful evidence.

Each real Freeze or Resume transition advances `recordingGeneration`; repeating the operation in its already-current state is idempotent. The bundled transport stamps the generation when an event enters its queue and keeps one stable `batchId` across retries. `Resume` opens writes only for the future generation. Queued or retried events stamped with an older generation remain terminally discarded after Resume, including when the original frozen acknowledgement was lost. A client that has not yet observed the new generation must refresh authoritative state or accept that its stale frame will be discarded and reported as a continuity break.

`Clear` remains available while frozen. It truncates the current NDJSON evidence and resets the documented current-log counters, but it neither unfreezes recording nor advances the generation. The collector linearizes Clear against the complete ingest commit, including the persistence-acknowledgement response write and flush: Clear occurs either before the append or after that acknowledgement attempt, never between the append and its reported `persistedEvents`. Resolved batch IDs remain protected from replay: retrying a batch that had persisted before Clear returns the terminal `discarded_cleared` disposition, rather than resurrecting old evidence or falsely claiming that the cleared evidence is still persisted. `Stop` still stops the collector.

Every non-empty outer `batchId` is authoritative. The collector overwrites any caller-supplied per-event `transportBatchId` with that outer ID before persistence and binds the ID at its first terminal outcome to both the event count and a SHA-256 digest of the canonicalized parsed event array. An idempotent retry must match that complete frame identity exactly whether the original outcome was persisted, discarded, or later changed to `discarded_cleared`. Reusing the ID with a different count or any different event content returns HTTP `409` with `transport_batch_id_conflict`; it never returns an accepted or duplicate-confirmed acknowledgement and never changes the recorded outcome or evidence. When a replacement collector hydrates a resolved outer ID from NDJSON but cannot recover its original canonical input digest, retries fail closed with the same conflict and make the run incomplete; they must never be re-appended or falsely confirmed as persisted.

`FROZEN` is not collector-health failure, a completed run, an acknowledged evidence checkpoint, or proof that all active probe events arrived. It is a user-controlled decision to stop persisting newly arriving evidence. `dashboard-status` reports frontend confirmation plus an independent `recording: live`, `recording: frozen`, or `recording: unknown`. Before a deliberate reproduction, run `resume-recording` when it reports frozen and then rerun `dashboard-status` until recording is live. Do not use session `resume` for this purpose: `resume` only validates and reuses the existing collector, whereas `resume-recording` changes its write gate without creating a process, port, dashboard, or session. If the user freezes during an active run, end that run as incomplete whenever any active-probe occurrence was discarded; Resume starts only a future valid interval and cannot rehabilitate the discarded interval.

## Session commands

Use the lifecycle CLI rather than reimplementing token handling and cleanup in shell snippets.

```bash
# Resume the exact active session recorded in the investigation ledger
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py resume \
  --ready-file <READY_FILE>

# Health only
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py health \
  --ready-file <READY_FILE>

# Full state summary
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py state \
  --ready-file <READY_FILE>

# Normalized dashboard line for a user-owned reproduction handoff
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py dashboard-status \
  --ready-file <READY_FILE>

# Clear the current session log and in-memory counters
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py clear \
  --ready-file <READY_FILE>

# Freeze collector HTTP ingestion; Clear remains available
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py freeze-recording \
  --ready-file <READY_FILE>

# Resume writes for the next recording generation
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py resume-recording \
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

Keep `resume` and `resume-recording` distinct. Session `resume` is the first command on investigation continuation and never changes recording mode. `resume-recording` is an explicit write-gate transition used only when authoritative state is frozen before a new recording pass.

Use `--keep-artifacts` on `stop` only when the user asks to retain raw evidence. Use `--delete-root-cause-document <PATH>` only after a terminal diagnosis or successful repair verification and after updating the document's cleanup status.

## Health, clear, and restart rules

Before every deliberate recording pass:

1. Read the same investigation ledger and recover its exact active ready file; do not search for alternatives.
2. Run `resume --ready-file <READY_FILE>` before any `start` attempt.
3. If resume succeeds, keep the same collector, endpoint, port, and dashboard. Do not call `start` or `open-dashboard` as part of the new pass.
4. If the ready file is missing or the collector is unreachable, or an explicit isolation/replacement directive applies, preserve needed evidence, append the prior session status and replacement reason to the ledger, start the replacement, and record its exact ready file as active.
5. Patch every temporary endpoint constant only when an allowed replacement changed the port.
6. Finish the previous run's summary and ledger transition, then preserve any raw evidence that must survive log truncation.
7. Remove superseded temporary probes, debug logging calls, and breakpoints or debugger statements; retain only instrumentation required by the next validated plan or verification run, and sync the exact remaining active location set.
8. Run `clear` on the active session so the next pass does not inherit the prior run's log records or counters. Clear is valid while frozen and does not change recording mode or generation.
9. Run `dashboard-status`. If it reports `recording: frozen`, run `resume-recording --ready-file <READY_FILE>` and then rerun `dashboard-status`; require `recording: live` before reproduction. If it remains `unknown`, refresh authoritative state and report the exact error rather than assuming writes are enabled.
10. Use a fresh `runId` within that session and initialize generation-aware transports from the refreshed `recordingGeneration`.
11. Inspect every active emitter and the initial transport status. Require one shared acknowledged transport for every browser or repeating producer, observable occurrence/enqueue/persistence counts, no direct `/ingest` path in those producers, and no multiple `/ingest` requests already pending. Fail the gate before reproduction when any condition is unmet.

A fresh `runId` separates evidence; it never requests or implies a fresh collector session.

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

The location-state sidecar is a near-real-time operational view. Only sidecar-file rewrites are debounced to avoid rewriting a large JSON file for every event; this never delays, replaces, combines, or suppresses event ingestion or NDJSON records. Sync, clear, startup, and shutdown force a current sidecar write. Use the NDJSON file as evidence of record.

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

Treat `message` as optional human-readable context rather than evidence identity. In the dashboard log stream, show the first non-empty value from `message`, `event`, and `probeId`; do not synthesize a `message` into the stored payload, and show `No message` only when all three are absent.

Required when work crosses async, concurrent, process, service, queue, persistence, or browser-lifecycle boundaries:

- `parentCorrelationId` or another durable flow identifier when child operations fan out
- `operationId` and `requestId` when those boundaries exist
- `correlationId`
- `sequence`
- attempt/generation/version metadata in `data`

Keep values bounded and JSON-serializable. Log serialization must not throw into product code, but a contained serialization failure must increment the transport's rejection count and make the run incomplete. Every execution occurrence of an active probe owns a separate immutable event object and, for repeating producers, a monotonic source or transport sequence; never reuse a mutable payload or storage slot for a later occurrence.

## Browser routing

Read [browser-debugging.md](./browser-debugging.md) before adding client instrumentation, wrapping `fetch`, collecting long-lived or high-frequency browser streams, or crossing navigation and reload boundaries. Keep browser-specific transport details out of non-browser investigations.

All browser probes, including a probe expected to execute only once, must acquire the registry-owned acknowledged transport through `getOrCreateBrowserDebugTransport` and enqueue through that one instance for the page realm and collector session. HMR must reuse it. Assign the only acquisition to one top-level canonical `const`; keep direct sinks and producer installers in that module, and export narrow functions instead of rebinding the transport in probe modules. Give replaceable wrappers, listeners, timers, and other producers a stable realm-owned key, a token-safe lease/disposer, and realm-persistent source sequence. Acquisition while the key is active must fail before cleanup; release the current lease before HMR reacquisition, which preserves state and source sequence without letting one source silently replace another. Do not issue browser `/ingest` requests directly. Call the shared transport exactly once for every active-probe occurrence and validate its occurrence, enqueue, acknowledgement, rejection, abandonment, discard, registry-conflict, fatal-protocol, and persisted-record counts at the planned checkpoint.

## Non-JavaScript guidance

Route every producer whose active probe can execute more than once through one shared, acknowledged transport for that process and run. This includes loops, callbacks, listeners, retries, workers, scheduled work, request handlers, and streams. Reuse the project's existing transport when present; otherwise implement the same generation-aware `/ingest/batch` contract. The transport must serialize and enqueue one immutable event synchronously for every occurrence, assign monotonic delivery identity, preserve FIFO order, retain each event until terminal acknowledgement, retry a frame with the same non-empty `batchId`, and expose occurrence, enqueue, acknowledgement, persisted, rejection, and discard counts. Split frames only by request bytes or a runtime payload boundary. Events from an older `recordingGeneration` receive a terminal discard and make the run incomplete rather than becoming post-Resume evidence.

Reserve the single-event `endpoint` (`/ingest`) for a bounded, one-shot, non-browser producer that emits exactly one planned event and can await its response before finishing. Stamp that event with the current authoritative `recordingGeneration`, parse the response, and require all of the following:

- the HTTP request succeeded;
- `persistedEvents` is exactly `1`;
- `discardedEvents` is exactly `0`.

Treat a timeout, missing or malformed response, any other count, or a legacy `accepted` / `acceptedEvents` value without the persistence fields as incomplete delivery. Never use `/ingest` from browser code or from a producer that can repeat. Never fire and forget it, issue one request per loop or callback occurrence, or treat Network-panel completion as a substitute for validating the response body.

Do not append planned-probe evidence directly to `logFile`. Direct writes bypass recording generations and the collector acknowledgement that distinguishes persisted from discarded events. If neither an existing acknowledged transport nor the collector contract can be used, report the instrumentation gate as blocked.

## Event cardinality and payload controls

For every active probe and bounded evidence interval, preserve this equality:

```text
source occurrence count = enqueued event count = persisted NDJSON record count
```

Serialize each occurrence independently and give it stable probe, correlation, and sequence identity. HMR release-then-reacquire must preserve the producer's source sequence and must neither miss nor duplicate the authoritative occurrence; an acquisition attempted while the old owner remains active invalidates the run instead of replacing that owner. A batch is only a wire frame containing those independent events; it must not merge identities, replace earlier events, wait for the business stream to close, or change the record count. At a live checkpoint, compare the source occurrence count and enqueue watermark for the captured prefix with the acknowledged and persisted prefix. After production stops, additionally require an empty queue and no in-flight request.

Choose fewer or better probe locations before activating the run when projected observer cost is unsafe. Once a probe is active, do not sample, throttle, debounce, keep only the first events, emit once per key, gate on changes or anomalies, aggregate, coalesce, overwrite, deduplicate, or otherwise suppress its occurrences. Do not reinterpret a rejected or lost occurrence as intentionally omitted.

Control observer cost by bounding payload content, not event count. Use selected scalar fields, hashes, lengths, enums, identifiers, compact timestamps, and bounded error messages instead of complete payloads, unbounded arrays, state trees, bodies, or stacks. Redact secrets before enqueueing. Bound the complete wire request—including `batchId` and JSON envelope—with `frameBytes`; reject an event before enqueue when its one-item request cannot fit. Any enrichment, serialization, queue-append, or oversized-event rejection, forced abandonment, registry conflict, queue loss, missing acknowledgement, terminal discard, count mismatch, or source/transport sequence gap makes the run incomplete.

Multiple simultaneous `/ingest` rows in `Pending` state are an instrumentation gate failure: they indicate a repeating or browser producer is bypassing the acknowledged shared transport. Stop the run, remove the direct emitter, route every occurrence through the single shared transport, and start a fresh run. One outstanding `/ingest/batch` frame from that transport may be normal while its acknowledgement is pending; validate it through transport status and collector persistence counts.

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

The summarizer reports persisted NDJSON record counts together with valid/invalid lines, probe and hypothesis coverage, correlations, causal-sequence gaps/regressions, browser transport-sequence gaps or duplicate/regressed sequences, error-like events, and a bounded timeline. It does not observe source occurrences or enqueue attempts by itself. Retain the producer's occurrence counter/checkpoint and the shared transport's enqueue and acknowledgement status, then reconcile them with the summarizer for the same `runId`, producer, probe set, and bounded interval. It does not infer the root cause; use it to select raw evidence and reject any interval whose occurrence, enqueue, and persisted counts differ or whose transport continuity is broken.

## Reading raw evidence

After summarization:

1. Verify the expected run and correlation exist.
2. Verify flow start and the configured terminal or observation-checkpoint sentinel.
3. Reconcile `source occurrences = enqueued events = persisted NDJSON records` for the same checkpoint. Use producer-side occurrence counts, the transport enqueue watermark/count, acknowledged persistence status, and the summarizer or raw NDJSON count; do not substitute `accepted` / `acceptedEvents`.
4. Require zero serialization or byte rejections, zero lost events, zero `discardedEvents`, `continuityBroken: false`, an acknowledged watermark through the checkpoint target, and no source/transport sequence gap. Any mismatch or discard makes the run incomplete and disqualifies it as successful evidence.
5. Inspect the ingestion shape before causal interpretation. Multiple simultaneous `/ingest` rows in `Pending` state are an instrumentation gate failure, not high-volume success: stop, replace the direct per-occurrence emitter with the acknowledged shared transport, clear the invalid interval, and reproduce under a fresh `runId`. A single pending `/ingest/batch` frame is evaluated through its acknowledgement and the same count reconciliation.
6. Check missing planned probes and identify the earliest invalid value, invariant failure, or invalid ordering only after the cardinality and transport gates pass.
7. Read the raw NDJSON lines for that causal interval.
8. Cite probe ID, location, run, correlation, sequence, and selected data.
9. Evaluate every hypothesis, including `NOT_REACHED` paths.

Do not paste the entire NDJSON file into chat when a compact summary and targeted lines suffice.

## Dashboard startup and recovery

The collector serves a same-origin dashboard with state, bounded log windows, and active source locations. Browser-capable local `start` sessions open it after the HTTP health endpoint responds, wait for the frontend callback, and make at most two fallback attempts before returning a non-fatal `dashboardRecovery` result.

Use this manual recovery sequence only for newly established sessions whose dashboard startup needs recovery, or when the user or host explicitly requests a dashboard open. It is never part of normal investigation continuation: if `resume` succeeds, keep the existing dashboard state, surface its exact URL, and skip this sequence.

1. Read the ready payload, capture `dashboardUrl`, and note whether `dashboardAutoOpenEnabled` is `true`.
2. Check `dashboardOpenPending`, `dashboardOpenSucceeded`, `dashboardOpenError`, and `dashboardOpenAttempts`.
3. When recovery is actually required, run `debug_session.py open-dashboard --ready-file <READY_FILE>`, then re-query state. The command skips reopening when the frontend is already recorded, retries platform and Python browser openers, waits briefly for the page-load callback, and always returns `dashboardUrl`.
4. Make no more than two manual fallback attempts for one session. Record and surface both opener failures and accepted requests that never produced a frontend callback.
5. If the page still does not load, surface the exact URL and errors. Do not restart a healthy collector merely to open the page.
6. Continue evidence collection through the CLI and NDJSON file.

Dashboard state must not block logging, reproduction, analysis, or cleanup and must not appear in the coverage plan as evidence. Use `--no-open-dashboard` instead of relying on opener failure only when the collector host is verified to have no local graphical browser; do not use it merely because the user owns the reproduction.

## CORS and security

The collector binds to `127.0.0.1` by default.

- Browser instrumentation must enqueue through the single shared acknowledged transport and its `/ingest/batch` wire frames; it must never post directly to `/ingest`. The collector supplies CORS headers for the transport's ingest requests.
- Mutating operator APIs require the session-scoped `X-Debug-Dashboard-Token`.
- Browser operator calls must be same-origin.
- The lifecycle CLI reads the token from the ready file.
- Do not expose the collector publicly or log its token into product telemetry.
- Do not create a project-local proxy unless shared-transport delivery from the browser to the collector is proven impossible.

## Reproduction handoff

Apply the reproduction-run rules in `SKILL.md`; the steps below implement the default user-handoff path. Requesting the user to operate their own browser or application is a manual handoff, not agent-operated browser automation, and does not justify disabling dashboard auto-open.

For user-owned reproduction, use the canonical Markdown template and pre-send checks in `SKILL.md`. Its rendered blocks must remain distinct: the dashboard opening paragraph, `### Failure contract`, `### Coverage`, `### Residual ambiguities`, and the final `### Reproduction` ordered list. Preserve the required coverage content: hypothesis families and mapped coverage; probe and shared-probe counts; causal-boundary coverage; the one-event-per-occurrence policy; the shared acknowledged transport and checkpoint; and payload, privacy, and perturbation controls. Never pack these sections into one soft-line-break paragraph, a table, or a code block.

Before sending that handoff, inspect every active probe and emitter. Require browser and repeating producers to call the one shared transport once per occurrence, require exactly one active producer per stable producer key, require its source-occurrence/enqueue/persistence counters to be observable for the planned checkpoint, and require `/ingest` to be absent from those paths. If the Network panel already shows multiple simultaneous `/ingest` rows in `Pending` state, fail the instrumentation gate and repair the emitter before asking for reproduction; do not describe the collector as ready. A one-shot non-browser `/ingest` producer is valid only under the awaited `persistedEvents: 1` and `discardedEvents: 0` contract above.

For a bundled session, run `debug_session.py dashboard-status --ready-file <READY_FILE>` immediately before the handoff. Its line must include the independent recording value `live`, `frozen`, or `unknown`. If it reports frozen, run `debug_session.py resume-recording --ready-file <READY_FILE>`, rerun `dashboard-status`, and require live before reproduction; session `resume` does not change this state. If recording remains unknown, refresh authoritative state and surface the exact error rather than inventing live status. For a newly established browser-capable local session that reports `disabled`, run `debug_session.py open-dashboard --ready-file <READY_FILE>`, refresh `dashboard-status`, and then copy its refreshed `line` verbatim as the opening paragraph. After a successful ledger-based resume, preserve the existing dashboard, do not call `open-dashboard`, and copy the refreshed status line and exact URL. Surface the exact URL and error if bounded startup recovery fails; do not block the reproduction. When commands are prohibited, derive the same line and recovery decision from the supplied authoritative state. For a host-provided session, use its authoritative state and the same display values where possible; do not invent a URL, confirmation status, or recording mode. Never collapse this handoff to reproduction steps alone.

Define the final reproduction step as the exact observation checkpoint that snapshots source occurrence count and shared-transport enqueue/acknowledgement status. After the completion signal, compare those counts with persisted NDJSON records before interpreting the bug. Report the run as incomplete when the counts differ, an acknowledgement is missing, a producer was duplicated, or any event was rejected, abandoned, discarded, or involved in a registry conflict. After producers and wrappers are detached, call `flushAndStop()` before replacing or removing the browser transport; never use forced `stop()` as normal teardown. Whether the terminal drain succeeds or fails, later acquisition uses a fresh `runId`; the registry retains the terminal run audit and rejects attempts to reopen it. A user-triggered Freeze remains valid operator control, but any resulting discard prevents that run from serving as successful evidence; Resume and reproduce under a fresh run interval and `runId`.

Make the reproduction request the final visible section and stop. Use the host's real completion action when available; otherwise ask for a short reply such as `done`. For a validated agent-autonomous plan, execute the reproduction directly after the runtime gate instead of asking the user. Agent experiments outside that plan are supporting evidence only and do not satisfy the failing-run gate.

Use one `runId` for the clean initial reproduction. Do not mix setup activity with the failing flow. For an intentionally long-lived flow, give the user the plan's exact checkpoint condition; reaching it ends the evidence window, not the business stream. When the run completes, record its purpose, owner, delegation, evidence filter, and status in the ledger before changing the plan's `run` block. A subsequent request for the agent to investigate means analyze this evidence; it does not transfer reproduction ownership.

## In-scope root-cause repair verification

- Apply this section whenever repair is in scope under the completion rules in `SKILL.md`; do not wait for a second authorization after proving the cause. Keep discriminating probes active while applying the repair.
- Eliminate the evidence-proven causal mechanism and restore its violated invariant or contract at the owning boundary.
- Treat change size as a constraint, not the objective. After establishing causal sufficiency, choose the narrowest safe, coherent repair; include every causally necessary file or layer and exclude unrelated cleanup.
- Do not substitute a smaller downstream guard, fallback, or coercion while the proven causal mechanism remains active.
- Use a new `runId`, such as `post-repair`.
- Default verification to user ownership. Apply a still-valid `remaining-runs` delegation or a new explicit verification delegation only after assigning the new verification `runId`; require its `effectiveRunId` to match.
- Reproduce the same flow and compare the same probe IDs and invariants; for user ownership, issue the canonical handoff again and pause for completion.
- Treat a missing post-repair symptom as insufficient when the flow itself did not complete.
- If verification fails, preserve the failed-repair evidence and update the same investigation document.

## Final cleanup

After a diagnosis-only evidence handoff completes, or after an in-scope repair verifies:

1. Remove every temporary probe, debug logging call, breakpoint or debugger statement, helper, endpoint constant, header, transport hook, and debug-only import; verify that the product no longer emits the retired debug events.
2. For a session owned by this invocation, sync `{"locations": []}`. For a host-provided or shared session, remove or report only this invocation's locations according to host policy; never replace shared location state with an empty set.
3. Update any investigation document with the terminal diagnosis or verification status and cleanup decision.
4. Run `debug_session.py stop --ready-file <READY_FILE>` only when this invocation started and owns the session. By default this closes logging and deletes its owned NDJSON, service log, location state, and ready-file artifacts; retain them only under an explicit evidence-retention decision. Never stop a host-provided or shared collector.
5. For an owned session, verify every `ownedArtifacts` path is absent unless `--keep-artifacts` was requested.
6. Remove an empty `.debug-logs/` directory only when this invocation created it.
7. Delete or retain the coverage plan and investigation document according to [root-cause-document.md](./root-cause-document.md).

Do not use Git status as cleanup proof because `.debug-logs/` is commonly ignored.
