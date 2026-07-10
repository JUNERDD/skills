#!/usr/bin/env python3
"""Validate the canonical structural contract of a code-review Markdown report."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

REQUIRED_HEADINGS = [
    "Report Contract",
    "Scope",
    "Review Orchestration",
    "Review Snapshot",
    "Complete Findings Index",
    "Blocker",
    "Major",
    "Minor",
    "Questions",
    "Test Gaps",
    "Review Coverage Ledger",
    "Subagent Candidate Adjudication",
    "Evidence Appendix",
    "Receiving Handoff",
    "Report Self-Check",
]
SEVERITIES = {"Blocker", "Major", "Minor", "Question"}
RECOMMENDATIONS = {"Block", "Changes requested", "Discuss", "Pass with caveat", "Pass"}


def field(text: str, name: str) -> str | None:
    match = re.search(rf"^- {re.escape(name)}:\s*(?:`([^`]+)`|(.+))$", text, re.MULTILINE)
    if not match:
        return None
    return (match.group(1) or match.group(2)).strip()


def section(text: str, heading: str, next_heading: str | None = None) -> str:
    start = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    if not start:
        return ""
    body_start = start.end()
    if next_heading:
        end = re.search(rf"^## {re.escape(next_heading)}\s*$", text[body_start:], re.MULTILINE)
        if end:
            return text[body_start : body_start + end.start()]
    end = re.search(r"^## .+$", text[body_start:], re.MULTILINE)
    if end:
        return text[body_start : body_start + end.start()]
    return text[body_start:]


def markdown_rows(block: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip().strip("`") for cell in line[1:-1].split("|")]
        if not cells or all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def ids_from_field(value: str | None, prefix: str) -> set[str]:
    if not value or value.lower() == "none":
        return set()
    return set(re.findall(rf"\b{re.escape(prefix)}\d+\b", value))


def duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for value in values:
        if value in seen:
            dupes.add(value)
        seen.add(value)
    return dupes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    if not args.report.is_file():
        print(f"ERROR: report not found: {args.report}", file=sys.stderr)
        return 2

    text = args.report.read_text(encoding="utf-8")

    heading_positions: list[int] = []
    for heading in REQUIRED_HEADINGS:
        match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
        if not match:
            errors.append(f"missing required heading: ## {heading}")
        else:
            heading_positions.append(match.start())
    if len(heading_positions) == len(REQUIRED_HEADINGS) and heading_positions != sorted(heading_positions):
        errors.append("required headings are not in the contract order")

    if field(text, "Report type") != "code-review":
        errors.append("Report type must be code-review")

    report_id = field(text, "Report ID")
    if not report_id or not re.fullmatch(r"cr-\d{8}-[a-z0-9]{6,32}", report_id):
        errors.append("Report ID must match cr-YYYYMMDD-<6-32 lowercase letters/digits>")

    git_mutation = field(text, "Git mutation during review")
    if git_mutation != "None":
        errors.append("Git mutation during review must be None")

    orchestration = field(text, "Orchestration decision")
    if orchestration not in {"Single reviewer", "Parallel specialists"}:
        errors.append("Orchestration decision must be Single reviewer or Parallel specialists")

    assessment = field(text, "Assessment subagent")
    if not assessment:
        errors.append("Assessment subagent status is required")
    elif not (assessment.startswith("R0 launched") or assessment.startswith("Subagent unavailable")):
        errors.append("Assessment subagent must record R0 launched or the unavailable fallback")

    recommendation = field(text, "Recommendation")
    if recommendation not in RECOMMENDATIONS:
        errors.append(f"invalid Recommendation: {recommendation!r}")

    completion = field(text, "Completion")
    if not completion:
        errors.append("Completion is required")

    index_block = section(text, "Complete Findings Index", "Blocker")
    index_rows = markdown_rows(index_block)
    indexed: dict[str, str] = {}
    for row in index_rows:
        if not row or row[0] == "ID":
            continue
        finding_id = row[0]
        if not re.fullmatch(r"F\d+", finding_id):
            continue
        if len(row) < 2 or row[1] not in SEVERITIES:
            errors.append(f"{finding_id} has invalid or missing severity in Complete Findings Index")
            continue
        if finding_id in indexed:
            errors.append(f"duplicate finding in Complete Findings Index: {finding_id}")
        indexed[finding_id] = row[1]

    card_matches = re.findall(
        r"^###\s+(F\d+)\s+(Blocker|Major|Minor|Question)\s+-\s+.+$", text, re.MULTILINE
    )
    card_ids = [finding_id for finding_id, _ in card_matches]
    for finding_id in duplicates(card_ids):
        errors.append(f"duplicate finding card: {finding_id}")
    cards = dict(card_matches)

    if set(indexed) != set(cards):
        missing_cards = sorted(set(indexed) - set(cards))
        missing_index = sorted(set(cards) - set(indexed))
        if missing_cards:
            errors.append(f"indexed findings missing cards: {', '.join(missing_cards)}")
        if missing_index:
            errors.append(f"finding cards missing from index: {', '.join(missing_index)}")
    for finding_id in sorted(set(indexed) & set(cards)):
        if indexed[finding_id] != cards[finding_id]:
            errors.append(
                f"severity mismatch for {finding_id}: index={indexed[finding_id]}, card={cards[finding_id]}"
            )

    tests_block = section(text, "Test Gaps", "Review Coverage Ledger")
    test_rows = markdown_rows(tests_block)
    tests: dict[str, str] = {}
    for row in test_rows:
        if not row or row[0] == "ID":
            continue
        test_id = row[0]
        if not re.fullmatch(r"T\d+", test_id):
            continue
        if len(row) < 2 or row[1] not in {"Blocker", "Major", "Minor"}:
            errors.append(f"{test_id} has invalid or missing severity")
            continue
        if test_id in tests:
            errors.append(f"duplicate test gap: {test_id}")
        tests[test_id] = row[1]

    coverage_block = section(text, "Review Coverage Ledger", "Subagent Candidate Adjudication")
    coverage_rows = markdown_rows(coverage_block)
    areas: dict[str, str] = {}
    valid_statuses = {
        "Reviewed - no issue found",
        "Not review-relevant",
        "Not covered",
    }
    for row in coverage_rows:
        if not row or row[0] == "Area ID":
            continue
        area_id = row[0]
        if not re.fullmatch(r"A\d+", area_id):
            continue
        if area_id in areas:
            errors.append(f"duplicate coverage area: {area_id}")
        status = row[5] if len(row) > 5 else ""
        areas[area_id] = status
        finding_ref = re.fullmatch(r"Finding\s+(F\d+)", status)
        if finding_ref:
            if finding_ref.group(1) not in indexed:
                errors.append(f"{area_id} references unknown finding {finding_ref.group(1)}")
        elif status not in valid_statuses:
            errors.append(f"{area_id} has invalid coverage status: {status!r}")
        if status == "Not covered":
            evidence = row[7] if len(row) > 7 else ""
            if not evidence or evidence.lower() in {"none", "n/a"}:
                errors.append(f"{area_id} is Not covered but lacks a reason and next step")

    if not areas:
        errors.append("Review Coverage Ledger must contain at least one A# row")

    observed_severities = list(indexed.values()) + list(tests.values())
    has_not_covered = any(status == "Not covered" for status in areas.values())
    incomplete = bool(completion and completion.startswith("Incomplete"))
    if "Blocker" in observed_severities:
        expected_recommendation = "Block"
    elif "Major" in observed_severities:
        expected_recommendation = "Changes requested"
    elif "Question" in observed_severities:
        expected_recommendation = "Discuss"
    elif has_not_covered or incomplete:
        expected_recommendation = "Discuss"
    elif "Minor" in observed_severities:
        expected_recommendation = "Pass with caveat"
    else:
        expected_recommendation = "Pass"
    if recommendation and recommendation != expected_recommendation:
        errors.append(
            f"Recommendation must be {expected_recommendation!r} for the unresolved item/coverage state, got {recommendation!r}"
        )

    known_findings = set(indexed)
    known_tests = set(tests)
    known_areas = set(areas)
    handoff_checks = [
        ("Actionable finding IDs", "F", known_findings),
        ("Actionable test-gap IDs", "T", known_tests),
        ("Open question IDs", "F", known_findings),
        ("Open coverage area IDs", "A", known_areas),
    ]
    for field_name, prefix, known in handoff_checks:
        value = field(text, field_name)
        if value is None:
            errors.append(f"Receiving Handoff is missing {field_name}")
            continue
        unknown = ids_from_field(value, prefix) - known
        if unknown:
            errors.append(f"{field_name} references unknown IDs: {', '.join(sorted(unknown))}")

    if re.search(r"^- `no` ", section(text, "Report Self-Check"), re.MULTILINE):
        errors.append("Report Self-Check contains a no result")

    if "[" in (report_id or "") or "<random-id>" in text:
        warnings.append("report appears to contain template placeholders")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        return 1

    print(
        "Valid code-review report: "
        f"{len(indexed)} findings, {len(tests)} test gaps, {len(areas)} coverage areas, "
        f"recommendation={recommendation}."
    )
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
