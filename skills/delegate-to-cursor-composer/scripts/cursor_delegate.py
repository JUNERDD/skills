#!/usr/bin/env python3
"""Dispatch a bounded task packet to Cursor Agent/Composer in headless mode."""

from __future__ import annotations

import argparse
from collections import Counter
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit
import uuid

DEFAULT_CURSOR_MODEL = "composer-2.5-fast"
STATUS_TEXT_LIMIT = 800
RECENT_TOOL_LIMIT = 12
RECENT_SUBAGENT_LIMIT = 12
PROMPT_ARG_LIMIT = 100_000

AUTHORITY_HEADINGS: dict[str, str] = {
    "master-direct": "Master Direct Implementation Instructions",
    "non-cursor-planning-subagent": "Approved Upstream Plan",
    "orchestrator-subagent": "Approved Local Plan",
    "user-provided-plan": "User-Provided Approved Plan",
    "follow-up": "Cursor Follow-up Task Packet",
}
FOLLOW_UP_REQUIRED_HEADINGS = ("Original Authority", "Review Findings to Address")
PLANNING_SOURCE_CHOICES = tuple(["auto", *AUTHORITY_HEADINGS.keys()])
HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
PLACEHOLDER_RE = re.compile(r"<([^>\n]{1,160})>")
PLACEHOLDER_LEAD_WORDS = {
    "accepted",
    "allowed",
    "api",
    "approved",
    "branch",
    "command",
    "concrete",
    "condition",
    "criterion",
    "description",
    "disabled",
    "exact",
    "explicit",
    "id",
    "item",
    "known",
    "log-dir",
    "local",
    "master-direct",
    "mode",
    "none",
    "non-goal",
    "one",
    "owner",
    "path",
    "purpose",
    "repo",
    "stable",
    "status",
    "step",
    "summarize",
    "user",
    "workspace",
    "0-2",
    "0-4",
}
SENSITIVE_KEY_RE = re.compile(
    r"(token|secret|api[_-]?key|authorization|cookie|password|credential|private[_-]?key)",
    re.IGNORECASE,
)
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)(token|secret|api[_-]?key|authorization|cookie|password|credential|private[_-]?key)(\s*[:=]\s*)([^\s,;]+)"
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def markdown_headings(task_text: str) -> list[str]:
    headings: list[str] = []
    for match in HEADING_RE.finditer(task_text):
        heading = match.group(1).strip().rstrip("#").strip()
        if heading:
            headings.append(heading)
    return headings


def section_body(task_text: str, heading: str) -> str:
    matches = list(HEADING_RE.finditer(task_text))
    for index, match in enumerate(matches):
        current = match.group(1).strip().rstrip("#").strip()
        if current != heading:
            continue
        marker = match.group(0).lstrip()
        level = len(marker) - len(marker.lstrip("#"))
        start = match.end()
        end = len(task_text)
        for next_match in matches[index + 1:]:
            next_marker = next_match.group(0).lstrip()
            next_level = len(next_marker) - len(next_marker.lstrip("#"))
            if next_level <= level:
                end = next_match.start()
                break
        return task_text[start:end].strip()
    return ""


def looks_like_template_placeholder(token: str) -> bool:
    normalized = token.strip().lower()
    if not normalized:
        return False
    if re.fullmatch(r"/[a-z][a-z0-9:-]*", normalized):
        return False
    if any(separator in normalized for separator in (" ", "|", " or ", " if ", "/", "`")):
        return True
    first_word = re.split(r"[^a-z0-9-]+", normalized, maxsplit=1)[0]
    return first_word in PLACEHOLDER_LEAD_WORDS


def placeholder_tokens(task_text: str) -> list[str]:
    return sorted(
        {
            match.group(0)
            for match in PLACEHOLDER_RE.finditer(task_text)
            if looks_like_template_placeholder(match.group(1))
        }
    )


def authority_sources(task_text: str) -> list[str]:
    counts = Counter(markdown_headings(task_text))
    return [source for source, heading in AUTHORITY_HEADINGS.items() if counts[heading] > 0]


