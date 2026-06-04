#!/usr/bin/env python3
"""List local agent skills from common Codex/agent skill roots."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def frontmatter_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""

    body: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)
    return "\n".join(body)


def clean_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(path: Path) -> dict[str, str]:
    frontmatter = frontmatter_text(path)
    result = {"name": path.parent.name, "description": ""}
    if not frontmatter:
        return result

    lines = frontmatter.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            index += 1
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key not in result:
            index += 1
            continue

        if value in {"", ">", ">-", "|", "|-"}:
            chunks: list[str] = []
            index += 1
            while index < len(lines):
                next_line = lines[index]
                if next_line and not next_line.startswith((" ", "\t")) and ":" in next_line:
                    index -= 1
                    break
                chunks.append(next_line.strip())
                index += 1
            result[key] = " ".join(chunk for chunk in chunks if chunk)
        else:
            result[key] = clean_value(value)
        index += 1

    return result


def candidate_roots(extra_roots: list[str]) -> list[Path]:
    home = Path.home()
    roots: list[Path] = []
    skill_collection_root = Path(__file__).resolve().parent.parent.parent

    env_roots = os.environ.get("SELECT_SKILLS_ROOTS")
    if env_roots:
        roots.extend(expand_path(root) for root in env_roots.split(os.pathsep) if root)

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        roots.append(expand_path(codex_home) / "skills")

    roots.extend(
        [
            skill_collection_root,
            home / ".codex" / "skills",
            home / ".agents" / "skills",
            home / ".claude" / "skills",
            home / ".codex" / "plugins" / "cache",
        ]
    )

    cwd = Path.cwd().resolve()
    for directory in [cwd, *cwd.parents]:
        for name in (".codex", ".agents", ".claude"):
            roots.append(directory / name / "skills")

    roots.extend(expand_path(root) for root in extra_roots)

    seen: set[Path] = set()
    existing: list[Path] = []
    for root in roots:
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        existing.append(resolved)
    return existing


def scope_for(path: Path) -> str:
    home = Path.home().resolve()
    path = path.resolve()
    cwd = Path.cwd().resolve()
    skill_collection_root = Path(__file__).resolve().parent.parent.parent

    if path == skill_collection_root or skill_collection_root in path.parents:
        return "skill-collection"

    scope_markers = [
        (home / ".codex" / "plugins" / "cache", "plugin-cache"),
        (home / ".codex" / "skills", "codex-user"),
        (home / ".agents" / "skills", "agent-user"),
        (home / ".claude" / "skills", "claude-user"),
    ]
    for root, scope in scope_markers:
        if path == root or root in path.parents:
            return scope

    for directory in [cwd, *cwd.parents]:
        for name in (".codex", ".agents", ".claude"):
            root = directory / name / "skills"
            if path == root or root in path.parents:
                return "project"
    return "extra"


def list_skills(roots: list[Path]) -> list[dict[str, str]]:
    seen: set[Path] = set()
    skills: list[dict[str, str]] = []

    for root in roots:
        for skill_file in root.rglob("SKILL.md"):
            try:
                resolved = skill_file.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)

            metadata = parse_frontmatter(resolved)
            skills.append(
                {
                    "name": metadata["name"],
                    "description": metadata["description"],
                    "scope": scope_for(resolved.parent),
                    "path": str(resolved),
                }
            )

    return sorted(skills, key=lambda item: (item["name"].lower(), item["path"]))


def filter_skills(skills: list[dict[str, str]], query: str | None) -> list[dict[str, str]]:
    if not query:
        return skills

    terms = [term.lower() for term in query.split() if term.strip()]
    if not terms:
        return skills

    filtered: list[dict[str, str]] = []
    for skill in skills:
        haystack = " ".join(
            [skill["name"], skill["description"], skill["scope"], skill["path"]]
        ).lower()
        if all(term in haystack for term in terms):
            filtered.append(skill)
    return filtered


def print_markdown(skills: list[dict[str, str]]) -> None:
    print("| Name | Scope | Description | Path |")
    print("| --- | --- | --- | --- |")
    for skill in skills:
        description = skill["description"].replace("|", "\\|")
        print(f"| {skill['name']} | {skill['scope']} | {description} | {skill['path']} |")


def print_tsv(skills: list[dict[str, str]]) -> None:
    for skill in skills:
        print(
            "\t".join(
                [
                    skill["name"],
                    skill["scope"],
                    skill["description"].replace("\t", " "),
                    skill["path"],
                ]
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="List local agent skills.")
    parser.add_argument("--format", choices=("markdown", "json", "tsv"), default="markdown")
    parser.add_argument("--query", help="Filter by terms across name, description, scope, and path.")
    parser.add_argument("--root", action="append", default=[], help="Additional skill root to scan.")
    args = parser.parse_args()

    skills = filter_skills(list_skills(candidate_roots(args.root)), args.query)

    if args.format == "json":
        print(json.dumps(skills, ensure_ascii=False, indent=2))
    elif args.format == "tsv":
        print_tsv(skills)
    else:
        print_markdown(skills)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
