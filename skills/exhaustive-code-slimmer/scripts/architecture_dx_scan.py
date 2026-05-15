#!/usr/bin/env python3
"""Heuristic DX architecture scan for code-slimming work.

This script does not decide architecture quality on its own. It surfaces signals
that often block effective slimming: cycles, god files, deep paths, pass-through
layer naming, config sprawl, and ownership ambiguity. Use the report to decide
whether to continue deletion-first or pause for user approval of architecture
options.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
from collections import Counter, defaultdict
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
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".kts",
    ".rb",
    ".php",
    ".cs",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".swift",
    ".scala",
}

LOCAL_JS_IMPORT_RE = re.compile(
    r"(?:import\s+(?:[^'\"]+?\s+from\s+)?|export\s+[^'\"]*?\s+from\s+|require\s*\()"
    r"['\"](?P<spec>\.{1,2}/[^'\"]+)['\"]"
)
LAYER_WORDS = {
    "adapter",
    "adapters",
    "base",
    "common",
    "commons",
    "core",
    "factory",
    "factories",
    "helper",
    "helpers",
    "infra",
    "infrastructure",
    "manager",
    "managers",
    "misc",
    "repository",
    "repositories",
    "service",
    "services",
    "shared",
    "util",
    "utils",
}
CONFIG_NAME_RE = re.compile(r"(^|[._-])(config|settings|env|environment|flags?|feature[-_]?flags?)([._-]|$)", re.I)
BARREL_EXPORT_RE = re.compile(r"^\s*export\s+(?:\*|\{)", re.M)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan architecture/DX signals relevant to code slimming.")
    parser.add_argument("--repo", default=".", help="Repository root to scan.")
    parser.add_argument("--json-output", help="Write full scan JSON to this path.")
    parser.add_argument("--markdown-output", help="Write human-readable Markdown report to this path.")
    parser.add_argument("--exclude-dir", action="append", default=[], help="Additional directory name to exclude; repeatable.")
    parser.add_argument("--large-file-loc", type=int, default=800, help="Nonblank LOC threshold for god-file signal.")
    parser.add_argument("--deep-path-depth", type=int, default=6, help="Path depth threshold for deep-path signal.")
    parser.add_argument("--max-cycles", type=int, default=25, help="Maximum import cycles to report.")
    return parser.parse_args()


def safe_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
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


def line_metrics(text: str) -> tuple[int, int]:
    lines = text.splitlines()
    nonblank = sum(1 for line in lines if line.strip())
    return len(lines), nonblank


def module_name_for_py(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def build_python_module_index(files: list[Path], root: Path) -> dict[str, str]:
    index: dict[str, str] = {}
    for path in files:
        if path.suffix == ".py":
            module = module_name_for_py(path, root)
            if module:
                index[module] = safe_rel(path, root)
    return index


def resolve_python_import(module_index: dict[str, str], module: str | None) -> str | None:
    if not module:
        return None
    parts = module.split(".")
    for end in range(len(parts), 0, -1):
        candidate = ".".join(parts[:end])
        if candidate in module_index:
            return module_index[candidate]
    return None


def package_for_file(path: Path, root: Path) -> list[str]:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] != "__init__":
        parts = parts[:-1]
    else:
        parts = parts[:-1]
    return parts


def py_import_edges(path: Path, root: Path, module_index: dict[str, str]) -> list[str]:
    text = read_text(path)
    if not text:
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    targets: list[str] = []
    current_pkg = package_for_file(path, root)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = resolve_python_import(module_index, alias.name)
                if resolved:
                    targets.append(resolved)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base_parts = current_pkg[: max(0, len(current_pkg) - node.level + 1)]
                module_parts = node.module.split(".") if node.module else []
                module = ".".join(base_parts + module_parts)
            else:
                module = node.module or ""
            resolved = resolve_python_import(module_index, module)
            if resolved:
                targets.append(resolved)
    return targets


def resolve_js_spec(path: Path, spec: str, root: Path) -> str | None:
    base = (path.parent / spec).resolve()
    if not str(base).startswith(str(root.resolve())):
        return None
    candidates = [base]
    suffixes = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json"]
    candidates.extend(Path(str(base) + suffix) for suffix in suffixes)
    candidates.extend(base / f"index{suffix}" for suffix in suffixes)
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return safe_rel(candidate, root)
    return None


def js_import_edges(path: Path, root: Path) -> list[str]:
    text = read_text(path)
    if not text:
        return []
    targets: list[str] = []
    for match in LOCAL_JS_IMPORT_RE.finditer(text):
        resolved = resolve_js_spec(path, match.group("spec"), root)
        if resolved:
            targets.append(resolved)
    return targets


def find_cycles(graph: dict[str, list[str]], max_cycles: int) -> list[list[str]]:
    cycles: list[list[str]] = []
    seen_keys: set[tuple[str, ...]] = set()
    stack: list[str] = []
    on_stack: set[str] = set()

    def canonical(cycle: list[str]) -> tuple[str, ...]:
        if not cycle:
            return tuple()
        rotations = [tuple(cycle[i:] + cycle[:i]) for i in range(len(cycle))]
        return min(rotations)

    def visit(node: str) -> None:
        if len(cycles) >= max_cycles:
            return
        stack.append(node)
        on_stack.add(node)
        for target in graph.get(node, []):
            if target not in graph:
                continue
            if target in on_stack:
                idx = stack.index(target)
                cycle = stack[idx:].copy()
                key = canonical(cycle)
                if key not in seen_keys:
                    seen_keys.add(key)
                    cycles.append(cycle + [target])
                    if len(cycles) >= max_cycles:
                        break
            elif target not in stack:
                visit(target)
                if len(cycles) >= max_cycles:
                    break
        on_stack.remove(node)
        stack.pop()

    for node in sorted(graph):
        if len(cycles) >= max_cycles:
            break
        visit(node)
    return cycles


def option_suggestions(signals: dict[str, Any]) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    if signals["import_cycles"]:
        suggestions.append(
            {
                "option": "Dependency-direction cleanup",
                "dx_improvement": "Break cycles so modules can be tested, deleted, and reasoned about independently.",
                "code_slimming_payoff": "Often exposes duplicate adapters, stale DTO conversion, and dead side-effect imports.",
                "approval_required": "yes",
            }
        )
    if signals["layer_word_hotspots"]:
        suggestions.append(
            {
                "option": "Flatten pass-through layers",
                "dx_improvement": "Reduce hops through generic service/manager/helper layers.",
                "code_slimming_payoff": "Deletes wrappers, redundant interfaces, and mock-only abstractions when oracle coverage is sufficient.",
                "approval_required": "yes",
            }
        )
    if signals["large_files"] or signals["dominant_top_level_dirs"]:
        suggestions.append(
            {
                "option": "Feature/domain slice",
                "dx_improvement": "Put related behavior near its tests and data boundary instead of scattering changes across technical folders.",
                "code_slimming_payoff": "Reveals duplicate validators, mappers, config, and fixtures after ownership becomes explicit.",
                "approval_required": "yes",
            }
        )
    if signals["barrel_exports"] or signals["config_sprawl"]:
        suggestions.append(
            {
                "option": "Prune in place first",
                "dx_improvement": "Keep layout stable while removing noisy exports/config and measuring what remains.",
                "code_slimming_payoff": "Low-risk first pass that may avoid a larger architecture refactor.",
                "approval_required": "no for local deletions; yes for boundary changes",
            }
        )
    if not suggestions:
        suggestions.append(
            {
                "option": "Deletion-first shrinking",
                "dx_improvement": "Architecture signals are not severe; proceed with oracle-checked candidate deletion.",
                "code_slimming_payoff": "Focus on files, dependencies, unused exports, duplicate blocks, and local simplification.",
                "approval_required": "no unless structural refactor candidates are introduced",
            }
        )
    return suggestions[:4]


def build_scan(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    exclude_dirs.update(args.exclude_dir)

    files = [path for path in iter_files(root, exclude_dirs)]
    code_files = [path for path in files if path.suffix.lower() in CODE_SUFFIXES]
    py_index = build_python_module_index(code_files, root)

    file_records: list[dict[str, Any]] = []
    graph: dict[str, list[str]] = {}
    reverse_graph: dict[str, list[str]] = defaultdict(list)
    top_level_loc: Counter[str] = Counter()
    layer_words: Counter[str] = Counter()
    config_files: list[str] = []
    barrel_exports: list[str] = []
    deep_paths: list[dict[str, Any]] = []
    large_files: list[dict[str, Any]] = []

    for path in code_files:
        rel = safe_rel(path, root)
        text = read_text(path) or ""
        lines, nonblank = line_metrics(text)
        parts = Path(rel).parts
        top = parts[0] if len(parts) > 1 else "<root>"
        top_level_loc[top] += nonblank
        depth = len(parts)
        for part in parts[:-1]:
            normalized = re.sub(r"[^a-zA-Z]", "", part).lower()
            if normalized in LAYER_WORDS:
                layer_words[normalized] += 1
        if CONFIG_NAME_RE.search(Path(rel).name):
            config_files.append(rel)
        if Path(rel).name in {"index.ts", "index.tsx", "index.js", "index.jsx", "index.mjs"} and BARREL_EXPORT_RE.search(text):
            barrel_exports.append(rel)
        if depth >= args.deep_path_depth:
            deep_paths.append({"path": rel, "depth": depth})
        if nonblank >= args.large_file_loc:
            large_files.append({"path": rel, "nonblank_lines": nonblank, "lines": lines})
        record = {"path": rel, "suffix": path.suffix.lower(), "lines": lines, "nonblank_lines": nonblank}
        file_records.append(record)

        if path.suffix == ".py":
            targets = py_import_edges(path, root, py_index)
        elif path.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
            targets = js_import_edges(path, root)
        else:
            targets = []
        if targets:
            graph[rel] = sorted(set(targets))
            for target in set(targets):
                reverse_graph[target].append(rel)
        else:
            graph.setdefault(rel, [])

    total_loc = sum(top_level_loc.values()) or 1
    dominant_dirs = [
        {"dir": name, "nonblank_lines": loc, "share": round(loc / total_loc, 3)}
        for name, loc in top_level_loc.most_common()
        if loc / total_loc >= 0.30 and name != "<root>"
    ]

    cycles = find_cycles(graph, args.max_cycles)
    fan_out = sorted(
        ({"path": path, "imports": len(targets)} for path, targets in graph.items() if len(targets) >= 12),
        key=lambda item: item["imports"],
        reverse=True,
    )[:25]
    fan_in = sorted(
        ({"path": path, "imported_by": len(sources)} for path, sources in reverse_graph.items() if len(sources) >= 12),
        key=lambda item: item["imported_by"],
        reverse=True,
    )[:25]

    signals = {
        "large_files": sorted(large_files, key=lambda item: item["nonblank_lines"], reverse=True)[:25],
        "deep_paths": sorted(deep_paths, key=lambda item: item["depth"], reverse=True)[:25],
        "import_cycles": cycles,
        "high_fan_out": fan_out,
        "high_fan_in": fan_in,
        "layer_word_hotspots": layer_words.most_common(25),
        "config_sprawl": sorted(config_files)[:100],
        "barrel_exports": sorted(barrel_exports)[:100],
        "dominant_top_level_dirs": dominant_dirs,
    }

    return {
        "repo": str(root),
        "excluded_dirs": sorted(exclude_dirs),
        "summary": {
            "code_files": len(code_files),
            "code_nonblank_lines": sum(record["nonblank_lines"] for record in file_records),
            "import_graph_nodes": len(graph),
            "import_graph_edges": sum(len(targets) for targets in graph.values()),
            "cycle_count_reported": len(cycles),
            "large_file_count": len(large_files),
            "deep_path_count": len(deep_paths),
            "config_file_count": len(config_files),
            "barrel_export_count": len(barrel_exports),
        },
        "top_level_nonblank_loc": dict(top_level_loc.most_common()),
        "signals": signals,
        "architecture_options": option_suggestions(signals),
        "approval_note": "Architecture-level refactors require explicit user approval before execution.",
    }


def write_markdown(scan: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    summary = scan["summary"]
    signals = scan["signals"]
    lines.append("# Architecture / DX scan")
    lines.append("")
    lines.append("This is a heuristic signal report, not an automatic refactor decision. Architecture-level changes remain approval-gated.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Architecture signals")
    lines.append("")

    def render_items(title: str, items: list[Any], formatter) -> None:  # type: ignore[no-untyped-def]
        lines.append(f"### {title}")
        lines.append("")
        if not items:
            lines.append("- None reported.")
        else:
            for item in items[:25]:
                lines.append(f"- {formatter(item)}")
        lines.append("")

    render_items("Import cycles", signals["import_cycles"], lambda c: " -> ".join(f"`{x}`" for x in c))
    render_items("Large files", signals["large_files"], lambda x: f"`{x['path']}`: {x['nonblank_lines']} nonblank LOC")
    render_items("Deep paths", signals["deep_paths"], lambda x: f"`{x['path']}`: depth {x['depth']}")
    render_items("High fan-out", signals["high_fan_out"], lambda x: f"`{x['path']}` imports {x['imports']} local modules")
    render_items("High fan-in", signals["high_fan_in"], lambda x: f"`{x['path']}` imported by {x['imported_by']} local modules")
    render_items("Layer-word hotspots", signals["layer_word_hotspots"], lambda x: f"`{x[0]}` appears in {x[1]} paths")
    render_items("Config sprawl", signals["config_sprawl"], lambda x: f"`{x}`")
    render_items("Barrel exports", signals["barrel_exports"], lambda x: f"`{x}`")
    render_items("Dominant top-level directories", signals["dominant_top_level_dirs"], lambda x: f"`{x['dir']}`: {x['nonblank_lines']} nonblank LOC ({x['share']})")

    lines.append("## Candidate architecture options")
    lines.append("")
    for idx, option in enumerate(scan["architecture_options"], start=1):
        lines.append(f"### Option {idx}: {option['option']}")
        lines.append("")
        lines.append(f"- DX improvement: {option['dx_improvement']}")
        lines.append(f"- Code-slimming payoff: {option['code_slimming_payoff']}")
        lines.append(f"- Approval required: {option['approval_required']}")
        lines.append("")
    lines.append("Architecture-level refactors require explicit user approval before execution.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = Path(args.repo).resolve()
    if not root.exists():
        raise SystemExit(f"Repository root does not exist: {root}")

    scan = build_scan(root, args)
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(scan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.markdown_output:
        write_markdown(scan, Path(args.markdown_output))
    print(json.dumps(scan["summary"], indent=2, ensure_ascii=False))
    if not args.json_output and not args.markdown_output:
        print("Tip: add --json-output or --markdown-output for persisted results.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
