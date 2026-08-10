# Runtime Debugging Reference

Use this reference for collector selection, language-neutral instrumentation, dashboard operation, evidence reading, and cleanup.

## Table of contents

- Session selection
- Resolve Python and skill root
- Validate the coverage plan
- Resume the active local session
- Start a local session
- Ready-file contract
- Collection controls
- Session commands
- Post-run analysis snapshot
- Health, clear, and restart rules
- Location synchronization
- Structured log format
- Temporary source markers
- Language-neutral delivery
- Browser routing
- Event cardinality and payload controls
- Evidence summarization
- Reading raw evidence
- Dashboard startup, recovery, and interactions
- CORS and security
- Reproduction handoff
- In-scope root-cause repair verification
- Final cleanup

## Session selection

Treat lifecycle scope as `investigation > collector session > run`. The investigation is one reported bug tracked by one evolving ledger. A collector session is the concrete process, exact ready file, endpoint, port, dashboard, and evidence file used by that investigation. A run is one failing, blind-spot, or verification pass identified by `runId`. User replies, evidence analysis, context compaction, repair work, and a fresh `runId` do not create a collector-session boundary.

Prefer this order:

1. For a continuing investigation, read its ledger and run `scripts/debug_session.py resume --ready-file <READY_FILE>` with the exact active ready file recorded there.
2. When establishing the investigation's initial session, reuse an authoritative project or host logger supplied by the host or user.
3. Otherwise start the bundled local collector once and send events with the target runtime's ordinary HTTP client.
4. Use direct NDJSON append only as an explicit collector-free fallback when HTTP ingestion and an authoritative logger are both unavailable. Do not present that fallback as a live collector session: dashboard collection controls, HTTP response confirmation, and collector-managed Clear do not govern direct writers.

Never scan `.debug-logs/`, the workspace, process lists, or port ranges to guess which session belongs to an investigation. The ledger's exact active ready file is the only automatic continuation source. Start a replacement only when that file is missing or its collector is unreachable, or when the user or host explicitly requires isolation or replacement. Preserve the previous evidence and append both the prior session and the replacement reason to the same investigation ledger.

The bundled collector and lifecycle CLI use only Python standard-library code. They do not require a language-specific producer library.

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

`resume` validates that exact ready file and checks its collector. It does not discover other sessions, start a process, clear evidence, change collection state, or open/reopen the dashboard. A successful result reports `sessionAction: "reused"`; its `dashboardRecovery` is a no-op snapshot with zero fallback attempts. `lifecycleMode: "local-cli"` identifies the command path, not cleanup ownership: preserve ownership from the investigation ledger. Use the returned ready payload and the same `<READY_FILE>` for every later command.

If the recorded ready file is missing or its collector is unreachable, preserve the prior session's evidence reference, mark that session accordingly in the ledger, and only then establish a replacement. An explicit user or host isolation/replacement directive may also establish another session, but must record its reason and resulting active ready file in the same ledger.

## Start a local session

Use `start` only after session selection proves that the investigation has no resumable active session or that replacement is allowed. Use a unique session ID for the newly established or replacement collector, not for each run. The CLI starts the collector detached, waits for the ready file, and prints the ready payload as JSON with `sessionAction: "started"`.

```bash
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py start \
  --workspace-root "$PWD" \
  --session-id "checkout-$(date +%s)"
```

The default is to open the live dashboard automatically. The collector publishes its ready file, starts serving HTTP, verifies the health endpoint, and only then asks the operating system to open the dashboard. The session CLI waits for `dashboardFrontendOpenRecorded` and, when needed, makes at most two fallback open attempts. Use `--no-open-dashboard` or its `--headless` alias only when the collector host is verified to have no usable local graphical browser, such as CI, container-only, or remote operation. A user-owned run, a wait for user reproduction, missing agent browser control, or a prohibition on agent-operated product browsing does not qualify. Add `--ide <IDE_ID>` when source-opening from the dashboard is useful.

