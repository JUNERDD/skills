#!/usr/bin/env python3
"""Exhaustive, oracle-checked code slimming candidate runner.

Candidate JSONL schema:
  {"id":"...", "type":"delete_file", "path":"src/x.py", "score":123, "group":"src"}
  {"id":"...", "type":"delete_span", "path":"src/x.py", "start_line":10, "end_line":20}
  {"id":"...", "type":"replace_span", "path":"src/x.py", "start_line":10, "end_line":20, "replacement":"..."}
  {"id":"...", "type":"regex_replace", "path":"src/x.py", "pattern":"...", "replacement":"", "count":0}

Architecture-level candidates should include {"requires_user_approval": true}.
They are skipped unless --allow-approval-gated is passed after explicit approval.

The script maximizes the sum of candidate scores subject to the oracle passing.
Use exact mode for small sets; use partition-exact for larger frontiers.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

DEFAULT_COPY_IGNORE = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
}

SPAN_TYPES = {"delete_span", "replace_span"}
VALID_TYPES = SPAN_TYPES | {"delete_file", "regex_replace"}


@dataclass(frozen=True)
class Candidate:
    index: int
    id: str
    type: str
    path: str
    raw: dict[str, Any]
    score: int
    group: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run exhaustive code slimming candidates against an oracle.")
    parser.add_argument("--repo", default=".", help="Repository root to shrink.")
    parser.add_argument("--candidates", required=True, help="JSONL file of candidate operations.")
    parser.add_argument("--oracle", required=True, help="Shell command that must exit 0 for an accepted change.")
    parser.add_argument("--mode", choices=("exact", "partition-exact", "greedy"), default="exact")
    parser.add_argument("--apply", action="store_true", help="Apply the best passing subset to the real repository.")
    parser.add_argument("--timeout", type=int, default=300, help="Oracle timeout in seconds.")
    parser.add_argument("--max-candidates", type=int, default=18, help="Maximum candidates for exact powerset mode.")
    parser.add_argument("--max-subsets", type=int, default=262144, help="Maximum subsets to test in exact searches.")
    parser.add_argument("--passes", type=int, default=2, help="Passes for partition-exact or greedy mode.")
    parser.add_argument("--skip-baseline", action="store_true", help="Do not verify that the oracle passes on the unmodified repo.")
    parser.add_argument("--copy-ignore", action="append", default=[], help="Extra directory name to ignore while copying; repeatable.")
    parser.add_argument("--keep-workdirs", action="store_true", help="Keep temporary workdirs for debugging.")
    parser.add_argument("--summary-output", help="Write JSON summary to this path.")
    parser.add_argument(
        "--allow-approval-gated",
        action="store_true",
        help="Include candidates marked requires_user_approval=true. Use only after explicit user approval.",
    )
    return parser.parse_args()


def is_approval_gated(raw: dict[str, Any]) -> bool:
    return bool(raw.get("requires_user_approval") or raw.get("approval_required"))


def load_candidates(path: Path, repo: Path, allow_approval_gated: bool = False) -> tuple[list[Candidate], list[dict[str, Any]]]:
    candidates: list[Candidate] = []
    skipped_approval_gated: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON on candidate line {line_number}: {exc}") from exc
            if is_approval_gated(raw) and not allow_approval_gated:
                skipped_approval_gated.append({
                    "line": line_number,
                    "id": str(raw.get("id") or f"approval-gated:{line_number}"),
                    "path": str(raw.get("path", "")),
                    "reason": raw.get("reason") or raw.get("architecture_option") or "requires_user_approval",
                })
                continue
            ctype = str(raw.get("type", ""))
            if ctype not in VALID_TYPES:
                raise SystemExit(f"Candidate line {line_number} has unsupported type: {ctype!r}")
            rel_path = str(raw.get("path", ""))
            assert_safe_relpath(rel_path)
            candidate_id = str(raw.get("id") or f"{ctype}:{rel_path}:{line_number}")
            score = raw.get("score")
            if score is None:
                score = estimate_score(repo, raw)
            try:
                score_int = int(score)
            except (TypeError, ValueError):
                score_int = 1
            candidates.append(
                Candidate(
                    index=len(candidates),
                    id=candidate_id,
                    type=ctype,
                    path=rel_path,
                    raw=raw,
                    score=max(1, score_int),
                    group=str(raw.get("group") or default_group(rel_path)),
                )
            )
    return candidates, skipped_approval_gated


def default_group(rel_path: str) -> str:
    path = Path(rel_path)
    if path.parent == Path("."):
        return "<root>"
    first = path.parts[0] if path.parts else "<root>"
    return first


def assert_safe_relpath(rel_path: str) -> None:
    path = Path(rel_path)
    if not rel_path or path.is_absolute() or ".." in path.parts:
        raise SystemExit(f"Unsafe candidate path: {rel_path!r}")


def estimate_score(repo: Path, raw: dict[str, Any]) -> int:
    rel_path = str(raw.get("path", ""))
    path = repo / rel_path
    try:
        if raw.get("type") == "delete_file":
            return max(1, path.stat().st_size)
        if raw.get("type") in SPAN_TYPES:
            start = int(raw.get("start_line"))
            end = int(raw.get("end_line"))
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
            return max(1, sum(len(line.encode("utf-8", errors="ignore")) for line in lines[start - 1 : end]))
    except Exception:
        return 1
    return 1


def copy_repo(src: Path, dst: Path, ignore_names: set[str]) -> None:
    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {name for name in names if name in ignore_names}

    shutil.copytree(src, dst, ignore=ignore)


def run_oracle(repo: Path, command: str, timeout: int) -> tuple[bool, str]:
    env = os.environ.copy()
    env["CODE_SLIM_ROOT"] = str(repo)
    try:
        completed = subprocess.run(
            command,
            cwd=repo,
            shell=True,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        return False, f"TIMEOUT after {timeout}s\n{output}"
    return completed.returncode == 0, completed.stdout[-4000:]


def validate_combination(candidates: Iterable[Candidate]) -> bool:
    by_file_spans: dict[str, list[tuple[int, int]]] = {}
    deleted_files: set[str] = set()
    touched_files: set[str] = set()

    for candidate in candidates:
        if candidate.type == "delete_file":
            deleted_files.add(candidate.path)
        else:
            touched_files.add(candidate.path)
        if candidate.type in SPAN_TYPES:
            try:
                start = int(candidate.raw["start_line"])
                end = int(candidate.raw["end_line"])
            except (KeyError, TypeError, ValueError):
                return False
            if start < 1 or end < start:
                return False
            by_file_spans.setdefault(candidate.path, []).append((start, end))

    if deleted_files & touched_files:
        return False

    for spans in by_file_spans.values():
        spans.sort()
        for (_, prev_end), (next_start, _) in zip(spans, spans[1:]):
            if next_start <= prev_end:
                return False
    return True


def apply_candidates(repo: Path, candidates: Iterable[Candidate]) -> None:
    selected = list(candidates)
    if not validate_combination(selected):
        raise ValueError("Candidate combination is invalid or overlapping")

    # Delete files first; other operations on deleted files are disallowed by validation.
    for candidate in selected:
        if candidate.type == "delete_file":
            target = repo / candidate.path
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()

    span_by_file: dict[str, list[Candidate]] = {}
    regex_by_file: dict[str, list[Candidate]] = {}
    for candidate in selected:
        if candidate.type in SPAN_TYPES:
            span_by_file.setdefault(candidate.path, []).append(candidate)
        elif candidate.type == "regex_replace":
            regex_by_file.setdefault(candidate.path, []).append(candidate)

    for rel_path, file_candidates in span_by_file.items():
        target = repo / rel_path
        lines = target.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
        for candidate in sorted(file_candidates, key=lambda c: int(c.raw["start_line"]), reverse=True):
            start = int(candidate.raw["start_line"])
            end = int(candidate.raw["end_line"])
            replacement = replacement_lines(candidate.raw.get("replacement", "")) if candidate.type == "replace_span" else []
            lines[start - 1 : end] = replacement
        target.write_text("".join(lines), encoding="utf-8")

    for rel_path, file_candidates in regex_by_file.items():
        target = repo / rel_path
        text = target.read_text(encoding="utf-8", errors="ignore")
        for candidate in file_candidates:
            flags = regex_flags(candidate.raw.get("flags", []))
            pattern = str(candidate.raw.get("pattern", ""))
            replacement = str(candidate.raw.get("replacement", ""))
            count = int(candidate.raw.get("count", 0))
            text = re.sub(pattern, replacement, text, count=count, flags=flags)
        target.write_text(text, encoding="utf-8")


def replacement_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        rendered: list[str] = []
        for item in value:
            line = str(item)
            rendered.append(line if line.endswith("\n") else line + "\n")
        return rendered
    if value is None:
        return []
    return str(value).splitlines(keepends=True)


def regex_flags(values: Any) -> int:
    if isinstance(values, str):
        values = [values]
    flags = 0
    mapping = {
        "IGNORECASE": re.IGNORECASE,
        "MULTILINE": re.MULTILINE,
        "DOTALL": re.DOTALL,
        "VERBOSE": re.VERBOSE,
        "ASCII": re.ASCII,
    }
    for value in values or []:
        flags |= mapping.get(str(value).upper(), 0)
    return flags


def subset_score(candidates: Iterable[Candidate]) -> int:
    return sum(candidate.score for candidate in candidates)


def all_nonempty_subsets(candidates: list[Candidate], max_subsets: int) -> Iterable[tuple[Candidate, ...]]:
    total = (1 << len(candidates)) - 1
    if total > max_subsets:
        raise SystemExit(
            f"Exact search would test {total} subsets for {len(candidates)} candidates, exceeding --max-subsets={max_subsets}. "
            "Reduce candidates, increase the budget, or use --mode partition-exact."
        )
    # Larger subsets often remove more; test them first to find a high-water mark early.
    for size in range(len(candidates), 0, -1):
        yield from itertools.combinations(candidates, size)


def test_subset(
    repo: Path,
    subset: list[Candidate] | tuple[Candidate, ...],
    oracle: str,
    timeout: int,
    ignore_names: set[str],
    keep_workdirs: bool,
) -> tuple[bool, str]:
    if not validate_combination(subset):
        return False, "invalid_combination"
    temp_parent = Path(tempfile.mkdtemp(prefix="code-slim-"))
    workdir = temp_parent / "repo"
    try:
        copy_repo(repo, workdir, ignore_names)
        apply_candidates(workdir, subset)
        return run_oracle(workdir, oracle, timeout)
    finally:
        if keep_workdirs:
            print(f"kept workdir: {workdir}", file=sys.stderr)
        else:
            shutil.rmtree(temp_parent, ignore_errors=True)


def exact_search(
    repo: Path,
    candidates: list[Candidate],
    args: argparse.Namespace,
    ignore_names: set[str],
    base_accepted: list[Candidate] | None = None,
) -> dict[str, Any]:
    base_accepted = base_accepted or []
    if len(candidates) > args.max_candidates:
        raise SystemExit(
            f"Exact mode received {len(candidates)} candidates, exceeding --max-candidates={args.max_candidates}. "
            "Reduce candidates, increase --max-candidates, or use partition-exact."
        )

    tested = 0
    passing = 0
    best: list[Candidate] = []
    best_score = 0
    failures: list[dict[str, Any]] = []

    for subset in all_nonempty_subsets(candidates, args.max_subsets):
        combined = base_accepted + list(subset)
        if not validate_combination(combined):
            continue
        tested += 1
        ok, output = test_subset(repo, combined, args.oracle, args.timeout, ignore_names, args.keep_workdirs)
        if ok:
            passing += 1
            score = subset_score(subset)
            if score > best_score or (score == best_score and len(subset) < len(best)):
                best = list(subset)
                best_score = score
        elif len(failures) < 10:
            failures.append({"ids": [c.id for c in subset], "reason_tail": output[-500:]})

    return {
        "tested_subsets": tested,
        "passing_subsets": passing,
        "best_score": best_score,
        "best_candidates": [candidate_to_dict(c) for c in best],
        "sample_failures": failures,
    }


def partition_exact_search(repo: Path, candidates: list[Candidate], args: argparse.Namespace, ignore_names: set[str]) -> dict[str, Any]:
    accepted: list[Candidate] = []
    remaining = list(candidates)
    events: list[dict[str, Any]] = []

    for pass_number in range(1, args.passes + 1):
        changed = False
        groups: dict[str, list[Candidate]] = {}
        for candidate in remaining:
            groups.setdefault(candidate.group, []).append(candidate)

        for group_name in sorted(groups):
            group_candidates = groups[group_name]
            if not group_candidates:
                continue
            if len(group_candidates) > args.max_candidates:
                # Split oversized groups deterministically into chunks so exactness is honest per chunk.
                chunks = [group_candidates[i : i + args.max_candidates] for i in range(0, len(group_candidates), args.max_candidates)]
            else:
                chunks = [group_candidates]

            for chunk_index, chunk in enumerate(chunks, start=1):
                result = exact_search(repo, chunk, args, ignore_names, base_accepted=accepted)
                best_ids = {item["id"] for item in result["best_candidates"]}
                chosen = [candidate for candidate in chunk if candidate.id in best_ids]
                if chosen:
                    accepted.extend(chosen)
                    remaining = [candidate for candidate in remaining if candidate.id not in best_ids]
                    changed = True
                event = {
                    "pass": pass_number,
                    "group": group_name,
                    "chunk": chunk_index,
                    "chunk_candidates": len(chunk),
                    **result,
                }
                events.append(event)
        if not changed:
            break

    return {
        "accepted_candidates": [candidate_to_dict(c) for c in accepted],
        "accepted_score": subset_score(accepted),
        "events": events,
    }


def greedy_search(repo: Path, candidates: list[Candidate], args: argparse.Namespace, ignore_names: set[str]) -> dict[str, Any]:
    accepted: list[Candidate] = []
    remaining = sorted(candidates, key=lambda c: (c.score, c.id), reverse=True)
    events: list[dict[str, Any]] = []

    for pass_number in range(1, args.passes + 1):
        changed = False
        next_remaining: list[Candidate] = []
        for candidate in remaining:
            trial = accepted + [candidate]
            if not validate_combination(trial):
                next_remaining.append(candidate)
                continue
            ok, output = test_subset(repo, trial, args.oracle, args.timeout, ignore_names, args.keep_workdirs)
            events.append({"pass": pass_number, "candidate": candidate_to_dict(candidate), "accepted": ok})
            if ok:
                accepted.append(candidate)
                changed = True
            else:
                # Retest later: another accepted deletion can make this one safe.
                next_remaining.append(candidate)
        remaining = next_remaining
        if not changed:
            break

    return {
        "accepted_candidates": [candidate_to_dict(c) for c in accepted],
        "accepted_score": subset_score(accepted),
        "events": events,
    }


def candidate_to_dict(candidate: Candidate) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "type": candidate.type,
        "path": candidate.path,
        "score": candidate.score,
        "group": candidate.group,
        "raw": candidate.raw,
    }


def apply_to_real_repo(repo: Path, candidates: list[Candidate], oracle: str, timeout: int) -> None:
    if not candidates:
        print("No passing candidates to apply.")
        return
    apply_candidates(repo, candidates)
    ok, output = run_oracle(repo, oracle, timeout)
    if not ok:
        raise SystemExit(
            "Applied candidates failed the oracle in the real repository. Restore from version control.\n"
            + output[-4000:]
        )


def baseline_check(repo: Path, args: argparse.Namespace, ignore_names: set[str]) -> None:
    ok, output = test_subset(repo, [], args.oracle, args.timeout, ignore_names, args.keep_workdirs)
    if not ok:
        raise SystemExit("Baseline oracle failed before shrinking; fix the oracle/repo first.\n" + output[-4000:])


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    if not repo.exists():
        raise SystemExit(f"Repository root does not exist: {repo}")

    ignore_names = set(DEFAULT_COPY_IGNORE)
    ignore_names.update(args.copy_ignore)
    candidates, skipped_approval_gated = load_candidates(Path(args.candidates), repo, args.allow_approval_gated)
    if not candidates:
        message = "No candidates loaded."
        if skipped_approval_gated:
            message += f" Skipped {len(skipped_approval_gated)} approval-gated candidates; rerun with --allow-approval-gated after explicit approval."
        raise SystemExit(message)

    if not args.skip_baseline:
        baseline_check(repo, args, ignore_names)

    if args.mode == "exact":
        result = exact_search(repo, candidates, args, ignore_names)
        selected = [Candidate(i, item["id"], item["type"], item["path"], item["raw"], item["score"], item["group"]) for i, item in enumerate(result["best_candidates"])]
    elif args.mode == "partition-exact":
        result = partition_exact_search(repo, candidates, args, ignore_names)
        selected = [Candidate(i, item["id"], item["type"], item["path"], item["raw"], item["score"], item["group"]) for i, item in enumerate(result["accepted_candidates"])]
    else:
        result = greedy_search(repo, candidates, args, ignore_names)
        selected = [Candidate(i, item["id"], item["type"], item["path"], item["raw"], item["score"], item["group"]) for i, item in enumerate(result["accepted_candidates"])]

    summary = {
        "mode": args.mode,
        "repo": str(repo),
        "candidate_count": len(candidates),
        "skipped_approval_gated_count": len(skipped_approval_gated),
        "skipped_approval_gated": skipped_approval_gated,
        "approval_gated_included": bool(args.allow_approval_gated),
        "selected_count": len(selected),
        "selected_score": subset_score(selected),
        "selected_ids": [c.id for c in selected],
        "result": result,
        "applied": bool(args.apply),
    }

    if args.apply:
        apply_to_real_repo(repo, selected, args.oracle, args.timeout)

    rendered = json.dumps(summary, indent=2, ensure_ascii=False)
    print(rendered)
    if args.summary_output:
        Path(args.summary_output).write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
