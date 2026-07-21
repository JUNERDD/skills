#!/usr/bin/env python3
"""Manage the bundled local debug collector through its local HTTP API."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

SKILL_ROOT = Path(__file__).resolve().parent.parent
COLLECTOR_MAIN = SKILL_ROOT / "scripts" / "local_log_collector" / "main.py"
COLLECTOR_DIR = COLLECTOR_MAIN.parent
SESSION_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_DASHBOARD_FRONTEND_CONFIRM_SECONDS = 3.0
DASHBOARD_FALLBACK_ATTEMPTS = 2
DASHBOARD_RECOVERY_HTTP_TIMEOUT_SECONDS = 5.0
PROCESS_START_CLOCK_SKEW_MS = 2_000
PROCESS_STARTUP_MAX_MS = 60_000

if str(COLLECTOR_DIR) not in sys.path:
    sys.path.insert(0, str(COLLECTOR_DIR))

from collector_browser import open_dashboard_in_browser  # noqa: E402


class SessionError(RuntimeError):
    """Raised for safe, user-actionable session lifecycle failures."""


@dataclass(frozen=True)
class _ProcessIdentity:
    pid: int
    started_at_ms: int | None
    command_line: str = ""


@dataclass(frozen=True)
class _CollectorProcessReference:
    pid: int
    started_at_ms: int | None
    command_line: str


def _json_dump(payload: Any, *, stream: Any = sys.stdout) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), file=stream)


def _validate_session_id(session_id: str) -> None:
    if SESSION_ID_PATTERN.fullmatch(session_id):
        return
    raise SessionError(
        "session_id must be 1-128 characters, start with a letter or number, "
        "and contain only letters, numbers, '.', '_', or '-'"
    )


def _resolved_directory(value: str | Path, *, label: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise SessionError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise SessionError(f"{label} is not a directory: {path}")
    return path


def _ensure_inside(path: Path, root: Path, *, label: str) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise SessionError(f"{label} must remain inside workspace_root: {path}") from exc


def _read_ready_file(path_text: str | Path) -> tuple[Path, dict[str, Any]]:
    path = Path(path_text).expanduser().resolve()
    if not path.exists():
        raise SessionError(f"ready file not found: {path}")
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionError(f"cannot read ready file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SessionError(f"ready file must contain a JSON object: {path}")
    payload.setdefault("readyFile", str(path))
    return path, payload


def _http_json(
    url: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    token: str | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    headers: dict[str, str] = {"Accept": "application/json"}
    body: bytes | None = None
    if method != "GET":
        headers["Content-Type"] = "application/json"
        body = json.dumps(data or {}, separators=(",", ":")).encode("utf-8")
    if token:
        headers["X-Debug-Dashboard-Token"] = token

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SessionError(f"HTTP {exc.code} from {url}: {detail or exc.reason}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SessionError(f"request failed for {url}: {exc}") from exc

    if not raw:
        return {}
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SessionError(f"non-JSON response from {url}") from exc
    if not isinstance(payload, dict):
        raise SessionError(f"expected JSON object from {url}")
    return payload


def _try_health(payload: dict[str, Any], timeout: float = 0.5) -> bool:
    health_url = str(payload.get("healthUrl") or "")
    if not health_url:
        return False
    try:
        _http_json(health_url, timeout=timeout)
    except SessionError:
        return False
    return True


def _matching_live_health(
    ready_payload: dict[str, Any],
    *,
    timeout: float,
) -> dict[str, Any]:
    health_url = str(ready_payload.get("healthUrl") or "")
    if not health_url:
        raise SessionError("ready file does not contain healthUrl")

    health = _http_json(health_url, timeout=timeout)
    if health.get("ok") is not True or health.get("status") != "running":
        raise SessionError("collector health is not running")

    for key in ("sessionId", "pid", "startedAt", "dashboardToken"):
        ready_value = ready_payload.get(key)
        health_value = health.get(key)
        if ready_value is None or health_value is None:
            raise SessionError(f"collector identity is missing {key}")
        if ready_value != health_value:
            raise SessionError(f"collector identity mismatch for {key}")

    for key in ("workspaceRoot", "logFile"):
        ready_value = ready_payload.get(key)
        health_value = health.get(key)
        if not isinstance(ready_value, str) or not ready_value:
            raise SessionError(f"ready file does not contain {key}")
        if not isinstance(health_value, str) or not health_value:
            raise SessionError(f"collector health does not contain {key}")
        ready_path = Path(ready_value).expanduser().resolve()
        health_path = Path(health_value).expanduser().resolve()
        if ready_path != health_path:
            raise SessionError(f"collector identity mismatch for {key}")

    return health


def _reused_session_payload(
    ready_path: Path,
    ready_payload: dict[str, Any],
    *,
    timeout: float,
) -> dict[str, Any]:
    recorded_ready_file = ready_payload.get("readyFile")
    if not isinstance(recorded_ready_file, str) or not recorded_ready_file:
        raise SessionError("ready file payload does not contain readyFile")
    if Path(recorded_ready_file).expanduser().resolve() != ready_path.resolve():
        raise SessionError("ready file payload does not match the requested ready file")

    health = _matching_live_health(ready_payload, timeout=timeout)
    result = {**ready_payload, **health}
    result["readyFile"] = str(ready_path)
    frontend_confirmed = result.get("dashboardFrontendOpenRecorded") is True
    dashboard_url = str(result.get("dashboardUrl") or "")
    if frontend_confirmed:
        dashboard_status = "frontend_confirmed"
        dashboard_error = ""
    elif result.get("dashboardAutoOpenEnabled") is False:
        dashboard_status = "disabled"
        dashboard_error = str(
            result.get("dashboardFrontendOpenLastError")
            or result.get("dashboardOpenError")
            or ""
        )
    else:
        dashboard_status = "frontend_not_confirmed"
        dashboard_error = str(
            result.get("dashboardFrontendOpenLastError")
            or result.get("dashboardOpenError")
            or ""
        )
    result["dashboardRecovery"] = {
        "status": dashboard_status,
        "dashboardUrl": dashboard_url,
        "frontendConfirmed": frontend_confirmed,
        "fallbackAttemptCount": 0,
        "fallbackAttempts": [],
        "error": " ".join(dashboard_error.split()),
    }
    result["lifecycleMode"] = "local-cli"
    result["sessionAction"] = "reused"
    return result


def _wait_for_dashboard_startup(
    ready_file: Path,
    *,
    session_id: str,
    wait_seconds: float,
    initial_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wait for the asynchronous auto-open attempt without making it a startup dependency."""

    deadline = time.monotonic() + max(wait_seconds, 0.0)
    latest: dict[str, Any] = dict(initial_payload or {})
    while True:
        try:
            _, candidate = _read_ready_file(ready_file)
        except SessionError:
            if time.monotonic() >= deadline:
                return latest
            time.sleep(0.05)
            continue
        if candidate.get("sessionId") != session_id:
            raise SessionError("collector rewrote the ready file for a different session")
        latest = candidate
        if "dashboardOpenPending" not in latest or not latest.get("dashboardOpenPending"):
            return latest
        if time.monotonic() >= deadline:
            return latest
        time.sleep(0.05)


