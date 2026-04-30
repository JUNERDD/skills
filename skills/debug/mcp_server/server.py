#!/usr/bin/env python3
"""MCP server for evidence-first runtime debugging.

Exposes the debug skill's collector as MCP tools, resources, and prompts
so any MCP-compatible agent can use the debug workflow.

Run:
    cd mcp_server
    uv run server.py
"""

from __future__ import annotations

import atexit
import asyncio
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

SKILL_ROOT = Path(__file__).resolve().parent.parent
COLLECTOR_MAIN = SKILL_ROOT / "scripts" / "local_log_collector" / "main.py"
SKILL_MD = SKILL_ROOT / "SKILL.md"
RUNTIME_DEBUGGING_MD = SKILL_ROOT / "references" / "runtime-debugging.md"

mcp = FastMCP(
    "debug",
    instructions=(
        "Evidence-first runtime debugging MCP server. "
        "Use start_debug_session to begin, instrument your code with fetch() "
        "calls to the returned endpoint, then use get_debug_logs to analyze evidence."
    ),
)

# --- Session state ---

_active_session: dict[str, Any] | None = None
_collector_process: subprocess.Popen | None = None
_session_start_lock = asyncio.Lock()
_shutdown_cleanup_registered = False
SESSION_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


# --- HTTP helpers (stdlib only) ---


def _http_get(url: str, timeout: float = 5.0) -> dict[str, Any]:
    """GET a JSON endpoint."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _http_post(
    url: str,
    data: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """POST JSON to an endpoint, optionally with dashboard token auth."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["X-Debug-Dashboard-Token"] = token
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _require_session() -> dict[str, Any]:
    """Return active session or raise a tool error."""
    if _active_session is None:
        return {"error": "No active debug session. Call start_debug_session first."}
    return _active_session


def _resolve_python3() -> str:
    """Find a Python 3 interpreter."""
    for candidate in ("python3", "python"):
        path = shutil.which(candidate)
        if path:
            try:
                out = subprocess.check_output(
                    [path, "--version"], stderr=subprocess.STDOUT, timeout=5
                )
                if b"Python 3" in out:
                    return path
            except (subprocess.SubprocessError, OSError):
                continue
    raise RuntimeError("No Python 3 interpreter found")


def _validate_session_id(session_id: str) -> str | None:
    if SESSION_ID_PATTERN.fullmatch(session_id):
        return None
    return (
        "session_id must be 1-128 characters and may contain only letters, "
        "numbers, '.', '_', and '-'. It cannot include path separators."
    )


def _kill_and_reap_process(proc: subprocess.Popen, timeout: float = 2.0) -> None:
    if proc.poll() is None:
        proc.kill()
    proc.wait(timeout=timeout)


def _cleanup_collector_session() -> list[str]:
    global _active_session, _collector_process

    session = _active_session
    proc = _collector_process
    deleted: list[str] = []

    if session is not None:
        shutdown_url = session.get("shutdown_url")
        token = session.get("dashboard_token")
        if shutdown_url and token:
            try:
                _http_post(shutdown_url, token=token, timeout=3)
            except (urllib.error.URLError, OSError):
                pass

    if proc is not None:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                _kill_and_reap_process(proc)
            except subprocess.TimeoutExpired:
                pass
        finally:
            if _collector_process is proc:
                _collector_process = None

    if session is not None:
        for artifact_path in session.get("owned_artifacts", []):
            p = Path(artifact_path)
            if p.exists():
                p.unlink()
                deleted.append(str(p))

        log_file = session.get("log_file", "")
        if log_file:
            log_dir = Path(log_file).parent
            if log_dir.exists() and not any(log_dir.iterdir()):
                log_dir.rmdir()
                deleted.append(str(log_dir))

    _active_session = None
    return deleted


def _handle_shutdown_signal(signum: int, _frame: object) -> None:
    _cleanup_collector_session()
    raise SystemExit(128 + signum)


def _register_shutdown_cleanup() -> None:
    global _shutdown_cleanup_registered
    if _shutdown_cleanup_registered:
        return
    atexit.register(_cleanup_collector_session)
    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)
    _shutdown_cleanup_registered = True


def _file_uri_to_path(uri: Any) -> Path | None:
    parsed = urllib.parse.urlparse(str(uri))
    if parsed.scheme != "file":
        return None

    path_text = urllib.parse.unquote(parsed.path)
    if parsed.netloc and parsed.netloc != "localhost":
        path_text = f"//{parsed.netloc}{path_text}"
    if (
        os.name == "nt"
        and path_text.startswith("/")
        and len(path_text) > 2
        and path_text[2] == ":"
    ):
        path_text = path_text[1:]
    return Path(path_text).expanduser().resolve()


