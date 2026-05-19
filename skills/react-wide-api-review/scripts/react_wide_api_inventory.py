#!/usr/bin/env python3
# Heuristic fallback tool. Prefer AST/language-server analysis when available; use this script for candidate discovery and sanity checks.
"""Fallback helper for AST-first review. Heuristic inventory scanner for wide React/TypeScript API surfaces.

This script is intentionally conservative and dependency-free. It does not replace
AST analysis. Use it to build a candidate inventory for react-wide-api-review.

It reports:
- object-like type/interface definitions with many top-level fields
- components that receive many props through file-local props types, inline object types, destructuring, or direct property reads
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
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

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


@dataclass
class TypeShape:
    name: str
    count: int
    start: int
    end: int


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


def find_matching_paren(text: str, start: int) -> int:
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
        if ch == "(":
            depth += 1
        elif ch == ")":
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


def find_top_level_char(text: str, target: str) -> int:
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
        elif ch == target and not any((depth_angle, depth_paren, depth_brace, depth_bracket)):
            return i
    return -1


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


def count_destructured_fields(body: str) -> int:
    count = 0
    for item in split_top_level(body, separators=","):
        item = item.strip()
        if not item:
            continue
        if item.startswith("..."):
            count += 1
            continue
        # Defaults and aliases still represent one top-level incoming field.
        field = item.split("=", 1)[0].strip()
        if re.match(r"^['\"][^'\"]+['\"]\s*:", field):
            count += 1
        elif re.match(r"^\[[^\]]+\]\s*:", field):
            count += 1
        elif re.match(r"^[A-Za-z_$][\w$]*\??(?:\s*:.*)?$", field):
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


def collect_type_shapes(text: str) -> List[TypeShape]:
    shapes: List[TypeShape] = []
    patterns = [
        re.compile(r"\b(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)[^{}]*\{"),
        re.compile(r"\b(?:export\s+)?type\s+([A-Za-z_$][\w$]*)\s*(?:<[^=]+>)?=\s*\{"),
    ]
    for pattern in patterns:
        for match in pattern.finditer(text):
            name = match.group(1)
            brace_start = text.find("{", match.end() - 1)
            if brace_start < 0:
                continue
            brace_end = find_matching_brace(text, brace_start)
            if brace_end < 0:
                continue
            body = text[brace_start + 1 : brace_end]
            shapes.append(TypeShape(name, count_object_fields(body), match.start(), brace_end + 1))
    return shapes


def scan_types(path: Path, text: str, warn: int, high: int, critical: int) -> List[Finding]:
    findings: List[Finding] = []
    clean = strip_comments(text)

    for shape in collect_type_shapes(clean):
        if shape.count >= warn or TYPE_SUFFIX_RE.search(shape.name):
            if shape.count >= warn:
                findings.append(
                    Finding(
                        severity_for_count(shape.count, warn, high, critical),
                        "wide-type",
                        str(path),
                        line_number(clean, shape.start),
                        shape.name,
                        shape.count,
                        f"Type/interface '{shape.name}' has {shape.count} top-level fields.",
                        snippet=clean[shape.start : min(shape.end, shape.start + 240)].replace("\n", " "),
                    )
                )
    return findings


def first_param_name(param_text: str) -> Optional[str]:
    params = split_top_level(param_text, separators=",")
    if not params:
        return None
    match = re.match(r"\s*([A-Za-z_$][\w$]*)\b", params[0])
    if not match:
        return None
    return match.group(1)


def first_param_text(param_text: str) -> str:
    params = split_top_level(param_text, separators=",")
    return params[0].strip() if params else ""


def destructured_param_count(param_text: str) -> int:
    first = first_param_text(param_text)
    if not first.startswith("{"):
        return 0
    brace_end = find_matching_brace(first, 0)
    if brace_end < 0:
        return 0
    return count_destructured_fields(first[1:brace_end])


def first_param_type_text(param_text: str) -> str:
    first = first_param_text(param_text)
    colon = find_top_level_char(first, ":")
    if colon < 0:
        return ""
    type_text = first[colon + 1 :].strip()
    default_start = find_top_level_char(type_text, "=")
    if default_start >= 0:
        type_text = type_text[:default_start].strip()
    return type_text


def inline_object_type_count(param_text: str) -> int:
    type_text = first_param_type_text(param_text)
    if not type_text:
        return 0
    obj_start = type_text.find("{")
    if obj_start < 0:
        return 0
    obj_end = find_matching_brace(type_text, obj_start)
    if obj_end < 0:
        return 0
    return count_object_fields(type_text[obj_start + 1 : obj_end])


def referenced_type_name(param_text: str) -> Optional[str]:
    type_text = first_param_type_text(param_text)
    if not type_text or type_text.startswith("{"):
        return None
    match = re.match(r"(?:readonly\s+)?([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)?)\b", type_text)
    if not match:
        return None
    name = match.group(1).split(".")[-1]
    if name in {"Readonly", "Partial", "Required", "Pick", "Omit", "PropsWithChildren"}:
        inner = re.search(r"<\s*([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)?)\b", type_text)
        if inner:
            return inner.group(1).split(".")[-1]
    return name


def declared_component_props_type(declaration_text: str) -> Optional[str]:
    match = re.search(
        r":\s*(?:React\.)?(?:FC|FunctionComponent|ComponentType|MemoExoticComponent)\s*<\s*([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)?)\b",
        declaration_text,
    )
    if not match:
        return None
    return match.group(1).split(".")[-1]


def distinct_property_reads(body: str, binding: str) -> Tuple[int, List[str]]:
    fields = set(re.findall(rf"\b{re.escape(binding)}\s*(?:\?\.|\.)\s*([A-Za-z_$][\w$]*)\b", body))
    fields.update(re.findall(rf"\b{re.escape(binding)}\s*\[\s*['\"]([^'\"]+)['\"]\s*\]", body))
    return len(fields), sorted(fields)


def arrow_params(clean: str, start: int, arrow_pos: int) -> Optional[Tuple[int, int, str]]:
    params_start = clean.rfind("(", start, arrow_pos)
    if params_start >= 0:
        params_end = find_matching_paren(clean, params_start)
        if 0 <= params_end <= arrow_pos:
            return params_start, params_end, clean[params_start + 1 : params_end]

    equal_pos = clean.rfind("=", start, arrow_pos)
    if equal_pos < 0:
        return None
    raw = clean[equal_pos + 1 : arrow_pos].strip()
    if not re.match(r"^[A-Za-z_$][\w$]*$", raw):
        return None
    param_start = clean.find(raw, equal_pos + 1, arrow_pos)
    return param_start, param_start + len(raw), raw


def arrow_body_bounds(clean: str, arrow_pos: int) -> Optional[Tuple[int, int, bool]]:
    body_start = arrow_pos + 2
    while body_start < len(clean) and clean[body_start].isspace():
        body_start += 1
    if body_start >= len(clean):
        return None
    if clean[body_start] == "{":
        body_end = find_matching_brace(clean, body_start)
        if body_end < 0:
            return None
        return body_start + 1, body_end, True

    candidates = [idx for idx in (clean.find("\n\n", body_start), clean.find(";", body_start)) if idx >= 0]
    body_end = min(candidates) if candidates else min(len(clean), body_start + 3000)
    return body_start, body_end, False


def add_component_props_finding(
    findings: List[Finding],
    path: Path,
    clean: str,
    name: str,
    count: int,
    warn: int,
    high: int,
    critical: int,
    location: int,
    source: str,
    snippet_start: int,
    snippet_end: int,
) -> None:
    if count < warn:
        return
    findings.append(
        Finding(
            severity_for_count(count, warn, high, critical),
            "wide-component-props",
            str(path),
            line_number(clean, location),
            name,
            count,
            f"Component '{name}' uses about {count} props via {source}.",
            snippet=clean[snippet_start : min(snippet_end, snippet_start + 240)].replace("\n", " "),
        )
    )


def add_destructure_findings_from_body(
    findings: List[Finding],
    path: Path,
    clean: str,
    name: str,
    body_start: int,
    body_end: int,
    binding: str,
    warn: int,
    high: int,
    critical: int,
) -> None:
    body = clean[body_start:body_end]
    pattern = re.compile(r"\b(?:const|let|var)\s*\{")
    for match in pattern.finditer(body):
        obj_start = body.find("{", match.end() - 1)
        if obj_start < 0:
            continue
        obj_end = find_matching_brace(body, obj_start)
        if obj_end < 0:
            continue
        tail = body[obj_end + 1 : obj_end + 160]
        if not re.match(rf"\s*(?::[^=]+)?=\s*{re.escape(binding)}\b", tail):
            continue
        count = count_destructured_fields(body[obj_start + 1 : obj_end])
        add_component_props_finding(
            findings,
            path,
            clean,
            name,
            count,
            warn,
            high,
            critical,
            body_start + match.start(),
            f"local destructuring from '{binding}'",
            body_start + match.start(),
            body_start + obj_end + 1,
        )


def add_property_read_finding(
    findings: List[Finding],
    path: Path,
    clean: str,
    name: str,
    body_start: int,
    body_end: int,
    binding: str,
    warn: int,
    high: int,
    critical: int,
) -> None:
    body = clean[body_start:body_end]
    count, fields = distinct_property_reads(body, binding)
    if count < warn:
        return
    first_read = re.search(rf"\b{re.escape(binding)}\s*(?:\?\.|\.|\[)", body)
    location = body_start + first_read.start() if first_read else body_start
    sample = ", ".join(fields[:8])
    if len(fields) > 8:
        sample += ", ..."
    add_component_props_finding(
        findings,
        path,
        clean,
        name,
        count,
        warn,
        high,
        critical,
        location,
        f"direct property reads on '{binding}' ({sample})",
        location,
        min(body_end, location + 240),
    )


def add_param_shape_findings(
    findings: List[Finding],
    path: Path,
    clean: str,
    name: str,
    params: str,
    type_counts: Dict[str, TypeShape],
    warn: int,
    high: int,
    critical: int,
    location: int,
    source_prefix: str,
    snippet_start: int,
    snippet_end: int,
) -> None:
    param_count = destructured_param_count(params)
    add_component_props_finding(
        findings,
        path,
        clean,
        name,
        param_count,
        warn,
        high,
        critical,
        location,
        f"{source_prefix} parameter destructuring",
        snippet_start,
        snippet_end,
    )

    inline_count = inline_object_type_count(params)
    add_component_props_finding(
        findings,
        path,
        clean,
        name,
        inline_count,
        warn,
        high,
        critical,
        location,
        f"{source_prefix} inline props type",
        snippet_start,
        snippet_end,
    )

    type_name = referenced_type_name(params)
    if not type_name:
        return
    shape = type_counts.get(type_name)
    if not shape:
        return
    add_component_props_finding(
        findings,
        path,
        clean,
        name,
        shape.count,
        warn,
        high,
        critical,
        location,
        f"file-local props type '{type_name}'",
        snippet_start,
        snippet_end,
    )


def add_declared_type_finding(
    findings: List[Finding],
    path: Path,
    clean: str,
    name: str,
    declaration_text: str,
    type_counts: Dict[str, TypeShape],
    warn: int,
    high: int,
    critical: int,
    location: int,
    snippet_start: int,
    snippet_end: int,
) -> None:
    type_name = declared_component_props_type(declaration_text)
    if not type_name:
        return
    shape = type_counts.get(type_name)
    if not shape:
        return
    add_component_props_finding(
        findings,
        path,
        clean,
        name,
        shape.count,
        warn,
        high,
        critical,
        location,
        f"component type annotation '{type_name}'",
        snippet_start,
        snippet_end,
    )


def scan_components(path: Path, text: str, warn: int, high: int, critical: int) -> List[Finding]:
    findings: List[Finding] = []
    clean = strip_comments(text)
    type_counts = {shape.name: shape for shape in collect_type_shapes(clean)}

    function_pattern = re.compile(
        r"\b(?:export\s+)?(?:default\s+)?function\s+([A-Z][A-Za-z0-9_]*)\s*(?:<[^>{}()]*>)?\s*\("
    )
    for match in function_pattern.finditer(clean):
        name = match.group(1)
        params_start = clean.find("(", match.end() - 1)
        params_end = find_matching_paren(clean, params_start)
        if params_end < 0:
            continue
        params = clean[params_start + 1 : params_end]
        add_param_shape_findings(
            findings,
            path,
            clean,
            name,
            params,
            type_counts,
            warn,
            high,
            critical,
            params_start,
            "function",
            match.start(),
            params_end + 1,
        )
        binding = first_param_name(params)
        if not binding:
            continue
        body_start = clean.find("{", params_end)
        if body_start < 0:
            continue
        body_end = find_matching_brace(clean, body_start)
        if body_end < 0:
            continue
        add_destructure_findings_from_body(
            findings,
            path,
            clean,
            name,
            body_start + 1,
            body_end,
            binding,
            warn,
            high,
            critical,
        )
        add_property_read_finding(
            findings,
            path,
            clean,
            name,
            body_start,
            body_end,
            binding,
            warn,
            high,
            critical,
        )

    arrow_pattern = re.compile(r"\b(?:export\s+)?const\s+([A-Z][A-Za-z0-9_]*)\b[^=]*=")
    for match in arrow_pattern.finditer(clean):
        name = match.group(1)
        add_declared_type_finding(
            findings,
            path,
            clean,
            name,
            clean[match.start() : match.end()],
            type_counts,
            warn,
            high,
            critical,
            match.start(),
            match.start(),
            match.end(),
        )
        search_end = clean.find("\n\n", match.end())
        if search_end < 0:
            search_end = min(len(clean), match.end() + 3000)
        arrow_pos = clean.find("=>", match.end(), search_end)
        if arrow_pos < 0:
            continue
        params_info = arrow_params(clean, match.start(), arrow_pos)
        if not params_info:
            continue
        params_start, params_end, params = params_info
        add_param_shape_findings(
            findings,
            path,
            clean,
            name,
            params,
            type_counts,
            warn,
            high,
            critical,
            params_start,
            "arrow function",
            match.start(),
            params_end + 1,
        )
        binding = first_param_name(params)
        if not binding:
            continue
        body_info = arrow_body_bounds(clean, arrow_pos)
        if not body_info:
            continue
        body_start, body_end, is_block = body_info
        if is_block:
            add_destructure_findings_from_body(
                findings,
                path,
                clean,
                name,
                body_start,
                body_end,
                binding,
                warn,
                high,
                critical,
            )
        add_property_read_finding(
            findings,
            path,
            clean,
            name,
            body_start,
            body_end,
            binding,
            warn,
            high,
            critical,
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
    findings.extend(
        scan_components(
            path,
            text,
            args.component_props_warn,
            args.component_props_high,
            args.component_props_critical,
        )
    )
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
    parser.add_argument("--component-props-warn", type=int, default=12)
    parser.add_argument("--component-props-high", type=int, default=24)
    parser.add_argument("--component-props-critical", type=int, default=40)
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