def _terminate_started_process(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, 15)
        else:
            process.terminate()
        process.wait(timeout=2)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _tail_text(path: Path, max_bytes: int = 4096) -> str:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(size - max_bytes, 0))
            return handle.read().decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def command_start(args: argparse.Namespace) -> dict[str, Any]:
    if sys.version_info.major != 3:
        raise SessionError("debug_session.py requires Python 3")
    if not COLLECTOR_MAIN.exists():
        raise SessionError(f"collector entrypoint not found: {COLLECTOR_MAIN}")

    workspace_root = _resolved_directory(args.workspace_root, label="workspace_root")
    session_id = args.session_id or f"debug-{int(time.time() * 1000)}"
    _validate_session_id(session_id)

    artifact_dir = Path(args.artifact_dir).expanduser() if args.artifact_dir else Path(".debug-logs")
    if not artifact_dir.is_absolute():
        artifact_dir = workspace_root / artifact_dir
    artifact_dir = artifact_dir.resolve()
    _ensure_inside(artifact_dir, workspace_root, label="artifact_dir")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    log_file = artifact_dir / f"{session_id}.ndjson"
    location_state_file = artifact_dir / f"{session_id}.locations.json"
    ready_file = artifact_dir / f"{session_id}.json"
    service_log_file = artifact_dir / f"{session_id}.service.log"
    candidate_paths = (log_file, location_state_file, ready_file, service_log_file)

    if ready_file.exists():
        try:
            _, existing = _read_ready_file(ready_file)
        except SessionError:
            existing = {}
        if existing and _try_health(existing):
            raise SessionError(
                f"a reachable collector already uses this ready file: {ready_file}; "
                f"run resume --ready-file {ready_file}"
            )

    existing_paths = [path for path in candidate_paths if path.exists()]
    if existing_paths and not args.replace_stale:
        joined = "\n".join(str(path) for path in existing_paths)
        raise SessionError(
            "stale or existing session artifacts would be overwritten; use a new session ID "
            f"or --replace-stale after preserving evidence:\n{joined}"
        )
    if args.replace_stale:
        for path in existing_paths:
            if path.is_file():
                path.unlink()

    command = [
        sys.executable,
        str(COLLECTOR_MAIN),
        "--log-file",
        str(log_file),
        "--location-state-file",
        str(location_state_file),
        "--ready-file",
        str(ready_file),
        "--session-id",
        session_id,
        "--workspace-root",
        str(workspace_root),
        "--service-log-file",
        str(service_log_file),
        "--location-state-flush-ms",
        str(args.location_state_flush_ms),
    ]
    if not args.open_dashboard:
        command.append("--no-open-dashboard")
    if args.ide:
        command.extend(["--default-ide", args.ide])

    popen_kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "cwd": str(COLLECTOR_MAIN.parent),
    }
    if os.name == "nt":
        detached = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        new_group = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
        popen_kwargs["creationflags"] = detached | new_group
    else:
        popen_kwargs["start_new_session"] = True

    with service_log_file.open("ab", buffering=0) as service_log:
        process = subprocess.Popen(
            command,
            stdout=service_log,
            stderr=subprocess.STDOUT,
            **popen_kwargs,
        )

    deadline = time.monotonic() + args.wait_seconds
    while time.monotonic() < deadline:
        if ready_file.exists():
            try:
                _, payload = _read_ready_file(ready_file)
            except SessionError:
                time.sleep(0.05)
                continue
            if payload.get("sessionId") != session_id:
                _terminate_started_process(process)
                raise SessionError("collector wrote a ready file for a different session")
            if not _try_health(payload):
                time.sleep(0.05)
                continue
            if args.open_dashboard:
                payload = _wait_for_dashboard_startup(
                    ready_file,
                    session_id=session_id,
                    wait_seconds=args.dashboard_open_wait_seconds,
                    initial_payload=payload,
                )
                payload = _recover_dashboard_after_start(ready_file, payload)
            else:
                payload["dashboardRecovery"] = {
                    "status": "disabled",
                    "dashboardUrl": str(payload.get("dashboardUrl") or ""),
                    "frontendConfirmed": False,
                    "fallbackAttemptCount": 0,
                    "fallbackAttempts": [],
                    "error": "",
                }
            payload["readyFile"] = str(ready_file)
            payload["lifecycleMode"] = "local-cli"
            payload["sessionAction"] = "started"
            return payload
        if process.poll() is not None:
            detail = _tail_text(service_log_file)
            raise SessionError(
                "collector exited before becoming ready"
                + (f":\n{detail}" if detail else "")
            )
        time.sleep(0.05)

    _terminate_started_process(process)
    detail = _tail_text(service_log_file)
    raise SessionError(
        f"collector did not become ready within {args.wait_seconds:g}s"
        + (f":\n{detail}" if detail else "")
    )


