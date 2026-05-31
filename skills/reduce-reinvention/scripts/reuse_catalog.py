#!/usr/bin/env python3
"""Create a lightweight inventory of likely reusable assets in a repository.

This helper is intentionally dependency-free and heuristic. Use its output as a
starting point for a maintained catalog, not as the final source of truth.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "vendor", "dist", "build", "target", "coverage",
    ".venv", "venv", "env", "__pycache__", ".mypy_cache", ".pytest_cache", ".next", ".nuxt", ".terraform",
}

MANIFESTS = {
    "package.json": "npm-package",
    "pyproject.toml": "python-package",
    "setup.py": "python-package",
    "setup.cfg": "python-package",
    "go.mod": "go-module",
    "Cargo.toml": "rust-crate",
    "pom.xml": "java-package",
    "build.gradle": "jvm-package",
    "build.gradle.kts": "jvm-package",
    "composer.json": "php-package",
    "Gemfile": "ruby-package",
    "Package.swift": "swift-package",
    "catalog-info.yaml": "catalog-metadata",
    "catalog-info.yml": "catalog-metadata",
    "CODEOWNERS": "ownership",
}

REUSABLE_PATH_RE = re.compile(r"(^|/)(shared|common|utils|util|lib|libs|packages|components|templates|modules|platform|infra|terraform|charts|workflows)(/|$)", re.I)
PUBLIC_SYMBOL_PATTERNS = [
    ("python", re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)),
    ("python", re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*[(:]", re.M)),
    ("typescript", re.compile(r"^\s*export\s+(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", re.M)),
    ("typescript", re.compile(r"^\s*export\s+(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=", re.M)),
    ("typescript", re.compile(r"^\s*export\s+(?:class|interface|type)\s+([A-Za-z_$][\w$]*)", re.M)),
    ("go", re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Z][A-Za-z0-9_]*)\s*\(", re.M)),
    ("go", re.compile(r"^\s*type\s+([A-Z][A-Za-z0-9_]*)\s+", re.M)),
    ("rust", re.compile(r"^\s*pub\s+(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)),
    ("rust", re.compile(r"^\s*pub\s+(?:struct|enum|trait)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)),
]

EXT_TO_LANGUAGE = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin", ".cs": "csharp",
    ".tf": "terraform", ".yaml": "yaml", ".yml": "yaml", ".md": "markdown",
}


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace(os.sep, "/")


def iter_files(root: Path, max_file_bytes: int) -> Iterable[Path]:
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for filename in filenames:
            path = Path(current) / filename
            try:
                if path.stat().st_size > max_file_bytes:
                    continue
            except OSError:
                continue
            yield path


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def package_name(path: Path, text: str) -> str:
    name = path.name
    if name == "package.json":
        try:
            data = json.loads(text)
            return str(data.get("name") or path.parent.name)
        except Exception:
            return path.parent.name
    if name == "pyproject.toml":
        match = re.search(r"(?m)^name\s*=\s*[\"']([^\"']+)[\"']", text)
        return match.group(1) if match else path.parent.name
    if name == "go.mod":
        match = re.search(r"(?m)^module\s+(.+)$", text)
        return match.group(1).strip() if match else path.parent.name
    if name == "Cargo.toml":
        match = re.search(r"(?m)^name\s*=\s*[\"']([^\"']+)[\"']", text)
        return match.group(1) if match else path.parent.name
    if name in {"catalog-info.yaml", "catalog-info.yml"}:
        match = re.search(r"(?m)^\s*name:\s*([^\n#]+)", text)
        return match.group(1).strip().strip('"\'') if match else path.parent.name
    if path.suffix == ".csproj":
        return path.stem
    return path.parent.name


def extract_public_symbols(path: Path, text: str, max_symbols: int) -> List[str]:
    suffix = path.suffix.lower()
    language = EXT_TO_LANGUAGE.get(suffix, "")
    symbols: List[str] = []
    for pattern_language, pattern in PUBLIC_SYMBOL_PATTERNS:
        if pattern_language == "typescript" and language not in {"typescript", "javascript"}:
            continue
        if pattern_language != "typescript" and pattern_language != language:
            continue
        for match in pattern.finditer(text):
            name = match.group(1)
            if name.startswith("_") or len(name) < 4:
                continue
            symbols.append(name)
            if len(symbols) >= max_symbols:
                return sorted(set(symbols))
    return sorted(set(symbols))[:max_symbols]


def infer_owner(root: Path, path: Path, codeowners_text: str) -> str:
    if not codeowners_text:
        return "unknown"
    rel_path = "/" + rel(path, root)
    owner = "unknown"
    for raw in codeowners_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        pattern, owners = parts[0], parts[1:]
        simple = pattern.rstrip("*")
        if pattern == "*" or rel_path.startswith(simple if simple.startswith("/") else "/" + simple):
            owner = ", ".join(owners)
    return owner


def collect(root: Path, args: argparse.Namespace) -> Dict[str, object]:
    files = list(iter_files(root, args.max_file_bytes))
    codeowners_text = ""
    for candidate in [root / "CODEOWNERS", root / ".github" / "CODEOWNERS", root / "docs" / "CODEOWNERS"]:
        if candidate.exists():
            codeowners_text = read_text(candidate)
            break

    assets: List[Dict[str, object]] = []
    seen_paths = set()

    for path in files:
        rel_path = rel(path, root)
        text = read_text(path) if path.suffix.lower() in {".json", ".toml", ".xml", ".yaml", ".yml", ".gradle", ".kts", ".py", ".cfg", ".swift"} or path.name in MANIFESTS else ""
        kind = MANIFESTS.get(path.name)
        if not kind and path.suffix == ".csproj":
            kind = "dotnet-package"
        if kind:
            asset_path = rel(path.parent, root) if path.parent != root else "."
            assets.append({
                "name": package_name(path, text),
                "type": kind,
                "path": asset_path,
                "owner": infer_owner(root, path, codeowners_text),
                "signals": [f"manifest:{path.name}"],
                "public_symbols": [],
            })
            seen_paths.add(asset_path)

    for path in files:
        rel_path = rel(path, root)
        if not REUSABLE_PATH_RE.search(rel_path):
            continue
        if path.suffix.lower() not in EXT_TO_LANGUAGE:
            continue
        text = read_text(path)
        symbols = extract_public_symbols(path, text, args.max_symbols_per_asset)
        if not symbols and path.suffix.lower() not in {".md", ".yaml", ".yml", ".tf"}:
            continue
        parent = rel(path.parent, root) if path.parent != root else "."
        key = f"{parent}:{path.suffix.lower()}"
        if key in seen_paths:
            continue
        seen_paths.add(key)
        assets.append({
            "name": path.stem,
            "type": "candidate-reusable-source",
            "path": rel_path,
            "owner": infer_owner(root, path, codeowners_text),
            "signals": ["reusable-path", f"language:{EXT_TO_LANGUAGE.get(path.suffix.lower(), 'unknown')}"] + (["public-symbols"] if symbols else []),
            "public_symbols": symbols,
        })
        if len(assets) >= args.max_assets:
            break

    return {
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(root),
        "files_scanned": len(files),
        "asset_count": len(assets),
        "assets": assets[: args.max_assets],
    }


def md_table(rows: Sequence[Sequence[object]], headers: Sequence[str]) -> str:
    if not rows:
        return ""
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(cell).replace("\n", " ").replace("|", "\\|") for cell in row) + " |")
    return "\n".join(out)


def render_markdown(report: Dict[str, object]) -> str:
    rows = []
    for asset in report["assets"]:
        rows.append([
            asset["name"],
            asset["type"],
            f"`{asset['path']}`",
            asset["owner"],
            ", ".join(asset["signals"]),
            ", ".join(asset["public_symbols"][:8]) + (" ..." if len(asset["public_symbols"]) > 8 else ""),
        ])
    lines = [
        "# Reuse Catalog Inventory",
        "",
        f"Generated UTC: {report['generated_at_utc']}",
        f"Root: `{report['root']}`",
        f"Files scanned: {report['files_scanned']}",
        f"Candidate assets: {report['asset_count']}",
        "",
        "## Candidate reusable assets",
        "",
        md_table(rows, ["Name", "Type", "Path", "Owner", "Signals", "Public symbols"]) if rows else "No reusable asset candidates found with current heuristics.",
        "",
        "## Suggested next steps",
        "",
        "- Confirm owner, lifecycle, docs, examples, consumers, and support channel for high-value assets.",
        "- Promote mature assets into a maintained catalog entry.",
        "- Mark experimental or unsafe assets as `assess` or `hold` to avoid accidental reuse.",
    ]
    return "\n".join(lines) + "\n"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a lightweight inventory of reusable asset candidates.")
    parser.add_argument("path", help="Repository or directory path to scan")
    parser.add_argument("--output", "-o", help="Write report to this path; defaults to stdout")
    parser.add_argument("--format", choices=["md", "json"], default="md", help="Output format")
    parser.add_argument("--max-file-bytes", type=int, default=1_000_000, help="Skip files larger than this")
    parser.add_argument("--max-assets", type=int, default=250, help="Maximum assets to report")
    parser.add_argument("--max-symbols-per-asset", type=int, default=12, help="Maximum public symbols to show per asset")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.path).resolve()
    if not root.exists() or not root.is_dir():
        print(f"[ERROR] path is not a directory: {root}", file=sys.stderr)
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
