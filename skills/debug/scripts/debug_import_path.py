#!/usr/bin/env python3
"""Resolve and verify file-relative imports used by temporary debug helpers."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any


class ImportPathError(ValueError):
    """Raised when a debug helper import cannot be resolved safely."""


def _resolve_workspace_path(raw_path: str, workspace_root: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = workspace_root / path
    return path.resolve()


def _require_within_workspace(path: Path, workspace_root: Path, label: str) -> None:
    try:
        path.relative_to(workspace_root)
    except ValueError as exc:
        raise ImportPathError(f"{label} is outside workspace root: {path}") from exc


def _relative_specifier(importer: Path, target: Path, *, strip_extension: bool) -> str:
    relative = os.path.relpath(target, start=importer.parent).replace(os.sep, "/")
    if not relative.startswith("."):
        relative = f"./{relative}"
    if strip_extension and target.suffix and relative.endswith(target.suffix):
        relative = relative[: -len(target.suffix)]
    return relative


def _specifier_resolves_to_target(specifier: str, importer: Path, target: Path) -> bool:
    if not specifier.startswith(("./", "../")):
        raise ImportPathError(
            "--specifier must be file-relative; validate project aliases with the "
            "project's own compiler or resolver"
        )
    if "?" in specifier or "#" in specifier:
        raise ImportPathError("--specifier must not contain query or fragment text")

    candidate = (importer.parent / specifier).resolve()
    if candidate == target:
        return True
    return bool(target.suffix and Path(f"{candidate}{target.suffix}") == target)


def resolve_import_path(args: argparse.Namespace) -> dict[str, Any]:
    workspace_root = Path(args.workspace_root).expanduser().resolve()
    if not workspace_root.is_dir():
        raise ImportPathError(f"workspace root is not a directory: {workspace_root}")

    importer = _resolve_workspace_path(args.importer, workspace_root)
    target = _resolve_workspace_path(args.target, workspace_root)
    _require_within_workspace(importer, workspace_root, "importer")
    _require_within_workspace(target, workspace_root, "target")

    if not importer.is_file():
        raise ImportPathError(f"importer file does not exist: {importer}")
    if not target.is_file():
        raise ImportPathError(f"target helper file does not exist: {target}")

    expected = _relative_specifier(
        importer,
        target,
        strip_extension=args.strip_extension,
    )
    if args.specifier is not None and not _specifier_resolves_to_target(
        args.specifier,
        importer,
        target,
    ):
        raise ImportPathError(
            f"specifier resolves to a different path: {args.specifier!r}; "
            f"expected {expected!r}"
        )

    return {
        "ok": True,
        "workspaceRoot": str(workspace_root),
        "importer": str(importer),
        "target": str(target),
        "specifier": expected,
        "verifiedSpecifier": args.specifier,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compute a debug helper import from the importing file's directory and "
            "optionally verify an already-injected file-relative specifier."
        )
    )
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--importer", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument(
        "--strip-extension",
        action="store_true",
        help="Omit the target's final extension, for repositories that use extensionless imports.",
    )
    parser.add_argument(
        "--specifier",
        help="Verify that this existing file-relative specifier resolves to --target.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = resolve_import_path(args)
    except ImportPathError as exc:
        error = {"ok": False, "error": str(exc)}
        if args.format == "json":
            print(json.dumps(error, indent=2), file=sys.stderr)
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(payload["specifier"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