def _session_url(payload: dict[str, Any], key: str) -> str:
    url = payload.get(key)
    if not isinstance(url, str) or not url:
        raise SessionError(f"ready file does not contain {key}")
    return url


def command_resume(args: argparse.Namespace) -> dict[str, Any]:
    ready_path, payload = _read_ready_file(args.ready_file)
    return _reused_session_payload(ready_path, payload, timeout=args.timeout)


def command_health(args: argparse.Namespace) -> dict[str, Any]:
    ready_path, payload = _read_ready_file(args.ready_file)
    result = _http_json(_session_url(payload, "healthUrl"), timeout=args.timeout)
    return {"ok": True, "readyFile": str(ready_path), "health": result}


def command_state(args: argparse.Namespace) -> dict[str, Any]:
    ready_path, payload = _read_ready_file(args.ready_file)
    result = _http_json(_session_url(payload, "stateUrl"), timeout=args.timeout)
    return {"ok": True, "readyFile": str(ready_path), "state": result}


def _single_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def command_dashboard_status(args: argparse.Namespace) -> dict[str, Any]:
    """Return one stable, user-visible dashboard line for reproduction handoffs."""

    ready_path, ready_payload = _read_ready_file(args.ready_file)
    service = ready_payload
    refreshed_state: dict[str, Any] | None = None
    refresh_error = ""
    try:
        refreshed_state = _http_json(
            _session_url(ready_payload, "stateUrl"),
            timeout=args.timeout,
        )
    except SessionError as exc:
        refresh_error = _single_line(exc)
    else:
        current_service = refreshed_state.get("service")
        if isinstance(current_service, dict):
            service = current_service

    dashboard_url = _single_line(service.get("dashboardUrl"))
    frontend_recorded = service.get("dashboardFrontendOpenRecorded")
    auto_open_enabled = service.get("dashboardAutoOpenEnabled")

    if not dashboard_url:
        status = "unavailable"
        frontend_confirmed: bool | None = None
    elif frontend_recorded is True:
        status = "frontend_confirmed"
        frontend_confirmed = True
    elif auto_open_enabled is False:
        status = "disabled"
        frontend_confirmed = False
    else:
        status = "frontend_not_confirmed"
        frontend_confirmed = False

    dashboard_error = ""
    if status != "frontend_confirmed":
        dashboard_error = _single_line(
            service.get("dashboardFrontendOpenLastError")
            or service.get("dashboardOpenError")
        )
    errors = [item for item in (dashboard_error, refresh_error) if item]
    error = "; ".join(errors)
    frontend_text = (
        "unknown" if frontend_confirmed is None else str(frontend_confirmed).lower()
    )

    recording_frozen: bool | None = None
    recording_generation: int | None = None
    service_recording_frozen = service.get("recordingFrozen")
    if isinstance(service_recording_frozen, bool):
        recording_frozen = service_recording_frozen
    elif refreshed_state is not None:
        state_status = refreshed_state.get("status")
        if state_status == "frozen":
            recording_frozen = True
        elif state_status == "running":
            recording_frozen = False
    service_recording_generation = service.get("recordingGeneration")
    if (
        isinstance(service_recording_generation, int)
        and not isinstance(service_recording_generation, bool)
        and service_recording_generation >= 0
    ):
        recording_generation = service_recording_generation
    recording_status = (
        "unknown"
        if recording_frozen is None
        else "frozen"
        if recording_frozen
        else "live"
    )
    line = (
        f"Dashboard: {status} — {dashboard_url or 'unavailable'} "
        f"(frontend confirmed: {frontend_text}; recording: {recording_status})"
    )
    if error:
        line += f" — error: {error}"

    return {
        "ok": True,
        "readyFile": str(ready_path),
        "status": status,
        "dashboardUrl": dashboard_url,
        "frontendConfirmed": frontend_confirmed,
        "recordingFrozen": recording_frozen,
        "recordingStatus": recording_status,
        "recordingGeneration": recording_generation,
        "error": error,
        "stateRefreshError": refresh_error,
        "line": line,
    }