def validate_authority(task_text: str, expected: str, allow_placeholders: bool) -> tuple[bool, str | None, str]:
    placeholders = placeholder_tokens(task_text)
    if placeholders and not allow_placeholders:
        return False, None, f"task packet contains {len(placeholders)} unresolved placeholder token(s)"

    headings = markdown_headings(task_text)
    counts = Counter(headings)
    for source, heading in AUTHORITY_HEADINGS.items():
        if counts[heading] > 1:
            return False, None, f"authority heading appears more than once: {heading}"

    sources = authority_sources(task_text)
    if expected != "auto":
        if sources != [expected]:
            return False, None, f"expected exactly {expected}; found {sources or ['none']}"
        detected = expected
    else:
        if len(sources) != 1:
            return False, None, f"expected exactly one authority heading; found {sources or ['none']}"
        detected = sources[0]

    authority_heading = AUTHORITY_HEADINGS[detected]
    if not section_body(task_text, authority_heading):
        return False, None, f"authority section is empty: {authority_heading}"

    if detected == "follow-up":
        for required in FOLLOW_UP_REQUIRED_HEADINGS:
            if not section_body(task_text, required):
                return False, None, f"follow-up packet requires non-empty section: {required}"
    return True, detected, "authority accepted"


def describe_authority(source: str) -> str:
    descriptions = {
        "master-direct": "The Master Direct Implementation Instructions section is the source of truth.",
        "non-cursor-planning-subagent": "The Approved Upstream Plan section is the source of truth after upstream review.",
        "orchestrator-subagent": "The Approved Local Plan section is the source of truth within its workstream contract.",
        "user-provided-plan": "The User-Provided Approved Plan section is the source of truth after upstream acceptance.",
        "follow-up": "The Cursor Follow-up Task Packet section is the source of truth for a narrow follow-up loop.",
    }
    return descriptions[source]


def resolve_executable(value: str) -> str | None:
    candidate = Path(value).expanduser()
    if candidate.exists():
        return str(candidate.resolve())
    return shutil.which(value)


def find_cursor_agent(explicit: str | None = None) -> str:
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    for env_name in ("CURSOR_AGENT_PATH", "AGENT_PATH"):
        env_value = os.environ.get(env_name)
        if env_value:
            candidates.append(env_value)
    candidates.extend(["cursor-agent", "agent"])
    for candidate in candidates:
        path = resolve_executable(candidate)
        if path:
            return path
    raise SystemExit("Cursor Agent CLI not found. Pass --agent-bin or set CURSOR_AGENT_PATH.")