Automatic browser opening is non-fatal and never part of the evidence gate. The `start` result adds `dashboardRecovery` with `frontendConfirmed`, `fallbackAttemptCount`, `dashboardUrl`, and `error`. Preserve those values and always show the refreshed dashboard status and URL before a user-owned reproduction. For a browser-capable local session, recover an accidental `disabled` state with `open-dashboard` before showing the refreshed line; proceed directly with `disabled` only for a verified no-local-GUI host. `dashboardOpenSucceeded` means an opener accepted the request, while `dashboardFrontendOpenRecorded` confirms that the page loaded. Neither field proves instrumentation coverage or that a tab remains open.

The CLI writes session artifacts under `<workspace>/.debug-logs/` unless `--artifact-dir` is supplied. Capture the returned `readyFile` path, record it as the investigation ledger's active ready file, and use it for every later command and continuation.

Do not manually start a second collector for the same investigation. Changing the session ID or ready-file name is not a valid way to bypass the ledger-first resume gate.

## Ready-file contract

Treat the ready file as authoritative. It includes the single producer endpoint, dashboard and operator endpoints, evidence paths, and process identity needed by any target language:

```json
{
  "endpoint": "http://127.0.0.1:43125/ingest",
  "dashboardUrl": "http://127.0.0.1:43125/",
  "dashboardToken": "<SESSION_TOKEN>",
  "dashboardAutoOpenEnabled": true,
  "dashboardFrontendOpenRecorded": true,
  "stateUrl": "http://127.0.0.1:43125/api/state",
  "logsUrl": "http://127.0.0.1:43125/api/logs",
  "logDetailUrl": "http://127.0.0.1:43125/api/logs/detail",
  "locationsUrl": "http://127.0.0.1:43125/api/locations",
  "syncLocationsUrl": "http://127.0.0.1:43125/api/locations/sync",
  "configUrl": "http://127.0.0.1:43125/api/config",
  "openLocationUrl": "http://127.0.0.1:43125/api/open-location",
  "clearUrl": "http://127.0.0.1:43125/api/clear",
  "freezeRecordingUrl": "http://127.0.0.1:43125/api/recording/freeze",
  "resumeRecordingUrl": "http://127.0.0.1:43125/api/recording/resume",
  "shutdownUrl": "http://127.0.0.1:43125/api/shutdown",
  "healthUrl": "http://127.0.0.1:43125/health",
  "recordingFrozen": false,
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

When an allowed collector replacement starts on another port, replace stale endpoint constants in all active temporary probes before reproduction.

`POST /ingest` is the only write endpoint. Send either one event object or an exact `{"events": [...]}` envelope whose sole top-level key is `events`; the collector appends each array item as one NDJSON record. A top-level JSON array is invalid. An ordinary event may still contain an opaque `events` field when it also has other fields. The envelope requires no extra client metadata, retry ledger, or special client.

The dashboard may keep bounded count lists and a lightweight read index so polling and virtualized log browsing do not compete with ingestion. Those are presentation details, not requirements imposed on producers. The NDJSON file remains the evidence of record.

## Collection controls

The dashboard's single `Freeze` / `Resume` control operates one collector-wide write gate. The UI continues polling while frozen. Every open dashboard tab, a reloaded dashboard, later user replies, analysis turns, and fresh run IDs observe the same collector state. Freezing does not stop or disconnect the collector: `/health` remains running, while dashboard state reports frozen and the badge shows `FROZEN`.

Linearize Freeze, Resume, Clear, and append operations with the collector's write lock:

- **Collect:** while live, accept one JSON event or an exact `{"events": [...]}` envelope at `/ingest`, append one compact NDJSON line per event, and report the number persisted.
- **Freeze:** stop persisting later HTTP events. Reject them with a non-success response that reports zero persisted events; do not buffer, replay, or silently promote them after Resume.
- **Resume:** allow only future requests to persist. Resume does not reinterpret a request handled while frozen.
- **Clear:** truncate current evidence and reset log-derived counters while preserving the current live/frozen state, selected IDE, and explicitly synchronized location set.
- **Stop:** stop accepting requests, flush collector-owned state, and shut down the service.

These controls require no producer-side delivery state or terminalization protocol. A request that spans a Freeze/Resume transition is rejected with `recording_state_changed`, persists zero events, and cannot spill into the next recording window. A frozen or transition-rejected response is not evidence persistence. Treat the affected observation window as incomplete and reproduce after Resume if the event is needed.

`FROZEN` is not collector-health failure, a completed run, or proof that every planned event arrived. Use it to stabilize the current evidence view only after the reproduction reaches its declared terminal or observation checkpoint and the target runtime has completed any ordinary logging calls it owns.

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

# Clear the current session log and log-derived counters
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py clear \
  --ready-file <READY_FILE>

# Freeze collector HTTP ingestion; dashboard polling and Clear remain available
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_session.py freeze-recording \
  --ready-file <READY_FILE>

# Resume collection for future requests
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

Keep session `resume` and collection `resume-recording` distinct. Session `resume` validates and reuses an existing process without changing collection state. `resume-recording` opens the existing collector write gate for future requests.

Use `--keep-artifacts` on `stop` only when the user asks to retain raw evidence. Use `--delete-root-cause-document <PATH>` only after a terminal diagnosis or successful repair verification and after updating the document's cleanup status.

## Post-run analysis snapshot

After a failing, blind-spot, or verification run reaches its completion signal:

1. Recover the investigation ledger's exact active ready file with session `resume`.
2. Require the planned terminal or observation checkpoint to occur. Let any finite, target-runtime logging call at that boundary finish without adding a universal client drain protocol.
3. Verify that the expected terminal/checkpoint event and the generic persisted counts available for the bounded run are present. If delivery cannot be established, record that limitation and do not use a missing interior event as proof.
4. Run `freeze-recording --ready-file <READY_FILE>`, then refresh `dashboard-status` and require `recording: frozen` before taking a stable analysis snapshot.
5. Summarize and read bounded evidence. Keep the collector frozen while that snapshot is being analyzed when doing so prevents unrelated traffic from mixing into it.

Freeze is a write gate, not a delivery checkpoint. Do not require a language-specific client state machine before using it.

## Health, clear, and restart rules

Before every deliberate recording pass:

1. Read the same investigation ledger and recover its exact active ready file; do not search for alternatives.
2. Run `resume --ready-file <READY_FILE>` before any `start` attempt.
3. If resume succeeds, keep the same collector, endpoint, port, and dashboard. Do not call `start` or `open-dashboard` as part of the new pass.
4. If the ready file is missing or the collector is unreachable, or an explicit isolation/replacement directive applies, preserve needed evidence, append the prior session status and replacement reason to the ledger, start the replacement, and record its exact ready file as active.
5. Patch temporary endpoint constants only when an allowed replacement changed the port.
6. Finish the previous run's analysis and ledger transition, then preserve any raw evidence that must survive log truncation.
7. Remove superseded temporary probes, debug logging calls, and breakpoints or debugger statements; retain only instrumentation required by the next validated plan or verification run, and sync the exact remaining active location set.
8. Run `clear` so the next pass does not inherit prior log records or log-derived counters. Clear remains valid while frozen and does not Resume collection.
9. Run `dashboard-status`. If it reports `recording: frozen`, run `resume-recording`, rerun `dashboard-status`, and require `recording: live` before reproduction.
10. Use a fresh `runId` within the same healthy collector session.
11. Send one bounded test event through the selected project/host logger or target-runtime HTTP adapter and verify that the collector persisted it. Clear that test event before the deliberate run when it would pollute evidence.

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

The location-state sidecar is a near-real-time operational view. Sidecar rewrites may be debounced so frequent events do not force a large JSON rewrite; this never changes NDJSON event count. Sync, clear, startup, and shutdown force a current sidecar write. Use the NDJSON file as evidence of record.

Keep location sync and IDE source opening even when simplifying ingestion. They are dashboard/operator features and impose no language-specific producer dependency.

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
- attempt/version metadata in `data`

The bundled summarizer checks top-level `sequence` continuity within each `runId` plus `correlationId`. Make that field a contiguous logging-event sequence for that scope. Put a domain-specific stream offset, queue ordinal, or source counter in a separately named bounded `data` field when its owner or cadence differs; analyze that field at its real producer boundary instead of treating it as the logging sequence.

Treat `message` as optional human-readable context rather than evidence identity. In the dashboard log stream, show the first non-empty value from `message`, `event`, and `probeId`; do not synthesize a `message` into the stored payload, and show `No message` only when all three are absent.

Keep values bounded and JSON-serializable. Instrumentation must not throw into product code. Surface a serialization or send failure through the target runtime's normal diagnostic mechanism and mark the affected evidence interval incomplete.

## Temporary source markers

Mark every source edit that exists only for the current investigation so it can be found, reviewed, moved with its ownership intact, and removed without guessing. This includes structured probe calls, inserted `debugger` statements, debug-only imports and endpoint constants, runtime adapters, wrappers, listeners, timers, and helper functions. A native debugger breakpoint that does not edit source belongs only in the coverage plan and debugger; do not add a source marker for it.

Preserve these exact marker payloads:

- `#region agent log` starts executable instrumentation or an inserted-breakpoint block.
- `#region agent log config` starts shared debug-only imports, constants, adapters, or helpers.
- `#endregion` ends either kind of block.

