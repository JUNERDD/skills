#!/usr/bin/env python3
"""Validate a receiving-code-review/v2 resolution report and its source linkage."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

REQUIRED_HEADINGS = [
    "Report Contract",
    "Source Review",
    "Current Scope",
    "Re-Review Orchestration",
    "Intake Integrity",
    "Disposition Ledger",
    "Challenges to Source Review",
    "Implementation Plan and Delegation",
    "Code Changes",
    "Verification",
    "Review Refresh",
    "Residual Risks",
    "Final State",
    "Resolution Self-Check",
]
VERDICTS = {
    "Confirmed",
    "Narrowed",
    "Reclassified",
    "Disproved",
    "Stale",
    "Duplicate",
    "Intentional",
    "Unverifiable",
    "Open",
}
ACTIONS = {
    "No change needed",
    "Fix required",
    "Test required",
    "Evidence/answer required",
    "Coverage verification required",
    "Carried forward",
}
IMPLEMENTATION_STATES = {
    "Not needed",
    "Not started",
    "Implemented",
    "Verified",
    "Blocked",
    "Carried forward",
}


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


def duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for value in values:
        if value in seen:
            dupes.add(value)
        seen.add(value)
    return dupes


def ids_from_value(value: str | None) -> set[str]:
    if not value or value.lower() == "none":
        return set()
    return set(re.findall(r"\b(?:F|T|A|I)\d+\b", value))


def source_item_ids(source_text: str) -> tuple[set[str], set[str], set[str]]:
    findings: set[str] = set()
    for row in markdown_rows(section(source_text, "Complete Findings Index", "Blocker")):
        if row and re.fullmatch(r"F\d+", row[0]):
            findings.add(row[0])

    tests: set[str] = set()
    for row in markdown_rows(section(source_text, "Test Gaps", "Review Coverage Ledger")):
        if row and re.fullmatch(r"T\d+", row[0]):
            tests.add(row[0])

    uncovered: set[str] = set()
    for row in markdown_rows(section(source_text, "Review Coverage Ledger", "Subagent Candidate Adjudication")):
        if row and re.fullmatch(r"A\d+", row[0]) and len(row) > 5 and row[5] == "Not covered":
            uncovered.add(row[0])
    return findings, tests, uncovered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resolution_report", type=Path)
    parser.add_argument("--source-report", type=Path)
    args = parser.parse_args()

    errors: list[str] = []

    if not args.resolution_report.is_file():
        print(f"ERROR: resolution report not found: {args.resolution_report}", file=sys.stderr)
        return 2
    text = args.resolution_report.read_text(encoding="utf-8")

    positions: list[int] = []
    for heading in REQUIRED_HEADINGS:
        match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
        if not match:
            errors.append(f"missing required heading: ## {heading}")
        else:
            positions.append(match.start())
    if len(positions) == len(REQUIRED_HEADINGS) and positions != sorted(positions):
        errors.append("required headings are not in the contract order")

    if field(text, "Schema") != "receiving-code-review/v2":
        errors.append("Schema must be receiving-code-review/v2")

    resolution_id = field(text, "Resolution ID")
    if not resolution_id or not re.fullmatch(r"rr-\d{8}-[a-z0-9]{6,32}", resolution_id):
        errors.append("Resolution ID must match rr-YYYYMMDD-<6-32 lowercase letters/digits>")

    if field(text, "Git index mutation by this workflow") != "None":
        errors.append("Git index mutation by this workflow must be None")

    assessment = field(text, "Assessment subagent")
    if not assessment:
        errors.append("Assessment subagent status is required")
    elif not (assessment.startswith("V0 launched") or assessment.startswith("Subagent unavailable")):
        errors.append("Assessment subagent must record V0 launched or the unavailable fallback")

    orchestration = field(text, "Orchestration decision")
    if orchestration not in {"Single verifier", "Parallel specialists"}:
        errors.append("Orchestration decision must be Single verifier or Parallel specialists")

    intake_rows = markdown_rows(section(text, "Intake Integrity", "Disposition Ledger"))
    intake_ids = {row[0] for row in intake_rows if row and re.fullmatch(r"I\d+", row[0])}

    ledger_rows = markdown_rows(section(text, "Disposition Ledger", "Challenges to Source Review"))
    ledger: dict[str, dict[str, str]] = {}
    ledger_id_list: list[str] = []
    for row in ledger_rows:
        if not row or row[0] == "Item ID" or not re.fullmatch(r"(?:F|T|A|I)\d+", row[0]):
            continue
        item_id = row[0]
        ledger_id_list.append(item_id)
        if len(row) < 8:
            errors.append(f"{item_id} disposition row has fewer than 8 columns")
            continue
        ledger[item_id] = {
            "source_status": row[1],
            "verdict": row[2],
            "action": row[3],
            "implementation": row[4],
            "challenge": row[5],
            "evidence": row[6],
            "next_action": row[7],
        }
        if row[2] not in VERDICTS:
            errors.append(f"{item_id} has invalid verdict: {row[2]!r}")
        if row[3] not in ACTIONS:
            errors.append(f"{item_id} has invalid action state: {row[3]!r}")
        if row[4] not in IMPLEMENTATION_STATES:
            errors.append(f"{item_id} has invalid implementation state: {row[4]!r}")
        if not row[6] or row[6].lower() in {"none", "n/a"}:
            errors.append(f"{item_id} lacks disposition evidence")
    for item_id in duplicates(ledger_id_list):
        errors.append(f"duplicate disposition row: {item_id}")

    source_expected: set[str] = set()
    if args.source_report:
        if not args.source_report.is_file():
            errors.append(f"source report not found: {args.source_report}")
        else:
            source_text = args.source_report.read_text(encoding="utf-8")
            if field(source_text, "Schema") != "code-review/v2":
                errors.append("--source-report must have Schema code-review/v2")
            source_report_id = field(source_text, "Report ID")
            linked_source_id = field(text, "Source report ID")
            if source_report_id and linked_source_id != source_report_id:
                errors.append(
                    f"Source report ID mismatch: resolution={linked_source_id!r}, source={source_report_id!r}"
                )
            findings, tests, uncovered = source_item_ids(source_text)
            source_expected = findings | tests | uncovered
            missing = source_expected - set(ledger)
            extra_source_ids = {
                item_id
                for item_id in ledger
                if item_id.startswith(("F", "T", "A")) and item_id not in source_expected
            }
            if missing:
                errors.append(f"source items missing dispositions: {', '.join(sorted(missing))}")
            if extra_source_ids:
                errors.append(
                    "resolution has F/T/A items not present in source item universe: "
                    + ", ".join(sorted(extra_source_ids))
                )

    if intake_ids != {item_id for item_id in ledger if item_id.startswith("I")}:
        missing_intake = intake_ids - set(ledger)
        extra_intake = {item_id for item_id in ledger if item_id.startswith("I")} - intake_ids
        if missing_intake:
            errors.append(f"intake issues missing dispositions: {', '.join(sorted(missing_intake))}")
        if extra_intake:
            errors.append(f"I# dispositions missing from Intake Issues: {', '.join(sorted(extra_intake))}")

    challenge_cards = re.findall(
        r"^###\s+(C\d+)\s+-\s+Challenge to\s+((?:F|T|A|I)\d+)\s*$", text, re.MULTILINE
    )
    challenge_ids = [challenge_id for challenge_id, _ in challenge_cards]
    for challenge_id in duplicates(challenge_ids):
        errors.append(f"duplicate challenge card: {challenge_id}")
    challenge_map = dict(challenge_cards)

    for item_id, data in ledger.items():
        challenge = data["challenge"]
        if challenge != "None":
            if not re.fullmatch(r"C\d+", challenge):
                errors.append(f"{item_id} has invalid challenge reference: {challenge!r}")
            elif challenge not in challenge_map:
                errors.append(f"{item_id} references missing challenge card {challenge}")
            elif challenge_map[challenge] != item_id:
                errors.append(
                    f"{challenge} targets {challenge_map[challenge]} but ledger attaches it to {item_id}"
                )
        if data["verdict"] in {"Narrowed", "Reclassified", "Disproved", "Stale", "Duplicate", "Intentional"}:
            if challenge == "None":
                errors.append(f"{item_id} verdict {data['verdict']} requires a C# challenge card")

    challenge_block = section(text, "Challenges to Source Review", "Implementation Plan and Delegation")
    for challenge_id, target in challenge_cards:
        card_start = re.search(
            rf"^###\s+{re.escape(challenge_id)}\s+-\s+Challenge to\s+{re.escape(target)}\s*$",
            challenge_block,
            re.MULTILINE,
        )
        if not card_start:
            continue
        next_card = re.search(r"^###\s+C\d+\s+-", challenge_block[card_start.end() :], re.MULTILINE)
        card = (
            challenge_block[card_start.start() : card_start.end() + next_card.start()]
            if next_card
            else challenge_block[card_start.start() :]
        )
        required_labels = [
            "Source claim:",
            "Source evidence:",
            "Counterclaim:",
            "Argument:",
            "Counter-evidence:",
            "Limits and residual uncertainty:",
            "Settlement criterion:",
            "Verdict effect:",
        ]
        for label in required_labels:
            if label not in card:
                errors.append(f"{challenge_id} is missing challenge component: {label}")

    actionable = {
        item_id
        for item_id, data in ledger.items()
        if data["action"] in {"Fix required", "Test required"}
    }
    declared_actionable = ids_from_value(field(text, "Actionable IDs"))
    if actionable != declared_actionable:
        missing = actionable - declared_actionable
        extra = declared_actionable - actionable
        if missing:
            errors.append(f"Actionable IDs omits: {', '.join(sorted(missing))}")
        if extra:
            errors.append(f"Actionable IDs includes non-actionable items: {', '.join(sorted(extra))}")

    coding_stage = field(text, "Coding stage")
    coding_subagent = field(text, "Coding subagent")
    if actionable:
        if coding_stage != "Required":
            errors.append("Coding stage must be Required when Fix required or Test required items exist")
        if not coding_subagent or not (
            coding_subagent.startswith("D1 launched") or coding_subagent.startswith("Subagent unavailable")
        ):
            errors.append("actionable items require D1 launched or the unavailable coding fallback")
    else:
        if not coding_stage or not coding_stage.startswith("Not required"):
            errors.append("Coding stage must record Not required when there are no actionable items")
        if coding_subagent != "Not required":
            errors.append("Coding subagent must be Not required when there are no actionable items")

    verification_rows = markdown_rows(section(text, "Verification", "Review Refresh"))
    verified_ids = {
        row[0]
        for row in verification_rows
        if row and re.fullmatch(r"(?:F|T|A|I)\d+", row[0])
    }
    for item_id, data in ledger.items():
        if data["implementation"] in {"Implemented", "Verified"} and item_id not in verified_ids:
            errors.append(f"{item_id} is implemented/verified but lacks Coordinator Verification")

    if field(text, "New changes staged") != "No":
        errors.append("New changes staged must be No")
    if field(text, "Pre-existing staged paths unchanged") not in {"yes", "Yes"}:
        errors.append("Pre-existing staged paths unchanged must be yes")

    final_completion = field(text, "Completion")
    if final_completion not in {"Resolved", "Partially resolved", "Blocked"}:
        errors.append("Final State Completion must be Resolved, Partially resolved, or Blocked")

    if re.search(r"^- `no` ", section(text, "Resolution Self-Check"), re.MULTILINE):
        errors.append("Resolution Self-Check contains a no result")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    source_count = len(source_expected) if args.source_report else "unstructured"
    print(
        "Valid receiving-code-review/v2 resolution report: "
        f"{len(ledger)} dispositions, {len(challenge_cards)} challenges, "
        f"{len(actionable)} actionable items, source_items={source_count}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