async def _mcp_file_roots(ctx: Context | None) -> list[Path]:
    if ctx is None:
        return []
    try:
        roots_result = await ctx.session.list_roots()
    except Exception:
        return []

    roots: list[Path] = []
    seen: set[str] = set()
    for root in getattr(roots_result, "roots", []):
        path = _file_uri_to_path(getattr(root, "uri", ""))
        if path is None:
            continue
        text = str(path)
        if text in seen:
            continue
        seen.add(text)
        roots.append(path)
    return roots


async def _resolve_workspace_root(
    workspace_root: str,
    ctx: Context | None,
) -> tuple[Path | None, str | None]:
    """Resolve the target workspace, preserving cwd as the legacy fallback."""
    if workspace_root:
        return Path(workspace_root).expanduser().resolve(), None

    for env_name in (
        "JUNERDD_DEBUG_WORKSPACE_ROOT",
        "DEBUG_WORKSPACE_ROOT",
        "MCP_WORKSPACE_ROOT",
        "WORKSPACE_ROOT",
        "PROJECT_ROOT",
    ):
        value = os.environ.get(env_name, "").strip()
        if value:
            return Path(value).expanduser().resolve(), None

    roots = await _mcp_file_roots(ctx)
    if len(roots) == 1:
        return roots[0], None
    if len(roots) > 1:
        candidates = ", ".join(str(root) for root in roots)
        return (
            None,
            "Multiple MCP workspace roots are available. Pass the target project "
            f"as workspace_root. Candidates: {candidates}",
        )

    return Path.cwd().resolve(), None


# --- Tools ---


