#!/usr/bin/env python3
# Heuristic fallback tool. Prefer AST/language-server analysis when available; use this script for candidate discovery and sanity checks.
"""Fallback helper for AST-first review. Heuristic reference tracer for React wide API review.

The tracer searches a React/TypeScript tree for symbol and field-flow clues. It
is not a TypeScript AST engine; it is meant to support recursive review by
collecting locations that deserve manual inspection.

Examples:
  python react_wide_api_trace.py ./src --symbol UserEditorProps --symbol UserEditor
  python react_wide_api_trace.py ./src --symbol useUserEditor --field form --field actions
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Sequence

SKIP_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    "out",
    "vendor",
    ".turbo",
    ".cache",
}
EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}


@dataclass
class Hit:
    kind: str
    file: str
    line: int
    symbol: str
    field: str
    text: str


def iter_source_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        if root.suffix in EXTENSIONS:
            yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix in EXTENSIONS:
                yield path


def classify_line(line: str, symbol: str, fields: Sequence[str]) -> Optional[Hit]:
    stripped = line.strip()
    if not stripped:
        return None

    field = ""
    kind = "reference"

    if re.search(rf"\b(type|interface)\s+{re.escape(symbol)}\b", stripped):
        kind = "type-definition"
    elif re.search(rf"\bfunction\s+{re.escape(symbol)}\b", stripped) or re.search(rf"\bconst\s+{re.escape(symbol)}\s*=", stripped):
        kind = "function-or-component-definition"
    elif re.search(rf"<{re.escape(symbol)}\b", stripped):
        kind = "jsx-call"
    elif re.search(rf"\b{re.escape(symbol)}\s*\(", stripped):
        kind = "function-or-hook-call"
    elif re.search(r"\{\s*\.\.\.", stripped):
        kind = "spread-propagation"
    elif "useContext" in stripped:
        kind = "context-read"
    elif re.search(r"\.Provider\b", stripped) and "value" in stripped:
        kind = "context-provider"
    elif re.search(r"useEffect|useMemo|useCallback", stripped):
        kind = "effect-or-memo-bound"
    elif re.search(r"const\s*\{[^}]+\}\s*=", stripped):
        kind = "destructure"

    for f in fields:
        if re.search(rf"\b{re.escape(f)}\b", stripped):
            field = f
            if re.search(rf"\.{re.escape(f)}\b", stripped):
                kind = "field-access"
            elif re.search(rf"\{{[^}}]*\b{re.escape(f)}\b[^}}]*\}}\s*=", stripped):
                kind = "field-destructure"
            break

    if symbol and not re.search(rf"\b{re.escape(symbol)}\b|<{re.escape(symbol)}\b", stripped):
        if not field:
            return None
    return Hit(kind=kind, file="", line=0, symbol=symbol, field=field, text=stripped[:260])


def scan_file(path: Path, symbols: Sequence[str], fields: Sequence[str]) -> List[Hit]:
    hits: List[Hit] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return hits
    for idx, line in enumerate(lines, start=1):
        for symbol in symbols or [""]:
            hit = classify_line(line, symbol, fields)
            if hit:
                hit.file = str(path)
                hit.line = idx
                hits.append(hit)
                break
    return hits


def to_markdown(hits: Sequence[Hit]) -> str:
    lines = ["# React Wide API Trace", ""]
    if not hits:
        lines.append("No references found for the supplied symbols/fields.")
        return "\n".join(lines) + "\n"

    lines.append(f"Found {len(hits)} reference hit(s).")
    lines.append("")
    lines.append("| Kind | File:Line | Symbol | Field | Text |")
    lines.append("| --- | --- | --- | --- | --- |")
    for h in hits:
        text = h.text.replace("|", "\\|")
        lines.append(f"| {h.kind} | {h.file}:{h.line} | {h.symbol} | {h.field} | `{text}` |")

    lines.append("")
    lines.append("## Review usage")
    lines.append("")
    lines.append("Use these hits to build the recursive boundary graph. Pay special attention to `spread-propagation`, `context-provider`, `context-read`, `effect-or-memo-bound`, and `field-access` rows.")
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Project root, source directory, or source file")
    parser.add_argument("--symbol", action="append", default=[], help="Component, hook, type, context, or variable name to trace. Repeatable.")
    parser.add_argument("--field", action="append", default=[], help="Field name to trace. Repeatable.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)

    root = Path(args.root)
    hits: List[Hit] = []
    for path in iter_source_files(root):
        hits.extend(scan_file(path, args.symbol, args.field))
    hits.sort(key=lambda h: (h.file, h.line, h.kind, h.symbol, h.field))

    if args.format == "json":
        print(json.dumps([asdict(h) for h in hits], indent=2, ensure_ascii=False))
    else:
        print(to_markdown(hits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
