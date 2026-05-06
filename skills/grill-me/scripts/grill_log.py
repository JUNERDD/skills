#!/usr/bin/env python3

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
import re
from typing import Optional


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def read_file(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"[ERROR] Log file does not exist: {path}")
    return path.read_text(encoding="utf-8")


def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def quote_block(text: str, empty_fallback: str) -> str:
    normalized = text.replace("\r\n", "\n").strip("\n")
    if not normalized.strip():
        normalized = empty_fallback
    return "\n".join("> " + line if line else ">" for line in normalized.split("\n"))


def next_question_index(content: str) -> int:
    matches = [int(value) for value in re.findall(r"^## Question (\d+)$", content, re.MULTILINE)]
    return max(matches, default=0) + 1


def pending_question_indexes(content: str) -> list[int]:
    return [int(value) for value in re.findall(r"<<PENDING_ANSWER_(\d+)>>", content)]


def sanitize_session_key(session_key: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", session_key.strip())
    normalized = normalized.strip("-.")
    return normalized or "session"


def read_session_metadata(path: Path) -> dict[str, str]:
    header = read_file(path).split("## Questions", 1)[0]
    metadata = {}
    for line in header.splitlines():
        if not line.startswith("- ") or ":" not in line[2:]:
            continue
        key, value = line[2:].split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def update_session_metadata(
    path: Path,
    updates: dict[str, str],
    remove_keys: Optional[list[str]] = None,
) -> None:
    remove_keys = remove_keys or []
    content = read_file(path)
    if "## Questions" not in content:
        raise SystemExit(f"[ERROR] Session log is missing the questions section: {path}")

    header, questions = content.split("## Questions", 1)
    lines = header.rstrip("\n").split("\n")
    rewritten = []
    seen = set()

    for line in lines:
        if not line.startswith("- ") or ":" not in line[2:]:
            rewritten.append(line)
            continue
        key, _ = line[2:].split(":", 1)
        key = key.strip()
        if key in remove_keys:
            continue
        if key in updates:
            rewritten.append(f"- {key}: {updates[key]}")
            seen.add(key)
        else:
            rewritten.append(line)

    for key, value in updates.items():
        if key not in seen:
            rewritten.append(f"- {key}: {value}")

    write_file(path, "\n".join(rewritten).rstrip("\n") + "\n\n## Questions" + questions)


def parse_quote_block(block: str) -> str:
    lines = []
    for line in block.replace("\r\n", "\n").split("\n"):
        if line.startswith("> "):
            lines.append(line[2:])
        elif line == ">":
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines).strip("\n")