Render the payloads with comment syntax valid for the source language. Keep the historical JavaScript/TypeScript spellings exactly as follows:

```ts
// #region agent log config
const debugCollectorEndpoint = '<ENDPOINT>'
// #endregion

// #region agent log
await emitDebugEvent({ probeId: 'cart.commit.before' })
// #endregion
```

For example, use `# #region agent log` and `# #endregion` in Python, `-- #region agent log` and `-- #endregion` in SQL, or `<!-- #region agent log -->` and `<!-- #endregion -->` in markup. Preserve the marker payload even when the editor does not provide region folding.

Apply these ownership rules:

1. Create the smallest balanced region that contains the contiguous temporary edit.
2. Keep permanent product behavior and the eventual repair outside the region; split a mixed edit before the first reproduction.
3. Reuse a matching agent-log region when one already owns the block. Do not nest agent-log regions or span unrelated product code.
4. Search every instrumented path with `rg -n -F '#region agent log' <instrumented-paths>` before the runtime gate. Pair each start with the nearest valid `#endregion` in the same file, verify that no temporary source edit is unmarked, and rerun the narrowest syntax, type, or compile check after insertion.
5. Revalidate and resync plan locations after marker insertion, removal, or formatting changes source line numbers.
6. During cleanup, remove the entire paired region, including both comments. Never globally delete `#endregion`; an unpaired occurrence may belong to a project-owned folding region.

