---
name: debug
description: Evidence-first runtime debugging for application bugs, regressions, flaky behavior, and unclear failures. Use when an agent is asked to debug an issue and should avoid speculative fixes by forming hypotheses, attaching to or starting a logging session, instrumenting code, collecting runtime logs, analyzing the recorded log file, applying only proven fixes, and verifying the result before removing instrumentation, especially for browser or frontend issues where logs should go directly to the active collector endpoint instead of app-local proxy APIs.
---

# Debug

Use runtime evidence before changing behavior. Treat code reading as context building, not proof.

## Host adaptation

Before starting, normalize the current debugging environment without preflighting the target app:

- Determine whether the session already exposes a logging endpoint, log path, session ID, ready file, or other authoritative debug configuration.
- If no authoritative logging configuration exists, determine whether a local Python 3 interpreter is available for the bundled collector. Prefer `python3`; otherwise allow `python` only when it resolves to Python 3. If no Python 3 interpreter is available, stop and tell the user you need either an existing logging session or a local Python 3 runtime before continuing in evidence-first mode.
- Determine how the host keeps long-lived processes alive: persistent PTY, detached shell, task runner, or no background support.
- Determine whether the host can open or automate browser pages. If not, rely on the collector's ready file and HTTP APIs instead of UI inspection. When browser access exists, reserve page opening for the collector dashboard by default; do not open target-app pages unless the user explicitly asked you to open the project.
- Determine whether each planned log point runs in browser/client code, server/runtime code, or both. For browser/client code, prefer direct requests to the active collector endpoint instead of adding project-local proxy routes.
- Determine how the user signals that reproduction is complete: explicit UI button, task-state action, or a short chat reply.
- Do not treat target-app startup, health checks, route probes, or compile/build checks as default preflight. Only inspect them when the user explicitly asked to debug startup behavior or when a current hypothesis is about app boot, compilation, or endpoint availability.
- Store temporary artifacts in an existing host-specific scratch directory when one already exists. Otherwise default to a workspace-local hidden directory such as `.debug-logs/`.

## Workflow

1. Generate 3-5 precise hypotheses about why the bug happens. Make them specific enough that a log can confirm or reject each one.
2. Establish the active logging session before editing app code or probing the target app. If the session already provides a logging endpoint, log path, session ID, or ready file, use those values exactly. Otherwise first resolve a local Python 3 interpreter for the bundled collector. Prefer `python3`; otherwise allow `python` only when it resolves to Python 3. If no Python 3 interpreter is available, stop and tell the user you cannot proceed in this evidence-first mode unless they provide an authoritative logging session or make Python 3 available. When a Python 3 interpreter is available, start the bundled local collector app from `scripts/local_log_collector/main.py`, resolved relative to this skill's root directory, create a session-specific NDJSON log file, and treat the service's ready file as authoritative. If the command runner reaps child processes when the command returns, keep the collector alive in a persistent PTY or the host's equivalent long-lived session mechanism instead of assuming a plain trailing `&` is enough. The bundled service attempts to open its `dashboardUrl` in the system browser by default for live summary, log clearing, and service shutdown controls. If the ready file reports that this browser-open attempt succeeded, do not also open the same page with MCP or browser automation. Only fall back to MCP or an embedded browser when the ready file reports that the auto-open attempt failed, or when auto-open was intentionally disabled.
3. Add the minimum instrumentation needed to test all hypotheses in parallel. Prefer 2-6 logs; never skip instrumentation; do not exceed 10 logs. When instrumenting browser/client JavaScript, send logs directly to the active collector endpoint unless runtime evidence proves direct delivery is blocked in the current host.
4. Before each reproduction run or deliberate re-recording pass, verify that the current logging process is still alive. Prefer the active `healthUrl` or `stateUrl` when one exists. If the process has been closed or the check fails, start a new collector process and treat its new ready file values as authoritative before continuing.
5. If restarting the collector changed the active ingest endpoint or port, update the existing temporary logging code so it no longer points at the stale port. Apply that refresh before the next reproduction run and keep the edits limited to the active debug instrumentation for the current task.
6. Preserve any evidence you still need from the current run, then clear only the active session's existing logs so the next run starts from a low-noise baseline. Prefer the active clear endpoint when one exists; fall back to truncating the active session log file only when no clear endpoint is available.
7. Ask the user to reproduce the issue. End the response with a `<reproduction_steps>...</reproduction_steps>` block containing only a numbered list. Make the final instruction match the host's completion mechanic exactly: use the real button or task action label when one exists, otherwise ask for a short completion reply.
8. Read the active session's NDJSON log file and evaluate every hypothesis as `CONFIRMED`, `REJECTED`, or `INCONCLUSIVE`, citing the relevant log evidence.
9. Apply a fix only after the logs prove the root cause. Keep instrumentation in place while implementing the fix.
10. Before the post-fix verification run, verify the current logging process is still alive again. If it has been closed, start a new collector process and adopt its new ready file values before clearing and collecting verification logs.
11. If restarting the collector changed the active ingest endpoint or port again, update the temporary logging code to replace the stale port before the verification run.
12. Clear only the active session's current logs again so before/after evidence does not mix.
13. Ask for a post-fix reproduction run and compare before/after logs.
14. Remove all injected temporary logging code only after logs prove the fix worked and the user confirms the issue is gone. This includes the inserted log calls, debug-only endpoint constants, temporary headers, and any other scaffolding added only for this debugging pass.
15. If the fix fails, remove code changes that came from rejected hypotheses, keep useful instrumentation, generate new hypotheses from a different subsystem, and repeat.

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

## Instrumentation Rules

- Map each log to at least one `hypothesisId`.
- Include enough context to prove control flow and state transitions: parameters, branch choice, before/after values, errors, or return values.
- Wrap each inserted debug log in a collapsible code region when the language supports regions.
- If the session provides a logging endpoint, log path, session ID, or ready file, treat those values as authoritative and use them exactly.
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

Read [runtime-debugging.md](./references/runtime-debugging.md) for local collector bootstrap commands, dashboard URLs, CORS behavior, payload fields, logging templates, response shape, and verification rules.

## Response Shape

Structure the debugging conversation in this order:

1. Hypotheses
2. Instrumentation plan or applied log points
3. Reproduction request with the required `<reproduction_steps>` block
4. Log analysis with `CONFIRMED` / `REJECTED` / `INCONCLUSIVE`
5. Proven fix
6. Post-fix verification
7. Short root-cause explanation and 1-2 line fix summary after success
