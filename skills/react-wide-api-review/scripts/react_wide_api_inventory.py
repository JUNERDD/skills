#!/usr/bin/env python3
# Heuristic fallback tool. Prefer AST/language-server analysis when available; use this script for candidate discovery and sanity checks.
"""Fallback helper for AST-first review. Heuristic inventory scanner for wide React/TypeScript API surfaces.

This script is intentionally conservative and dependency-free. It does not replace
AST analysis. Use it to build a candidate inventory for react-wide-api-review.

It reports:
- object-like type/interface definitions with many top-level fields
- JSX tags with many attributes or spreads
- custom hooks with many positional parameters
- custom hooks returning large flat object literals
- createContext/provider inline values with many fields

Output formats: markdown (default) or json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

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
TYPE_SUFFIX_RE = re.compile(
    r"(Props|Options|Params|Config|Return|Result|State|Value|Context|Model|ViewModel|Controller|Actions|Callbacks)$"
)


@dataclass
class Finding:
    severity: str
    kind: str
    file: str
    line: int
    name: str
    count: int
    message: str
    snippet: str = ""


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


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def strip_comments(text: str) -> str:
    # Keep line count approximately stable.
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    text = re.sub(r"//.*", "", text)
    return text


def find_matching_brace(text: str, start: int) -> int:
    depth = 0
    quote: Optional[str] = None
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def split_top_level(text: str, separators: str = ",;\n") -> List[str]:
    items: List[str] = []
    start = 0
    depth_angle = depth_paren = depth_brace = depth_bracket = 0
    quote: Optional[str] = None
    escape = False
    for i, ch in enumerate(text):
        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            continue
        if ch == "<":
            depth_angle += 1
        elif ch == ">" and depth_angle > 0:
            depth_angle -= 1
        elif ch == "(":
            depth_paren += 1
        elif ch == ")" and depth_paren > 0:
            depth_paren -= 1
        elif ch == "{":
            depth_brace += 1
        elif ch == "}" and depth_brace > 0:
            depth_brace -= 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]" and depth_bracket > 0:
            depth_bracket -= 1
        elif ch in separators and not any((depth_angle, depth_paren, depth_brace, depth_bracket)):
            item = text[start:i].strip()
            if item:
                items.append(item)
            start = i + 1
    tail = text[start:].strip()
    if tail:
        items.append(tail)
    return items


def count_object_fields(body: str) -> int:
    count = 0
    for item in split_top_level(body):
        item = item.strip()
        if not item:
            continue
        if item.startswith(("//", "/*", "*")):
            continue
        # index signatures and methods count as fields because they affect the API surface.
        if re.match(r"^(readonly\s+)?[A-Za-z_$][\w$]*\??\s*[:(<]", item):
            count += 1
        elif re.match(r"^['\"][^'\"]+['\"]\??\s*:", item):
            count += 1
        elif re.match(r"^\[[^\]]+\]\s*:", item):
            count += 1
        elif re.match(r"^[A-Za-z_$][\w$]*$", item):
            # Shorthand object literal member, common in hook returns/provider values.
            count += 1
    return count


def severity_for_count(count: int, warn: int, high: int, critical: int) -> str:
    if count >= critical:
        return "critical"
    if count >= high:
        return "high"
    if count >= warn:
        return "medium"
    return "low"


def scan_types(path: Path, text: str, warn: int, high: int, critical: int) -> List[Finding]:
    findings: List[Finding] = []
    clean = strip_comments(text)

    patterns = [
        re.compile(r"\b(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)[^{}]*\{"),
        re.compile(r"\b(?:export\s+)?type\s+([A-Za-z_$][\w$]*)\s*(?:<[^=]+>)?=\s*\{"),
    ]
    for pattern in patterns:
        for match in pattern.finditer(clean):
            name = match.group(1)
            brace_start = clean.find("{", match.end() - 1)
            if brace_start < 0:
                continue
            brace_end = find_matching_brace(clean, brace_start)
            if brace_end < 0:
                continue
            body = clean[brace_start + 1 : brace_end]
            count = count_object_fields(body)
            if count >= warn or TYPE_SUFFIX_RE.search(name):
                if count >= warn:
                    findings.append(
                        Finding(
                            severity_for_count(count, warn, high, critical),
                            "wide-type",
                            str(path),
                            line_number(clean, match.start()),
                            name,
                            count,
                            f"Type/interface '{name}' has {count} top-level fields.",
                            snippet=clean[match.start() : min(brace_end + 1, match.start() + 240)].replace("\n", " "),
                        )
                    )
    return findings


def count_jsx_attrs(attr_text: str) -> int:
    # Counts named attrs and spreads. Intentionally heuristic.
    attr_text = re.sub(r"\s+", " ", attr_text.strip())
    if not attr_text:
        return 0
    count = len(re.findall(r"(?:^|\s)([A-Za-z_$][\w$:-]*)\s*(?:=|(?=\s|$))", attr_text))
    count += len(re.findall(r"\{\s*\.\.\.", attr_text))
    return count


def scan_jsx(path: Path, text: str, warn: int, high: int, critical: int) -> List[Finding]:
    findings: List[Finding] = []
    if path.suffix not in {".tsx", ".jsx"}:
        return findings
    clean = strip_comments(text)
    pattern = re.compile(r"<([A-Z][A-Za-z0-9_.$]*)\b([^<>]*?)(?:/?>)", re.S)
    for match in pattern.finditer(clean):
        name = match.group(1)
        attrs = match.group(2)
        count = count_jsx_attrs(attrs)
        if count >= warn:
            spread_count = len(re.findall(r"\{\s*\.\.\.", attrs))
            extra = f" Includes {spread_count} spread(s)." if spread_count else ""
            findings.append(
                Finding(
                    severity_for_count(count, warn, high, critical),
                    "wide-jsx-call",
                    str(path),
                    line_number(clean, match.start()),
                    name,
                    count,
                    f"JSX call '<{name}>' passes about {count} attributes/spreads.{extra}",
                    snippet=clean[match.start() : min(match.end(), match.start() + 240)].replace("\n", " "),
                )
            )
    return findings


def count_params(param_text: str) -> int:
    if not param_text.strip():
        return 0
    return len(split_top_level(param_text, separators=","))


def add_hook_return_findings(
    findings: List[Finding],
    path: Path,
    clean: str,
    name: str,
    obj_start: int,
    obj_end: int,
    warn_return: int,
    snippet_start: int,
) -> None:
    obj_body = clean[obj_start + 1 : obj_end]
    count = count_object_fields(obj_body)
    if count < warn_return:
        return
    findings.append(
        Finding(
            severity_for_count(count, warn_return, warn_return + 5, warn_return + 15),
            "wide-hook-return",
            str(path),
            line_number(clean, snippet_start),
            name,
            count,
            f"Hook '{name}' returns a flat object with about {count} top-level fields.",
            snippet=clean[snippet_start : min(obj_end + 1, snippet_start + 240)].replace("\n", " "),
        )
    )


def scan_hooks(path: Path, text: str, warn_params: int, warn_return: int) -> List[Finding]:
    findings: List[Finding] = []
    clean = strip_comments(text)
    hook_patterns = [
        re.compile(r"\bfunction\s+(use[A-Z][A-Za-z0-9_]*)\s*\(([^)]*)\)"),
        re.compile(r"\bconst\s+(use[A-Z][A-Za-z0-9_]*)\s*=\s*(?:<[^>]+>\s*)?\(([^)]*)\)\s*=>"),
    ]
    for pattern in hook_patterns:
        for match in pattern.finditer(clean):
            name = match.group(1)
            count = count_params(match.group(2))
            if count >= warn_params:
                findings.append(
                    Finding(
                        severity_for_count(count, warn_params, warn_params + 3, warn_params + 6),
                        "wide-hook-params",
                        str(path),
                        line_number(clean, match.start()),
                        name,
                        count,
                        f"Hook '{name}' has {count} positional parameters.",
                        snippet=clean[match.start() : min(match.end(), match.start() + 200)].replace("\n", " "),
                    )
                )

    # Function hook return object literal: return { a, b, c }
    for match in re.finditer(r"\bfunction\s+(use[A-Z][A-Za-z0-9_]*)\b", clean):
        name = match.group(1)
        body_start = clean.find("{", match.end())
        if body_start < 0:
            continue
        body_end = find_matching_brace(clean, body_start)
        if body_end < 0:
            continue
        body = clean[body_start + 1 : body_end]
        for ret in re.finditer(r"\breturn\s*\{", body):
            obj_start = body.find("{", ret.start())
            obj_end = find_matching_brace(body, obj_start)
            if obj_end < 0:
                continue
            add_hook_return_findings(
                findings,
                path,
                clean,
                name,
                body_start + 1 + obj_start,
                body_start + 1 + obj_end,
                warn_return,
                body_start + 1 + ret.start(),
            )

    # Arrow hook block body: const useX = () => { return { a, b, c } }
    arrow_block_pattern = re.compile(
        r"\bconst\s+(use[A-Z][A-Za-z0-9_]*)\s*=\s*(?:<[^>]+>\s*)?\([^)]*\)\s*=>\s*\{"
    )
    for match in arrow_block_pattern.finditer(clean):
        name = match.group(1)
        body_start = clean.find("{", match.end() - 1)
        if body_start < 0:
            continue
        body_end = find_matching_brace(clean, body_start)
        if body_end < 0:
            continue
        body = clean[body_start + 1 : body_end]
        for ret in re.finditer(r"\breturn\s*\{", body):
            obj_start = body.find("{", ret.start())
            obj_end = find_matching_brace(body, obj_start)
            if obj_end < 0:
                continue
            add_hook_return_findings(
                findings,
                path,
                clean,
                name,
                body_start + 1 + obj_start,
                body_start + 1 + obj_end,
                warn_return,
                body_start + 1 + ret.start(),
            )

    # Arrow hook concise body: const useX = () => ({ a, b, c })
    arrow_object_pattern = re.compile(
        r"\bconst\s+(use[A-Z][A-Za-z0-9_]*)\s*=\s*(?:<[^>]+>\s*)?\([^)]*\)\s*=>\s*\(\s*\{"
    )
    for match in arrow_object_pattern.finditer(clean):
        name = match.group(1)
        obj_start = clean.rfind("{", 0, match.end())
        if obj_start < 0:
            continue
        obj_end = find_matching_brace(clean, obj_start)
        if obj_end < 0:
            continue
        add_hook_return_findings(
            findings,
            path,
            clean,
            name,
            obj_start,
            obj_end,
            warn_return,
            match.start(),
        )
    return findings


def scan_context(path: Path, text: str, warn: int) -> List[Finding]:
    findings: List[Finding] = []
    clean = strip_comments(text)

    for match in re.finditer(r"\bcreateContext\s*(?:<[^>]+>)?\s*\(\s*\{", clean):
        obj_start = clean.rfind("{", 0, match.end())
        obj_end = find_matching_brace(clean, obj_start)
        if obj_end < 0:
            continue
        count = count_object_fields(clean[obj_start + 1 : obj_end])
        if count >= warn:
            findings.append(
                Finding(
                    severity_for_count(count, warn, warn + 5, warn + 15),
                    "wide-create-context",
                    str(path),
                    line_number(clean, match.start()),
                    "createContext",
                    count,
                    f"createContext default value has about {count} fields.",
                    snippet=clean[match.start() : min(obj_end + 1, match.start() + 240)].replace("\n", " "),
                )
            )

    provider_pattern = re.compile(r"<([A-Za-z0-9_.$]*Provider)\b[^>]*\bvalue\s*=\s*\{\s*\{", re.S)
    for match in provider_pattern.finditer(clean):
        name = match.group(1)
        obj_start = clean.rfind("{", 0, match.end())
        obj_end = find_matching_brace(clean, obj_start)
        if obj_end < 0:
            continue
        count = count_object_fields(clean[obj_start + 1 : obj_end])
        if count >= warn:
            findings.append(
                Finding(
                    severity_for_count(count, warn, warn + 5, warn + 15),
                    "wide-provider-value",
                    str(path),
                    line_number(clean, match.start()),
                    name,
                    count,
                    f"Provider '{name}' has an inline value object with about {count} fields.",
                    snippet=clean[match.start() : min(obj_end + 1, match.start() + 240)].replace("\n", " "),
                )
            )
    return findings


def scan_file(path: Path, args: argparse.Namespace) -> List[Finding]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        print(f"warning: could not read {path}: {exc}", file=sys.stderr)
        return []
    findings: List[Finding] = []
    findings.extend(scan_types(path, text, args.type_warn, args.type_high, args.type_critical))
    findings.extend(scan_jsx(path, text, args.jsx_warn, args.jsx_high, args.jsx_critical))
    findings.extend(scan_hooks(path, text, args.hook_params_warn, args.hook_return_warn))
    findings.extend(scan_context(path, text, args.context_warn))
    return findings


def to_markdown(findings: Sequence[Finding]) -> str:
    lines = ["# React Wide API Inventory", ""]
    if not findings:
        lines.append("No wide API candidates found with the current thresholds.")
        return "\n".join(lines) + "\n"
    lines.append(f"Found {len(findings)} candidate(s).")
    lines.append("")
    lines.append("| Severity | Kind | File:Line | Name | Count | Message |")
    lines.append("| --- | --- | --- | --- | ---: | --- |")
    for f in findings:
        file_line = f"{f.file}:{f.line}"
        msg = f.message.replace("|", "\\|")
        lines.append(f"| {f.severity} | {f.kind} | {file_line} | {f.name} | {f.count} | {msg} |")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("This inventory is heuristic. Use it to choose recursive review entry points, then inspect field flow manually or with `react_wide_api_trace.py`.")
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Project root, source directory, or individual source file")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--type-warn", type=int, default=12)
    parser.add_argument("--type-high", type=int, default=24)
    parser.add_argument("--type-critical", type=int, default=40)
    parser.add_argument("--jsx-warn", type=int, default=10)
    parser.add_argument("--jsx-high", type=int, default=18)
    parser.add_argument("--jsx-critical", type=int, default=30)
    parser.add_argument("--hook-params-warn", type=int, default=5)
    parser.add_argument("--hook-return-warn", type=int, default=10)
    parser.add_argument("--context-warn", type=int, default=8)
    args = parser.parse_args(argv)

    root = Path(args.root)
    findings: List[Finding] = []
    for path in iter_source_files(root):
        findings.extend(scan_file(path, args))
    findings.sort(key=lambda f: (f.file, f.line, f.kind, f.name))

    if args.format == "json":
        print(json.dumps([asdict(f) for f in findings], indent=2, ensure_ascii=False))
    else:
        print(to_markdown(findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