## Language-neutral delivery

Do not copy a preselected client implementation into every project. Select the smallest adapter already native to the target:

1. Reuse a project or host structured logger when it can preserve the event fields and identify the active run.
2. Otherwise use the target runtime's standard HTTP client to `POST` one event or an exact `{"events": [...]}` envelope to `/ingest`.
3. Use a small project-local helper only to avoid repeating endpoint, headers, serialization, and error handling. Match the language and framework already in the target repository.
4. Use locked one-line NDJSON append only as an explicitly collector-free fallback. Keep it separate from the collector-owned evidence file unless the user accepts that Freeze, Resume, Clear, live indexing, and HTTP persisted counts do not apply.

### Project-local helper references

Shared helpers are optional, not the default. Inline a small adapter when only one source file needs it. When a shared helper is justified, choose one final location that follows the repository's existing source-root, package, client/server, and test/build conventions, then create the helper before inserting references to it.

Resolve every reference from the actual importing file. Do not count directory segments by eye, infer a path from a nearby file, or paste the same `../` chain into differently nested importers. Prefer an existing source-root alias only when the authoritative project configuration already defines it and every applicable runtime, test, client, server, and bundler target resolves it. Do not add a permanent alias solely for temporary instrumentation.

For languages and module systems that use slash-delimited file-relative references, the optional helper below computes from `importer.parent` to an existing target and can verify an injected reference:

```bash
"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_import_path.py \
  --workspace-root <WORKSPACE_ROOT> \
  --importer <SOURCE_FILE> \
  --target <EXISTING_HELPER_FILE> \
  --strip-extension

"$PYTHON_BIN" <SKILL_ROOT>/scripts/debug_import_path.py \
  --workspace-root <WORKSPACE_ROOT> \
  --importer <SOURCE_FILE> \
  --target <EXISTING_HELPER_FILE> \
  --strip-extension \
  --specifier <INJECTED_RELATIVE_SPECIFIER>
```

Use `--strip-extension` only when the target repository normally uses extensionless file references. The helper deliberately does not interpret package or namespace semantics, repository aliases, Python dotted imports, Go modules, Rust modules, or Java/C# packages. For those systems, use the repository's native resolver, compiler, type checker, or build tool.

Before the runtime gate, enumerate every temporary cross-file reference inside `agent log config` regions and require all of the following:

- the target helper exists at its final path and remains inside the intended workspace;
- the reference resolves to that exact target, not merely to some module with the same basename;
- each importer was checked independently;
- every applicable client, server, test, or SSR build boundary that compiles the importer understands the reference;
- the narrowest native resolution, syntax, type, compile, or build command passes after injection.

A full application build may remain a later regression check, but it must not be the first mechanism that discovers a malformed debug-only reference.

For a single awaited event, require a successful HTTP response and a persisted count of one when the response exposes counts. For a multi-event envelope, require the persisted count to equal the number of submitted events. The smoke event must also round-trip the required camelCase field names into NDJSON and the dashboard projection; the collector deliberately does not impose a language-specific schema mapper. Do not impose extra client identity or lifecycle state beyond the structured event fields.

For a hot callback, do not synchronously block the product path on collector I/O. Prefer an existing asynchronous project logger or a bounded runtime-native queue. If delivery cannot be confirmed for the bounded evidence window, report that limitation rather than inventing a universal lossless client protocol.

When appending directly without a collector:

- use the same event schema;
- serialize under an appropriate process-safe lock when multiple writers share a file;
- keep each object on one physical line;
- do not mix unrelated sessions in one file;
- state explicitly that dashboard collection controls do not govern the writer.

## Browser routing

Read [browser-debugging.md](./browser-debugging.md) before adding client instrumentation, wrapping application `fetch`, collecting long-lived or high-frequency browser streams, or crossing navigation and reload boundaries. Keep browser-specific constraints out of non-browser investigations.

Browser code may use the same single `/ingest` contract through the project's existing logger or a small project-local adapter. The debug skill does not require a bundled browser client, prescribed module shape, or browser-only static checker.

## Event cardinality and payload controls

For every active probe and bounded evidence interval, preserve the logical goal:

```text
source occurrence count = emitted event count = persisted NDJSON record count
```

Serialize each occurrence independently and give it stable probe, correlation, and sequence identity. A multi-event envelope contains independent events; it must not merge identities, replace earlier events, or change record count.

Choose fewer or better probe locations before activating the run when projected observer cost is unsafe. Once a probe is active, do not sample, throttle, debounce, keep only the first events, emit once per key, gate on changes or anomalies, aggregate, coalesce, overwrite, deduplicate, or otherwise suppress its occurrences.

Control observer cost by bounding payload content, not event count. Use selected scalar fields, hashes, lengths, enums, identifiers, compact timestamps, and bounded error messages instead of complete payloads, unbounded arrays, state trees, bodies, or stacks. Redact secrets before sending. A serialization, payload-bound, send, or persisted-count mismatch makes the affected interval incomplete.

The bundled collector does not prove the producer's source count. Keep a source-side count or enclosing sentinels when exact cardinality matters, compare it with generic persisted record counts, and treat an otherwise unexplained missing event as `INCONCLUSIVE` rather than forcing every language to implement a transport state machine.

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

