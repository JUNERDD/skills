#!/usr/bin/env python3
"""Create and validate plan-mode Markdown plan artifacts."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path


REQUIRED_HEADINGS = [
    "## Summary",
    "## Clarifying Questions",
    "## File And Code References",
    "## Plan Todos",
    "## Grill-Me Outcome",
    "## Build From Plan",
    "## Validation",
    "## Risks",
    "## Approval",
]

PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO|PLACEHOLDER)\b|\[fill[^\]]*\]", re.IGNORECASE)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:64].strip("-") or "plan"


def resolve_workspace(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return Path.cwd().resolve()


def choose_plan_dir(workspace: Path) -> Path:
    for relative in ("docs/plans", "plans", ".codex/plans"):
        candidate = workspace / relative
        if candidate.is_dir():
            return candidate
    return workspace / "docs" / "plans"


def unique_path(base_path: Path, force: bool, reuse_existing: bool) -> Path:
    if reuse_existing and base_path.exists():
        return base_path
    if force or not base_path.exists():
        return base_path

    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def render_template(title: str, status: str, created: str) -> str:
    return f"""# {title}

Status: {status}
Created: {created}
Approval: Awaiting user approval

## Summary

TBD

## Clarifying Questions

- [ ] TBD

## File And Code References

- TBD

## Plan Todos

- [ ] TBD

## Grill-Me Outcome

- Transcript: Not run
- Outcome: Not run
- Summary: TBD

## Build From Plan

- Ready to build: No
- Selected todos: TBD
- Execution notes: TBD

## Validation

- TBD

## Risks

- TBD

## Approval

- Status: Draft - awaiting approval
"""


def command_init(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    title = args.title.strip()
    if not title:
        print("title is required", file=sys.stderr)
        return 2

    if args.path:
        path = Path(args.path).expanduser()
        if not path.is_absolute():
            path = workspace / path
        if path.suffix.lower() != ".md":
            path = path.with_suffix(".md")
    else:
        plan_dir = choose_plan_dir(workspace)
        created = args.date or dt.date.today().isoformat()
        path = plan_dir / f"{created}-{slugify(args.slug or title)}.md"

    path = unique_path(path.resolve(), args.force, args.reuse_existing)
    if args.reuse_existing and path.exists():
        print(path)
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    created = args.date or dt.date.today().isoformat()
    path.write_text(render_template(title, args.status, created), encoding="utf-8")
    print(path)
    return 0


def command_check(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve()
    if not path.is_file():
        print(f"plan file not found: {path}", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    if missing:
        print("missing required headings:", file=sys.stderr)
        for heading in missing:
            print(f"- {heading}", file=sys.stderr)
        return 1

    match = PLACEHOLDER_RE.search(text)
    if match:
        print(f"placeholder remains: {match.group(0)}", file=sys.stderr)
        return 1

    print(f"plan artifact is complete: {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a draft plan artifact")
    init_parser.add_argument("--workspace", help="workspace root; defaults to cwd")
    init_parser.add_argument("--title", required=True, help="plan title")
    init_parser.add_argument("--slug", help="filename slug; defaults to title")
    init_parser.add_argument("--path", help="explicit output path, absolute or workspace-relative")
    init_parser.add_argument("--date", help="ISO date for generated filename and header")
    init_parser.add_argument("--status", default="Draft - awaiting approval", help="plan status")
    init_parser.add_argument("--force", action="store_true", help="overwrite the requested path")
    init_parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="print the resolved path without overwriting when the plan already exists",
    )
    init_parser.set_defaults(func=command_init)

    check_parser = subparsers.add_parser("check", help="validate a completed plan artifact")
    check_parser.add_argument("path", help="plan artifact path")
    check_parser.set_defaults(func=command_check)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