def command_logs(args: argparse.Namespace) -> dict[str, Any]:
    ready_path, payload = _read_ready_file(args.ready_file)
    base_url = _session_url(payload, "logsUrl")
    query = urllib.parse.urlencode(
        {"offset": max(args.offset, 0), "limit": min(max(args.limit, 1), 300), "order": args.order}
    )
    result = _http_json(f"{base_url}?{query}", timeout=args.timeout)
    return {"ok": True, "readyFile": str(ready_path), "logs": result}


def command_clear(args: argparse.Namespace) -> dict[str, Any]:
    ready_path, payload = _read_ready_file(args.ready_file)
    result = _http_json(
        _session_url(payload, "clearUrl"),
        method="POST",
        token=str(payload.get("dashboardToken") or ""),
        timeout=args.timeout,
    )
    return {"ok": True, "readyFile": str(ready_path), "state": result}


def _command_set_recording_frozen(
    args: argparse.Namespace,
    *,
    frozen: bool,
) -> dict[str, Any]:
    ready_path, payload = _read_ready_file(args.ready_file)
    url_key = "freezeRecordingUrl" if frozen else "resumeRecordingUrl"
    result = _http_json(
        _session_url(payload, url_key),
        method="POST",
        token=str(payload.get("dashboardToken") or ""),
        timeout=args.timeout,
    )
    service = result.get("service") if isinstance(result, dict) else None
    recording_frozen = (
        service.get("recordingFrozen") if isinstance(service, dict) else None
    )
    recording_generation = (
        service.get("recordingGeneration") if isinstance(service, dict) else None
    )
    recording_status = (
        "frozen"
        if recording_frozen is True
        else "live"
        if recording_frozen is False
        else "unknown"
    )
    return {
        "ok": True,
        "readyFile": str(ready_path),
        "recordingFrozen": recording_frozen,
        "recordingStatus": recording_status,
        "recordingGeneration": recording_generation,
        "state": result,
    }


def command_freeze_recording(args: argparse.Namespace) -> dict[str, Any]:
    return _command_set_recording_frozen(args, frozen=True)


def command_resume_recording(args: argparse.Namespace) -> dict[str, Any]:
    return _command_set_recording_frozen(args, frozen=False)


def _dashboard_frontend_recorded(state: dict[str, Any]) -> bool:
    service = state.get("service") if isinstance(state, dict) else None
    return bool(
        isinstance(service, dict) and service.get("dashboardFrontendOpenRecorded")
    )


def _wait_for_dashboard_frontend(
    payload: dict[str, Any],
    *,
    timeout: float,
    confirm_seconds: float,
) -> tuple[bool, str]:
    state_url = _session_url(payload, "stateUrl")
    deadline = time.monotonic() + max(confirm_seconds, 0.0)
    last_error = ""

    while True:
        try:
            state = _http_json(state_url, timeout=timeout)
        except SessionError as exc:
            last_error = str(exc)
        else:
            last_error = ""
            if _dashboard_frontend_recorded(state):
                return True, ""
        if time.monotonic() >= deadline:
            return False, last_error
        time.sleep(0.1)


def _open_dashboard_attempt(
    ready_path: Path,
    payload: dict[str, Any],
    *,
    timeout: float,
    confirm_seconds: float,
) -> dict[str, Any]:
    """Open one dashboard view and distinguish launcher success from page load."""

    _http_json(_session_url(payload, "healthUrl"), timeout=timeout)
    dashboard_url = _session_url(payload, "dashboardUrl")

    initial_state = _http_json(_session_url(payload, "stateUrl"), timeout=timeout)
    if _dashboard_frontend_recorded(initial_state):
        return {
            "ok": True,
            "status": "already_open",
            "skipped": True,
            "readyFile": str(ready_path),
            "dashboardUrl": dashboard_url,
            "open": None,
            "frontendConfirmed": True,
            "failureRecorded": False,
            "failureRecordError": "",
        }

    result = open_dashboard_in_browser(dashboard_url)

    frontend_confirmed = False
    confirmation_error = ""
    if result.get("succeeded"):
        frontend_confirmed, confirmation_error = _wait_for_dashboard_frontend(
            payload,
            timeout=timeout,
            confirm_seconds=confirm_seconds,
        )

    failure_reason = ""
    if not result.get("succeeded"):
        failure_reason = str(result.get("error") or "dashboard_manual_open_failed")
    elif not frontend_confirmed:
        failure_reason = confirmation_error or (
            f"dashboard_frontend_not_confirmed_after_{confirm_seconds:g}s"
        )

    failure_recorded = False
    failure_record_error = ""
    if failure_reason:
        failed_url = str(payload.get("dashboardFrontendOpenFailedUrl") or "")
        if failed_url:
            try:
                _http_json(
                    failed_url,
                    method="POST",
                    data={
                        "error": failure_reason,
                        "attemptedUrl": dashboard_url,
                    },
                    token=str(payload.get("dashboardToken") or ""),
                    timeout=timeout,
                )
                failure_recorded = True
            except SessionError as exc:
                failure_record_error = str(exc)

    return {
        "ok": True,
        "status": (
            "frontend_confirmed"
            if frontend_confirmed
            else "open_request_failed"
            if not result.get("succeeded")
            else "frontend_not_confirmed"
        ),
        "skipped": False,
        "readyFile": str(ready_path),
        "dashboardUrl": dashboard_url,
        "open": result,
        "frontendConfirmed": frontend_confirmed,
        "confirmationError": confirmation_error,
        "failureReason": failure_reason,
        "failureRecorded": failure_recorded,
        "failureRecordError": failure_record_error,
    }