The summarizer reports persisted NDJSON record counts, valid/invalid lines, probe and hypothesis coverage, correlations, causal-sequence gaps or regressions, error-like events, and a bounded timeline. Sequence continuity is evaluated over every event in the selected `runId` and `correlationId` scope before narrower probe, hypothesis, operation, or request filters are applied, so a display subset cannot manufacture a gap. Its output names the continuity scope filters and counts sequence-bearing events that lack either required scope field instead of silently treating them as complete. It does not observe source occurrences or send attempts. Reconcile exact counts only when the selected project/host logger or target-runtime adapter exposes them; otherwise use sentinels and mark delivery-dependent absence claims inconclusive.

## Reading raw evidence

After summarization:

1. Verify the expected run and correlation exist.
2. Verify flow start and the configured terminal or observation-checkpoint sentinel.
3. Compare available source/emitted counts with persisted NDJSON records for the same bounded interval.
4. Check send errors, invalid lines, missing planned probes, and source or causal-sequence gaps.
5. Treat an unexplained missing event as incomplete delivery or `INCONCLUSIVE`, not as proof that product code did not execute.
6. Identify the earliest invalid value, invariant failure, or invalid ordering.
7. Read the raw NDJSON lines for that causal interval.
8. Cite probe ID, location, run, correlation, sequence, and selected data.
9. Evaluate every hypothesis, including `NOT_REACHED` paths.

Do not paste the entire NDJSON file into chat when a compact summary and targeted lines suffice.

## Dashboard startup, recovery, and interactions

The collector serves a same-origin dashboard with authoritative state, a virtualized newest-first log stream, entry payload/meta detail, run and hypothesis summaries, synchronized source locations, IDE selection and source opening, responsive desktop/mobile panels, Freeze/Resume, Clear, and Stop. Keep these interactions when simplifying ingestion; they are the operator surface over the same lightweight collector state.

Browser-capable local `start` sessions open the dashboard after the HTTP health endpoint responds, wait for the frontend callback, and make at most two fallback attempts before returning a non-fatal `dashboardRecovery` result.

Use this manual recovery sequence only for newly established sessions whose dashboard startup needs recovery, or when the user or host explicitly requests a dashboard open. It is never part of normal investigation continuation: if `resume` succeeds, keep the existing dashboard state, surface its exact URL, and skip this sequence.

1. Read the ready payload, capture `dashboardUrl`, and note whether `dashboardAutoOpenEnabled` is `true`.
2. Check `dashboardOpenPending`, `dashboardOpenSucceeded`, `dashboardOpenError`, and `dashboardOpenAttempts`.
3. When recovery is actually required, run `debug_session.py open-dashboard --ready-file <READY_FILE>`, then re-query state. The command skips reopening when the frontend is already recorded, retries platform and Python browser openers, waits briefly for the page-load callback, and always returns `dashboardUrl`.
4. Make no more than two manual fallback attempts for one session. Record and surface both opener failures and accepted requests that never produced a frontend callback.
5. If the page still does not load, surface the exact URL and errors. Do not restart a healthy collector merely to open the page.
6. Continue evidence collection through the CLI and NDJSON file.

Dashboard visibility, frontend confirmation, and opener recovery must not block logging, reproduction, analysis, or cleanup and must not appear in the coverage plan as evidence. Authoritative collection state is separate: require live before a deliberate recording pass and frozen only when a stable snapshot is desired. Use `--no-open-dashboard` only when the collector host is verified to have no local graphical browser; do not use it merely because the user owns the reproduction.

Preserve these frontend behaviors:

- keep polling while live and frozen;
- update the status badge and mutually exclusive Freeze/Resume control from authoritative collector state;
- leave Clear and Stop available while frozen;
- reset the log selection safely after Clear and show the stopped overlay after Stop;
- retain virtual scrolling, lazy log detail, Payload/Meta tabs, run/hypothesis collapsibles, metrics, responsive tabs, and action/error feedback;
- retain selected-IDE persistence, availability reporting, synchronized locations, workspace-bound path validation, and click-to-open source behavior.

## CORS and security

The collector binds to `127.0.0.1` by default.