def normalize_inline(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def summarize_text(text: str, limit: int = 160) -> str:
    normalized = normalize_inline(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def canonicalize_reply(text: str) -> str:
    lowered = normalize_inline(text).lower()
    lowered = re.sub(r"[.!?]+$", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def is_assent_only(answer_text: str) -> bool:
    canonical = canonicalize_reply(answer_text)
    if not canonical:
        return False

    assent_patterns = (
        r"yes",
        r"yes, do that",
        r"yes, use that",
        r"yes, go with that",
        r"yeah",
        r"yep",
        r"yup",
        r"ok",
        r"okay",
        r"ok, do that",
        r"okay, do that",
        r"sure",
        r"agreed",
        r"agree",
        r"lgtm",
        r"ship it",
        r"proceed",
        r"do that",
        r"use that",
        r"go with that",
        r"let's do that",
        r"lets do that",
        r"please do that",
        r"sounds good",
        r"sounds good to me",
        r"that works",
        r"works for me",
        r"fine",
        r"按推荐来",
        r"按建议来",
        r"按你推荐的来",
        r"按你的建议来",
        r"同意",
        r"可以",
        r"就这样",
        r"照这个来",
    )
    return any(re.fullmatch(pattern, canonical) for pattern in assent_patterns)


def assent_modifier_text(answer_text: str) -> str:
    normalized = normalize_inline(answer_text)
    if not normalized:
        return ""

    patterns = (
        r"^(?:按推荐来|按建议来|按你推荐的来|按你的建议来|同意|可以|照这个来)[,，.。!！\s]*(?P<rest>.+)$",
        r"^(?:yes|yeah|yep|yup|ok|okay|sure|agreed|agree|sounds good|that works|works for me)[,.\s]+(?P<rest>(?:but|however|except|and)\b.+)$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        rest = match.group("rest").strip()
        rest = re.sub(r"^(?:但是|但|不过|另外|同时|并且)[,，.。:：\s]*", "", rest)
        rest = re.sub(r"^(?:but|however|except|and)\b[,.:;\s]*", "", rest, flags=re.IGNORECASE)
        return rest.strip()

    return ""


def resolved_answer_text(entry: dict[str, str]) -> str:
    if entry.get("answer_is_resolved"):
        return entry["answer_text"]

    answer_text = entry["answer_text"]
    recommendation_text = entry["recommendation_text"]
    if is_assent_only(answer_text) and normalize_inline(recommendation_text):
        return recommendation_text
    modifier_text = assent_modifier_text(answer_text)
    if modifier_text and normalize_inline(recommendation_text):
        return f"{recommendation_text}\n\nUser modification: {modifier_text}"
    return answer_text


def has_distinct_raw_answer(entry: dict[str, str]) -> bool:
    return normalize_inline(resolved_answer_text(entry)) != normalize_inline(entry["raw_answer_text"])


UNCATEGORIZED_PLANNING_BUCKET = "Uncategorized Planning Seeds"


def primary_bucket(question_text: str) -> str:
    question = question_text.lower()
    if any(
        token in question
        for token in ("goal", "objective", "success", "outcome", "purpose", "problem", "目标", "价值", "成败", "成功", "解决")
    ):
        return "Goals"
    if any(token in question for token in ("scope", "non-goal", "out of scope", "defer", "phase", "范围", "不做", "延后", "阶段")):
        return "Scope Boundaries"
    if any(
        token in question
        for token in (
            "assumption",
            "assume",
            "evidence",
            "prove",
            "validate",
            "unknown",
            "uncertain",
            "hypothesis",
            "假设",
            "证据",
            "验证",
            "未知",
            "不确定",
            "验收",
        )
    ):
        return "Assumptions and Evidence"
    if any(
        token in question
        for token in ("risk", "failure", "prevent", "danger", "concern", "edge case", "abuse", "threat", "风险", "失败", "错误", "底线", "不能")
    ):
        return "Risks"
    if any(
        token in question
        for token in (
            "choose",
            "decision",
            "prefer",
            "trade-off",
            "tradeoff",
            "approach",
            "architecture",
            "design",
            "alternative",
            "option",
            "选择",
            "决策",
            "取舍",
            "方案",
            "支持",
            "入口",
            "路径",
            "主界面",
            "功能",
        )
    ):
        return "Decisions and Alternatives"
    if any(
        token in question
        for token in (
            "owner",
            "stakeholder",
            "operator",
            "rollout",
            "rollback",
            "migrate",
            "migration",
            "monitor",
            "alert",
            "test",
            "verify",
            "deploy",
            "上线",
            "发布",
            "回滚",
            "监控",
            "测试",
            "反馈",
            "删除",
            "登录",
            "注册",
            "数据",
        )
    ):
        return "Operations and Delivery"
    if any(
        token in question
        for token in (
            "constraint",
            "limit",
            "budget",
            "deadline",
            "cannot",
            "requirement",
            "latency",
            "throughput",
            "compatibility",
            "compliance",
            "约束",
            "限制",
            "预算",
            "期限",
            "必须",
            "最低",
            "合规",
        )
    ):
        return "Constraints"
    return UNCATEGORIZED_PLANNING_BUCKET


def parse_session_entries(content: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r"^## Question (?P<index>\d+)\n\n"
        r"Asked at: (?P<asked_at>.*?)\n\n"
        r"Question:\n(?P<question>.*?)\n\n"
        r"Recommendation:\n(?P<recommendation>.*?)\n\n"
        r"Answer:\n(?P<answer>.*?)"
        r"(?:\n\nRaw user answer:\n(?P<raw_answer>.*?))?\n\n"
        r"Answered at: (?P<answered_at>.*?)(?=\n## Question \d+\n|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    entries = []
    for match in pattern.finditer(content):
        question_text = parse_quote_block(match.group("question"))
        recommendation_text = parse_quote_block(match.group("recommendation"))
        answer_text = parse_quote_block(match.group("answer"))
        raw_answer_group = match.group("raw_answer")
        raw_answer_text = parse_quote_block(raw_answer_group) if raw_answer_group is not None else answer_text
        entries.append(
            {
                "index": match.group("index"),
                "asked_at": match.group("asked_at").strip(),
                "answered_at": match.group("answered_at").strip(),
                "question_text": question_text,
                "recommendation_text": recommendation_text,
                "answer_text": answer_text,
                "raw_answer_text": raw_answer_text,
                "answer_is_resolved": raw_answer_group is not None,
                "bucket": primary_bucket(question_text),
            }
        )
    return entries


def default_log_dir(workspace: Path) -> Path:
    return workspace / "tmp" / "grill-me"


def resolve_workspace(workspace: Optional[str]) -> Path:
    if not workspace:
        raise SystemExit("[ERROR] Provide --workspace when not operating on an explicit --file.")
    return Path(workspace).expanduser().resolve()


def resolve_log_dir(workspace: Optional[str], log_dir: Optional[str]) -> Path:
    if log_dir:
        return Path(log_dir).expanduser().resolve()
    return default_log_dir(resolve_workspace(workspace))


def resolve_session_key(explicit: Optional[str]) -> str:
    session_key = explicit or os.environ.get("CODEX_THREAD_ID")
    if not session_key:
        raise SystemExit("[ERROR] Provide --session-key or set CODEX_THREAD_ID.")
    return session_key


def session_key_matches(path: Path, session_key: str) -> bool:
    return read_session_metadata(path).get("Session key") == session_key


def session_status(path: Path) -> str:
    return read_session_metadata(path).get("Status", "active").lower()


def is_active_session(path: Path) -> bool:
    return session_status(path) == "active"


def active_session_pointer(log_dir: Path, session_key: str) -> Path:
    slug = sanitize_session_key(session_key)
    return log_dir / f".active-{slug}.txt"


def delete_active_session(log_dir: Path, session_key: str) -> None:
    pointer_path = active_session_pointer(log_dir, session_key)
    if pointer_path.exists():
        pointer_path.unlink()


def store_active_session(log_dir: Path, session_key: str, log_path: Path) -> None:
    pointer_path = active_session_pointer(log_dir, session_key)
    pointer_path.write_text(f"{log_path}\n", encoding="utf-8")


def load_active_session(log_dir: Path, session_key: str) -> Optional[Path]:
    pointer_path = active_session_pointer(log_dir, session_key)
    if not pointer_path.exists():
        return None

    stored_path = Path(pointer_path.read_text(encoding="utf-8").strip()).expanduser()
    if not stored_path.exists():
        return None

    resolved_path = stored_path.resolve()
    if not session_key_matches(resolved_path, session_key):
        return None
    if not is_active_session(resolved_path):
        return None

    return resolved_path


def unique_log_path(directory: Path, session_key: Optional[str] = None) -> Path:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    prefix = "session"
    if session_key:
        prefix = f"session-{sanitize_session_key(session_key)}"

    candidate = directory / f"{prefix}-{timestamp}.md"
    suffix = 1
    while candidate.exists():
        candidate = directory / f"{prefix}-{timestamp}-{suffix}.md"
        suffix += 1
    return candidate


def create_session_file(log_dir: Path, workspace: Optional[Path], session_key: Optional[str]) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = unique_log_path(log_dir, session_key)
    lines = [
        "# Grill Me Session",
        "",
        f"- Created: {now_iso()}",
        f"- Log file: {log_path}",
    ]
    if workspace:
        lines.append(f"- Workspace: {workspace}")
    if session_key:
        lines.append(f"- Session key: {session_key}")
    lines.extend(
        [
            "- Status: active",
            "",
            "## Questions",
            "",
        ]
    )
    write_file(log_path, "\n".join(lines))
    return log_path


def create_session(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace).expanduser().resolve() if args.workspace else None
    session_key = args.session_key
    log_dir = Path(args.dir).expanduser().resolve()
    log_path = create_session_file(log_dir, workspace, session_key)
    if session_key:
        store_active_session(log_dir, session_key, log_path)
    print(log_path)
    return 0


def latest_session_path(log_dir: Path, session_key: str, active_only: bool = True) -> Path:
    candidates = sorted(
        (
            path
            for path in log_dir.glob(f"session-{sanitize_session_key(session_key)}-*.md")
            if path.is_file()
            and session_key_matches(path, session_key)
            and (not active_only or is_active_session(path))
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        scope = "active " if active_only else ""
        raise SystemExit(
            f"[ERROR] No {scope}session logs found in: {log_dir} for session key {session_key!r}"
        )
    return candidates[0]


def latest_session(args: argparse.Namespace) -> int:
    log_dir = Path(args.dir).expanduser().resolve()
    if not log_dir.exists():
        raise SystemExit(f"[ERROR] Log directory does not exist: {log_dir}")

    log_path = latest_session_path(log_dir, args.session_key, active_only=True)
    store_active_session(log_dir, args.session_key, log_path)
    print(log_path)
    return 0


def current_session(args: argparse.Namespace) -> int:
    resolve_workspace(args.workspace)
    log_dir = resolve_log_dir(args.workspace, args.dir)
    session_key = resolve_session_key(args.session_key)
    log_dir.mkdir(parents=True, exist_ok=True)

    current_session_path = load_active_session(log_dir, session_key)
    if current_session_path:
        print(current_session_path)
        return 0

    latest_session_for_key = latest_session_path(log_dir, session_key, active_only=True)
    store_active_session(log_dir, session_key, latest_session_for_key)
    print(latest_session_for_key)
    return 0


def resolve_session_log_path(args: argparse.Namespace, create_if_missing: bool) -> Path:
    if args.file:
        return Path(args.file).expanduser().resolve()

    workspace = resolve_workspace(args.workspace)
    log_dir = resolve_log_dir(args.workspace, args.dir)
    session_key = resolve_session_key(args.session_key)
    log_dir.mkdir(parents=True, exist_ok=True)

    current_session = load_active_session(log_dir, session_key)
    if current_session:
        return current_session

    try:
        latest_session_for_key = latest_session_path(log_dir, session_key, active_only=True)
        store_active_session(log_dir, session_key, latest_session_for_key)
        return latest_session_for_key
    except SystemExit:
        if not create_if_missing:
            raise

    new_session = create_session_file(log_dir, workspace, session_key)
    store_active_session(log_dir, session_key, new_session)
    return new_session


def append_question(args: argparse.Namespace) -> int:
    log_path = resolve_session_log_path(args, create_if_missing=True)
    content = read_file(log_path)
    pending = pending_question_indexes(content)
    if pending:
        raise SystemExit(
            f"[ERROR] Question {pending[-1]} is still pending. Backfill its answer before asking another question."
        )

    index = next_question_index(content)
    asked_at = now_iso()
    question_block = quote_block(args.question, "_No question recorded._")
    recommendation_block = quote_block(
        args.recommendation or "",
        "_No recommendation recorded._",
    )
    entry = (
        f"## Question {index}\n\n"
        f"Asked at: {asked_at}\n\n"
        "Question:\n"
        f"{question_block}\n\n"
        "Recommendation:\n"
        f"{recommendation_block}\n\n"
        "Answer:\n"
        f"<<PENDING_ANSWER_{index}>>\n\n"
        "Answered at: "
        f"<<PENDING_ANSWERED_AT_{index}>>\n"
    )
    separator = "" if content.endswith("\n\n") else "\n"
    write_file(log_path, content + separator + entry)

    if not args.file:
        log_dir = resolve_log_dir(args.workspace, args.dir)
        session_key = resolve_session_key(args.session_key)
        store_active_session(log_dir, session_key, log_path)

    print(log_path)
    return 0


def read_answer_input(args: argparse.Namespace) -> str:
    if args.stdin and args.answer is not None:
        raise SystemExit("[ERROR] Pass either --answer or --stdin, not both.")
    if args.stdin:
        return sys.stdin.read()
    if args.answer is None:
        raise SystemExit("[ERROR] Provide --answer or --stdin.")
    return args.answer


def pending_recommendation_text(content: str, index: int) -> str:
    pattern = re.compile(
        rf"^## Question {index}\n\n"
        r"Asked at: .*?\n\n"
        r"Question:\n.*?\n\n"
        r"Recommendation:\n(?P<recommendation>.*?)\n\n"
        rf"Answer:\n<<PENDING_ANSWER_{index}>>",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    if not match:
        return ""
    return parse_quote_block(match.group("recommendation"))


def confirmed_answer_text(
    args: argparse.Namespace,
    content: str,
    index: int,
    raw_answer_text: str,
) -> str:
    if args.resolved_answer is not None:
        return args.resolved_answer

    recommendation_text = pending_recommendation_text(content, index)
    if is_assent_only(raw_answer_text) and normalize_inline(recommendation_text):
        return recommendation_text
    modifier_text = assent_modifier_text(raw_answer_text)
    if modifier_text and normalize_inline(recommendation_text):
        return f"{recommendation_text}\n\nUser modification: {modifier_text}"

    return raw_answer_text


def backfill_answer(args: argparse.Namespace) -> int:
    log_path = resolve_session_log_path(args, create_if_missing=False)
    content = read_file(log_path)
    pending = pending_question_indexes(content)
    if not pending:
        raise SystemExit("[ERROR] No pending question found in the log.")

    index = pending[-1]
    raw_answer_text = read_answer_input(args)
    answer_text = confirmed_answer_text(args, content, index, raw_answer_text)
    answer_block = quote_block(answer_text, "_No answer recorded._")
    raw_answer_block = quote_block(raw_answer_text, "_No user answer recorded._")
    replacement = f"{answer_block}\n\nRaw user answer:\n{raw_answer_block}"
    updated = content.replace(f"<<PENDING_ANSWER_{index}>>", replacement, 1)
    updated = updated.replace(f"<<PENDING_ANSWERED_AT_{index}>>", now_iso(), 1)
    write_file(log_path, updated)

    if not args.file:
        log_dir = resolve_log_dir(args.workspace, args.dir)
        session_key = resolve_session_key(args.session_key)
        store_active_session(log_dir, session_key, log_path)

    print(log_path)
    return 0


def outcome_path_for_session(log_path: Path) -> Path:
    stem = log_path.stem
    if stem.startswith("session-"):
        stem = "outcome-" + stem[len("session-") :]
    else:
        stem = stem + "-outcome"

    candidate = log_path.with_name(stem + ".md")
    suffix = 1
    while candidate.exists():
        candidate = log_path.with_name(f"{stem}-{suffix}.md")
        suffix += 1
    return candidate


def render_bucket_section(lines: list[str], title: str, entries: list[dict[str, str]]) -> None:
    if not entries:
        return
    lines.extend([f"### {title}", ""])
    for entry in entries:
        lines.append(f"- Q{entry['index']}: {summarize_text(resolved_answer_text(entry))}")
        lines.append(f"  Source question: {normalize_inline(entry['question_text'])}")
    lines.append("")


def build_outcome_markdown(
    log_path: Path,
    _outcome_path: Path,
    _metadata: dict[str, str],
    entries: list[dict[str, str]],
) -> str:
    bucket_order = [
        "Goals",
        "Scope Boundaries",
        "Assumptions and Evidence",
        "Constraints",
        "Risks",
        "Decisions and Alternatives",
        "Operations and Delivery",
        UNCATEGORIZED_PLANNING_BUCKET,
    ]

    lines = [
        "# Grill Me Outcome",
        "",
        f"- Source transcript: {log_path}",
        f"- Confirmed questions: {len(entries)}",
        "",
        "## Planning Seeds",
        "",
    ]

    bucketed = {title: [entry for entry in entries if entry["bucket"] == title] for title in bucket_order}
    for title in bucket_order:
        render_bucket_section(lines, title, bucketed[title])

    lines.extend(["## Confirmed Q&A", ""])
    for entry in entries:
        lines.append(f"### Q{entry['index']}. {normalize_inline(entry['question_text'])}")
        lines.append("")
        lines.append("Resolved answer:")
        lines.append(quote_block(resolved_answer_text(entry), "_No answer recorded._"))
        if has_distinct_raw_answer(entry):
            lines.append("")
            lines.append("Raw user answer:")
            lines.append(quote_block(entry["raw_answer_text"], "_No user answer recorded._"))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def finalize_session(args: argparse.Namespace) -> int:
    log_path = resolve_session_log_path(args, create_if_missing=False)
    content = read_file(log_path)
    pending = pending_question_indexes(content)
    if pending:
        raise SystemExit(f"[ERROR] Cannot finalize while question {pending[-1]} is still pending.")

    metadata = read_session_metadata(log_path)
    entries = parse_session_entries(content)
    if not entries:
        raise SystemExit("[ERROR] Cannot finalize an empty grilling session.")

    outcome_path = outcome_path_for_session(log_path)
    write_file(outcome_path, build_outcome_markdown(log_path, outcome_path, metadata, entries))

    update_session_metadata(
        log_path,
        {
            "Status": "finalized",
            "Finalized": now_iso(),
            "Outcome file": str(outcome_path),
        },
    )

    session_key = metadata.get("Session key")
    if session_key:
        log_dir = resolve_log_dir(metadata.get("Workspace") or args.workspace, args.dir) if not args.file else log_path.parent
        delete_active_session(log_dir, session_key)

    print(f"TRANSCRIPT={log_path}")
    print(f"OUTCOME={outcome_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and maintain a grill-me Markdown Q&A log.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Create a new session log and print its path.")
    new_parser.add_argument("--dir", required=True, help="Directory that will contain session Markdown files.")
    new_parser.add_argument("--workspace", help="Workspace root to record in the session header.")
    new_parser.add_argument(
        "--session-key",
        help="Stable session identifier used for safe recovery across multiple threads.",
    )
    new_parser.set_defaults(func=create_session)

    latest_parser = subparsers.add_parser("latest", help="Print the most recently modified session log.")
    latest_parser.add_argument("--dir", required=True, help="Directory that contains session Markdown files.")
    latest_parser.add_argument(
        "--session-key",
        required=True,
        help="Stable session identifier recorded when the session was created.",
    )
    latest_parser.set_defaults(func=latest_session)

    current_parser = subparsers.add_parser(
        "current",
        help="Print the active session log for the current workspace/thread.",
    )
    current_parser.add_argument(
        "--workspace",
        required=True,
        help="Workspace root used to locate the default log directory and active thread session.",
    )
    current_parser.add_argument(
        "--dir",
        help="Override the log directory when using --workspace mode.",
    )
    current_parser.add_argument(
        "--session-key",
        help="Override the thread/session key. Defaults to CODEX_THREAD_ID.",
    )
    current_parser.set_defaults(func=current_session)

    finalize_parser = subparsers.add_parser(
        "finalize",
        help="Write a planning-ready outcome Markdown file and close the active session.",
    )
    finalize_parser.add_argument("--file", help="Session Markdown file to finalize directly.")
    finalize_parser.add_argument(
        "--workspace",
        help="Workspace root used to locate the default log directory and active thread session.",
    )
    finalize_parser.add_argument(
        "--dir",
        help="Override the log directory when using --workspace mode.",
    )
    finalize_parser.add_argument(
        "--session-key",
        help="Override the thread/session key. Defaults to CODEX_THREAD_ID.",
    )
    finalize_parser.set_defaults(func=finalize_session)

    ask_parser = subparsers.add_parser("ask", help="Append a new pending question to the session log.")
    ask_parser.add_argument("--file", help="Session Markdown file to update directly.")
    ask_parser.add_argument(
        "--workspace",
        help="Workspace root used to locate the default log directory and active thread session.",
    )
    ask_parser.add_argument(
        "--dir",
        help="Override the log directory when using --workspace mode.",
    )
    ask_parser.add_argument(
        "--session-key",
        help="Override the thread/session key. Defaults to CODEX_THREAD_ID.",
    )
    ask_parser.add_argument("--question", required=True, help="Question that will be asked to the user.")
    ask_parser.add_argument(
        "--recommendation",
        help="Recommended answer or framing that will be shown alongside the question.",
    )
    ask_parser.set_defaults(func=append_question)

    answer_parser = subparsers.add_parser(
        "answer",
        help="Backfill the answer for the most recent pending question.",
    )
    answer_parser.add_argument("--file", help="Session Markdown file to update directly.")
    answer_parser.add_argument(
        "--workspace",
        help="Workspace root used to locate the default log directory and active thread session.",
    )
    answer_parser.add_argument(
        "--dir",
        help="Override the log directory when using --workspace mode.",
    )
    answer_parser.add_argument(
        "--session-key",
        help="Override the thread/session key. Defaults to CODEX_THREAD_ID.",
    )
    answer_parser.add_argument("--answer", help="Answer text to write into the pending question.")
    answer_parser.add_argument(
        "--resolved-answer",
        help="Planning-ready confirmed conclusion to store in the session Answer field.",
    )
    answer_parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read the answer text from standard input.",
    )
    answer_parser.set_defaults(func=backfill_answer)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
