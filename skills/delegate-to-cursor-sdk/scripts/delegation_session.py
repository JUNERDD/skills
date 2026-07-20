#!/usr/bin/env python3
"""Create and safely clean one delegate-to-cursor-sdk temporary session."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterator
import uuid

try:
    import fcntl
except ImportError:  # pragma: no cover - unavailable on Windows
    fcntl = None  # type: ignore[assignment]


SKILL_ROOT = Path(__file__).resolve().parent.parent
MARKER_NAME = ".cursor-delegate-skill-session.json"
ROOT_PREFIX = "cursor-delegate-skill-"
SCHEMA_VERSION = 1
RUN_DIR_PATTERN = re.compile(r"^\d{8}T\d{9}Z-[0-9a-f]{8}$")
RUN_FILE_NAMES = {
    "events.ndjson",
    "metadata.json",
    "prompt.txt",
    "snapshot.v2.json",
    "status.json",
    "stream.ndjson",
}
RUNTIME_JSON_TEMP_PATTERN = re.compile(
    r"^(?:status\.json|metadata\.json|snapshot\.v2\.json)\."
    r"[1-9]\d*\."
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.tmp$"
)
ACTIVE_STATES = {"starting", "running"}
PAUSED_OR_UNCONFIRMED_STATES = {"needs_input", "needs_authorization", "interrupted"}
TERMINAL_STATES = {"succeeded", "failed", "error", "cancelled"}
SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SIGNAL_GRACE_SECONDS = 30.0
SIGNAL_KILL_SECONDS = 5.0


class SessionError(RuntimeError):
    """Raised when session ownership or cleanup safety cannot be proven."""


@dataclass(frozen=True)
class OwnedEntry:
    """One lstat-verified session entry pinned by filesystem identity."""

    path: Path
    device: int
    inode: int
    file_type: int

    @classmethod
    def from_stat(cls, path: Path, result: os.stat_result) -> "OwnedEntry":
        return cls(
            path=path,
            device=result.st_dev,
            inode=result.st_ino,
            file_type=stat.S_IFMT(result.st_mode),
        )

    def matches(self, result: os.stat_result) -> bool:
        return (
            self.device == result.st_dev
            and self.inode == result.st_ino
            and self.file_type == stat.S_IFMT(result.st_mode)
        )


def _dump(payload: Any, *, stream: Any = sys.stdout) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), file=stream)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolved_directory(value: str | Path, *, label: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise SessionError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise SessionError(f"{label} is not a directory: {path}")
    return path


def _validate_session_location(temp_root: Path, workspace: Path) -> None:
    skill_root = SKILL_ROOT.resolve()
    filesystem_root = Path(temp_root.anchor or "/").resolve()
    home = Path.home().resolve()
    if temp_root in {filesystem_root, home, workspace, skill_root}:
        raise SessionError(f"system temporary directory is a protected path: {temp_root}")
    if _is_relative_to(temp_root, workspace) or _is_relative_to(temp_root, skill_root):
        raise SessionError("system temporary directory must remain outside the workspace and skill directory")


def _assert_not_symlink(path: Path, *, label: str) -> os.stat_result:
    try:
        result = path.lstat()
    except FileNotFoundError as exc:
        raise SessionError(f"{label} does not exist: {path}") from exc
    if stat.S_ISLNK(result.st_mode):
        raise SessionError(f"refusing symlink {label}: {path}")
    return result


def _write_json_descriptor(descriptor: int, payload: dict[str, Any], *, truncate: bool) -> None:
    if truncate:
        os.ftruncate(descriptor, 0)
        os.lseek(descriptor, 0, os.SEEK_SET)
    try:
        os.fchmod(descriptor, 0o600)
    except OSError:
        pass
    remaining = memoryview(
        (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("short write while persisting private JSON")
        remaining = remaining[written:]


def _write_private_json(
    path: Path,
    payload: dict[str, Any],
    *,
    exclusive: bool,
    expected: OwnedEntry | None = None,
) -> None:
    flags = os.O_WRONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    if exclusive:
        flags |= os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        if expected is not None and not expected.matches(os.fstat(descriptor)):
            raise SessionError(f"owned JSON file changed before rewrite: {path}")
        _write_json_descriptor(descriptor, payload, truncate=not exclusive)
    finally:
        os.close(descriptor)


def _write_private_json_at(
    directory_fd: int,
    name: str,
    payload: dict[str, Any],
    *,
    exclusive: bool,
    expected: OwnedEntry | None = None,
) -> None:
    flags = os.O_WRONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    if exclusive:
        flags |= os.O_CREAT | os.O_EXCL
    descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
    try:
        if expected is not None and not expected.matches(os.fstat(descriptor)):
            raise SessionError(f"owned JSON file changed before descriptor-relative rewrite: {name}")
        _write_json_descriptor(descriptor, payload, truncate=not exclusive)
    finally:
        os.close(descriptor)


def command_start(args: argparse.Namespace) -> dict[str, Any]:
    workspace = _resolved_directory(args.workspace, label="workspace")
    temp_root = Path(tempfile.gettempdir()).resolve()
    _resolved_directory(temp_root, label="system temporary directory")
    _validate_session_location(temp_root, workspace)

    root = Path(tempfile.mkdtemp(prefix=ROOT_PREFIX, dir=temp_root)).resolve()
    try:
        root.chmod(0o700)
        packets = root / "packets"
        logs = root / "logs"
        leases = root / "leases"
        packets.mkdir(mode=0o700)
        logs.mkdir(mode=0o700)
        leases.mkdir(mode=0o700)
        session_id = str(uuid.uuid4())
        marker = root / MARKER_NAME
        payload = {
            "schemaVersion": SCHEMA_VERSION,
            "owner": "delegate-to-cursor-sdk",
            "sessionId": session_id,
            "sessionRoot": str(root),
            "tempRoot": str(temp_root),
            "workspace": str(workspace),
            "packetsDir": str(packets),
            "logsDir": str(logs),
            "leasesDir": str(leases),
            "cleanupOwner": "root-upstream-agent",
            "createdAtUtc": _utc_now(),
        }
        _write_private_json(marker, payload, exclusive=True)
    except Exception:
        try:
            (root / MARKER_NAME).unlink()
        except OSError:
            pass
        for path in (root / "packets", root / "logs", root / "leases"):
            try:
                path.rmdir()
            except OSError:
                pass
        try:
            root.rmdir()
        except OSError:
            pass
        raise

    return {"ok": True, "status": "created", "sessionFile": str(marker), **payload}


def _read_session(path_text: str) -> tuple[Path, Path, dict[str, Any]]:
    requested = Path(path_text).expanduser()
    marker = requested if requested.is_absolute() else Path.cwd() / requested
    marker = marker.absolute()
    if marker.name != MARKER_NAME:
        raise SessionError(f"session file must be named {MARKER_NAME}: {marker}")

    root = marker.parent
    current_temp_root = Path(tempfile.gettempdir()).resolve()
    if not marker.exists() and not root.exists():
        raise SessionError(f"session is absent; cleanup ownership cannot be re-proven: {root}")

    root_stat = _assert_not_symlink(root, label="session root")
    if not stat.S_ISDIR(root_stat.st_mode):
        raise SessionError(f"session root is not a directory: {root}")
    marker_stat = _assert_not_symlink(marker, label="session marker")
    if not stat.S_ISREG(marker_stat.st_mode):
        raise SessionError(f"session marker is not a regular file: {marker}")

    try:
        payload: Any = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionError(f"cannot read session marker {marker}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SessionError("session marker must contain a JSON object")
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise SessionError("unsupported session marker schema")
    if payload.get("owner") != "delegate-to-cursor-sdk":
        raise SessionError("session marker owner does not match this skill")
    if not isinstance(payload.get("sessionId"), str) or not payload["sessionId"]:
        raise SessionError("session marker does not contain a valid sessionId")

    recorded_root = Path(str(payload.get("sessionRoot") or "")).expanduser().resolve()
    recorded_temp_root = Path(str(payload.get("tempRoot") or "")).expanduser().resolve()
    workspace = Path(str(payload.get("workspace") or "")).expanduser().resolve()
    packets = Path(str(payload.get("packetsDir") or "")).expanduser().resolve()
    logs = Path(str(payload.get("logsDir") or "")).expanduser().resolve()
    leases = Path(str(payload.get("leasesDir") or "")).expanduser().resolve()

    if root.resolve() != recorded_root:
        raise SessionError("session marker root does not match its containing directory")
    if root.parent.resolve() != recorded_temp_root or recorded_temp_root != current_temp_root:
        raise SessionError("session root is not an immediate child of the recorded system temporary directory")
    if not root.name.startswith(ROOT_PREFIX):
        raise SessionError("session root does not have the owned temporary prefix")
    if packets != root / "packets" or logs != root / "logs" or leases != root / "leases":
        raise SessionError("session marker packet/log/lease paths do not match the owned layout")

    protected = {Path("/").resolve(), Path.home().resolve(), workspace, SKILL_ROOT.resolve()}
    for target in protected:
        if root == target or _is_relative_to(target, root):
            raise SessionError(f"session root would contain a protected path: {target}")
    if _is_relative_to(root, workspace) or _is_relative_to(root, SKILL_ROOT.resolve()):
        raise SessionError("session root must remain outside the workspace and skill directory")

    return marker, root, payload


def _normalized_cli_args(values: list[str]) -> list[str]:
    command = list(values)
    if command and command[0] == "--":
        command = command[1:]
    if not command or Path(command[0]).name != "cursor-delegate":
        raise SessionError("run requires a cursor-delegate command after --")
    if any(value == "--log-dir" or value.startswith("--log-dir=") for value in command[1:]):
        raise SessionError("run owns --log-dir; do not pass it inside the cursor-delegate command")
    return command


def _retained_log_directory(value: str, *, session_root: Path) -> Path:
    requested = Path(value).expanduser()
    if not requested.is_absolute():
        raise SessionError("--retained-log-dir must be an absolute path")
    try:
        requested.lstat()
    except FileNotFoundError:
        pass
    else:
        raise SessionError("--retained-log-dir must not already exist")

    resolved = requested.resolve(strict=False)
    parent = _resolved_directory(resolved.parent, label="retained log parent")
    resolved = parent / resolved.name
    if resolved == session_root or _is_relative_to(resolved, session_root):
        raise SessionError("--retained-log-dir must remain outside the owned session")
    return resolved


def _signal_exit_code(signum: int) -> int:
    return 128 + int(signum)


def command_run(args: argparse.Namespace) -> int:
    _, root, payload = _read_session(args.session_file)
    if not SAFE_NAME_PATTERN.fullmatch(args.log_name):
        raise SessionError("--log-name must be 1-128 safe filename characters")

    logs = Path(payload["logsDir"])
    leases = Path(payload["leasesDir"])
    caller_retained = args.retained_log_dir is not None
    log_base = (
        _retained_log_directory(args.retained_log_dir, session_root=root)
        if caller_retained
        else logs / args.log_name
    )
    command = _normalized_cli_args(args.cli_args)
    command.extend(("--log-dir", str(log_base)))
    logs_stat = _assert_not_symlink(logs, label="logs directory")
    leases_stat = _assert_not_symlink(leases, label="leases directory")
    if not stat.S_ISDIR(logs_stat.st_mode) or not stat.S_ISDIR(leases_stat.st_mode):
        raise SessionError("session log and lease paths must remain directories")
    logs_fd = _open_verified_directory(logs, OwnedEntry.from_stat(logs, logs_stat))
    try:
        leases_fd = _open_verified_directory(leases, OwnedEntry.from_stat(leases, leases_stat))
    except Exception:
        os.close(logs_fd)
        raise

    lease_id = str(uuid.uuid4())
    lease = leases / f"{args.log_name}.json"
    lease_payload = {
        "schemaVersion": SCHEMA_VERSION,
        "owner": "delegate-to-cursor-sdk",
        "sessionId": payload["sessionId"],
        "leaseId": lease_id,
        "wrapperPid": os.getpid(),
        "childPid": None,
        "logBase": str(log_base),
        "logOwnership": "caller-retained" if caller_retained else "session-owned",
        "phase": "starting-child",
        "argvSha256": hashlib.sha256("\0".join(command).encode("utf-8")).hexdigest(),
        "startedAtUtc": _utc_now(),
    }
    try:
        _write_private_json_at(leases_fd, lease.name, lease_payload, exclusive=True)
        lease_stat = os.stat(lease.name, dir_fd=leases_fd, follow_symlinks=False)
        lease_entry = OwnedEntry.from_stat(lease, lease_stat)
    except Exception:
        os.close(leases_fd)
        os.close(logs_fd)
        raise

    process: subprocess.Popen[Any] | None = None
    received_signal: int | None = None
    signal_started_at = 0.0
    force_kill = False
    previous_handlers: dict[int, Any] = {}

    def forward_signal(signum: int, _frame: Any) -> None:
        nonlocal received_signal, signal_started_at, force_kill
        if received_signal is not None:
            force_kill = True
            return
        received_signal = signum
        signal_started_at = time.monotonic()
        if process is not None and process.poll() is None:
            try:
                process.send_signal(signum)
            except ProcessLookupError:
                pass

    handled_signals = [signal.SIGINT, signal.SIGTERM]
    if hasattr(signal, "SIGHUP"):
        handled_signals.append(signal.SIGHUP)
    for signum in handled_signals:
        previous_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, forward_signal)

    def kill_child_group() -> None:
        if process is None or process.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass

    try:
        if caller_retained:
            log_base.mkdir(mode=0o700)
        else:
            os.mkdir(args.log_name, mode=0o700, dir_fd=logs_fd)
        if received_signal is not None:
            return _signal_exit_code(received_signal)
        process = subprocess.Popen(command, start_new_session=os.name == "posix")
        lease_payload["childPid"] = process.pid
        lease_payload["phase"] = "child-recorded"
        _write_private_json_at(
            leases_fd,
            lease.name,
            lease_payload,
            exclusive=False,
            expected=lease_entry,
        )
        if received_signal is not None and process.poll() is None:
            process.send_signal(received_signal)

        while True:
            try:
                return_code = process.wait(timeout=0.25)
                break
            except subprocess.TimeoutExpired:
                if received_signal is None:
                    continue
                elapsed = time.monotonic() - signal_started_at
                if force_kill or elapsed >= SIGNAL_GRACE_SECONDS + SIGNAL_KILL_SECONDS:
                    kill_child_group()
                elif elapsed >= SIGNAL_GRACE_SECONDS:
                    try:
                        process.terminate()
                    except ProcessLookupError:
                        pass

        if received_signal is not None:
            return _signal_exit_code(received_signal)
        return return_code
    except Exception:
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=SIGNAL_KILL_SECONDS)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                kill_child_group()
                try:
                    process.wait(timeout=SIGNAL_KILL_SECONDS)
                except subprocess.TimeoutExpired:
                    pass
        raise
    finally:
        try:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
            if process is None or process.poll() is not None:
                try:
                    current_lease = os.stat(
                        lease.name,
                        dir_fd=leases_fd,
                        follow_symlinks=False,
                    )
                except FileNotFoundError:
                    pass
                else:
                    if not lease_entry.matches(current_lease):
                        raise SessionError(f"delegation lease changed before wrapper cleanup: {lease}")
                    os.unlink(lease.name, dir_fd=leases_fd)
        finally:
            os.close(leases_fd)
            os.close(logs_fd)


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionError(f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SessionError(f"{label} must contain a JSON object: {path}")
    return value


def _pid_is_alive(value: Any) -> bool:
    if not isinstance(value, int) or value <= 0:
        return False
    try:
        os.kill(value, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _validate_status_records(
    records: list[tuple[Path, dict[str, Any]]],
    *,
    allowed_nonterminal: set[Path],
    override_reason: str,
    verdict: str,
) -> None:
    successful_records: list[tuple[int, dict[str, Any]]] = []
    for success_path, success_payload in records:
        if success_payload.get("state") != "succeeded":
            continue
        successful_records.append((success_path.stat().st_mtime_ns, success_payload))
    for path, payload in records:
        state = payload.get("state")
        if state in ACTIVE_STATES:
            raise SessionError(f"refusing cleanup while a run is {state}: {path}")
        if state in PAUSED_OR_UNCONFIRMED_STATES:
            if path.resolve() not in allowed_nonterminal:
                raise SessionError(
                    f"refusing cleanup for {state} status without an explicit --allow-status reconciliation: {path}"
                )
            if not override_reason.strip():
                raise SessionError("--allow-status requires --override-reason")
            if verdict != "abandoned":
                if state == "needs_authorization":
                    correlation_keys = ("task_packet_sha256",)
                else:
                    strong_keys = tuple(
                        key
                        for key in ("agent_id", "workstream_id")
                        if isinstance(payload.get(key), str) and payload.get(key)
                    )
                    correlation_keys = strong_keys or ("task_packet_sha256",)
                old_mtime = path.stat().st_mtime_ns
                has_later_success = any(
                    timestamp > old_mtime
                    and all(
                        isinstance(payload.get(key), str)
                        and payload.get(key)
                        and payload.get(key) == success.get(key)
                        for key in correlation_keys
                    )
                    for timestamp, success in successful_records
                )
                if not correlation_keys or not has_later_success:
                    label = "task hash" if state == "needs_authorization" else "agent/workstream/task"
                    raise SessionError(
                        f"accepted cleanup requires a later succeeded in-session status with matching {label} correlation: {path}"
                    )
        elif state not in TERMINAL_STATES:
            raise SessionError(f"refusing cleanup for unknown run state {state!r}: {path}")

        frontend = payload.get("frontend")
        if isinstance(frontend, dict) and _pid_is_alive(frontend.get("pid")):
            raise SessionError(f"refusing cleanup while the recorded frontend process is alive: {path}")


def _validate_and_collect(
    marker: Path,
    root: Path,
    payload: dict[str, Any],
    *,
    allowed_nonterminal: set[Path],
    allowed_incomplete_runs: set[Path],
    allowed_leases: set[Path],
    allowed_temp_artifacts: set[Path],
    override_reason: str,
    verdict: str,
) -> tuple[list[OwnedEntry], list[OwnedEntry], int]:
    packets = Path(payload["packetsDir"])
    logs = Path(payload["logsDir"])
    leases = Path(payload["leasesDir"])
    expected_top = {marker, packets, logs, leases}
    actual_top = set(root.iterdir())
    unknown_top = sorted(str(path) for path in actual_top - expected_top)
    if unknown_top:
        raise SessionError("session root contains unowned entries:\n" + "\n".join(unknown_top))

    files: list[OwnedEntry] = []
    directories: list[OwnedEntry] = []
    total_bytes = 0
    present_directories: set[Path] = set()
    for directory, label in (
        (packets, "packets directory"),
        (logs, "logs directory"),
        (leases, "leases directory"),
    ):
        result = _assert_not_symlink(directory, label=label)
        if not stat.S_ISDIR(result.st_mode):
            raise SessionError(f"{label} is not a directory: {directory}")
        directories.append(OwnedEntry.from_stat(directory, result))
        present_directories.add(directory)

    if packets in present_directories:
        for current, dirnames, filenames in os.walk(packets, topdown=True, followlinks=False):
            current_path = Path(current)
            for name in dirnames:
                child = current_path / name
                result = _assert_not_symlink(child, label="packet directory")
                if not stat.S_ISDIR(result.st_mode):
                    raise SessionError(f"packet child is not a directory: {child}")
                directories.append(OwnedEntry.from_stat(child, result))
            for name in filenames:
                child = current_path / name
                result = _assert_not_symlink(child, label="task packet")
                if not stat.S_ISREG(result.st_mode) or child.suffix.lower() != ".md":
                    raise SessionError(f"unowned packet artifact; expected an ordinary .md file: {child}")
                files.append(OwnedEntry.from_stat(child, result))
                total_bytes += result.st_size

    seen_allowed_leases: set[Path] = set()
    if leases in present_directories:
        for lease in leases.iterdir():
            lease_stat = _assert_not_symlink(lease, label="delegation lease")
            if not stat.S_ISREG(lease_stat.st_mode) or lease.suffix.lower() != ".json":
                raise SessionError(f"unowned lease artifact: {lease}")
            lease_payload = _load_json_object(lease, label="delegation lease")
            if lease_payload.get("owner") != "delegate-to-cursor-sdk" or lease_payload.get(
                "sessionId"
            ) != payload.get("sessionId"):
                raise SessionError(f"delegation lease ownership mismatch: {lease}")
            log_ownership = lease_payload.get("logOwnership", "session-owned")
            log_base_text = lease_payload.get("logBase")
            if not isinstance(log_base_text, str) or not Path(log_base_text).is_absolute():
                raise SessionError(f"delegation lease log path is invalid: {lease}")
            resolved_log_base = Path(log_base_text).resolve(strict=False)
            if log_ownership == "session-owned":
                expected_log_base = logs / lease.name.removesuffix(".json")
                if resolved_log_base != expected_log_base:
                    raise SessionError(f"delegation lease session log path mismatch: {lease}")
            elif log_ownership == "caller-retained":
                if resolved_log_base == root or _is_relative_to(resolved_log_base, root):
                    raise SessionError(f"caller-retained lease points inside the session: {lease}")
            else:
                raise SessionError(f"delegation lease log ownership is invalid: {lease}")
            if _pid_is_alive(lease_payload.get("wrapperPid")) or _pid_is_alive(
                lease_payload.get("childPid")
            ):
                raise SessionError(f"refusing cleanup while an owning CLI lease is alive: {lease}")
            resolved_lease = lease.resolve()
            if resolved_lease not in allowed_leases or not override_reason.strip():
                raise SessionError(
                    f"stale CLI lease requires exact --allow-lease reconciliation and --override-reason: {lease}"
                )
            seen_allowed_leases.add(resolved_lease)
            files.append(OwnedEntry.from_stat(lease, lease_stat))
            total_bytes += lease_stat.st_size

    status_records: list[tuple[Path, dict[str, Any]]] = []
    seen_incomplete_runs: set[Path] = set()
    seen_temp_artifacts: set[Path] = set()
    if logs in present_directories:
        for log_base in logs.iterdir():
            result = _assert_not_symlink(log_base, label="dispatch log directory")
            if not stat.S_ISDIR(result.st_mode):
                raise SessionError(f"logs may contain only per-dispatch directories: {log_base}")
            directories.append(OwnedEntry.from_stat(log_base, result))
            for child in log_base.iterdir():
                result = _assert_not_symlink(child, label="dispatch log artifact")
                if child.name == "latest":
                    if not stat.S_ISREG(result.st_mode):
                        raise SessionError(f"latest pointer is not a regular file: {child}")
                    files.append(OwnedEntry.from_stat(child, result))
                    total_bytes += result.st_size
                    continue
                if not stat.S_ISDIR(result.st_mode) or not RUN_DIR_PATTERN.fullmatch(child.name):
                    raise SessionError(f"unowned entry in dispatch log directory: {child}")
                directories.append(OwnedEntry.from_stat(child, result))
                has_status = False
                for artifact in child.iterdir():
                    artifact_stat = _assert_not_symlink(artifact, label="run artifact")
                    if not stat.S_ISREG(artifact_stat.st_mode):
                        raise SessionError(f"unowned run artifact: {artifact}")
                    if artifact.name in RUN_FILE_NAMES:
                        if artifact.name == "status.json":
                            has_status = True
                            status_records.append(
                                (artifact, _load_json_object(artifact, label="status file"))
                            )
                    elif RUNTIME_JSON_TEMP_PATTERN.fullmatch(artifact.name):
                        resolved_artifact = artifact.resolve()
                        if (
                            resolved_artifact not in allowed_temp_artifacts
                            or not override_reason.strip()
                        ):
                            raise SessionError(
                                "runtime atomic JSON residue requires exact --allow-temp-artifact "
                                f"reconciliation and --override-reason: {artifact}"
                            )
                        seen_temp_artifacts.add(resolved_artifact)
                    else:
                        raise SessionError(f"unowned run artifact: {artifact}")
                    files.append(OwnedEntry.from_stat(artifact, artifact_stat))
                    total_bytes += artifact_stat.st_size
                if not has_status:
                    resolved_run = child.resolve()
                    if resolved_run not in allowed_incomplete_runs or not override_reason.strip():
                        raise SessionError(
                            f"incomplete run directory requires exact --allow-incomplete-run reconciliation "
                            f"and --override-reason: {child}"
                        )
                    seen_incomplete_runs.add(resolved_run)

    _validate_status_records(
        status_records,
        allowed_nonterminal=allowed_nonterminal,
        override_reason=override_reason,
        verdict=verdict,
    )

    if allowed_incomplete_runs and verdict != "abandoned" and not any(
        payload.get("state") == "succeeded" for _, payload in status_records
    ):
        raise SessionError("accepted cleanup of an incomplete run requires another succeeded in-session run")

    allowed_paths = {entry.path.resolve() for entry in files}
    for allowed in allowed_nonterminal:
        if allowed not in allowed_paths or allowed.name != "status.json":
            raise SessionError(f"--allow-status must name a status.json inside this session: {allowed}")
    for allowed in allowed_incomplete_runs:
        if allowed not in seen_incomplete_runs:
            raise SessionError(f"--allow-incomplete-run must name an incomplete run inside this session: {allowed}")
    for allowed in allowed_leases:
        if allowed not in seen_allowed_leases:
            raise SessionError(f"--allow-lease must name a stale lease inside this session: {allowed}")
    for allowed in allowed_temp_artifacts:
        if allowed not in seen_temp_artifacts:
            raise SessionError(
                f"--allow-temp-artifact must name a recognized runtime JSON temp inside this session: {allowed}"
            )

    return files, directories, total_bytes


def _cleanup_payload(
    payload: dict[str, Any],
    files: list[OwnedEntry],
    directories: list[OwnedEntry],
    *,
    verdict: str,
    override_reason: str,
) -> dict[str, Any]:
    entries: dict[Path, tuple[OwnedEntry, str]] = {}
    root = Path(payload["sessionRoot"])
    for entry in directories:
        entries[entry.path] = (entry, "directory")
    for entry in files:
        entries[entry.path] = (entry, "file")
    manifest = []
    for path, (entry, kind) in sorted(entries.items(), key=lambda item: str(item[0])):
        relative = path.relative_to(root).as_posix()
        manifest.append(
            {
                "path": relative,
                "kind": kind,
                "device": entry.device,
                "inode": entry.inode,
                "fileType": entry.file_type,
            }
        )
    result = dict(payload)
    result["cleanupState"] = {
        "schemaVersion": 1,
        "phase": "deleting",
        "verdict": verdict,
        "startedAtUtc": _utc_now(),
        "overrideReasonSha256": (
            hashlib.sha256(override_reason.encode("utf-8")).hexdigest()
            if override_reason.strip()
            else None
        ),
        "entries": manifest,
    }
    return result


def _manifest_entry(root: Path, record: Any) -> tuple[OwnedEntry, str]:
    if not isinstance(record, dict):
        raise SessionError("cleanup manifest entry must be an object")
    relative_text = record.get("path")
    kind = record.get("kind")
    device = record.get("device")
    inode = record.get("inode")
    file_type = record.get("fileType")
    if not isinstance(relative_text, str) or not relative_text:
        raise SessionError("cleanup manifest entry has an invalid path")
    relative = Path(relative_text)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise SessionError(f"cleanup manifest entry has an unsafe path: {relative_text!r}")
    if kind not in {"file", "directory"}:
        raise SessionError(f"cleanup manifest entry has an invalid kind: {relative_text!r}")
    if any(not isinstance(value, int) or isinstance(value, bool) for value in (device, inode, file_type)):
        raise SessionError(f"cleanup manifest entry has an invalid identity: {relative_text!r}")
    expected_type = stat.S_IFREG if kind == "file" else stat.S_IFDIR
    if file_type != expected_type:
        raise SessionError(f"cleanup manifest entry type disagrees with its kind: {relative_text!r}")
    path = root.joinpath(*relative.parts)
    if path == root / MARKER_NAME or not _is_relative_to(path, root):
        raise SessionError(f"cleanup manifest entry targets a protected path: {relative_text!r}")
    return OwnedEntry(path, device, inode, file_type), kind


def _collect_cleanup_retry(
    marker: Path,
    root: Path,
    payload: dict[str, Any],
    *,
    verdict: str,
) -> tuple[list[OwnedEntry], list[OwnedEntry], int, dict[str, Any]]:
    cleanup_state = payload.get("cleanupState")
    if not isinstance(cleanup_state, dict):
        raise SessionError("cleanup retry state is malformed")
    if cleanup_state.get("schemaVersion") != 1 or cleanup_state.get("phase") != "deleting":
        raise SessionError("cleanup retry state is unsupported")
    if cleanup_state.get("verdict") != verdict:
        raise SessionError("cleanup retry verdict must match the recorded cleanup manifest")
    raw_entries = cleanup_state.get("entries")
    if not isinstance(raw_entries, list):
        raise SessionError("cleanup retry manifest is missing its entries")

    expected: dict[Path, tuple[OwnedEntry, str]] = {}
    for record in raw_entries:
        entry, kind = _manifest_entry(root, record)
        if entry.path in expected:
            raise SessionError(f"cleanup retry manifest contains a duplicate path: {entry.path}")
        expected[entry.path] = (entry, kind)

    files: list[OwnedEntry] = []
    directories: list[OwnedEntry] = []
    total_bytes = 0

    def visit(directory: Path) -> None:
        nonlocal total_bytes
        for child in directory.iterdir():
            if directory == root and child == marker:
                continue
            result = _assert_not_symlink(child, label="cleanup retry artifact")
            recorded = expected.get(child)
            if recorded is None:
                raise SessionError(f"cleanup retry found an unowned new entry: {child}")
            expected_entry, kind = recorded
            if not expected_entry.matches(result):
                raise SessionError(f"cleanup retry entry changed identity: {child}")
            if kind == "directory":
                if not stat.S_ISDIR(result.st_mode):
                    raise SessionError(f"cleanup retry directory changed type: {child}")
                directories.append(expected_entry)
                visit(child)
            else:
                if not stat.S_ISREG(result.st_mode):
                    raise SessionError(f"cleanup retry file changed type: {child}")
                files.append(expected_entry)
                total_bytes += result.st_size

    visit(root)
    return files, directories, total_bytes, payload


def _directory_open_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _entry_parts(entry: OwnedEntry, root: Path) -> tuple[str, ...]:
    try:
        parts = entry.path.relative_to(root).parts
    except ValueError as exc:
        raise SessionError(f"owned entry escaped the session root: {entry.path}") from exc
    if not parts or any(part in {"", ".", ".."} or os.sep in part for part in parts):
        raise SessionError(f"owned entry has an unsafe relative path: {entry.path}")
    return parts


def _open_verified_directory(path: Path, expected: OwnedEntry) -> int:
    descriptor = os.open(path, _directory_open_flags())
    if not expected.matches(os.fstat(descriptor)):
        os.close(descriptor)
        raise SessionError(f"owned directory changed after validation: {path}")
    return descriptor


@contextmanager
def _open_entry_parent(
    root_fd: int,
    root: Path,
    entry: OwnedEntry,
    directory_entries: dict[tuple[str, ...], OwnedEntry],
) -> Iterator[tuple[int, str]]:
    parts = _entry_parts(entry, root)
    descriptor = os.dup(root_fd)
    prefix: list[str] = []
    try:
        for component in parts[:-1]:
            prefix.append(component)
            expected = directory_entries.get(tuple(prefix))
            if expected is None:
                raise SessionError(f"owned parent directory was not validated: {entry.path}")
            try:
                child_fd = os.open(component, _directory_open_flags(), dir_fd=descriptor)
            except FileNotFoundError:
                raise
            except OSError as exc:
                raise SessionError(
                    f"owned parent directory became unsafe before deletion: {expected.path}"
                ) from exc
            os.close(descriptor)
            descriptor = child_fd
            if not expected.matches(os.fstat(descriptor)):
                raise SessionError(f"owned parent directory changed before deletion: {expected.path}")
        yield descriptor, parts[-1]
    finally:
        os.close(descriptor)


def _remove_owned_entry(
    root_fd: int,
    root: Path,
    entry: OwnedEntry,
    directory_entries: dict[tuple[str, ...], OwnedEntry],
    *,
    directory: bool,
    missing_ok: bool = True,
) -> bool:
    try:
        with _open_entry_parent(root_fd, root, entry, directory_entries) as (parent_fd, name):
            try:
                current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                if missing_ok:
                    return False
                raise SessionError(f"owned entry disappeared before deletion: {entry.path}") from None
            if not entry.matches(current):
                raise SessionError(f"owned entry changed before deletion: {entry.path}")
            if directory:
                os.rmdir(name, dir_fd=parent_fd)
            else:
                os.unlink(name, dir_fd=parent_fd)
            return True
    except FileNotFoundError:
        if missing_ok:
            return False
        raise SessionError(f"owned parent disappeared before deletion: {entry.path}") from None


def _acquire_marker_lock(marker: Path, expected: OwnedEntry) -> int:
    flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(marker, flags)
    if not expected.matches(os.fstat(descriptor)):
        os.close(descriptor)
        raise SessionError("session marker changed before cleanup lock acquisition")
    if fcntl is not None:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(descriptor)
            raise SessionError("another cleanup invocation already owns this session marker") from exc
    return descriptor


def _verified_root_parent(root: Path, expected: OwnedEntry) -> int:
    descriptor = os.open(root.parent, _directory_open_flags())
    try:
        current = os.stat(root.name, dir_fd=descriptor, follow_symlinks=False)
    except Exception:
        os.close(descriptor)
        raise
    if not expected.matches(current):
        os.close(descriptor)
        raise SessionError("session root changed before final removal")
    return descriptor


def command_cleanup(args: argparse.Namespace) -> dict[str, Any]:
    marker, root, payload = _read_session(args.session_file)
    marker_entry = OwnedEntry.from_stat(marker, _assert_not_symlink(marker, label="session marker"))
    root_entry = OwnedEntry.from_stat(root, _assert_not_symlink(root, label="session root"))
    marker_lock_fd = _acquire_marker_lock(marker, marker_entry)
    root_fd = -1
    root_parent_fd = -1
    try:
        root_fd = _open_verified_directory(root, root_entry)
        root_parent_fd = _verified_root_parent(root, root_entry)

        if payload.get("cleanupState") is not None:
            files, directories, total_bytes, cleanup_payload = _collect_cleanup_retry(
                marker,
                root,
                payload,
                verdict=args.verdict,
            )
        else:
            if args.verdict == "abandoned" and not args.override_reason.strip():
                raise SessionError("an abandoned session requires --override-reason")

            allowed_nonterminal = {
                Path(value).expanduser().resolve() for value in args.allow_status
            }
            allowed_incomplete_runs = {
                Path(value).expanduser().resolve() for value in args.allow_incomplete_run
            }
            allowed_leases = {Path(value).expanduser().resolve() for value in args.allow_lease}
            allowed_temp_artifacts = {
                Path(value).expanduser().resolve() for value in args.allow_temp_artifact
            }
            files, directories, total_bytes = _validate_and_collect(
                marker,
                root,
                payload,
                allowed_nonterminal=allowed_nonterminal,
                allowed_incomplete_runs=allowed_incomplete_runs,
                allowed_leases=allowed_leases,
                allowed_temp_artifacts=allowed_temp_artifacts,
                override_reason=args.override_reason,
                verdict=args.verdict,
            )
            cleanup_payload = _cleanup_payload(
                payload,
                files,
                directories,
                verdict=args.verdict,
                override_reason=args.override_reason,
            )
            _write_json_descriptor(marker_lock_fd, cleanup_payload, truncate=True)
            os.fsync(marker_lock_fd)

        unique_directories = {entry.path: entry for entry in directories}
        directory_entries = {
            entry.path.relative_to(root).parts: entry for entry in unique_directories.values()
        }
        deleted: list[str] = []
        for artifact in files:
            if _remove_owned_entry(
                root_fd,
                root,
                artifact,
                directory_entries,
                directory=False,
            ):
                deleted.append(str(artifact.path))
        for directory in sorted(
            unique_directories.values(),
            key=lambda value: len(value.path.parts),
            reverse=True,
        ):
            if _remove_owned_entry(
                root_fd,
                root,
                directory,
                directory_entries,
                directory=True,
            ):
                deleted.append(str(directory.path))

        remaining = set(os.listdir(root_fd))
        if remaining != {marker.name}:
            unexpected = sorted(remaining - {marker.name})
            raise SessionError(
                "session root changed during cleanup; refusing marker removal"
                + ("\n" + "\n".join(unexpected) if unexpected else "")
            )
        current_root = os.stat(root.name, dir_fd=root_parent_fd, follow_symlinks=False)
        if not root_entry.matches(current_root):
            raise SessionError("session root changed before marker removal")
        if not _remove_owned_entry(
            root_fd,
            root,
            marker_entry,
            directory_entries,
            directory=False,
            missing_ok=False,
        ):
            raise SessionError("session marker disappeared before final removal")
        deleted.append(str(marker))
        try:
            current_root = os.stat(root.name, dir_fd=root_parent_fd, follow_symlinks=False)
            if not root_entry.matches(current_root):
                raise SessionError("session root changed before final removal")
            os.rmdir(root.name, dir_fd=root_parent_fd)
        except (OSError, SessionError) as exc:
            recovery_error: OSError | None = None
            try:
                _write_private_json_at(root_fd, marker.name, cleanup_payload, exclusive=True)
            except OSError as marker_exc:
                recovery_error = marker_exc
            detail = f"; marker recovery failed: {recovery_error}" if recovery_error else ""
            raise SessionError(
                f"session root was not empty or changed after allowlisted cleanup: {root}{detail}"
            ) from exc
        deleted.append(str(root))
        if root.exists():
            raise SessionError(f"a path reappeared at the removed session root: {root}")
    finally:
        if root_parent_fd >= 0:
            os.close(root_parent_fd)
        if root_fd >= 0:
            os.close(root_fd)
        os.close(marker_lock_fd)

    return {
        "ok": True,
        "status": "cleaned",
        "sessionId": payload["sessionId"],
        "sessionRoot": str(root),
        "verdict": args.verdict,
        "deletedEntryCount": len(deleted),
        "deletedBytes": total_bytes,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage a private temporary session owned by delegate-to-cursor-sdk."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Create a private task-packet and log root.")
    start.add_argument("--workspace", required=True, help="Target repository/workspace path.")
    start.set_defaults(handler=command_start)

    run = subparsers.add_parser(
        "run", help="Run cursor-delegate in the foreground with an owned CLI lease and log base."
    )
    run.add_argument("--session-file", required=True, help="Exact marker path returned by start.")
    run.add_argument("--log-name", required=True, help="Unique single-level log-base name.")
    run.add_argument(
        "--retained-log-dir",
        help=(
            "Absolute caller-retained log directory outside the session. It must not exist; "
            "the wrapper creates it and cleanup never removes it."
        ),
    )
    run.add_argument("cli_args", nargs=argparse.REMAINDER, help="-- cursor-delegate <arguments>")
    run.set_defaults(handler=command_run)

    cleanup = subparsers.add_parser(
        "cleanup", help="Delete only allowlisted artifacts from an owned completed session."
    )
    cleanup.add_argument("--session-file", required=True, help="Exact marker path returned by start.")
    cleanup.add_argument(
        "--verdict",
        required=True,
        choices=("accepted", "accepted-with-notes", "abandoned"),
        help="Upstream terminal disposition. Pending, follow-up, and blocked states are not cleanable.",
    )
    cleanup.add_argument(
        "--allow-status",
        action="append",
        default=[],
        help=(
            "Exact in-session status.json whose needs_input, needs_authorization, or interrupted state "
            "was reconciled. Repeat as needed and provide --override-reason."
        ),
    )
    cleanup.add_argument(
        "--allow-incomplete-run",
        action="append",
        default=[],
        help="Exact in-session run directory left before status.json; requires --override-reason.",
    )
    cleanup.add_argument(
        "--allow-lease",
        action="append",
        default=[],
        help="Exact dead in-session CLI lease; requires --override-reason.",
    )
    cleanup.add_argument(
        "--allow-temp-artifact",
        action="append",
        default=[],
        help=(
            "Exact in-session status/metadata/snapshot atomic JSON .tmp residue left by an "
            "abrupt CLI exit; repeat as needed and provide --override-reason."
        ),
    )
    cleanup.add_argument(
        "--override-reason",
        default="",
        help="Required for abandoned sessions or explicitly reconciled nonterminal historical statuses.",
    )
    cleanup.set_defaults(handler=command_cleanup)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = args.handler(args)
    except KeyboardInterrupt:
        return 130
    except SessionError as exc:
        _dump({"ok": False, "error": str(exc)}, stream=sys.stderr)
        return 2
    except OSError as exc:
        _dump({"ok": False, "error": f"filesystem operation failed: {exc}"}, stream=sys.stderr)
        return 2
    if isinstance(result, int):
        return result
    _dump(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
