#!/usr/bin/env python3
"""Dispatch a bounded task packet to Cursor Agent/Composer in headless mode.

This wrapper enforces the delegation contract:
- master-direct: the upstream agent determined subagent planning is unnecessary;
- non-cursor-planning-subagent: a planner produced a plan reviewed upstream;
- orchestrator-subagent: a bounded workstream orchestrator produced a reviewed local plan;
- user-provided-plan: the user supplied a plan accepted by the upstream agent.

Cursor remains the implementation executor. Final review stays upstream.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import threading
from typing import Any, Iterable
import uuid


AUTHORITY_MARKERS: dict[str, tuple[str, ...]] = {
    "master-direct": (
        "## Master Direct Implementation Instructions",
        "# Master Direct Implementation Instructions",
        "Master Direct Implementation Instructions",
    ),
    "non-cursor-planning-subagent": (
        "## Approved Upstream Plan",
        "# Approved Upstream Plan",
        "Approved Upstream Plan",
    ),
    "orchestrator-subagent": (
        "## Approved Local Plan",
        "# Approved Local Plan",
        "Approved Local Plan",
    ),
    "user-provided-plan": (
        "## User-Provided Approved Plan",
        "# User-Provided Approved Plan",
        "User-Provided Approved Plan",
    ),
}

PLANNING_SOURCE_CHOICES = tuple(["auto", *AUTHORITY_MARKERS.keys()])
DEFAULT_CURSOR_MODEL = "composer-2.5-fast"
STATUS_TEXT_LIMIT = 800
RECENT_TOOL_LIMIT = 12
RECENT_SUBAGENT_LIMIT = 12


def find_cursor_agent() -> str:
    for candidate in ("agent", "cursor-agent"):
        path = shutil.which(candidate)
        if path:
            return path
    raise SystemExit(
        "Cursor Agent CLI not found. Install Cursor CLI and ensure `agent` or `cursor-agent` is on PATH."
    )


def run_git_status(workspace: Path) -> tuple[bool, list[str], str]:
    result = subprocess.run(
        ["git", "-C", str(workspace), "status", "--porcelain=v1"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        return False, [], result.stderr.strip()
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return True, lines, ""


def status_path(line: str) -> str:
    # Porcelain v1: XY<space>path, with rename as "old -> new".
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
        p = status_path(line)
        is_untracked = line.startswith("??")
        if is_untracked and task_rel and p == task_rel:
            continue
        if is_untracked and p.startswith(".agent/delegations/"):
            continue
        kept.append(line)
    return kept


def markers_present(task_text: str) -> dict[str, bool]:
    return {
        source: any(marker in task_text for marker in markers)
        for source, markers in AUTHORITY_MARKERS.items()
    }


def detect_planning_source(task_text: str) -> str | None:
    present = [source for source, found in markers_present(task_text).items() if found]
    if len(present) == 1:
        return present[0]
    if len(present) > 1:
        # Prefer the most specific downstream source when several template headings remain.
        for source in (
            "orchestrator-subagent",
            "non-cursor-planning-subagent",
            "master-direct",
            "user-provided-plan",
        ):
            if source in present:
                return source
    return None


def has_required_authority(task_text: str, planning_source: str) -> bool:
    if planning_source == "auto":
        return detect_planning_source(task_text) is not None
    return any(marker in task_text for marker in AUTHORITY_MARKERS[planning_source])


def describe_authority(planning_source: str) -> str:
    if planning_source == "master-direct":
        return (
            "The upstream agent determined this task is small and clear enough for direct Cursor execution. "
            "The Master Direct Implementation Instructions section is the source of truth."
        )
    if planning_source == "non-cursor-planning-subagent":
        return (
            "The implementation plan was produced outside Cursor by a non-Cursor planning subagent and reviewed upstream. "
            "The Approved Upstream Plan section is the source of truth."
        )
    if planning_source == "orchestrator-subagent":
        return (
            "This task comes from a bounded workstream orchestrator subagent operating under an upstream workstream contract. "
            "The Approved Local Plan section is the source of truth and is subordinate to the upstream workstream contract."
        )
    if planning_source == "user-provided-plan":
        return (
            "The user supplied a plan that the upstream agent accepted. "
            "The User-Provided Approved Plan section is the source of truth."
        )
    return "The task packet contains an upstream authority section. Follow it exactly."


def build_prompt(task_file: Path, task_text: str, args: argparse.Namespace) -> tuple[str, str | None]:
    detected_source = detect_planning_source(task_text)
    planning_source = detected_source if args.planning_source == "auto" else args.planning_source
    mode = "apply" if args.apply else "proposal"
    if args.inspect_only:
        mode = "inspect-only"
    internal_subagent_model = args.internal_subagent_model or args.model

    lines = [
        f"You are Cursor Composer running model `{args.model}` as the downstream implementation executor for an upstream delegation/review agent.",
        describe_authority(planning_source or "auto"),
        f"Delegation mode: {mode}.",
        f"Read and follow this bounded task packet exactly: {task_file.resolve()}",
        "Do not switch or infer a different Cursor model; only an explicit user instruction to Cursor may authorize a model override.",
        f"If the task packet allows Cursor internal subagents / Task() calls, request model `{internal_subagent_model}` for every internal subagent unless the packet quotes an explicit user Cursor-model override.",
        "Do not launch Cursor internal subagents unless the task packet includes a Cursor Internal Subagent Policy that permits them.",
        "Do not create a competing architecture plan. Do not broaden scope.",
        "Do not commit, push, deploy, rotate credentials, alter billing, run destructive commands, or modify unrelated files.",
        "Leave changes unstaged for upstream review.",
        "If the task requires a new dependency, breaking API change, migration, credential access, external service change, destructive command, or scope expansion not listed in the packet, stop and report instead of improvising.",
    ]
    if args.inspect_only:
        lines.append(
            "Inspect feasibility and blockers only. Do not edit files. Report repository-reality conflicts, missing context, and exact questions for the upstream reviewer."
        )
    elif args.apply:
        lines.append(
            "Implement the task with the smallest coherent diff that satisfies the authority section and acceptance criteria."
        )
    else:
        lines.append(
            "Analyze implementation feasibility and report proposed edits. Do not assume direct file modifications will be applied unless the runtime explicitly permits them."
        )
    lines.append(
        "End with a final report containing: Summary, Files Changed, Verification, Internal Subagents, Deviations, Risks/Follow-ups, and Notes for Upstream Reviewer."
    )
    if args.delegation_owner:
        lines.append(f"Upstream delegation owner: {args.delegation_owner}.")
    if args.workstream_id:
        lines.append(f"Workstream ID: {args.workstream_id}.")
    if args.extra_instruction:
        lines.append("Additional upstream instructions:")
        lines.extend(f"- {item}" for item in args.extra_instruction)
    if not has_required_authority(task_text, args.planning_source):
        lines.append(
            "Warning: the task packet did not contain the expected authority marker. Proceed only with explicit upstream authorization."
        )
    return "\n".join(lines), detected_source


def make_log_dir(base: Path) -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    stamp = f"{stamp}-{uuid.uuid4().hex[:8]}"
    path = base / stamp
    path.mkdir(parents=True, exist_ok=False)
    return path


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def truncate_text(value: object, limit: int = STATUS_TEXT_LIMIT) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "..."


def selected_primitive_fields(data: dict[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in keys:
        value = data.get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            summary[key] = truncate_text(value, 240) if isinstance(value, str) else value
    return summary


def tool_event_parts(event: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    tool_call = event.get("tool_call")
    if not isinstance(tool_call, dict):
        return None, {}
    for tool_name, payload in tool_call.items():
        if isinstance(payload, dict):
            return tool_name, payload
    return None, {}


def safe_tool_args(tool_name: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "taskToolCall":
        return safe_task_args(payload)
    args = payload.get("args")
    if not isinstance(args, dict):
        return {}
    common_keys = ("path", "cwd", "command", "cmd", "pattern", "query", "url", "name")
    summary = selected_primitive_fields(args, common_keys)
    if tool_name == "writeToolCall":
        summary.pop("fileText", None)
    return summary


def subagent_type_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and value:
        return ",".join(str(key) for key in sorted(value.keys()))
    return None


def safe_task_args(payload: dict[str, Any]) -> dict[str, Any]:
    args = payload.get("args")
    if not isinstance(args, dict):
        return {}
    summary = selected_primitive_fields(
        args,
        (
            "description",
            "model",
            "agentId",
            "mode",
            "environment",
            "readonly",
            "run_in_background",
            "resume",
            "interrupt",
        ),
    )
    subagent_type = subagent_type_name(args.get("subagentType") or args.get("subagent_type"))
    if subagent_type:
        summary["subagent_type"] = subagent_type
    attachments = args.get("attachments") or args.get("file_attachments")
    if isinstance(attachments, list):
        summary["attachments_count"] = len(attachments)
    responding = args.get("respondingToMessageIds")
    if isinstance(responding, list):
        summary["responding_to_message_count"] = len(responding)
    return summary


def safe_task_result(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result")
    if not isinstance(result, dict):
        return {}
    if isinstance(result.get("success"), dict):
        success = result["success"]
        summary = {
            "status": "success",
            **selected_primitive_fields(
                success,
                ("agentId", "isBackground", "durationMs", "backgroundReason"),
            ),
        }
        steps = success.get("conversationSteps")
        if isinstance(steps, list):
            summary["conversation_steps"] = len(steps)
        return summary
    if isinstance(result.get("error"), dict):
        return {"status": "error", **selected_primitive_fields(result["error"], ("message", "code"))}
    return selected_primitive_fields(result, ("status", "message", "agentId"))


def safe_tool_result(payload: dict[str, Any], tool_name: str | None = None) -> dict[str, Any]:
    if tool_name == "taskToolCall":
        return safe_task_result(payload)
    result = payload.get("result")
    if not isinstance(result, dict):
        return {}
    if isinstance(result.get("success"), dict):
        success = result["success"]
        return {
            "status": "success",
            **selected_primitive_fields(
                success,
                (
                    "path",
                    "linesCreated",
                    "linesModified",
                    "fileSize",
                    "totalLines",
                    "totalChars",
                    "isEmpty",
                    "exceededLimit",
                ),
            ),
        }
    if isinstance(result.get("error"), dict):
        return {"status": "error", **selected_primitive_fields(result["error"], ("message", "code"))}
    return selected_primitive_fields(result, ("status", "message", "path"))


def append_recent_tool(status: dict[str, Any], entry: dict[str, Any]) -> None:
    recent = status.setdefault("recent_tool_calls", [])
    if not isinstance(recent, list):
        recent = []
        status["recent_tool_calls"] = recent
    recent.append(entry)
    del recent[:-RECENT_TOOL_LIMIT]


def append_recent_subagent(status: dict[str, Any], entry: dict[str, Any]) -> None:
    recent = status.setdefault("recent_subagents", [])
    if not isinstance(recent, list):
        recent = []
        status["recent_subagents"] = recent
    recent.append(entry)
    del recent[:-RECENT_SUBAGENT_LIMIT]


def assistant_text(event: dict[str, Any]) -> str | None:
    message = event.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, list):
        return None
    parts = [
        block.get("text")
        for block in content
        if isinstance(block, dict) and isinstance(block.get("text"), str)
    ]
    return "".join(parts) if parts else None


def update_status_from_event(status: dict[str, Any], event: dict[str, Any]) -> None:
    event_type = event.get("type")
    subtype = event.get("subtype")
    status["updated_at_utc"] = utc_now()
    status["events_seen"] = int(status.get("events_seen", 0)) + 1
    status["last_event_type"] = event_type
    if subtype:
        status["last_event_subtype"] = subtype
    session_id = event.get("session_id")
    if isinstance(session_id, str):
        status["session_id"] = session_id

    if event_type == "system":
        status["state"] = "running"
        for key in ("model", "permissionMode", "cwd", "apiKeySource"):
            if isinstance(event.get(key), str):
                status[key] = event[key]
        return

    if event_type == "assistant":
        text = assistant_text(event)
        if text:
            status["last_assistant_text"] = truncate_text(text)
        return

    if event_type == "tool_call":
        tool_name, payload = tool_event_parts(event)
        entry = {
            "at_utc": status["updated_at_utc"],
            "call_id": event.get("call_id"),
            "subtype": subtype,
            "tool": tool_name,
            "args": safe_tool_args(tool_name, payload),
        }
        if tool_name == "taskToolCall":
            entry["kind"] = "cursor_internal_subagent"
            active = status.setdefault("active_subagents", {})
            if not isinstance(active, dict):
                active = {}
                status["active_subagents"] = active
            if subtype == "started":
                active[str(event.get("call_id"))] = entry
            elif subtype == "completed":
                entry["result"] = safe_tool_result(payload, tool_name)
                active.pop(str(event.get("call_id")), None)
                append_recent_subagent(status, entry)
        if subtype == "completed":
            entry["result"] = safe_tool_result(payload, tool_name)
            current = status.get("current_tool_call")
            if isinstance(current, dict) and current.get("call_id") == event.get("call_id"):
                status["current_tool_call"] = None
        elif subtype == "started":
            status["current_tool_call"] = entry
        append_recent_tool(status, entry)
        return

    if event_type == "result":
        is_error = bool(event.get("is_error")) or subtype not in (None, "success")
        status["state"] = "failed" if is_error else "succeeded"
        status["current_tool_call"] = None
        status["result"] = {
            "subtype": subtype,
            "is_error": bool(event.get("is_error")),
            "duration_ms": event.get("duration_ms"),
            "duration_api_ms": event.get("duration_api_ms"),
            "request_id": event.get("request_id"),
            "text": truncate_text(event.get("result")),
        }


def write_status(status_path: Path, status: dict[str, Any]) -> None:
    tmp_path = status_path.with_suffix(status_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(status_path)


def stream_pipe(
    pipe,
    sink_path: Path,
    prefix: str = "",
    event_sink_path: Path | None = None,
    status_path: Path | None = None,
    status: dict[str, Any] | None = None,
    status_lock: threading.Lock | None = None,
) -> None:
    event_sink = event_sink_path.open("w", encoding="utf-8") if event_sink_path else None
    with sink_path.open("w", encoding="utf-8") as sink:
        try:
            for line in iter(pipe.readline, ""):
                sink.write(line)
                sink.flush()
                if event_sink is not None:
                    raw = line.strip()
                    if raw.startswith("{"):
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            event = None
                        if isinstance(event, dict):
                            event_sink.write(raw + "\n")
                            event_sink.flush()
                            if status is not None and status_path is not None and status_lock is not None:
                                with status_lock:
                                    update_status_from_event(status, event)
                                    write_status(status_path, status)
                if prefix:
                    print(f"{prefix}{line}", end="")
                else:
                    print(line, end="")
        finally:
            if event_sink is not None:
                event_sink.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dispatch a bounded task packet to Cursor Agent/Composer 2.5 Fast under the bounded Cursor delegation model."
    )
    parser.add_argument("--workspace", default=".", help="Workspace/repo directory for Cursor Agent.")
    parser.add_argument("--task-file", required=True, help="Markdown task packet path.")
    parser.add_argument(
        "--planning-source",
        choices=PLANNING_SOURCE_CHOICES,
        default="auto",
        help="Authority source expected in the task packet. Use master-direct for direct Cursor mode; non-cursor-planning-subagent for planned mode; orchestrator-subagent for hierarchical workstream implementation; user-provided-plan when applicable. Default: auto-detect.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_CURSOR_MODEL,
        help="Cursor model name or model id. Default: composer-2.5-fast. Override only when the user explicitly directed Cursor to use a different model; also pass --user-authorized-model.",
    )
    parser.add_argument(
        "--internal-subagent-model",
        default=None,
        help="Model Cursor should request for internal Task()/taskToolCall subagents. Default: same as --model. Override only when the user explicitly directed Cursor internal subagents to use a different model.",
    )
    parser.add_argument(
        "--user-authorized-model",
        action="store_true",
        help="Confirm that a non-default --model or --internal-subagent-model value comes from an explicit user instruction to Cursor, not from subagent permission or outer-agent model preferences.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Enable direct file modifications via Cursor `--force`.",
    )
    parser.add_argument(
        "--inspect-only",
        action="store_true",
        help="Ask Cursor to inspect/report blockers without editing. Mutually exclusive with --apply.",
    )
    parser.add_argument(
        "--allow-missing-authority",
        action="store_true",
        help="Allow dispatch even if the task packet lacks the expected authority marker. Not recommended.",
    )
    parser.add_argument(
        "--output-format",
        choices=("text", "json", "stream-json"),
        default="stream-json",
        help="Cursor print-mode output format.",
    )
    parser.add_argument(
        "--stream-partial-output",
        action="store_true",
        help="Stream text deltas; only valid with stream-json output.",
    )
    parser.add_argument("--trust", action="store_true", help="Trust workspace in headless mode.")
    parser.add_argument(
        "--sandbox",
        choices=("enabled", "disabled"),
        default=None,
        help="Set Cursor sandbox mode.",
    )
    parser.add_argument(
        "--worktree",
        nargs="?",
        const="",
        default=None,
        help="Run in a new Cursor worktree. Optionally provide a worktree name.",
    )
    parser.add_argument("--worktree-base", default=None, help="Branch/ref to base the worktree on.")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow apply mode even if git status is dirty. Use only when intentional.",
    )
    parser.add_argument(
        "--allow-non-git",
        action="store_true",
        help="Allow apply mode outside a git repository. Not recommended.",
    )
    parser.add_argument(
        "--delegation-owner",
        default=None,
        help="Optional upstream owner for logs, e.g. upstream or orchestrator-subagent:<id>.",
    )
    parser.add_argument(
        "--workstream-id",
        default=None,
        help="Optional hierarchical workstream id for logs and prompts.",
    )
    parser.add_argument(
        "--log-dir",
        default=None,
        help="Directory for run logs. Default: <workspace>/.agent/delegations.",
    )
    parser.add_argument(
        "--extra-instruction",
        action="append",
        help="Additional instruction appended to the Cursor prompt. Repeatable.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print command and prompt, then exit.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    task_file = Path(args.task_file).expanduser().resolve()

    if args.apply and args.inspect_only:
        print("--apply and --inspect-only are mutually exclusive", file=sys.stderr)
        return 2
    if args.model != DEFAULT_CURSOR_MODEL and not args.user_authorized_model:
        print(
            f"Refusing Cursor model override {args.model!r}. Default to {DEFAULT_CURSOR_MODEL!r} unless "
            "the user explicitly directed Cursor to use a different model; permission to use subagents "
            "or outer-agent model preferences is not enough. Re-run with --user-authorized-model only "
            "when that explicit user instruction exists.",
            file=sys.stderr,
        )
        return 2
    if (
        args.internal_subagent_model
        and args.internal_subagent_model != args.model
        and not args.user_authorized_model
    ):
        print(
            f"Refusing internal subagent model override {args.internal_subagent_model!r}. "
            f"Default internal subagents to {args.model!r} unless the user explicitly directed "
            "Cursor internal subagents to use a different model; re-run with --user-authorized-model "
            "only when that explicit user instruction exists.",
            file=sys.stderr,
        )
        return 2
    if not workspace.exists() or not workspace.is_dir():
        print(f"Workspace does not exist or is not a directory: {workspace}", file=sys.stderr)
        return 2
    if not task_file.exists() or not task_file.is_file():
        print(f"Task file does not exist: {task_file}", file=sys.stderr)
        return 2
    if args.stream_partial_output and args.output_format != "stream-json":
        print("--stream-partial-output requires --output-format stream-json", file=sys.stderr)
        return 2

    task_text = task_file.read_text(encoding="utf-8")
    if not has_required_authority(task_text, args.planning_source) and not args.allow_missing_authority:
        expected = (
            "one of the supported authority markers"
            if args.planning_source == "auto"
            else f"the marker for {args.planning_source}: {AUTHORITY_MARKERS[args.planning_source][0]}"
        )
        print(
            f"Refusing dispatch because the task packet lacks {expected}. "
            "Add a proper authority section from references/task-contract.md, or pass --allow-missing-authority only for an intentional exception.",
            file=sys.stderr,
        )
        return 2

    is_git, status_lines, git_error = run_git_status(workspace)
    if args.apply:
        if not is_git and not args.allow_non_git:
            print(
                "Apply mode requires a git workspace for review/revert safety. "
                "Use --allow-non-git only if this is intentional.",
                file=sys.stderr,
            )
            if git_error:
                print(f"git status error: {git_error}", file=sys.stderr)
            return 2
        if is_git and not args.allow_dirty:
            dirty = filter_ignorable_status(status_lines, workspace, task_file)
            if dirty:
                print(
                    "Refusing apply mode because the workspace has existing git changes. "
                    "Commit/stash them or pass --allow-dirty if intentional.",
                    file=sys.stderr,
                )
                print("\n".join(dirty), file=sys.stderr)
                return 2

    if args.dry_run:
        agent_bin = shutil.which("agent") or shutil.which("cursor-agent") or "agent"
    else:
        agent_bin = find_cursor_agent()

    prompt, detected_source = build_prompt(task_file, task_text, args)

    cmd = [
        agent_bin,
        "-p",
        "--model",
        args.model,
        "--output-format",
        args.output_format,
        "--workspace",
        str(workspace),
    ]
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
    cmd.append(prompt)

    log_base = Path(args.log_dir).expanduser().resolve() if args.log_dir else workspace / ".agent" / "delegations"
    if args.dry_run:
        print("Command:")
        print(" ".join(shlex.quote(part) for part in cmd[:-1]) + " <prompt>")
        print("\nPrompt:")
        print(prompt)
        print(f"\nDetected authority source: {detected_source or 'none'}")
        print(f"Logs would be written under: {log_base}")
        print("Each run writes stdout.log, stderr.log, events.ndjson, status.json, prompt.txt, metadata.json, and a latest pointer.")
        return 0

    run_dir = make_log_dir(log_base)
    stdout_log = run_dir / "stdout.log"
    stderr_log = run_dir / "stderr.log"
    events_log = run_dir / "events.ndjson"
    status_file = run_dir / "status.json"
    latest_file = log_base / "latest"
    metadata = {
        "workspace": str(workspace),
        "task_file": str(task_file),
        "planning_source_arg": args.planning_source,
        "detected_authority_source": detected_source,
        "model": args.model,
        "internal_subagent_model": args.internal_subagent_model or args.model,
        "user_authorized_model_override": args.user_authorized_model,
        "mode": "inspect-only" if args.inspect_only else ("apply" if args.apply else "proposal"),
        "delegation_owner": args.delegation_owner,
        "workstream_id": args.workstream_id,
        "output_format": args.output_format,
        "command_without_prompt": cmd[:-1],
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "events_log": str(events_log),
        "status_file": str(status_file),
        "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    latest_file.write_text(str(run_dir) + "\n", encoding="utf-8")
    status: dict[str, Any] = {
        "state": "starting",
        "workspace": str(workspace),
        "task_file": str(task_file),
        "run_dir": str(run_dir),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "events_log": str(events_log),
        "metadata_file": str(run_dir / "metadata.json"),
        "mode": metadata["mode"],
        "model": args.model,
        "internal_subagent_model": args.internal_subagent_model or args.model,
        "output_format": args.output_format,
        "started_at_utc": metadata["started_at_utc"],
        "updated_at_utc": metadata["started_at_utc"],
        "events_seen": 0,
        "current_tool_call": None,
        "recent_tool_calls": [],
        "active_subagents": {},
        "recent_subagents": [],
    }
    status_lock = threading.Lock()
    write_status(status_file, status)

    print(f"Running Cursor Agent. Logs: {run_dir}")
    print(f"Live status: {status_file}")
    process = subprocess.Popen(
        cmd,
        cwd=str(workspace),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    assert process.stdout is not None
    assert process.stderr is not None

    stdout_thread = threading.Thread(
        target=stream_pipe,
        args=(process.stdout, stdout_log, "", events_log, status_file, status, status_lock),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=stream_pipe,
        args=(process.stderr, stderr_log, "[stderr] "),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    return_code = process.wait()
    stdout_thread.join(timeout=2)
    stderr_thread.join(timeout=2)

    metadata["finished_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    metadata["return_code"] = return_code
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    with status_lock:
        if status.get("state") not in ("succeeded", "failed"):
            status["state"] = "succeeded" if return_code == 0 else "failed"
        status["return_code"] = return_code
        status["finished_at_utc"] = metadata["finished_at_utc"]
        status["updated_at_utc"] = metadata["finished_at_utc"]
        write_status(status_file, status)

    if return_code != 0:
        print(f"Cursor Agent exited with code {return_code}. See logs: {run_dir}", file=sys.stderr)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