def command_open_dashboard(args: argparse.Namespace) -> dict[str, Any]:
    ready_path, payload = _read_ready_file(args.ready_file)
    return _open_dashboard_attempt(
        ready_path,
        payload,
        timeout=args.timeout,
        confirm_seconds=args.confirm_seconds,
    )


def _recover_dashboard_after_start(
    ready_path: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Confirm local dashboard startup with bounded, non-fatal fallback attempts."""

    dashboard_url = str(payload.get("dashboardUrl") or "")
    fallback_results: list[dict[str, Any]] = []
    frontend_confirmed = bool(payload.get("dashboardFrontendOpenRecorded"))
    recovery_error = ""

    if not frontend_confirmed and (
        payload.get("dashboardOpenSucceeded") or payload.get("dashboardOpenPending")
    ):
        try:
            frontend_confirmed, recovery_error = _wait_for_dashboard_frontend(
                payload,
                timeout=DASHBOARD_RECOVERY_HTTP_TIMEOUT_SECONDS,
                confirm_seconds=DEFAULT_DASHBOARD_FRONTEND_CONFIRM_SECONDS,
            )
        except SessionError as exc:
            recovery_error = str(exc)
    elif not frontend_confirmed:
        recovery_error = str(payload.get("dashboardOpenError") or "")

    for _ in range(DASHBOARD_FALLBACK_ATTEMPTS):
        if frontend_confirmed:
            break
        try:
            _, latest_payload = _read_ready_file(ready_path)
            if latest_payload.get("dashboardOpenPending"):
                recovery_error = "initial_dashboard_open_still_pending"
                break
            result = _open_dashboard_attempt(
                ready_path,
                latest_payload,
                timeout=DASHBOARD_RECOVERY_HTTP_TIMEOUT_SECONDS,
                confirm_seconds=DEFAULT_DASHBOARD_FRONTEND_CONFIRM_SECONDS,
            )
        except SessionError as exc:
            result = {
                "ok": False,
                "status": "recovery_error",
                "skipped": False,
                "readyFile": str(ready_path),
                "dashboardUrl": dashboard_url,
                "open": None,
                "frontendConfirmed": False,
                "confirmationError": str(exc),
                "failureReason": str(exc),
                "failureRecorded": False,
                "failureRecordError": "",
            }
        fallback_results.append(result)
        frontend_confirmed = bool(result.get("frontendConfirmed"))
        if not frontend_confirmed:
            recovery_error = str(
                result.get("failureReason")
                or result.get("confirmationError")
                or result.get("failureRecordError")
                or recovery_error
            )

    try:
        _, latest_payload = _read_ready_file(ready_path)
    except SessionError:
        latest_payload = dict(payload)
    if latest_payload.get("dashboardFrontendOpenRecorded"):
        frontend_confirmed = True
        recovery_error = ""

    fallback_attempt_count = sum(
        1 for result in fallback_results if not result.get("skipped")
    )
    latest_payload["dashboardRecovery"] = {
        "status": "frontend_confirmed" if frontend_confirmed else "frontend_not_confirmed",
        "dashboardUrl": dashboard_url,
        "frontendConfirmed": frontend_confirmed,
        "fallbackAttemptCount": fallback_attempt_count,
        "fallbackAttempts": fallback_results,
        "error": (
            ""
            if frontend_confirmed
            else recovery_error or "dashboard_frontend_not_confirmed"
        ),
    }
    return latest_payload


def _load_locations(path_text: str) -> list[Any]:
    path = Path(path_text).expanduser().resolve()
    if not path.exists():
        raise SessionError(f"locations file not found: {path}")
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionError(f"cannot read locations file {path}: {exc}") from exc
    if isinstance(payload, dict):
        if "probes" in payload:
            probes = payload["probes"]
            if not isinstance(probes, list):
                raise SessionError("coverage plan probes must be an array")
            if not probes:
                raise SessionError("coverage plan probes must be a non-empty array")

            locations: list[dict[str, Any]] = []
            for index, probe in enumerate(probes):
                if not isinstance(probe, dict):
                    raise SessionError(
                        f"coverage plan probe at index {index} must be an object"
                    )

                location = probe.get("location")
                if not isinstance(location, str) or not location.strip():
                    raise SessionError(
                        f"coverage plan probe at index {index} must have a non-empty location"
                    )
                hypothesis_ids = probe.get("hypothesisIds")
                if not isinstance(hypothesis_ids, list) or any(
                    not isinstance(item, str) or not item.strip()
                    for item in hypothesis_ids
                ):
                    raise SessionError(
                        f"coverage plan probe at index {index} must have a hypothesisIds string array"
                    )
                probe_id = probe.get("probeId")
                if not isinstance(probe_id, str) or not probe_id.strip():
                    raise SessionError(
                        f"coverage plan probe at index {index} must have a non-empty probeId"
                    )

                locations.append(
                    {
                        "location": location,
                        "hypothesisIds": hypothesis_ids,
                        "probeId": probe_id,
                    }
                )
            return locations
        elif "locations" in payload:
            payload = payload["locations"]
        else:
            raise SessionError(
                "locations file object must contain a locations array or a coverage plan probes array"
            )
    if not isinstance(payload, list):
        raise SessionError(
            "locations file must contain an array, an object with a locations array, "
            "or a coverage plan with a probes array"
        )
    return payload


def command_sync_locations(args: argparse.Namespace) -> dict[str, Any]:
    ready_path, payload = _read_ready_file(args.ready_file)
    locations = _load_locations(args.locations_file)
    result = _http_json(
        _session_url(payload, "syncLocationsUrl"),
        method="POST",
        data={"locations": locations},
        token=str(payload.get("dashboardToken") or ""),
        timeout=args.timeout,
    )
    return {
        "ok": True,
        "readyFile": str(ready_path),
        "submittedLocationCount": len(locations),
        "result": result,
    }


def _pid_exists_posix(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # An unexpected inspection error must not authorize artifact deletion.
        return True
    return True


def _read_windows_process_identity(pid: int) -> _ProcessIdentity | None:
    """Read a Windows process birth time without sending it a signal."""

    import ctypes
    from ctypes import wintypes

    process_query_limited_information = 0x1000
    still_active = 259
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        # ERROR_INVALID_PARAMETER means the PID does not exist. Access-denied and
        # other failures remain conservatively "present but unidentified".
        if ctypes.get_last_error() == 87:
            return None
        return _ProcessIdentity(pid=pid, started_at_ms=None)

    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return _ProcessIdentity(pid=pid, started_at_ms=None)
        if exit_code.value != still_active:
            return None

        creation = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel_time = wintypes.FILETIME()
        user_time = wintypes.FILETIME()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        ):
            return _ProcessIdentity(pid=pid, started_at_ms=None)
        filetime = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        started_at_ms = int(filetime / 10_000 - 11_644_473_600_000)
        return _ProcessIdentity(pid=pid, started_at_ms=started_at_ms)
    finally:
        kernel32.CloseHandle(handle)


def _read_process_identity(pid: int) -> _ProcessIdentity | None:
    if os.name == "nt":
        return _read_windows_process_identity(pid)

    command = [
        "ps",
        "-ww",
        "-p",
        str(pid),
        "-o",
        "lstart=",
        "-o",
        "stat=",
        "-o",
        "command=",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=1.0,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (OSError, subprocess.SubprocessError):
        if not _pid_exists_posix(pid):
            return None
        return _ProcessIdentity(pid=pid, started_at_ms=None)

    line = result.stdout.strip()
    if result.returncode != 0 or not line:
        if not _pid_exists_posix(pid):
            return None
        return _ProcessIdentity(pid=pid, started_at_ms=None)

    fields = line.split(None, 6)
    if len(fields) < 6:
        return _ProcessIdentity(pid=pid, started_at_ms=None)
    process_state = fields[5]
    if process_state.startswith("Z"):
        return None

    started_at_ms: int | None = None
    try:
        started_at_ms = int(
            time.mktime(time.strptime(" ".join(fields[:5]), "%a %b %d %H:%M:%S %Y"))
            * 1000
        )
    except (OverflowError, ValueError):
        pass
    command_line = fields[6] if len(fields) > 6 else ""
    return _ProcessIdentity(
        pid=pid,
        started_at_ms=started_at_ms,
        command_line=command_line,
    )


def _capture_collector_process_reference(
    payload: dict[str, Any],
    ready_path: Path,
) -> _CollectorProcessReference | None:
    pid = payload.get("pid")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        raise SessionError("ready file does not contain a valid collector pid")
    ready_started_at = payload.get("startedAt")
    if (
        not isinstance(ready_started_at, int)
        or isinstance(ready_started_at, bool)
        or ready_started_at <= 0
    ):
        raise SessionError("ready file does not contain a valid collector startedAt")

    identity = _read_process_identity(pid)
    if identity is None:
        return None

    if identity.started_at_ms is not None:
        startup_ms = ready_started_at - identity.started_at_ms
        if startup_ms < -PROCESS_START_CLOCK_SKEW_MS or startup_ms > PROCESS_STARTUP_MAX_MS:
            # The ready PID has already been reused by a differently born process.
            return None

    if identity.command_line:
        expected_markers = (str(COLLECTOR_MAIN.resolve()), str(ready_path.resolve()))
        if any(marker not in identity.command_line for marker in expected_markers):
            # A live but unrelated process now owns the recorded PID.
            return None

    return _CollectorProcessReference(
        pid=pid,
        started_at_ms=identity.started_at_ms,
        command_line=identity.command_line,
    )


def _same_process_is_running(reference: _CollectorProcessReference) -> bool:
    current = _read_process_identity(reference.pid)
    if current is None:
        return False
    if reference.started_at_ms is not None and current.started_at_ms is not None:
        if reference.started_at_ms != current.started_at_ms:
            return False
    if reference.command_line and current.command_line:
        if reference.command_line != current.command_line:
            return False
    # Missing current identity fields are inconclusive: the PID is still present,
    # so fail closed and keep waiting instead of deleting collector artifacts.
    return True


def _wait_until_stopped(
    reference: _CollectorProcessReference,
    *,
    wait_seconds: float,
) -> bool:
    deadline = time.monotonic() + max(wait_seconds, 0.0)
    while True:
        if not _same_process_is_running(reference):
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(0.1, remaining))


def _safe_artifact_paths(payload: dict[str, Any], workspace_root: Path) -> list[Path]:
    raw_paths = payload.get("ownedArtifacts")
    if not isinstance(raw_paths, list):
        raise SessionError("ready file does not contain a valid ownedArtifacts list")
    paths: list[Path] = []
    seen: set[str] = set()
    for value in raw_paths:
        if not isinstance(value, str) or not value:
            continue
        path = Path(value).expanduser().resolve()
        _ensure_inside(path, workspace_root, label="owned artifact")
        text = str(path)
        if text not in seen:
            seen.add(text)
            paths.append(path)
    return paths


def _safe_root_cause_path(path_text: str, workspace_root: Path) -> Path:
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = workspace_root / path
    path = path.resolve()
    _ensure_inside(path, workspace_root, label="root-cause document")
    if path.suffix.lower() != ".md":
        raise SessionError("root-cause document must use a .md suffix")
    return path


def command_stop(args: argparse.Namespace) -> dict[str, Any]:
    ready_path, payload = _read_ready_file(args.ready_file)
    workspace_value = payload.get("workspaceRoot")
    if not isinstance(workspace_value, str) or not workspace_value:
        raise SessionError("ready file does not contain workspaceRoot")
    workspace_root = _resolved_directory(workspace_value, label="workspaceRoot")

    process_reference = _capture_collector_process_reference(payload, ready_path)

    shutdown_url = str(payload.get("shutdownUrl") or "")
    shutdown_result: dict[str, Any] | None = None
    if shutdown_url and process_reference is not None:
        try:
            shutdown_result = _http_json(
                shutdown_url,
                method="POST",
                token=str(payload.get("dashboardToken") or ""),
                timeout=args.timeout,
            )
        except SessionError:
            # An already-stopped collector is acceptable only when it is no longer healthy.
            if _try_health(payload):
                raise

    if process_reference is not None and not _wait_until_stopped(
        process_reference,
        wait_seconds=args.wait_seconds,
    ):
        raise SessionError(
            "collector process is still running after shutdown; artifacts were not deleted"
        )

    artifacts = _safe_artifact_paths(payload, workspace_root)
    if args.keep_artifacts:
        return {
            "ok": True,
            "status": "stopped_artifacts_retained",
            "readyFile": str(ready_path),
            "shutdown": shutdown_result,
            "retainedArtifacts": [str(path) for path in artifacts],
        }

    deleted: list[str] = []
    for artifact in artifacts:
        try:
            if artifact.is_dir():
                raise SessionError(f"refusing to unlink directory listed as artifact: {artifact}")
            artifact.unlink()
            deleted.append(str(artifact))
        except FileNotFoundError:
            pass

    root_cause_deleted: str | None = None
    if args.delete_root_cause_document:
        document = _safe_root_cause_path(args.delete_root_cause_document, workspace_root)
        try:
            document.unlink()
            root_cause_deleted = str(document)
        except FileNotFoundError:
            root_cause_deleted = str(document)
        if document.exists():
            raise SessionError(f"root-cause document still exists after deletion: {document}")

    remaining = [str(path) for path in artifacts if path.exists()]
    if remaining:
        raise SessionError("collector cleanup left artifacts:\n" + "\n".join(remaining))

    artifact_anchor = payload.get("logFile")
    if isinstance(artifact_anchor, str) and artifact_anchor:
        artifact_dir = Path(artifact_anchor).expanduser().resolve().parent
        _ensure_inside(artifact_dir, workspace_root, label="artifact directory")
        try:
            artifact_dir.rmdir()
            deleted.append(str(artifact_dir))
        except OSError:
            pass

    return {
        "ok": True,
        "status": "stopped",
        "readyFile": str(ready_path),
        "shutdown": shutdown_result,
        "deletedArtifacts": deleted,
        "deletedRootCauseDocument": root_cause_deleted,
    }


def _add_ready_and_timeout(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ready-file", required=True, help="Collector ready JSON path.")
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Start and operate the bundled local debug collector."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start a detached collector session.")
    start.add_argument("--workspace-root", default=".", help="Target project root. Defaults to cwd.")
    start.add_argument("--session-id", default="", help="Unique session ID. Auto-generated when omitted.")
    start.add_argument(
        "--artifact-dir",
        default="",
        help="Artifact directory inside workspace. Defaults to .debug-logs.",
    )
    start.add_argument("--ide", default="", help="Optional dashboard IDE identifier.")
    dashboard_mode = start.add_mutually_exclusive_group()
    dashboard_mode.add_argument(
        "--open-dashboard",
        dest="open_dashboard",
        action="store_true",
        help="Open the collector dashboard automatically. This is the default.",
    )
    dashboard_mode.add_argument(
        "--no-open-dashboard",
        "--headless",
        dest="open_dashboard",
        action="store_false",
        help="Do not open a browser; use only for explicit headless, CI, or remote sessions.",
    )
    start.set_defaults(open_dashboard=True)
    start.add_argument(
        "--dashboard-open-wait-seconds",
        type=float,
        default=6.0,
        help="Maximum time to wait for the asynchronous dashboard-open attempt before returning.",
    )
    start.add_argument(
        "--replace-stale",
        action="store_true",
        help="Delete stale files for the same session ID after preserving any needed evidence.",
    )
    start.add_argument(
        "--location-state-flush-ms",
        type=int,
        default=250,
        help="Debounce interval for sidecar runtime updates. Use 0 to flush every event.",
    )
    start.add_argument("--wait-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    start.set_defaults(handler=command_start)

    resume = subparsers.add_parser(
        "resume",
        help="Reuse one exact healthy collector without starting a process or opening a dashboard.",
    )
    _add_ready_and_timeout(resume)
    resume.set_defaults(handler=command_resume)

    health = subparsers.add_parser("health", help="Check collector health.")
    _add_ready_and_timeout(health)
    health.set_defaults(handler=command_health)

    state = subparsers.add_parser("state", help="Read full collector state.")
    _add_ready_and_timeout(state)
    state.set_defaults(handler=command_state)

    dashboard_status = subparsers.add_parser(
        "dashboard-status",
        help="Print normalized dashboard status for a user reproduction handoff.",
    )
    _add_ready_and_timeout(dashboard_status)
    dashboard_status.set_defaults(handler=command_dashboard_status)

    logs = subparsers.add_parser("logs", help="Read a bounded metadata window from the collector.")
    _add_ready_and_timeout(logs)
    logs.add_argument("--offset", type=int, default=0)
    logs.add_argument("--limit", type=int, default=120)
    logs.add_argument("--order", choices=("asc", "desc"), default="desc")
    logs.set_defaults(handler=command_logs)

    clear = subparsers.add_parser("clear", help="Clear the active session log.")
    _add_ready_and_timeout(clear)
    clear.set_defaults(handler=command_clear)

    freeze_recording = subparsers.add_parser(
        "freeze-recording",
        help="Discard new debug events at the collector while keeping Clear available.",
    )
    _add_ready_and_timeout(freeze_recording)
    freeze_recording.set_defaults(handler=command_freeze_recording)

    resume_recording = subparsers.add_parser(
        "resume-recording",
        help="Resume collector writes for future debug events.",
    )
    _add_ready_and_timeout(resume_recording)
    resume_recording.set_defaults(handler=command_resume_recording)

    open_dashboard = subparsers.add_parser(
        "open-dashboard",
        help="Retry opening the dashboard for an existing healthy session.",
    )
    _add_ready_and_timeout(open_dashboard)
    open_dashboard.add_argument(
        "--confirm-seconds",
        type=float,
        default=DEFAULT_DASHBOARD_FRONTEND_CONFIRM_SECONDS,
        help="Wait briefly for the dashboard frontend page-load callback.",
    )
    open_dashboard.set_defaults(handler=command_open_dashboard)

    sync = subparsers.add_parser(
        "sync-locations", help="Replace the complete active instrumentation-location set."
    )
    _add_ready_and_timeout(sync)
    sync.add_argument(
        "--locations-file",
        required=True,
        help="JSON array, {locations:[...]}, or coverage-plan file.",
    )
    sync.set_defaults(handler=command_sync_locations)

    stop = subparsers.add_parser("stop", help="Stop the collector and clean owned artifacts.")
    _add_ready_and_timeout(stop)
    stop.add_argument("--wait-seconds", type=float, default=5.0)
    stop.add_argument("--keep-artifacts", action="store_true")
    stop.add_argument(
        "--delete-root-cause-document",
        default="",
        help="Optional Markdown path inside workspace to delete after successful verification.",
    )
    stop.set_defaults(handler=command_stop)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        payload = args.handler(args)
    except SessionError as exc:
        _json_dump({"ok": False, "error": str(exc)}, stream=sys.stderr)
        return 1
    _json_dump(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