def run_git_status(workspace: Path) -> tuple[bool, list[str], str]:
    result = subprocess.run(
        ["git", "-C", str(workspace), "status", "--porcelain=v1"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return False, [], result.stderr.strip()
    return True, [line for line in result.stdout.splitlines() if line.strip()], ""


def status_path(line: str) -> str:
    path = line[3:].strip() if len(line) > 3 else ""
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path


def relative_to_workspace(path: Path, workspace: Path) -> str | None:
    try:
        return str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        return None


def filter_ignorable_status(lines: Iterable[str], workspace: Path, task_file: Path) -> list[str]:
    task_rel = relative_to_workspace(task_file, workspace)
    kept: list[str] = []
    for line in lines:
        path = status_path(line)
        if line.startswith("??") and task_rel and path == task_rel:
            continue
        if line.startswith("??") and path.startswith(".agent/delegations/"):
            continue
        kept.append(line)
    return kept


def redact_text(value: object, limit: int = STATUS_TEXT_LIMIT) -> str | None:
    if value is None:
        return None
    text = str(value)
    text = SENSITIVE_ASSIGNMENT_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}<redacted>", text)
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def redact_url(value: str) -> str:
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return redact_text(value, 240) or ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def primitive_summary(data: dict[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in keys:
        if key not in data or SENSITIVE_KEY_RE.search(key):
            continue
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            summary[key] = redact_url(value) if key == "url" else redact_text(value, 240)
        elif isinstance(value, (int, float, bool)):
            summary[key] = value
    return summary


def summarize_command(data: dict[str, Any]) -> dict[str, Any]:
    command = data.get("command") if "command" in data else data.get("cmd")
    if not isinstance(command, str) or not command.strip():
        return {}
    try:
        command_kind = shlex.split(command)[0]
    except ValueError:
        command_kind = command.split()[0]
    return {"command_present": True, "command_kind": redact_text(command_kind, 80)}


def safe_tool_args(tool_name: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    args = payload.get("args") if isinstance(payload, dict) else None
    if not isinstance(args, dict):
        return {}
    if tool_name == "taskToolCall":
        summary = primitive_summary(
            args,
            ("description", "model", "agentId", "mode", "environment", "readonly", "run_in_background"),
        )
        attachments = args.get("attachments") or args.get("file_attachments")
        if isinstance(attachments, list):
            summary["attachments_count"] = len(attachments)
        return summary
    summary = primitive_summary(args, ("path", "cwd", "pattern", "query", "url", "name"))
    summary.update(summarize_command(args))
    return summary


def safe_tool_result(tool_name: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        return {}
    if isinstance(result.get("success"), dict):
        success = result["success"]
        keys = ("agentId", "isBackground", "durationMs") if tool_name == "taskToolCall" else (
            "path",
            "linesCreated",
            "linesModified",
            "fileSize",
            "totalLines",
            "totalChars",
            "isEmpty",
            "exceededLimit",
        )
        return {"status": "success", **primitive_summary(success, keys)}
    if isinstance(result.get("error"), dict):
        return {"status": "error", **primitive_summary(result["error"], ("message", "code"))}
    return primitive_summary(result, ("status", "message", "path", "agentId"))


def tool_event_parts(event: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    tool_call = event.get("tool_call")
    if isinstance(tool_call, dict):
        for tool_name, payload in tool_call.items():
            if isinstance(payload, dict):
                return tool_name, payload
    return None, {}


def assistant_text(event: dict[str, Any]) -> str | None:
    message = event.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, list):
        return None
    parts = [block.get("text") for block in content if isinstance(block, dict) and isinstance(block.get("text"), str)]
    return "".join(parts) if parts else None


def append_recent(status: dict[str, Any], key: str, entry: dict[str, Any], limit: int) -> None:
    recent = status.setdefault(key, [])
    if not isinstance(recent, list):
        recent = []
        status[key] = recent
    recent.append(entry)
    del recent[:-limit]


def update_status_from_event(status: dict[str, Any], event: dict[str, Any]) -> None:
    event_type = event.get("type")
    subtype = event.get("subtype")
    status["updated_at_utc"] = utc_now()
    status["events_seen"] = int(status.get("events_seen", 0)) + 1
    status["last_event_type"] = redact_text(event_type, 80)
    if subtype:
        status["last_event_subtype"] = redact_text(subtype, 80)

    if event_type == "system":
        status["state"] = "running"
        for key in ("model", "permissionMode", "cwd"):
            if isinstance(event.get(key), str):
                status[key] = redact_text(event[key], 240)
        return

    if event_type == "assistant":
        text = assistant_text(event)
        if text:
            status["last_assistant_text"] = redact_text(text)
        return

    if event_type == "tool_call":
        tool_name, payload = tool_event_parts(event)
        entry = {
            "at_utc": status["updated_at_utc"],
            "call_id": redact_text(event.get("call_id"), 120),
            "subtype": redact_text(subtype, 80),
            "tool": redact_text(tool_name, 120),
            "args": safe_tool_args(tool_name, payload),
        }
        if subtype == "started":
            status["current_tool_call"] = entry
            if tool_name == "taskToolCall":
                status.setdefault("active_subagents", {})[str(event.get("call_id"))] = entry
        elif subtype == "completed":
            entry["result"] = safe_tool_result(tool_name, payload)
            current = status.get("current_tool_call")
            if isinstance(current, dict) and current.get("call_id") == entry.get("call_id"):
                status["current_tool_call"] = None
            if tool_name == "taskToolCall":
                status.setdefault("active_subagents", {}).pop(str(event.get("call_id")), None)
                append_recent(status, "recent_subagents", entry, RECENT_SUBAGENT_LIMIT)
        append_recent(status, "recent_tool_calls", entry, RECENT_TOOL_LIMIT)
        return

    if event_type == "result":
        is_error = bool(event.get("is_error")) or subtype not in (None, "success")
        status["state"] = "failed" if is_error else "succeeded"
        status["current_tool_call"] = None
        status["result"] = {
            "subtype": redact_text(subtype, 80),
            "is_error": bool(event.get("is_error")),
            "duration_ms": event.get("duration_ms"),
            "duration_api_ms": event.get("duration_api_ms"),
            "request_id": redact_text(event.get("request_id"), 160),
            "text": redact_text(event.get("result")),
        }


def write_json(path: Path, data: dict[str, Any]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(path)


def stream_pipe(
    pipe: Any,
    sink_path: Path | None,
    prefix: str,
    events_path: Path | None,
    status_file: Path | None,
    status: dict[str, Any] | None,
    status_lock: threading.Lock | None,
) -> None:
    with contextlib.ExitStack() as stack:
        sink = stack.enter_context(sink_path.open("w", encoding="utf-8")) if sink_path else None
        event_sink = stack.enter_context(events_path.open("w", encoding="utf-8")) if events_path else None
        for line in iter(pipe.readline, ""):
            if sink is not None:
                sink.write(line)
                sink.flush()
            raw = line.strip()
            if raw.startswith("{"):
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    event = None
                if isinstance(event, dict):
                    if event_sink is not None:
                        event_sink.write(raw + "\n")
                        event_sink.flush()
                    if status is not None and status_file is not None and status_lock is not None:
                        with status_lock:
                            update_status_from_event(status, event)
                            write_json(status_file, status)
            print(f"{prefix}{line}", end="") if prefix else print(line, end="")


def make_log_dir(base: Path) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    try:
        base.chmod(0o700)
    except OSError:
        pass
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = base / f"{stamp}-{uuid.uuid4().hex[:8]}"
    path.mkdir(mode=0o700, parents=False, exist_ok=False)
    return path


def copy_ignore(_: str, names: list[str]) -> set[str]:
    ignored = {
        ".git",
        ".agent",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".next",
        "dist",
        "build",
    }
    return {name for name in names if name in ignored}


def readonly_mode(path: Path) -> int:
    mode = stat.S_IMODE(path.stat().st_mode)
    return mode & ~0o222


def make_readonly_copy(workspace: Path) -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="cursor-delegate-readonly-"))
    target = temp_root / workspace.name
    shutil.copytree(workspace, target, symlinks=True, ignore=copy_ignore)
    remap_symlinks_to_copy(workspace, target)
    for item in target.rglob("*"):
        if item.is_symlink():
            continue
        try:
            item.chmod(readonly_mode(item))
        except OSError:
            pass
    try:
        target.chmod(readonly_mode(target))
    except OSError:
        pass
    return target


def path_relative_to(path: Path, root: Path) -> Path | None:
    try:
        return path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return None


def replace_symlink_with_placeholder(path: Path, raw_target: str) -> None:
    path.unlink()
    path.write_text(
        f"Symlink omitted from read-only workspace copy: {raw_target}\n",
        encoding="utf-8",
    )


def remap_symlinks_to_copy(workspace: Path, target: Path) -> None:
    for item in target.rglob("*"):
        if not item.is_symlink():
            continue
        raw_target = os.readlink(item)
        try:
            resolved = item.resolve(strict=True)
        except OSError:
            replace_symlink_with_placeholder(item, raw_target)
            continue

        if path_relative_to(resolved, target) is not None:
            continue

        original_rel = path_relative_to(resolved, workspace)
        if original_rel is None:
            replace_symlink_with_placeholder(item, raw_target)
            continue

        copied_target = target / original_rel
        if not copied_target.exists() and not copied_target.is_symlink():
            replace_symlink_with_placeholder(item, raw_target)
            continue

        item.unlink()
        relative_target = os.path.relpath(copied_target, item.parent)
        item.symlink_to(relative_target, target_is_directory=copied_target.is_dir())


def collect_unsafe_overrides(args: argparse.Namespace) -> list[str]:
    flags: list[str] = []
    if args.allow_missing_authority:
        flags.append("--allow-missing-authority")
    if args.allow_placeholders:
        flags.append("--allow-placeholders")
    if args.allow_dirty:
        flags.append("--allow-dirty")
    if args.allow_non_git:
        flags.append("--allow-non-git")
    if args.trust:
        flags.append("--trust")
    if args.sandbox == "disabled":
        flags.append("--sandbox disabled")
    if args.workspace_copy == "never" and not args.apply:
        flags.append("--workspace-copy never")
    if getattr(args, "include_raw_logs", False):
        flags.append("--include-raw-logs")
    if getattr(args, "include_raw_events", False):
        flags.append("--include-raw-events")
    if args.user_authorized_model and (
        args.model != DEFAULT_CURSOR_MODEL
        or (args.internal_subagent_model and args.internal_subagent_model != args.model)
    ):
        flags.append("--user-authorized-model")
    return flags


def build_prompt(
    task_file: Path,
    args: argparse.Namespace,
    detected_source: str,
    active_workspace: Path,
    original_workspace: Path,
) -> str:
    mode = "apply" if args.apply else "proposal"
    if args.inspect_only:
        mode = "inspect-only"
    internal_subagent_model = args.internal_subagent_model or args.model

    lines = [
        f"You are Cursor Composer running model `{args.model}` as the downstream implementation executor for an upstream delegation/review agent.",
        describe_authority(detected_source),
        f"Delegation mode: {mode}.",
        f"Read and follow this bounded task packet exactly: {task_file.resolve()}",
        f"Active workspace: {active_workspace}",
        "Do not switch or infer a different Cursor model; only an explicit user instruction to Cursor may authorize a model override.",
        f"If the task packet allows Cursor internal subagents / Task() calls, request model `{internal_subagent_model}` for every internal subagent unless the packet quotes an explicit user Cursor-model override.",
        "Do not launch Cursor internal subagents unless the task packet includes a Cursor Internal Subagent Policy that permits them.",
        "Do not create a competing architecture plan. Do not broaden scope.",
        "Do not commit, push, deploy, rotate credentials, alter billing, run destructive commands, or modify unrelated files.",
        "Leave changes unstaged for upstream review when apply mode is used.",
        "If the task requires a new dependency, breaking API change, migration, credential access, external service change, destructive command, or scope expansion not listed in the packet, stop and report instead of improvising.",
    ]
    if active_workspace != original_workspace:
        lines.append("This run uses a read-only workspace copy. Do not claim edits were applied to the original workspace. Report proposed edits and blockers only.")
    if args.inspect_only:
        lines.append("Inspect feasibility and blockers only. Do not edit files. Report repository-reality conflicts, missing context, and exact questions for the upstream reviewer.")
    elif args.apply:
        lines.append("Implement the task with the smallest coherent diff that satisfies the authority section and acceptance criteria.")
    else:
        lines.append("Analyze implementation feasibility and report proposed edits. Do not rely on direct file modification unless the runtime explicitly permits it.")
    lines.append("End with a completion report containing: Summary, Files Touched, Verification, Internal Subagents, Deviations, Risks/Follow-ups, and Notes for Upstream Reviewer.")
    if args.delegation_owner:
        lines.append(f"Upstream delegation owner: {args.delegation_owner}.")
    if args.workstream_id:
        lines.append(f"Workstream ID: {args.workstream_id}.")
    if args.extra_instruction:
        lines.append("Additional upstream instructions:")
        lines.extend(f"- {item}" for item in args.extra_instruction)
    return "\n".join(lines)


def parser_instance() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dispatch a bounded task packet to Cursor Agent/Composer 2.5 Fast under the bounded Cursor delegation model."
    )
    parser.add_argument("--workspace", default=".", help="Workspace/repo directory for Cursor Agent.")
    parser.add_argument("--task-file", required=True, help="Markdown task packet path.")
    parser.add_argument("--agent-bin", default=None, help="Cursor Agent executable path or name. Overrides PATH discovery.")
    parser.add_argument("--planning-source", choices=PLANNING_SOURCE_CHOICES, default="auto", help="Authority source expected in the task packet. Default: auto-detect exactly one supported authority heading.")
    parser.add_argument("--model", default=DEFAULT_CURSOR_MODEL, help="Cursor model. Default: composer-2.5-fast.")
    parser.add_argument("--internal-subagent-model", default=None, help="Cursor internal Task()/taskToolCall model. Default: same as --model.")
    parser.add_argument("--user-authorized-model", action="store_true", help="Confirm an explicit user instruction authorized a non-default Cursor model.")
    parser.add_argument("--apply", action="store_true", help="Enable direct file modifications via Cursor `--force`.")
    parser.add_argument("--inspect-only", action="store_true", help="Ask Cursor to inspect/report blockers without editing. Mutually exclusive with --apply.")
    parser.add_argument("--allow-missing-authority", action="store_true", help="Allow dispatch despite authority validation failure.")
    parser.add_argument("--allow-placeholders", action="store_true", help="Allow unresolved angle-bracket placeholder tokens in the task packet.")
    parser.add_argument("--override-reason", default=None, help="Reason for any unsafe override or user-authorized model override.")
    parser.add_argument("--output-format", choices=("text", "json", "stream-json"), default="stream-json", help="Cursor print-mode output format.")
    parser.add_argument("--stream-partial-output", action="store_true", help="Stream text deltas; only valid with stream-json output.")
    parser.add_argument("--include-raw-logs", action="store_true", help="Write raw stdout.log, stderr.log, and events.ndjson. Raw logs may contain sensitive context.")
    parser.add_argument("--include-raw-events", action="store_true", help="Write raw JSON stream events to events.ndjson without stdout/stderr logs. Raw events may contain sensitive context.")
    parser.add_argument("--trust", action="store_true", help="Trust workspace in headless mode.")
    parser.add_argument("--sandbox", choices=("enabled", "disabled"), default=None, help="Set Cursor sandbox mode.")
    parser.add_argument("--worktree", nargs="?", const="", default=None, help="Run in a new Cursor worktree. Optionally provide a worktree name.")
    parser.add_argument("--worktree-base", default=None, help="Branch/ref to base the worktree on.")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow apply mode even if git status is dirty.")
    parser.add_argument("--allow-non-git", action="store_true", help="Allow apply mode outside a git repository.")
    parser.add_argument("--workspace-copy", choices=("auto", "always", "never"), default="auto", help="Use a read-only temporary copy. auto uses a copy for inspect-only and proposal runs; apply uses the original workspace.")
    parser.add_argument("--delegation-owner", default=None, help="Optional upstream owner for logs.")
    parser.add_argument("--workstream-id", default=None, help="Optional hierarchical workstream id for logs and prompts.")
    parser.add_argument("--log-dir", default=None, help="Directory for run logs. Default: <workspace>/.agent/delegations.")
    parser.add_argument("--extra-instruction", action="append", help="Additional instruction appended to the Cursor prompt. Repeatable.")
    parser.add_argument("--prompt-transport", choices=("argv", "stdin"), default="argv", help="How to pass the prompt to Cursor. Default: argv.")
    parser.add_argument("--allow-long-argv", action="store_true", help="Allow prompt argv longer than the wrapper safety threshold.")
    parser.add_argument("--dry-run", action="store_true", help="Print command and prompt, then exit.")
    return parser


def main() -> int:
    parser = parser_instance()
    args = parser.parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    task_file = Path(args.task_file).expanduser().resolve()

    if args.apply and args.inspect_only:
        print("--apply and --inspect-only are mutually exclusive", file=sys.stderr)
        return 2
    if args.stream_partial_output and args.output_format != "stream-json":
        print("--stream-partial-output requires --output-format stream-json", file=sys.stderr)
        return 2
    if args.apply and args.workspace_copy == "always":
        print("--workspace-copy always is not compatible with --apply", file=sys.stderr)
        return 2
    if args.model != DEFAULT_CURSOR_MODEL and not args.user_authorized_model:
        print(f"Refusing Cursor model override {args.model!r}. Default to {DEFAULT_CURSOR_MODEL!r} unless the user explicitly directed Cursor to use a different model.", file=sys.stderr)
        return 2
    if args.internal_subagent_model and args.internal_subagent_model != args.model and not args.user_authorized_model:
        print(f"Refusing internal subagent model override {args.internal_subagent_model!r}. Default internal subagents to {args.model!r} unless the user explicitly directed Cursor internal subagents to use a different model.", file=sys.stderr)
        return 2
    if not workspace.exists() or not workspace.is_dir():
        print(f"Workspace does not exist or is not a directory: {workspace}", file=sys.stderr)
        return 2
    if not task_file.exists() or not task_file.is_file():
        print(f"Task file does not exist: {task_file}", file=sys.stderr)
        return 2

    unsafe_overrides = collect_unsafe_overrides(args)
    if unsafe_overrides and not args.override_reason:
        print("Unsafe override flags require --override-reason: " + ", ".join(unsafe_overrides), file=sys.stderr)
        return 2

    task_text = task_file.read_text(encoding="utf-8")
    ok, detected_source, authority_message = validate_authority(task_text, args.planning_source, args.allow_placeholders)
    if not ok:
        missing_only = "found ['none']" in authority_message
        if not (args.allow_missing_authority and missing_only):
            print(f"Refusing dispatch: {authority_message}", file=sys.stderr)
            return 2
        detected_source = args.planning_source if args.planning_source != "auto" else "master-direct"
    assert detected_source is not None

    is_git, status_lines, git_error = run_git_status(workspace)
    if args.apply:
        if not is_git and not args.allow_non_git:
            print("Apply mode requires a git workspace for review/revert safety.", file=sys.stderr)
            if git_error:
                print(f"git status error: {git_error}", file=sys.stderr)
            return 2
        if is_git and not args.allow_dirty:
            dirty = filter_ignorable_status(status_lines, workspace, task_file)
            if dirty:
                print("Refusing apply mode because the workspace has existing git changes.", file=sys.stderr)
                print("\n".join(dirty), file=sys.stderr)
                return 2

    if args.dry_run:
        agent_bin = find_cursor_agent(args.agent_bin) if args.agent_bin else (shutil.which("cursor-agent") or shutil.which("agent") or "cursor-agent")
    else:
        agent_bin = find_cursor_agent(args.agent_bin)

    use_copy = args.workspace_copy == "always" or (args.workspace_copy == "auto" and not args.apply)
    active_workspace = workspace
    if use_copy and not args.dry_run:
        active_workspace = make_readonly_copy(workspace)

    prompt = build_prompt(task_file, args, detected_source, active_workspace, workspace)
    if args.prompt_transport == "argv" and len(prompt) > PROMPT_ARG_LIMIT and not args.allow_long_argv:
        print(f"Prompt is {len(prompt)} characters; use --prompt-transport stdin or pass --allow-long-argv intentionally.", file=sys.stderr)
        return 2

    cmd = [agent_bin, "-p", "--model", args.model, "--output-format", args.output_format, "--workspace", str(active_workspace)]
    if args.stream_partial_output:
        cmd.append("--stream-partial-output")
    if args.trust:
        cmd.append("--trust")
    if args.sandbox:
        cmd.extend(["--sandbox", args.sandbox])
    if args.worktree is not None:
        cmd.append("--worktree")
        if args.worktree:
            cmd.append(args.worktree)
    if args.worktree_base:
        cmd.extend(["--worktree-base", args.worktree_base])
    if args.apply:
        cmd.append("--force")
    if args.prompt_transport == "argv":
        cmd.append(prompt)

    log_base = Path(args.log_dir).expanduser().resolve() if args.log_dir else workspace / ".agent" / "delegations"
    if args.dry_run:
        rendered = " ".join(shlex.quote(part) for part in cmd[:-1]) + " <prompt>" if args.prompt_transport == "argv" else " ".join(shlex.quote(part) for part in cmd) + " < prompt"
        print("Command:")
        print(rendered)
        print("\nPrompt:")
        print(prompt)
        print(f"\nDetected authority source: {detected_source}")
        print(f"Authority validation: {authority_message}")
        print(f"Workspace copy: {'yes' if use_copy else 'no'}")
        if use_copy:
            print("Dry-run note: no temporary workspace copy is created during dry-run; real non-dry-run execution will create a read-only copy before assembling the Cursor command.")
        print(f"Logs would be written under: {log_base}")
        print("Each run writes status.json, prompt.txt, metadata.json, and a latest pointer. Raw stdout/stderr/events are written only with --include-raw-logs; events-only logging uses --include-raw-events.")
        return 0

    run_dir = make_log_dir(log_base)
    stdout_log = run_dir / "stdout.log" if args.include_raw_logs else None
    stderr_log = run_dir / "stderr.log" if args.include_raw_logs else None
    events_log = run_dir / "events.ndjson" if (args.include_raw_logs or args.include_raw_events) else None
    status_file = run_dir / "status.json"
    latest_file = log_base / "latest"
    metadata_file = run_dir / "metadata.json"
    started_at = utc_now()
    unsafe_metadata = [{"flag": flag, "reason": args.override_reason} for flag in unsafe_overrides]

    metadata = {
        "workspace": str(workspace),
        "active_workspace": str(active_workspace),
        "workspace_copy_used": active_workspace != workspace,
        "task_file": str(task_file),
        "planning_source_arg": args.planning_source,
        "detected_authority_source": detected_source,
        "authority_validation": authority_message,
        "model": args.model,
        "internal_subagent_model": args.internal_subagent_model or args.model,
        "user_authorized_model_override": args.user_authorized_model,
        "mode": "inspect-only" if args.inspect_only else ("apply" if args.apply else "proposal"),
        "delegation_owner": args.delegation_owner,
        "workstream_id": args.workstream_id,
        "output_format": args.output_format,
        "prompt_transport": args.prompt_transport,
        "raw_logs_enabled": args.include_raw_logs,
        "raw_events_enabled": bool(args.include_raw_logs or args.include_raw_events),
        "unsafe_overrides": unsafe_metadata,
        "command_without_prompt": cmd[:-1] if args.prompt_transport == "argv" else cmd,
        "stdout_log": str(stdout_log) if stdout_log else None,
        "stderr_log": str(stderr_log) if stderr_log else None,
        "events_log": str(events_log) if events_log else None,
        "status_file": str(status_file),
        "started_at_utc": started_at,
    }
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    write_json(metadata_file, metadata)
    latest_file.write_text(str(run_dir) + "\n", encoding="utf-8")

    status: dict[str, Any] = {
        "state": "starting",
        "workspace": str(workspace),
        "active_workspace": str(active_workspace),
        "workspace_copy_used": active_workspace != workspace,
        "task_file": str(task_file),
        "run_dir": str(run_dir),
        "stdout_log": str(stdout_log) if stdout_log else None,
        "stderr_log": str(stderr_log) if stderr_log else None,
        "events_log": str(events_log) if events_log else None,
        "metadata_file": str(metadata_file),
        "mode": metadata["mode"],
        "model": args.model,
        "internal_subagent_model": args.internal_subagent_model or args.model,
        "output_format": args.output_format,
        "raw_logs_enabled": args.include_raw_logs,
        "raw_events_enabled": bool(args.include_raw_logs or args.include_raw_events),
        "started_at_utc": started_at,
        "updated_at_utc": started_at,
        "events_seen": 0,
        "current_tool_call": None,
        "recent_tool_calls": [],
        "active_subagents": {},
        "recent_subagents": [],
    }
    status_lock = threading.Lock()
    write_json(status_file, status)

    print(f"Running Cursor Agent. Logs: {run_dir}")
    print(f"Live status: {status_file}")
    process = subprocess.Popen(
        cmd,
        cwd=str(active_workspace),
        text=True,
        stdin=subprocess.PIPE if args.prompt_transport == "stdin" else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    if args.prompt_transport == "stdin":
        assert process.stdin is not None
        process.stdin.write(prompt)
        process.stdin.close()

    stdout_thread = threading.Thread(target=stream_pipe, args=(process.stdout, stdout_log, "", events_log, status_file, status, status_lock), daemon=True)
    stderr_thread = threading.Thread(target=stream_pipe, args=(process.stderr, stderr_log, "[stderr] ", None, None, None, None), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    return_code = process.wait()
    stdout_thread.join(timeout=2)
    stderr_thread.join(timeout=2)

    finished_at = utc_now()
    metadata["finished_at_utc"] = finished_at
    metadata["return_code"] = return_code
    write_json(metadata_file, metadata)
    with status_lock:
        if status.get("state") not in ("succeeded", "failed"):
            status["state"] = "succeeded" if return_code == 0 else "failed"
        status["return_code"] = return_code
        status["finished_at_utc"] = finished_at
        status["updated_at_utc"] = finished_at
        write_json(status_file, status)

    if return_code != 0:
        print(f"Cursor Agent exited with code {return_code}. See logs: {run_dir}", file=sys.stderr)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
