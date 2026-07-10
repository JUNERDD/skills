#!/usr/bin/env python3
"""Manage the bundled local debug collector through its local HTTP API."""

from __future__ import annotations

import argparse
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
SESSION_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
DEFAULT_TIMEOUT_SECONDS = 10.0


class SessionError(RuntimeError):
    """Raised for safe, user-actionable session lifecycle failures."""


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
                f"a healthy session already uses this ready file: {ready_file}; "
                "reuse it or stop it first"
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
            payload["readyFile"] = str(ready_file)
            payload["lifecycleMode"] = "local-cli"
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


def command_health(args: argparse.Namespace) -> dict[str, Any]:
    ready_path, payload = _read_ready_file(args.ready_file)
    result = _http_json(_session_url(payload, "healthUrl"), timeout=args.timeout)
    return {"ok": True, "readyFile": str(ready_path), "health": result}


def command_state(args: argparse.Namespace) -> dict[str, Any]:
    ready_path, payload = _read_ready_file(args.ready_file)
    result = _http_json(_session_url(payload, "stateUrl"), timeout=args.timeout)
    return {"ok": True, "readyFile": str(ready_path), "state": result}


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


def _load_locations(path_text: str) -> list[Any]:
    path = Path(path_text).expanduser().resolve()
    if not path.exists():
        raise SessionError(f"locations file not found: {path}")
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionError(f"cannot read locations file {path}: {exc}") from exc
    if isinstance(payload, dict):
        payload = payload.get("locations")
    if not isinstance(payload, list):
        raise SessionError("locations file must contain an array or an object with a locations array")
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


def _wait_until_stopped(payload: dict[str, Any], *, wait_seconds: float) -> bool:
    health_url = str(payload.get("healthUrl") or "")
    if not health_url:
        return True
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        try:
            _http_json(health_url, timeout=0.25)
        except SessionError:
            return True
        time.sleep(0.1)
    return False


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

    shutdown_url = str(payload.get("shutdownUrl") or "")
    shutdown_result: dict[str, Any] | None = None
    if shutdown_url:
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

    if not _wait_until_stopped(payload, wait_seconds=args.wait_seconds):
        raise SessionError("collector is still reachable after shutdown; artifacts were not deleted")

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
    start.add_argument(
        "--open-dashboard",
        action="store_true",
        help="Open the collector dashboard. Headless is the default.",
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

    health = subparsers.add_parser("health", help="Check collector health.")
    _add_ready_and_timeout(health)
    health.set_defaults(handler=command_health)

    state = subparsers.add_parser("state", help="Read full collector state.")
    _add_ready_and_timeout(state)
    state.set_defaults(handler=command_state)

    logs = subparsers.add_parser("logs", help="Read a bounded metadata window from the collector.")
    _add_ready_and_timeout(logs)
    logs.add_argument("--offset", type=int, default=0)
    logs.add_argument("--limit", type=int, default=120)
    logs.add_argument("--order", choices=("asc", "desc"), default="desc")
    logs.set_defaults(handler=command_logs)

    clear = subparsers.add_parser("clear", help="Clear the active session log.")
    _add_ready_and_timeout(clear)
    clear.set_defaults(handler=command_clear)

    sync = subparsers.add_parser(
        "sync-locations", help="Replace the complete active instrumentation-location set."
    )
    _add_ready_and_timeout(sync)
    sync.add_argument("--locations-file", required=True, help="JSON array or {locations:[...]} file.")
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
