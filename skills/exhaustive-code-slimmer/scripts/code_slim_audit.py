#!/usr/bin/env python3
"""Repository audit for exhaustive code slimming.

Produces baseline metrics and optional JSONL deletion candidates. The script is
intentionally conservative: candidates are evidence prompts, not automatic truth.
Every candidate must still pass the user's oracle before being accepted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
    "coverage",
    "dist",
    "build",
    ".next",
    ".turbo",
    "target",
    "vendor",
}

CODE_SUFFIXES = {
    ".asm",
    ".c",
    ".cc",
    ".clj",
    ".cljs",
    ".cpp",
    ".cs",
    ".css",
    ".dart",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".lua",
    ".m",
    ".mm",
    ".php",
    ".pl",
    ".pm",
    ".py",
    ".r",
    ".rb",
    ".rs",
    ".scala",
    ".scss",
    ".sh",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}

TEXT_SUFFIXES = CODE_SUFFIXES | {
    ".cfg",
    ".conf",
    ".csv",
    ".env",
    ".ini",
    ".json",
    ".lock",
    ".md",
    ".rst",
    ".toml",
    ".txt",
}

COMMENT_PREFIXES = ("#", "//", "--", "/*", "*", "*/")
PROTECTED_EMPTY_NAMES = {"__init__.py", ".gitkeep", ".keep", "package-info.java"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a repository for code slimming opportunities.")
    parser.add_argument("--repo", default=".", help="Repository root to scan.")
    parser.add_argument("--json-output", help="Write full audit JSON to this path.")
    parser.add_argument("--markdown-output", help="Write human-readable Markdown report to this path.")
    parser.add_argument("--candidates-output", help="Write JSONL candidate operations to this path.")
    parser.add_argument("--exclude-dir", action="append", default=[], help="Additional directory name to exclude; repeatable.")
    parser.add_argument("--include-vendor", action="store_true", help="Do not exclude vendor-like directories by default.")
    parser.add_argument("--duplicate-window", type=int, default=8, help="Line-window size for duplicate block detection.")
    parser.add_argument("--min-duplicate-chars", type=int, default=120, help="Minimum normalized chunk length to report.")
    parser.add_argument("--top", type=int, default=25, help="Number of largest files/duplicate groups to include.")
    parser.add_argument(
        "--emit-duplicate-span-candidates",
        action="store_true",
        help="Emit delete_span candidates for repeated line windows. These are noisy and must be oracle-verified.",
    )
    return parser.parse_args()


def safe_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_probably_binary(data: bytes) -> bool:
    if b"\0" in data:
        return True
    if not data:
        return False
    # Allow common whitespace/control chars; a high control-byte ratio suggests binary.
    control = sum(1 for b in data[:4096] if b < 9 or (13 < b < 32))
    return control / min(len(data), 4096) > 0.10


def read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if is_probably_binary(data):
        return None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def iter_files(root: Path, exclude_dirs: set[str]) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        current = Path(dirpath)
        for filename in filenames:
            yield current / filename


def count_file(path: Path, root: Path) -> dict[str, Any] | None:
    text = read_text(path)
    if text is None:
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        return {
            "path": safe_rel(path, root),
            "suffix": path.suffix.lower(),
            "bytes": size,
            "text": False,
            "code": False,
            "lines": 0,
            "nonblank_lines": 0,
            "comment_like_lines": 0,
            "sha256": None,
        }

    lines = text.splitlines()
    nonblank = [line for line in lines if line.strip()]
    comment_like = [line for line in nonblank if line.strip().startswith(COMMENT_PREFIXES)]
    suffix = path.suffix.lower()
    code = suffix in CODE_SUFFIXES
    return {
        "path": safe_rel(path, root),
        "suffix": suffix,
        "bytes": len(text.encode("utf-8", errors="ignore")),
        "text": True,
        "code": code,
        "lines": len(lines),
        "nonblank_lines": len(nonblank),
        "comment_like_lines": len(comment_like),
        "sha256": hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest(),
    }


def normalize_line(line: str) -> str:
    stripped = line.strip()
    stripped = re.sub(r"\s+", " ", stripped)
    return stripped


def duplicate_chunks(root: Path, file_records: list[dict[str, Any]], window: int, min_chars: int, top: int) -> list[dict[str, Any]]:
    chunks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in file_records:
        if not record.get("text") or not record.get("code"):
            continue
        path = root / record["path"]
        text = read_text(path)
        if not text:
            continue
        raw_lines = text.splitlines()
        if len(raw_lines) < window:
            continue
        normalized = [normalize_line(line) for line in raw_lines]
        for idx in range(0, len(normalized) - window + 1):
            block_lines = normalized[idx : idx + window]
            if not any(block_lines):
                continue
            joined = "\n".join(block_lines)
            if len(joined) < min_chars:
                continue
            digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
            chunks[digest].append(
                {
                    "path": record["path"],
                    "start_line": idx + 1,
                    "end_line": idx + window,
                    "normalized_chars": len(joined),
                    "sample": joined[:240],
                }
            )

    groups = []
    for digest, occurrences in chunks.items():
        unique_spans = {(o["path"], o["start_line"], o["end_line"]) for o in occurrences}
        unique_paths = {o["path"] for o in occurrences}
        if len(unique_spans) > 1 and len(unique_paths) > 0:
            groups.append(
                {
                    "hash": digest,
                    "occurrences": occurrences[:20],
                    "occurrence_count": len(unique_spans),
                    "path_count": len(unique_paths),
                    "score": len(unique_spans) * occurrences[0]["normalized_chars"],
                }
            )
    groups.sort(key=lambda g: (g["score"], g["occurrence_count"]), reverse=True)
    return groups[:top]


def build_audit(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    if args.include_vendor:
        exclude_dirs -= {"node_modules", "vendor", "dist", "build", "target"}
    exclude_dirs.update(args.exclude_dir)

    records = []
    for path in iter_files(root, exclude_dirs):
        record = count_file(path, root)
        if record is not None:
            records.append(record)

    text_records = [r for r in records if r["text"]]
    code_records = [r for r in records if r["code"]]

    by_suffix: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0, "lines": 0, "nonblank_lines": 0})
    for record in records:
        suffix = record["suffix"] or "<none>"
        by_suffix[suffix]["files"] += 1
        by_suffix[suffix]["bytes"] += int(record["bytes"])
        by_suffix[suffix]["lines"] += int(record["lines"])
        by_suffix[suffix]["nonblank_lines"] += int(record["nonblank_lines"])

    exact_groups: list[dict[str, Any]] = []
    hash_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in text_records:
        if record["sha256"]:
            hash_groups[record["sha256"]].append(record)
    for digest, group in hash_groups.items():
        if len(group) > 1 and group[0]["bytes"] > 0:
            group_sorted = sorted(group, key=lambda r: r["path"])
            exact_groups.append(
                {
                    "hash": digest,
                    "bytes_each": group_sorted[0]["bytes"],
                    "paths": [r["path"] for r in group_sorted],
                    "duplicate_count": len(group_sorted) - 1,
                    "potential_bytes": group_sorted[0]["bytes"] * (len(group_sorted) - 1),
                }
            )
    exact_groups.sort(key=lambda g: (g["potential_bytes"], g["duplicate_count"]), reverse=True)

    duplicate_block_groups = duplicate_chunks(
        root,
        records,
        window=max(2, args.duplicate_window),
        min_chars=max(20, args.min_duplicate_chars),
        top=args.top,
    )

    top_files = sorted(code_records, key=lambda r: (r["nonblank_lines"], r["bytes"]), reverse=True)[: args.top]
    empty_text_files = [r for r in text_records if r["bytes"] == 0 or r["nonblank_lines"] == 0]

    return {
        "repo": str(root),
        "excluded_dirs": sorted(exclude_dirs),
        "summary": {
            "files": len(records),
            "text_files": len(text_records),
            "code_files": len(code_records),
            "bytes": sum(int(r["bytes"]) for r in records),
            "text_bytes": sum(int(r["bytes"]) for r in text_records),
            "code_bytes": sum(int(r["bytes"]) for r in code_records),
            "lines": sum(int(r["lines"]) for r in records),
            "code_lines": sum(int(r["lines"]) for r in code_records),
            "code_nonblank_lines": sum(int(r["nonblank_lines"]) for r in code_records),
            "code_comment_like_lines": sum(int(r["comment_like_lines"]) for r in code_records),
        },
        "by_suffix": dict(sorted(by_suffix.items())),
        "top_code_files": top_files,
        "empty_text_files": empty_text_files[: args.top * 2],
        "exact_duplicate_files": exact_groups[: args.top],
        "duplicate_code_blocks": duplicate_block_groups,
    }


def write_markdown(audit: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    summary = audit["summary"]
    lines.append("# Code slimming audit")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Largest code files")
    lines.append("")
    for record in audit["top_code_files"]:
        lines.append(f"- `{record['path']}`: {record['nonblank_lines']} nonblank LOC, {record['bytes']} bytes")
    lines.append("")
    lines.append("## Exact duplicate files")
    lines.append("")
    for group in audit["exact_duplicate_files"]:
        keep = group["paths"][0]
        dupes = ", ".join(f"`{p}`" for p in group["paths"][1:])
        lines.append(f"- Keep candidate `{keep}`; duplicate deletion candidates: {dupes}")
    lines.append("")
    lines.append("## Duplicate code blocks")
    lines.append("")
    for group in audit["duplicate_code_blocks"]:
        occ = group["occurrences"][:5]
        rendered = ", ".join(f"`{o['path']}:{o['start_line']}-{o['end_line']}`" for o in occ)
        lines.append(f"- {group['occurrence_count']} occurrences, {group['path_count']} files: {rendered}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def candidate_records(audit: dict[str, Any], emit_duplicate_spans: bool) -> Iterable[dict[str, Any]]:
    for record in audit["empty_text_files"]:
        name = Path(record["path"]).name
        if name in PROTECTED_EMPTY_NAMES:
            continue
        yield {
            "id": f"delete-empty-file:{record['path']}",
            "type": "delete_file",
            "path": record["path"],
            "score": max(1, int(record["bytes"])),
            "group": "empty-files",
            "reason": "empty_or_blank_text_file",
        }

    for group in audit["exact_duplicate_files"]:
        keep = group["paths"][0]
        for path in group["paths"][1:]:
            yield {
                "id": f"delete-duplicate-file:{path}",
                "type": "delete_file",
                "path": path,
                "score": int(group["bytes_each"]),
                "group": "duplicate-files",
                "reason": f"byte_identical_duplicate_of:{keep}",
            }

    if emit_duplicate_spans:
        for group in audit["duplicate_code_blocks"]:
            # Keep first occurrence; propose the rest as noisy deletion candidates.
            for occurrence in group["occurrences"][1:]:
                yield {
                    "id": f"delete-duplicate-span:{occurrence['path']}:{occurrence['start_line']}-{occurrence['end_line']}",
                    "type": "delete_span",
                    "path": occurrence["path"],
                    "start_line": occurrence["start_line"],
                    "end_line": occurrence["end_line"],
                    "score": int(occurrence["normalized_chars"]),
                    "group": f"duplicate-block:{group['hash'][:12]}",
                    "reason": "normalized_duplicate_code_window_keep_first_occurrence",
                }


def main() -> int:
    args = parse_args()
    root = Path(args.repo).resolve()
    if not root.exists():
        raise SystemExit(f"Repository root does not exist: {root}")

    audit = build_audit(root, args)
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.markdown_output:
        write_markdown(audit, Path(args.markdown_output))
    if args.candidates_output:
        with Path(args.candidates_output).open("w", encoding="utf-8") as handle:
            for candidate in candidate_records(audit, args.emit_duplicate_span_candidates):
                handle.write(json.dumps(candidate, ensure_ascii=False) + "\n")

    print(json.dumps(audit["summary"], indent=2, ensure_ascii=False))
    if not args.json_output and not args.markdown_output and not args.candidates_output:
        print("Tip: add --json-output, --markdown-output, or --candidates-output for persisted results.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