- Browser instrumentation may post directly to `/ingest`; the collector supplies ingest CORS headers.
- Mutating operator APIs require the session-scoped `X-Debug-Dashboard-Token`.
- Browser operator calls must be same-origin.
- The lifecycle CLI reads the token from the ready file.
- Do not expose the collector publicly or log its token into product telemetry.
- Do not create a project-local proxy unless direct browser-to-collector delivery is proven impossible.

## Reproduction handoff

Apply the reproduction-run rules in `SKILL.md`; the steps below implement the default user-handoff path. Requesting the user to operate their own browser or application is a manual handoff, not agent-operated browser automation, and does not justify disabling dashboard auto-open.

For user-owned reproduction, use the canonical Markdown template and pre-send checks in `SKILL.md`. Its rendered blocks must remain distinct: the dashboard opening paragraph, `### Failure contract`, `### Coverage`, `### Residual ambiguities`, and the final `### Reproduction` ordered list. Preserve the required coverage content: hypothesis families and mapped coverage; breakpoint, probe, and shared-probe counts; causal-boundary coverage; the one-event-per-occurrence policy; selected logging path; and payload, privacy, and perturbation controls.

Before sending that handoff, inspect every active probe and emitter. Require it to use the selected project/host logger or target-runtime HTTP adapter, preserve the event schema, surface send errors, and avoid blocking the product path. Send and verify one bounded test event, then Clear it before the deliberate run when necessary.

For a bundled session, run `debug_session.py dashboard-status --ready-file <READY_FILE>` immediately before the handoff. If it reports frozen, run `debug_session.py resume-recording`, rerun `dashboard-status`, and require live before reproduction; session `resume` does not change this state. For a newly established browser-capable local session that reports `disabled`, run `debug_session.py open-dashboard`, refresh `dashboard-status`, and copy its refreshed line as the opening paragraph. After a successful ledger-based resume, preserve the existing dashboard and do not reopen it. Surface the exact URL and error if bounded startup recovery fails; do not block reproduction.

Define the final reproduction step as the exact observable product or flow condition that closes the evidence window. Arrange instrumentation to emit the terminal or checkpoint sentinel automatically at that boundary. Do not invent a product-page command, DevTools step, or `window` or `globalThis` helper as the host completion action.

Make the reproduction request the final visible section and stop. Use a completion action already exposed by the current Codex host when available; otherwise ask for a short reply such as `done`. Treat that signal only as notice that the user reached the boundary, never as proof that logs persisted. For a validated agent-autonomous plan, execute the reproduction directly after the runtime gate instead of asking the user.

Use one `runId` for the clean initial reproduction. Do not mix setup activity with the failing flow. For an intentionally long-lived flow, give the user the plan's exact checkpoint condition; reaching it ends the evidence window, not the business stream. When the run completes, record its purpose, owner, delegation, evidence filter, persisted-count confidence, and status in the ledger before changing the plan's `run` block.

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

1. Search every instrumented path for `#region agent log`, remove each complete paired temporary region including its two marker comments, then remove any remaining temporary probe, debug logging call, native breakpoint, endpoint constant, header, or debug-only import; verify that no agent-log start marker or retired debug event remains.
2. For a session owned by this invocation, sync `{"locations": []}`. For a host-provided or shared session, remove or report only this invocation's locations according to host policy; never replace shared location state with an empty set.
3. Update any investigation document with the terminal diagnosis or verification status and cleanup decision.
4. Run `debug_session.py stop --ready-file <READY_FILE>` only when this invocation started and owns the session. By default this closes logging and deletes its owned NDJSON, service log, location state, and ready-file artifacts; retain them only under an explicit evidence-retention decision. Never stop a host-provided or shared collector.
5. For an owned session, verify every `ownedArtifacts` path is absent unless `--keep-artifacts` was requested.
6. Remove an empty `.debug-logs/` directory only when this invocation created it.
7. Delete or retain the coverage plan and investigation document according to [root-cause-document.md](./root-cause-document.md).

Do not use Git status as cleanup proof because `.debug-logs/` is commonly ignored.
