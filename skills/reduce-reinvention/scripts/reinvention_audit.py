#!/usr/bin/env python3
"""Scan a repository for duplicate-code and reinvention signals.

This is a heuristic helper: treat its output as candidates for human/agent review,
not as proof that consolidation is correct.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".kt", ".kts", ".cs",
    ".rb", ".php", ".rs", ".swift", ".cpp", ".cc", ".c", ".h", ".hpp", ".m", ".mm",
    ".scala", ".sh", ".bash", ".zsh", ".ps1", ".sql", ".yaml", ".yml", ".json",
    ".toml", ".xml", ".md", ".mdx", ".css", ".scss", ".html", ".vue", ".svelte",
}

DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", "dist", "build", "target", "coverage",
    ".venv", "venv", "env", "__pycache__", ".mypy_cache", ".pytest_cache", ".next", ".nuxt",
    ".terraform", ".gradle", ".idea", ".vscode", "tmp", "temp",
}

COMMON_SYMBOLS = {
    "main", "init", "setup", "index", "handler", "run", "start", "stop", "get", "set", "test",
    "create", "update", "delete", "list", "render", "component",
}

SYMBOL_PATTERNS: Sequence[Tuple[str, Sequence[str], re.Pattern[str]]] = [
    ("function", [".py"], re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)),
    ("class", [".py"], re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*[(:]", re.M)),
    ("function", [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"], re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", re.M)),
    ("function", [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"], re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^=]*\)|[A-Za-z_$][\w$]*)\s*=>", re.M)),
    ("class", [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"], re.compile(r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)", re.M)),
    ("interface", [".ts", ".tsx"], re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)", re.M)),
    ("type", [".ts", ".tsx"], re.compile(r"^\s*(?:export\s+)?type\s+([A-Za-z_$][\w$]*)\s*=", re.M)),
    ("function", [".go"], re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)),
    ("type", [".go"], re.compile(r"^\s*type\s+([A-Za-z_][A-Za-z0-9_]*)\s+(?:struct|interface)", re.M)),
    ("class", [".java", ".kt", ".kts", ".cs", ".scala"], re.compile(r"^\s*(?:public\s+|private\s+|protected\s+|internal\s+|abstract\s+|final\s+|data\s+|sealed\s+)*class\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)),
    ("function", [".java", ".kt", ".kts", ".cs", ".scala"], re.compile(r"^\s*(?:public|private|protected|internal|static|final|override|suspend|async|virtual|def|fun)\s+[\w<>?,\s\[\]]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)),
    ("function", [".rs"], re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)),
    ("type", [".rs"], re.compile(r"^\s*(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)),
]

SIGNAL_RE = re.compile(
    r"duplicate|duplicated|copy|copied|forked|clone|same as|borrowed from|ported from|"
    r"TODO[^\n]*(?:reuse|dedupe|shared)|FIXME[^\n]*(?:duplicate|dedupe)|"
    r"重复|复制|拷贝|复用|轮子|造轮子",
    re.I,
)

STRING_RE = re.compile(r"(?<!\\)(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)")
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace(os.sep, "/")


def is_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return True
    return b"\0" in chunk


def iter_files(root: Path, max_file_bytes: int, include_all_text: bool) -> Iterable[Path]:
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDE_DIRS and not d.endswith(".egg-info")]
        for filename in filenames:
            path = Path(current) / filename
            try:
                if path.stat().st_size > max_file_bytes:
                    continue
            except OSError:
                continue
            if not include_all_text and path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            if is_binary(path):
                continue
            yield path


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def normalized_exact(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line.strip()) for line in text.replace("\r\n", "\n").splitlines()]
    return "\n".join(line for line in lines if line)


def normalized_similarity_lines(text: str) -> List[str]:
    lines: List[str] = []
    for raw in text.replace("\r\n", "\n").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("//", "#", "--", "*", "/*", "*/")):
            continue
        line = STRING_RE.sub('"STR"', line)
        line = NUMBER_RE.sub("NUM", line)
        line = re.sub(r"\s+", " ", line).lower()
        if line:
            lines.append(line)
    return lines


def make_shingles(lines: Sequence[str], width: int) -> Set[str]:
    if len(lines) < width:
        return set()
    output: Set[str] = set()
    for i in range(0, len(lines) - width + 1):
        joined = "\n".join(lines[i : i + width])
        output.add(hashlib.sha1(joined.encode("utf-8")).hexdigest())
    return output


def line_number_for_match(text: str, start: int) -> int:
    return text.count("\n", 0, start) + 1


def extract_symbols(text: str, suffix: str) -> List[Dict[str, object]]:
    found: List[Dict[str, object]] = []
    suffix = suffix.lower()
    for kind, suffixes, pattern in SYMBOL_PATTERNS:
        if suffix not in suffixes:
            continue
        for match in pattern.finditer(text):
            name = match.group(1)
            key = name.lower()
            if len(key) < 4 or key in COMMON_SYMBOLS:
                continue
            found.append({"kind": kind, "name": name, "line": line_number_for_match(text, match.start())})
    return found


def collect(root: Path, args: argparse.Namespace) -> Dict[str, object]:
    files = list(iter_files(root, args.max_file_bytes, args.include_all_text))
    file_infos: List[Dict[str, object]] = []
    exact_groups: Dict[str, List[str]] = defaultdict(list)
    shingle_index: Dict[str, List[int]] = defaultdict(list)
    symbol_index: Dict[Tuple[str, str], List[Dict[str, object]]] = defaultdict(list)
    signals: List[Dict[str, object]] = []

    for idx, path in enumerate(files):
        text = read_text(path)
        rel_path = rel(path, root)
        exact = normalized_exact(text)
        exact_hash = hashlib.sha256(exact.encode("utf-8")).hexdigest() if exact else ""
        lines = normalized_similarity_lines(text)
        shingles = make_shingles(lines, args.shingle_width) if len(lines) >= args.min_lines else set()
        exact_line_count = len(exact.splitlines()) if exact else 0
        if exact and exact_line_count >= args.min_exact_lines:
            exact_groups[exact_hash].append(rel_path)
        for shingle in shingles:
            shingle_index[shingle].append(idx)
        for sym in extract_symbols(text, path.suffix):
            symbol_index[(str(sym["kind"]), str(sym["name"]).lower())].append(
                {"name": sym["name"], "kind": sym["kind"], "path": rel_path, "line": sym["line"]}
            )
        for line_no, line in enumerate(text.splitlines(), start=1):
            if SIGNAL_RE.search(line):
                signals.append({"path": rel_path, "line": line_no, "text": line.strip()[:220]})
                if len(signals) >= args.max_signals:
                    break
        file_infos.append({
            "path": rel_path,
            "line_count": len(lines),
            "exact_hash": exact_hash,
            "shingles": shingles,
        })

    exact_duplicates = [
        {"paths": sorted(paths), "count": len(paths)}
        for _, paths in sorted(exact_groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        if len(paths) > 1
    ]

    pair_counts: Counter[Tuple[int, int]] = Counter()
    for ids in shingle_index.values():
        if len(ids) < 2 or len(ids) > args.max_shingle_fanout:
            continue
        ids = sorted(set(ids))
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                pair_counts[(a, b)] += 1

    similar_pairs: List[Dict[str, object]] = []
    for (a, b), shared in pair_counts.most_common(args.max_pairs_to_score):
        shingles_a = file_infos[a]["shingles"]
        shingles_b = file_infos[b]["shingles"]
        if not isinstance(shingles_a, set) or not isinstance(shingles_b, set):
            continue
        union = len(shingles_a | shingles_b)
        if union == 0:
            continue
        similarity = shared / union
        if similarity >= args.similarity_threshold:
            similar_pairs.append({
                "path_a": file_infos[a]["path"],
                "path_b": file_infos[b]["path"],
                "similarity": round(similarity, 3),
                "shared_shingles": shared,
                "lines_a": file_infos[a]["line_count"],
                "lines_b": file_infos[b]["line_count"],
            })
            if len(similar_pairs) >= args.max_similar_pairs:
                break

    duplicate_symbols = []
    for (kind, name), occs in sorted(symbol_index.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        distinct_paths = sorted({str(o["path"]) for o in occs})
        if len(distinct_paths) >= args.min_symbol_paths:
            display = str(occs[0]["name"])
            duplicate_symbols.append({
                "kind": kind,
                "name": display,
                "paths": distinct_paths,
                "occurrences": sorted(occs, key=lambda o: (str(o["path"]), int(o["line"]))),
            })
            if len(duplicate_symbols) >= args.max_duplicate_symbols:
                break

    return {
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(root),
        "files_scanned": len(files),
        "settings": {
            "min_lines": args.min_lines,
            "min_exact_lines": args.min_exact_lines,
            "shingle_width": args.shingle_width,
            "similarity_threshold": args.similarity_threshold,
        },
        "exact_duplicate_files": exact_duplicates[: args.max_exact_groups],
        "near_duplicate_files": similar_pairs,
        "duplicate_symbols": duplicate_symbols,
        "reinvention_signals": signals[: args.max_signals],
        "summary": {
            "exact_duplicate_groups": len(exact_duplicates),
            "near_duplicate_pairs": len(similar_pairs),
            "duplicate_symbol_names": len(duplicate_symbols),
            "reinvention_signal_lines": len(signals[: args.max_signals]),
        },
    }


def md_table(rows: Sequence[Sequence[object]], headers: Sequence[str]) -> str:
    if not rows:
        return ""
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(cell).replace("\n", " ").replace("|", "\\|") for cell in row) + " |")
    return "\n".join(out)


def render_markdown(report: Dict[str, object]) -> str:
    summary = report["summary"]
    settings = report["settings"]
    lines = [
        "# Reinvention Audit Report",
        "",
        f"Generated UTC: {report['generated_at_utc']}",
        f"Root: `{report['root']}`",
        f"Files scanned: {report['files_scanned']}",
        f"Settings: min_lines={settings['min_lines']}, min_exact_lines={settings['min_exact_lines']}, shingle_width={settings['shingle_width']}, similarity_threshold={settings['similarity_threshold']}",
        "",
        "## Summary",
        "",
        md_table([
            ["Exact duplicate file groups", summary["exact_duplicate_groups"]],
            ["Near duplicate file pairs", summary["near_duplicate_pairs"]],
            ["Duplicate symbol names", summary["duplicate_symbol_names"]],
            ["Reinvention signal lines", summary["reinvention_signal_lines"]],
        ], ["Metric", "Value"]),
        "",
        "## Exact duplicate file groups",
        "",
    ]

    exact = report["exact_duplicate_files"]
    if exact:
        rows = [[i + 1, item["count"], "<br>".join(f"`{p}`" for p in item["paths"])] for i, item in enumerate(exact)]
        lines.append(md_table(rows, ["#", "Files", "Paths"]))
    else:
        lines.append("No exact duplicate file groups found with current thresholds.")

    lines += ["", "## Near duplicate file pairs", ""]
    near = report["near_duplicate_files"]
    if near:
        rows = [
            [i + 1, f"{item['similarity']:.3f}", f"`{item['path_a']}`", f"`{item['path_b']}`", item["shared_shingles"]]
            for i, item in enumerate(near)
        ]
        lines.append(md_table(rows, ["#", "Similarity", "Path A", "Path B", "Shared shingles"]))
    else:
        lines.append("No near duplicate file pairs found with current thresholds.")

    lines += ["", "## Duplicate symbol names", ""]
    syms = report["duplicate_symbols"]
    if syms:
        rows = []
        for item in syms:
            locations = ", ".join(f"`{o['path']}:{o['line']}`" for o in item["occurrences"][:8])
            if len(item["occurrences"]) > 8:
                locations += f", +{len(item['occurrences']) - 8} more"
            rows.append([item["kind"], item["name"], len(item["paths"]), locations])
        lines.append(md_table(rows, ["Kind", "Name", "Distinct paths", "Locations"]))
    else:
        lines.append("No duplicate symbol names found with current thresholds.")

    lines += ["", "## Reinvention signal lines", ""]
    sigs = report["reinvention_signals"]
    if sigs:
        rows = [[f"`{s['path']}:{s['line']}`", s["text"]] for s in sigs]
        lines.append(md_table(rows, ["Location", "Text"]))
    else:
        lines.append("No copy/fork/reuse signal lines found.")

    lines += [
        "",
        "## Review notes",
        "",
        "- Treat each item as a candidate. Confirm same domain semantics, change cadence, ownership, and consumers before consolidating.",
        "- Generated/vendor/test-fixture files can create false positives; exclude them or classify as justified.",
        "- For high-impact candidates, create an ADR/RFC with alternatives and migration plan.",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan a repo for duplicate-code and reinvention signals.")
    parser.add_argument("path", help="Repository or directory path to scan")
    parser.add_argument("--output", "-o", help="Write report to this path; defaults to stdout")
    parser.add_argument("--format", choices=["md", "json"], default="md", help="Output format")
    parser.add_argument("--include-all-text", action="store_true", help="Scan any non-binary text file, not just known extensions")
    parser.add_argument("--max-file-bytes", type=int, default=1_000_000, help="Skip files larger than this")
    parser.add_argument("--min-lines", type=int, default=12, help="Minimum normalized lines for near-clone analysis")
    parser.add_argument("--min-exact-lines", type=int, default=6, help="Minimum normalized lines for exact duplicate file groups")
    parser.add_argument("--shingle-width", type=int, default=5, help="Number of normalized lines per shingle")
    parser.add_argument("--similarity-threshold", type=float, default=0.82, help="Jaccard threshold for near duplicates")
    parser.add_argument("--min-symbol-paths", type=int, default=2, help="Minimum paths sharing a symbol name")
    parser.add_argument("--max-exact-groups", type=int, default=50)
    parser.add_argument("--max-similar-pairs", type=int, default=100)
    parser.add_argument("--max-duplicate-symbols", type=int, default=100)
    parser.add_argument("--max-signals", type=int, default=200)
    parser.add_argument("--max-shingle-fanout", type=int, default=200, help="Ignore very common shingles above this fanout")
    parser.add_argument("--max-pairs-to-score", type=int, default=50000, help="Cap candidate pair scoring for large repos")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.path).resolve()
    if not root.exists() or not root.is_dir():
        print(f"[ERROR] path is not a directory: {root}", file=sys.stderr)
        return 2
    if args.shingle_width < 2:
        print("[ERROR] --shingle-width must be >= 2", file=sys.stderr)
        return 2
    report = collect(root, args)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else render_markdown(report)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