@mcp.tool()
async def start_debug_session(
    session_id: str = "mcp-debug",
    workspace_root: str = "",
    ide: str = "",
    open_dashboard: bool = True,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Start a debug collector session.

    Spawns the NDJSON log collector as a subprocess and returns session info
    including the ingest endpoint, dashboard URL, and dashboard token.

    Args:
        session_id: Unique identifier for this debug session. Use letters,
            numbers, '.', '_', or '-' only; path separators are rejected.
        workspace_root: Workspace root for resolving relative paths. Defaults to the
            selected workspace env vars, then the single MCP client root when available,
            then cwd.
        ide: Default IDE id (cursor, vscode, windsurf, zed, webstorm, etc.).
        open_dashboard: Whether to auto-open the dashboard in a browser.
    """
    global _active_session, _collector_process

    session_id_error = _validate_session_id(session_id)
    if session_id_error:
        return {"error": session_id_error}

    async with _session_start_lock:
        if _active_session is not None:
            return {
                "error": "A debug session is already active. Call stop_debug_session first.",
                "session": _active_session,
            }

        try:
            python_bin = _resolve_python3()
        except RuntimeError as e:
            return {"error": str(e)}

        ws, workspace_error = await _resolve_workspace_root(workspace_root, ctx)
        if workspace_error:
            return {"error": workspace_error}
        assert ws is not None

        log_dir = ws / ".debug-logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"{session_id}.ndjson"
        ready_file = log_dir / f"{session_id}.json"
        location_state_file = log_dir / f"{session_id}.locations.json"
        service_log_file = log_dir / f"{session_id}.service.log"

        try:
            ready_file.unlink(missing_ok=True)
        except OSError as e:
            return {"error": f"Failed to clear stale ready file: {e}"}

        cmd = [
            python_bin,
            str(COLLECTOR_MAIN),
            "--log-file", str(log_file),
            "--ready-file", str(ready_file),
            "--location-state-file", str(location_state_file),
            "--service-log-file", str(service_log_file),
            "--session-id", session_id,
            "--workspace-root", str(ws),
        ]
        if not open_dashboard:
            cmd.append("--no-open-dashboard")
        if ide:
            cmd.extend(["--default-ide", ide])

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(SKILL_ROOT / "scripts" / "local_log_collector"),
            )
            _collector_process = proc
        except OSError as e:
            return {"error": f"Failed to start collector: {e}"}

        # Wait for ready file (up to 10s)
        for _ in range(100):
            if ready_file.exists():
                try:
                    raw = json.loads(ready_file.read_text())
                    session_info = {
                        "status": "started",
                        "session_id": session_id,
                        "endpoint": raw.get("endpoint"),
                        "dashboard_url": raw.get("dashboardUrl"),
                        "ingest_url": raw.get("endpoint"),
                        "health_url": raw.get("healthUrl"),
                        "state_url": raw.get("stateUrl"),
                        "logs_url": raw.get("logsUrl"),
                        "clear_url": raw.get("clearUrl"),
                        "locations_sync_url": raw.get("syncLocationsUrl"),
                        "open_location_url": raw.get("openLocationUrl"),
                        "shutdown_url": raw.get("shutdownUrl"),
                        "dashboard_token": raw.get("dashboardToken"),
                        "log_file": str(log_file),
                        "pid": proc.pid,
                        "owned_artifacts": raw.get("ownedArtifacts", []),
                    }
                    _active_session = session_info
                    return dict(session_info)
                except json.JSONDecodeError:
                    pass
            if proc.poll() is not None:
                stderr = (proc.stderr or b"").read().decode()
                if _collector_process is proc:
                    _collector_process = None
                return {"error": f"Collector exited immediately: {stderr}"}
            await asyncio.sleep(0.1)

        try:
            await asyncio.to_thread(_kill_and_reap_process, proc)
        except subprocess.TimeoutExpired:
            return {"error": "Collector did not exit after timeout kill"}
        finally:
            if _collector_process is proc:
                _collector_process = None
        return {"error": "Collector did not write ready file within 10s"}


@mcp.tool()
def stop_debug_session() -> dict[str, Any]:
    """Stop the active debug collector and clean up artifacts.

    Shuts down the collector process, deletes all session artifacts
    (log files, ready files, location state), and removes the scratch
    directory if empty.
    """
    if _active_session is None and _collector_process is None:
        return {"error": "No active debug session."}

    deleted = _cleanup_collector_session()
    return {"status": "stopped", "deleted_artifacts": deleted}


@mcp.tool()
def check_collector_health() -> dict[str, Any]:
    """Check if the debug collector is alive and responding."""
    session = _require_session()
    if "error" in session:
        return session

    health_url = session.get("health_url")
    if not health_url:
        return {"error": "No health URL in session."}

    try:
        result = _http_get(health_url)
        return {"status": "healthy", "details": result}
    except (urllib.error.URLError, OSError) as e:
        return {"status": "unhealthy", "error": str(e)}


@mcp.tool()
def ingest_log(
    message: str,
    hypothesis_id: str = "",
    location: str = "",
    run_id: str = "mcp",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a log entry to the debug collector.

    Use this to record observations, variable states, control flow evidence,
    or any data that helps confirm or reject hypotheses. Each log entry should
    be mapped to at least one hypothesis when possible.

    Args:
        message: Descriptive log message (what this evidence shows).
        hypothesis_id: Which hypothesis this log tests (e.g. "A", "B").
        location: Source location (e.g. "src/cart.ts:42" or "checkout flow step 3").
        run_id: Run identifier - use "mcp" for initial analysis, change for
                before/after comparison.
        data: Optional structured data (variable values, state snapshots, etc.).
    """
    session = _require_session()
    if "error" in session:
        return session

    ingest_url = session.get("ingest_url")
    if not ingest_url:
        return {"error": "No ingest URL in session."}

    payload: dict[str, Any] = {"message": message, "runId": run_id}
    if hypothesis_id:
        payload["hypothesisId"] = hypothesis_id
    if location:
        payload["location"] = location
    if data:
        payload["data"] = data

    try:
        result = _http_post(ingest_url, data=payload)
        return {"status": "logged", "entry": payload, "result": result}
    except (urllib.error.URLError, OSError) as e:
        return {"error": f"Failed to ingest log: {e}"}


@mcp.tool()
def get_debug_state() -> dict[str, Any]:
    """Get the full collector state: entry counts, run counts, hypothesis counts, and service metadata."""
    session = _require_session()
    if "error" in session:
        return session

    state_url = session.get("state_url")
    if not state_url:
        return {"error": "No state URL in session."}

    try:
        return _http_get(state_url)
    except (urllib.error.URLError, OSError) as e:
        return {"error": f"Failed to get state: {e}"}


@mcp.tool()
def get_debug_logs(
    offset: int = 0,
    limit: int = 120,
    order: str = "desc",
) -> dict[str, Any]:
    """Get paginated debug log entries from the collector.

    Args:
        offset: Number of entries to skip.
        limit: Maximum entries to return (max 300).
        order: Sort order - 'asc' for oldest first, 'desc' for newest first.
    """
    session = _require_session()
    if "error" in session:
        return session

    logs_url = session.get("logs_url")
    if not logs_url:
        return {"error": "No logs URL in session."}

    logs_url = f"{logs_url}?offset={offset}&limit={min(limit, 300)}&order={order}"
    try:
        return _http_get(logs_url)
    except (urllib.error.URLError, OSError) as e:
        return {"error": f"Failed to get logs: {e}"}


@mcp.tool()
def clear_debug_logs() -> dict[str, Any]:
    """Clear all debug logs for the current session.

    Use this before a new reproduction run so stale entries don't pollute evidence.
    """
    session = _require_session()
    if "error" in session:
        return session

    clear_url = session.get("clear_url")
    token = session.get("dashboard_token")
    if not clear_url:
        return {"error": "No clear URL in session."}

    try:
        return _http_post(clear_url, token=token)
    except (urllib.error.URLError, OSError) as e:
        return {"error": f"Failed to clear logs: {e}"}


@mcp.tool()
def sync_instrumentation_locations(
    locations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Sync active instrumentation locations with the collector.

    This replaces the full set of tracked locations (replace semantics).
    Call this after adding or removing instrumentation in your code.

    Args:
        locations: List of location objects, each with:
            - location: str (e.g. "src/cart.ts:118")
            - hypothesisIds: list[str] (e.g. ["A", "B"])
    """
    session = _require_session()
    if "error" in session:
        return session

    sync_url = session.get("locations_sync_url")
    token = session.get("dashboard_token")
    if not sync_url:
        return {"error": "No sync URL in session."}

    try:
        return _http_post(sync_url, data={"locations": locations}, token=token)
    except (urllib.error.URLError, OSError) as e:
        return {"error": f"Failed to sync locations: {e}"}


@mcp.tool()
def open_location_in_ide(location: str) -> dict[str, Any]:
    """Open a source file location in the configured IDE.

    Args:
        location: Source location string, e.g. "src/cart.ts:42" or "src/cart.ts:42:5".
    """
    session = _require_session()
    if "error" in session:
        return session

    open_url = session.get("open_location_url")
    token = session.get("dashboard_token")
    if not open_url:
        return {"error": "No open-location URL in session."}
    try:
        return _http_post(open_url, data={"location": location}, token=token)
    except (urllib.error.URLError, OSError) as e:
        return {"error": f"Failed to open location: {e}"}


# --- Resources ---


@mcp.resource("debug://workflow")
def get_workflow() -> str:
    """The full debug workflow (16-step evidence-first debugging process with guardrails)."""
    return SKILL_MD.read_text(encoding="utf-8")


@mcp.resource("debug://reference")
def get_reference() -> str:
    """Runtime debugging reference: collector bootstrap, log format, CORS, cleanup rules."""
    return RUNTIME_DEBUGGING_MD.read_text(encoding="utf-8")


# --- Prompts ---


@mcp.prompt()
def debug_workflow() -> str:
    """The complete 16-step evidence-first debugging workflow.

    Use this prompt to load the full debug methodology into your context
    before starting a debugging session.
    """
    return SKILL_MD.read_text(encoding="utf-8")


@mcp.prompt()
def hypothesis_template(
    bug_description: str = "",
    hypotheses: str = "",
) -> str:
    """Structured template for generating and tracking debug hypotheses.

    Args:
        bug_description: Brief description of the bug being debuged.
        hypotheses: Comma-separated list of hypothesis statements.
    """
    template = """# Debug Hypotheses

## Bug
{bug}

## Hypotheses

| ID | Hypothesis | Falsified By | Status |
|----|-----------|--------------|--------|
| A  | {h0} | | PENDING |
| B  | {h1} | | PENDING |
| C  | {h2} | | PENDING |
| D  | {h3} | | PENDING |
| E  | {h4} | | PENDING |

## Instrumentation Plan

For each hypothesis, identify:
- What log point would confirm or reject it
- Where in the code to inject it
- What data to capture (parameters, return values, branch choice)

## Evidence

After reproduction, fill in:
- Log entries that confirm/reject each hypothesis
- Root cause (which hypothesis was CONFIRMED)
- Fix applied

## Verification

After fix:
- Post-fix log entries showing the issue is resolved
- All temporary instrumentation removed
"""
    h_list = [h.strip() for h in hypotheses.split(",")] if hypotheses else [""] * 5
    while len(h_list) < 5:
        h_list.append("")
    return template.format(
        bug=bug_description or "(describe the bug)",
        h0=h_list[0] or "(hypothesis A)",
        h1=h_list[1] or "(hypothesis B)",
        h2=h_list[2] or "(hypothesis C)",
        h3=h_list[3] or "(hypothesis D)",
        h4=h_list[4] or "(hypothesis E)",
    )


def main() -> None:
    """Run the MCP server with stdio transport."""
    _register_shutdown_cleanup()
    try:
        mcp.run(transport="stdio")
    finally:
        _cleanup_collector_session()


if __name__ == "__main__":
    main()
