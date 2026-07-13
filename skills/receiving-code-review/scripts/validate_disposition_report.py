#!/usr/bin/env python3
"""Validate receiving-code-review lineage, execution chains, and bounded follow-up."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

REQUIRED_HEADINGS = [
    "Report Contract",
    "Source Review",
    "Current Scope",
    "Re-Review Orchestration",
    "Intake Integrity",
    "Disposition Lineage",
    "Execution Chain Reconstruction",
    "Disposition Ledger",
    "Challenges to Source Review",
    "Implementation Plan and Delegation",
    "Code Changes",
    "Verification",
    "Post-Implementation Review",
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
FIXABLE_VERDICTS = {"Confirmed", "Narrowed", "Reclassified"}
PROTECTED_VERDICTS = {"Disproved", "Stale", "Duplicate", "Intentional"}
UNRESOLVED_VERDICTS = {"Unverifiable", "Open"}
EVIDENCE_ACTIONS = {"Evidence/answer required", "Coverage verification required", "Carried forward"}
REPORT_ID = re.compile(r"cr-\d{8}-[a-z0-9]{6,32}")
RESOLUTION_ID = re.compile(r"rr-\d{8}-[a-z0-9]{6,32}")
CHAIN_ID = re.compile(r"rc-\d{8}-[a-z0-9]{6,32}")
ISSUE_FINGERPRINT = re.compile(r"ifp-sha256:[0-9a-f]{64}")
EXECUTION_CHAIN_ID = re.compile(r"EC\d+")
BASIS = re.compile(
    r"kind:(owner-decision|requirement|public-contract|approved-design|hard-invariant|"
    r"test-evidence|code-history|product-intent); "
    r"strength:(authoritative|inferred|unavailable); evidence:(.+)"
)
FINDING_KEY = re.compile(r"behavior; entry=([^;]+); contract=([^;]+); effect=([^;]+)")
TEST_GAP_KEY = re.compile(r"test-gap; entry=([^;]+); contract=([^;]+); gap=([^;]+)")
DELTA = re.compile(r"kind:(code|contract|evidence); ref:([^;]+); change:(.+)")
AUTHORITATIVE_KINDS = {
    "owner-decision",
    "requirement",
    "public-contract",
    "approved-design",
    "hard-invariant",
}
INFERRED_KINDS = {"test-evidence", "code-history", "product-intent"}
POST_REVIEW_REQUIRED_HEADINGS = [
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
    "Prior Resolution Reconciliation",
    "Receiving Handoff",
    "Report Self-Check",
]
LOCAL_IDENTITY = re.compile(
    r"\b(?:F|T|A|I|C|R|V|D|EC)\d+\b|\bgeneration\s+[01]\b|#L\d+|"
    r"\bline\s+\d+\b|\b[\w./\\-]+:\d+\b",
    re.IGNORECASE,
)


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


def execution_chain_ids(value: str) -> set[str]:
    return set(re.findall(r"\bEC\d+\b", value))


def expected_fingerprint(issue_key: str) -> str:
    return "ifp-sha256:" + hashlib.sha256(issue_key.encode("utf-8")).hexdigest()


def is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        normalized
        in {
            "",
            "none",
            "n/a",
            "unknown",
            "tbd",
            "todo",
            "placeholder",
            "not checked",
            "unverified",
        }
        or "<" in value
        or "[" in value
    )


def valid_delta(value: str) -> bool:
    match = DELTA.fullmatch(value.strip())
    return bool(match and all(not is_placeholder(part) for part in match.groups()[1:]))


def valid_issue_key(item_id: str, issue_key: str) -> bool:
    pattern = TEST_GAP_KEY if item_id.startswith("T") else FINDING_KEY
    match = pattern.fullmatch(issue_key)
    return bool(
        match
        and not LOCAL_IDENTITY.search(issue_key)
        and all(not is_placeholder(part) for part in match.groups())
    )


def source_items(source_text: str) -> dict[str, dict[str, str]]:
    items: dict[str, dict[str, str]] = {}
    for row in markdown_rows(section(source_text, "Complete Findings Index", "Blocker")):
        if row and re.fullmatch(r"F\d+", row[0]) and len(row) >= 10:
            items[row[0]] = {
                "status": row[1],
                "issue_key": row[7],
                "fingerprint": row[8],
            }
    for row in markdown_rows(section(source_text, "Test Gaps", "Review Coverage Ledger")):
        if row and re.fullmatch(r"T\d+", row[0]) and len(row) >= 10:
            items[row[0]] = {
                "status": f"{row[1]} test gap",
                "issue_key": row[7],
                "fingerprint": row[8],
            }
    for row in markdown_rows(
        section(source_text, "Review Coverage Ledger", "Subagent Candidate Adjudication")
    ):
        if row and re.fullmatch(r"A\d+", row[0]) and len(row) > 5 and row[5] == "Not covered":
            items[row[0]] = {
                "status": "Not covered",
                "issue_key": "N/A",
                "fingerprint": "N/A",
            }
    return items


def parent_verdicts(parent_text: str) -> dict[str, str]:
    verdicts: dict[str, str] = {}
    rows = markdown_rows(section(parent_text, "Disposition Ledger", "Challenges to Source Review"))
    for row in rows:
        if row and re.fullmatch(r"(?:F|T|A|I)\d+", row[0]) and len(row) >= 5:
            fingerprint = row[1]
            if ISSUE_FINGERPRINT.fullmatch(fingerprint):
                verdicts[fingerprint] = row[4]
    return verdicts


def parse_int_field(text: str, name: str, allowed: set[int], errors: list[str]) -> int | None:
    raw = field(text, name)
    if raw is None or not raw.isdigit() or int(raw) not in allowed:
        errors.append(f"{name} must be one of {sorted(allowed)}")
        return None
    return int(raw)


def resolve_report_path(raw_path: str | None, resolution_path: Path) -> Path | None:
    if not raw_path or raw_path == "None":
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path
    cwd_candidate = Path.cwd() / path
    if cwd_candidate.exists():
        return cwd_candidate
    return resolution_path.parent / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resolution_report", type=Path)
    parser.add_argument("--source-report", type=Path)
    parser.add_argument("--parent-resolution", type=Path)
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

    if field(text, "Report type") != "receiving-code-review":
        errors.append("Report type must be receiving-code-review")
    resolution_id = field(text, "Resolution ID")
    if not resolution_id or not RESOLUTION_ID.fullmatch(resolution_id):
        errors.append("Resolution ID must match rr-YYYYMMDD-<6-32 lowercase letters/digits>")
    review_chain_id = field(text, "Review chain ID")
    if not review_chain_id or not CHAIN_ID.fullmatch(review_chain_id):
        errors.append("Review chain ID must match rc-YYYYMMDD-<6-32 lowercase letters/digits>")
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

    source_generation = parse_int_field(text, "Source review generation", {0, 1}, errors)
    source_trigger = field(text, "Source review trigger")
    continuation_authority = field(text, "Continuation authority")
    source_parent_id = field(text, "Source parent resolution ID")
    source_parent_path = field(text, "Source parent resolution path")

    source_expected: dict[str, dict[str, str]] = {}
    source_text: str | None = None
    if args.source_report:
        if not args.source_report.is_file():
            errors.append(f"source report not found: {args.source_report}")
        else:
            source_text = args.source_report.read_text(encoding="utf-8")
            if field(source_text, "Report type") != "code-review":
                errors.append("--source-report must have Report type code-review")
            if field(text, "Source report ID") != field(source_text, "Report ID"):
                errors.append("Source report ID does not match --source-report")
            if review_chain_id != field(source_text, "Review chain ID"):
                errors.append("resolution and source report must use the same Review chain ID")
            if str(source_generation) != field(source_text, "Review generation"):
                errors.append("Source review generation does not match --source-report")
            if source_trigger != field(source_text, "Review trigger"):
                errors.append("Source review trigger does not match --source-report")
            if source_parent_id != field(source_text, "Parent resolution ID"):
                errors.append("Source parent resolution ID does not match --source-report")
            if source_parent_path != field(source_text, "Parent resolution path"):
                errors.append("Source parent resolution path does not match --source-report")
            source_expected = source_items(source_text)

    parent_text: str | None = None
    if source_generation == 0:
        if continuation_authority != "Initial receiving handoff":
            errors.append("generation 0 source must use Initial receiving handoff authority")
        if source_parent_id != "None" or source_parent_path != "None":
            errors.append("generation 0 source must not have a parent resolution")
        if args.parent_resolution:
            errors.append("generation 0 source must not receive --parent-resolution")
    elif source_generation == 1:
        if continuation_authority != "Explicit current user instruction":
            errors.append("generation 1 source requires Explicit current user instruction")
        if not source_parent_id or not RESOLUTION_ID.fullmatch(source_parent_id):
            errors.append("generation 1 source must link a valid parent resolution ID")
        if not source_parent_path or source_parent_path == "None":
            errors.append("generation 1 source must link a parent resolution path")
        if not args.parent_resolution or not args.parent_resolution.is_file():
            errors.append("generation 1 validation requires --parent-resolution")
        else:
            parent_text = args.parent_resolution.read_text(encoding="utf-8")
            if field(parent_text, "Report type") != "receiving-code-review":
                errors.append("--parent-resolution must be a receiving-code-review report")
            if field(parent_text, "Resolution ID") != source_parent_id:
                errors.append("Source parent resolution ID does not match --parent-resolution")
            if field(parent_text, "Review chain ID") != review_chain_id:
                errors.append("parent resolution must use the same Review chain ID")

    intake_rows = markdown_rows(section(text, "Intake Integrity", "Disposition Lineage"))
    intake_ids = {row[0] for row in intake_rows if row and re.fullmatch(r"I\d+", row[0])}

    lineage_rows = markdown_rows(
        section(text, "Disposition Lineage", "Execution Chain Reconstruction")
    )
    lineage: dict[str, dict[str, str]] = {}
    lineage_id_list: list[str] = []
    for row in lineage_rows:
        if not row or row[0] == "Item ID" or not re.fullmatch(r"(?:F|T)\d+", row[0]):
            continue
        item_id = row[0]
        lineage_id_list.append(item_id)
        if len(row) < 7:
            errors.append(f"{item_id} lineage row has fewer than 7 columns")
            continue
        lineage[item_id] = {
            "issue_key": row[1],
            "fingerprint": row[2],
            "parent": row[3],
            "delta": row[4],
            "state": row[5],
            "evidence": row[6],
        }
        if not valid_issue_key(item_id, row[1]):
            errors.append(f"{item_id} lineage has an invalid semantic Issue key")
        if row[2] != expected_fingerprint(row[1]) or not ISSUE_FINGERPRINT.fullmatch(row[2]):
            errors.append(f"{item_id} lineage fingerprint does not match sha256(Issue key)")
        if row[5] not in {"New", "Inherited", "Reopened"}:
            errors.append(f"{item_id} has invalid lineage state: {row[5]!r}")
        if not row[6] or row[6].lower() in {"none", "n/a"}:
            errors.append(f"{item_id} lineage lacks evidence")
    for item_id in duplicates(lineage_id_list):
        errors.append(f"duplicate lineage row: {item_id}")

    expected_lineage = {item_id for item_id in source_expected if item_id.startswith(("F", "T"))}
    if source_text and set(lineage) != expected_lineage:
        missing = expected_lineage - set(lineage)
        extra = set(lineage) - expected_lineage
        if missing:
            errors.append(f"source F/T items missing lineage: {', '.join(sorted(missing))}")
        if extra:
            errors.append(f"lineage has items absent from source: {', '.join(sorted(extra))}")
    for item_id, data in lineage.items():
        expected = source_expected.get(item_id)
        if expected:
            if data["issue_key"] != expected["issue_key"]:
                errors.append(f"{item_id} lineage Issue key does not match source")
            if data["fingerprint"] != expected["fingerprint"]:
                errors.append(f"{item_id} lineage fingerprint does not match source")
        if source_generation == 0 and data["state"] != "New":
            errors.append(f"generation 0 lineage item {item_id} must be New")

    chains_rows = markdown_rows(
        section(text, "Execution Chain Reconstruction", "Disposition Ledger")
    )
    chains: dict[str, dict[str, object]] = {}
    chain_id_list: list[str] = []
    for row in chains_rows:
        if not row or row[0] == "Chain ID" or not EXECUTION_CHAIN_ID.fullmatch(row[0]):
            continue
        chain_id = row[0]
        chain_id_list.append(chain_id)
        if len(row) < 10:
            errors.append(f"{chain_id} execution-chain row has fewer than 10 columns")
            continue
        basis = BASIS.fullmatch(row[7])
        if not basis:
            errors.append(f"{chain_id} has invalid Expected basis structure")
            basis_strength = "unavailable"
        else:
            basis_kind = basis.group(1)
            basis_strength = basis.group(2)
            evidence = basis.group(3).strip().lower()
            if evidence in {"", "none", "n/a", "unknown"} or "<" in evidence or "[" in evidence:
                errors.append(f"{chain_id} Expected basis lacks concrete evidence")
            if basis_kind in AUTHORITATIVE_KINDS and basis_strength != "authoritative":
                errors.append(f"{chain_id} Expected basis kind {basis_kind} must be authoritative")
            if basis_kind in INFERRED_KINDS and basis_strength == "authoritative":
                errors.append(f"{chain_id} Expected basis kind {basis_kind} cannot be authoritative")
        if row[9] not in {"Complete", "Blocked"}:
            errors.append(f"{chain_id} has invalid chain status: {row[9]!r}")
        if not row[8] or row[8].lower() in {"none", "n/a"}:
            errors.append(f"{chain_id} lacks chain evidence or an explicit gap")
        if row[9] == "Complete":
            labels = ["trigger/entry", "guards/alternates", "propagation", "terminal effect", "failure semantics"]
            for label, value in zip(labels, row[2:7]):
                if is_placeholder(value):
                    errors.append(f"{chain_id} Complete chain lacks concrete {label}")
            if is_placeholder(row[8]):
                errors.append(f"{chain_id} Complete chain lacks concrete evidence")
        chains[chain_id] = {
            "items": ids_from_value(row[1]),
            "basis_strength": basis_strength,
            "status": row[9],
        }
    for chain_id in duplicates(chain_id_list):
        errors.append(f"duplicate execution chain: {chain_id}")

    ledger_rows = markdown_rows(section(text, "Disposition Ledger", "Challenges to Source Review"))
    ledger: dict[str, dict[str, object]] = {}
    ledger_id_list: list[str] = []
    for row in ledger_rows:
        if not row or row[0] == "Item ID" or not re.fullmatch(r"(?:F|T|A|I)\d+", row[0]):
            continue
        item_id = row[0]
        ledger_id_list.append(item_id)
        if len(row) < 10:
            errors.append(f"{item_id} disposition row has fewer than 10 columns")
            continue
        ledger[item_id] = {
            "fingerprint": row[1],
            "chains": execution_chain_ids(row[2]),
            "source_status": row[3],
            "verdict": row[4],
            "action": row[5],
            "implementation": row[6],
            "challenge": row[7],
            "evidence": row[8],
            "next_action": row[9],
        }
        if row[4] not in VERDICTS:
            errors.append(f"{item_id} has invalid verdict: {row[4]!r}")
        if row[5] not in ACTIONS:
            errors.append(f"{item_id} has invalid action state: {row[5]!r}")
        if row[6] not in IMPLEMENTATION_STATES:
            errors.append(f"{item_id} has invalid implementation state: {row[6]!r}")
        if not row[8] or row[8].lower() in {"none", "n/a"}:
            errors.append(f"{item_id} lacks disposition evidence")
        if item_id.startswith(("F", "T")):
            expected = lineage.get(item_id)
            if not expected or row[1] != expected["fingerprint"]:
                errors.append(f"{item_id} disposition fingerprint does not match lineage")
        elif row[1] != "N/A":
            errors.append(f"{item_id} must use N/A issue fingerprint")

        item_chains = execution_chain_ids(row[2])
        if item_id.startswith(("F", "T", "A")):
            if not item_chains:
                errors.append(f"{item_id} must reference at least one EC# execution chain")
            for chain_id in item_chains:
                if chain_id not in chains:
                    errors.append(f"{item_id} references unknown execution chain {chain_id}")
                elif item_id not in chains[chain_id]["items"]:
                    errors.append(f"{chain_id} does not list referenced item {item_id}")
        elif row[2] != "N/A":
            errors.append(f"{item_id} intake-only item must use N/A execution chain")

    for item_id in duplicates(ledger_id_list):
        errors.append(f"duplicate disposition row: {item_id}")

    if source_text:
        missing = set(source_expected) - set(ledger)
        extra = {
            item_id
            for item_id in ledger
            if item_id.startswith(("F", "T", "A")) and item_id not in source_expected
        }
        if missing:
            errors.append(f"source items missing dispositions: {', '.join(sorted(missing))}")
        if extra:
            errors.append(f"resolution has source items absent from report: {', '.join(sorted(extra))}")
    if intake_ids != {item_id for item_id in ledger if item_id.startswith("I")}:
        errors.append("Intake Issues and I# disposition rows must match exactly")

    protected = parent_verdicts(parent_text) if parent_text else {}
    for item_id, data in lineage.items():
        fingerprint = data["fingerprint"]
        parent_verdict = protected.get(fingerprint)
        if source_generation == 1 and parent_verdict in PROTECTED_VERDICTS:
            if data["state"] not in {"Inherited", "Reopened"}:
                errors.append(f"{item_id} protected parent decision must be Inherited or Reopened")
            if data["state"] == "Inherited":
                ledger_item = ledger.get(item_id, {})
                if ledger_item.get("verdict") != parent_verdict:
                    errors.append(f"{item_id} inherited verdict must remain {parent_verdict}")
                if ledger_item.get("action") != "No change needed":
                    errors.append(f"{item_id} inherited protected verdict must need no change")
            elif not valid_delta(data["delta"]):
                errors.append(
                    f"{item_id} reopened protected decision requires structured code/contract/evidence delta"
                )
        elif data["state"] == "Inherited":
            errors.append(f"{item_id} cannot be Inherited without a matching protected parent verdict")

    for item_id, data in ledger.items():
        verdict = data["verdict"]
        action = data["action"]
        implementation = data["implementation"]
        item_chains = data["chains"]
        chain_statuses = {chains[chain_id]["status"] for chain_id in item_chains if chain_id in chains}
        chain_strengths = {
            chains[chain_id]["basis_strength"] for chain_id in item_chains if chain_id in chains
        }
        if "Blocked" in chain_statuses and verdict not in UNRESOLVED_VERDICTS:
            errors.append(f"{item_id} has a Blocked execution chain and must be Open or Unverifiable")
        if chain_strengths and chain_strengths != {"authoritative"} and verdict not in UNRESOLVED_VERDICTS:
            errors.append(
                f"{item_id} lacks authoritative expected-behavior basis and must be Open or Unverifiable"
            )
        if verdict == "Intentional":
            if not chain_strengths or chain_strengths != {"authoritative"}:
                errors.append(f"{item_id} Intentional verdict requires authoritative chain basis")
        if verdict in PROTECTED_VERDICTS:
            if action != "No change needed" or implementation != "Not needed":
                errors.append(
                    f"{item_id} verdict {verdict} requires No change needed + Not needed"
                )
        elif verdict in UNRESOLVED_VERDICTS:
            if action not in EVIDENCE_ACTIONS:
                errors.append(f"{item_id} verdict {verdict} cannot require a fix or test")
        elif verdict in FIXABLE_VERDICTS:
            if action not in {
                "Fix required",
                "Test required",
                "Evidence/answer required",
                "Coverage verification required",
                "Carried forward",
            }:
                errors.append(f"{item_id} verdict {verdict} has incompatible action {action}")

        if action == "No change needed" and implementation != "Not needed":
            errors.append(f"{item_id} No change needed requires Not needed implementation")
        elif action in {"Fix required", "Test required"}:
            if verdict not in FIXABLE_VERDICTS:
                errors.append(f"{item_id} actionable fix/test requires a confirmed-type verdict")
            if chain_statuses != {"Complete"}:
                errors.append(f"{item_id} actionable fix/test requires only Complete execution chains")
            if implementation not in {"Not started", "Implemented", "Verified", "Blocked"}:
                errors.append(f"{item_id} actionable fix/test has incompatible implementation state")
        elif action == "Carried forward" and implementation != "Carried forward":
            errors.append(f"{item_id} Carried forward action requires Carried forward implementation")
        elif action in {"Evidence/answer required", "Coverage verification required"} and implementation not in {
            "Not started",
            "Verified",
            "Blocked",
            "Carried forward",
        }:
            errors.append(f"{item_id} evidence/coverage action has incompatible implementation state")

    challenge_cards = re.findall(
        r"^###\s+(C\d+)\s+-\s+Challenge to\s+((?:F|T|A|I)\d+)\s*$",
        text,
        re.MULTILINE,
    )
    challenge_ids = [challenge_id for challenge_id, _ in challenge_cards]
    for challenge_id in duplicates(challenge_ids):
        errors.append(f"duplicate challenge card: {challenge_id}")
    challenge_map = dict(challenge_cards)
    referenced_challenges: set[str] = set()
    for item_id, data in ledger.items():
        challenge = data["challenge"]
        if challenge != "None":
            referenced_challenges.add(str(challenge))
            if not re.fullmatch(r"C\d+", challenge):
                errors.append(f"{item_id} has invalid challenge reference: {challenge!r}")
            elif challenge not in challenge_map:
                errors.append(f"{item_id} references missing challenge card {challenge}")
            elif challenge_map[challenge] != item_id:
                errors.append(f"{challenge} targets {challenge_map[challenge]} but ledger uses it for {item_id}")
        if data["verdict"] in {
            "Narrowed",
            "Reclassified",
            "Disproved",
            "Stale",
            "Duplicate",
            "Intentional",
        } and challenge == "None":
            errors.append(f"{item_id} verdict {data['verdict']} requires a C# challenge card")
    for challenge_id in set(challenge_map) - referenced_challenges:
        errors.append(f"{challenge_id} challenge card is not referenced by its disposition")

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
        for label in [
            "Execution chains:",
            "Source claim:",
            "Source evidence:",
            "Counterclaim:",
            "Argument:",
            "Counter-evidence:",
            "Limits and residual uncertainty:",
            "Settlement criterion:",
            "Decision authority:",
            "Reopen condition:",
            "Verdict effect:",
        ]:
            if label not in card:
                errors.append(f"{challenge_id} is missing challenge component: {label}")
        ledger_item = ledger.get(target)
        if ledger_item is None:
            errors.append(f"{challenge_id} targets unknown disposition {target}")
            continue
        verdict_effect = re.search(
            r"^- Re-review verdict:\s*`([^`]+)`\s*$", card, re.MULTILINE
        )
        action_effect = re.search(
            r"^- Severity/action effect:\s*`([^`]+)`\s*$", card, re.MULTILINE
        )
        if not verdict_effect:
            errors.append(f"{challenge_id} must record an exact Re-review verdict effect")
        elif verdict_effect.group(1) != ledger_item["verdict"]:
            errors.append(f"{challenge_id} Re-review verdict effect disagrees with {target}")
        if not action_effect:
            errors.append(f"{challenge_id} must record an exact action-state effect")
        elif action_effect.group(1) != ledger_item["action"]:
            errors.append(f"{challenge_id} action-state effect disagrees with {target}")

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

    assignment_rows = markdown_rows(
        section(text, "Implementation Plan and Delegation", "Code Changes")
    )
    assigned_item_list: list[str] = []
    assignment_agents: dict[str, set[str]] = {}
    for row in assignment_rows:
        if not row or row[0] == "Coding agent":
            continue
        if len(row) < 6:
            errors.append("Coding Assignments row has fewer than 6 columns")
            continue
        row_ids = ids_from_value(row[1])
        if not row_ids:
            errors.append(f"Coding assignment for {row[0]!r} lacks actionable item IDs")
        assigned_item_list.extend(sorted(row_ids))
        for item_id in row_ids:
            assignment_agents.setdefault(item_id, set()).add(row[0])
        for label, value in [
            ("coding agent", row[0]),
            ("file ownership", row[2]),
            ("expected result", row[3]),
            ("required verification", row[4]),
        ]:
            if is_placeholder(value):
                errors.append(f"Coding assignment has non-concrete {label}")
        if row[5] not in {"Complete", "Partial", "Failed", "Fallback"}:
            errors.append(f"Coding assignment has invalid status: {row[5]!r}")
    for item_id in duplicates(assigned_item_list):
        errors.append(f"actionable item is assigned more than once: {item_id}")
    assigned_items = set(assigned_item_list)
    if assigned_items != actionable:
        missing = actionable - assigned_items
        extra = assigned_items - actionable
        if missing:
            errors.append(f"Coding Assignments omits actionable items: {', '.join(sorted(missing))}")
        if extra:
            errors.append(
                f"Coding Assignments includes non-actionable items: {', '.join(sorted(extra))}"
            )

    coding_stage = field(text, "Coding stage")
    coding_subagent = field(text, "Coding subagent")
    coding_mode = field(text, "Coding mode")
    if actionable:
        if coding_stage != "Required":
            errors.append("Coding stage must be Required when actionable items exist")
        if not coding_subagent or not (
            coding_subagent.startswith("D1 launched") or coding_subagent.startswith("Subagent unavailable")
        ):
            errors.append("actionable items require D1 launched or the unavailable fallback")
        if coding_mode not in {"Single coding agent", "Multiple disjoint agents"}:
            errors.append("actionable items require a concrete Coding mode")
    else:
        if not coding_stage or not coding_stage.startswith("Not required"):
            errors.append("Coding stage must record Not required when there are no actionable items")
        if coding_subagent != "Not required":
            errors.append("Coding subagent must be Not required when there are no actionable items")
        if coding_mode != "Not applicable":
            errors.append("Coding mode must be Not applicable when there are no actionable items")

    code_change_rows = markdown_rows(section(text, "Code Changes", "Verification"))
    changed_item_list: list[str] = []
    for row in code_change_rows:
        if not row or row[0] == "Item ID" or not re.fullmatch(r"(?:F|T|A|I)\d+", row[0]):
            continue
        changed_item_list.append(row[0])
        if len(row) < 5:
            errors.append(f"{row[0]} Code Changes row has fewer than 5 columns")
            continue
        for label, value in [
            ("coding agent", row[1]),
            ("changed files", row[2]),
            ("focused change", row[3]),
            ("unrelated churn check", row[4]),
        ]:
            if is_placeholder(value):
                errors.append(f"{row[0]} Code Changes row has non-concrete {label}")
        if row[0] in assignment_agents and row[1] not in assignment_agents[row[0]]:
            errors.append(f"{row[0]} Code Changes coding agent disagrees with Coding Assignments")
    for item_id in duplicates(changed_item_list):
        errors.append(f"duplicate Code Changes row: {item_id}")
    changed_items = set(changed_item_list)
    expected_changed_items = {
        item_id
        for item_id, data in ledger.items()
        if data["implementation"] in {"Implemented", "Verified"}
    }
    if changed_items != expected_changed_items:
        missing = expected_changed_items - changed_items
        extra = changed_items - expected_changed_items
        if missing:
            errors.append(
                "Code Changes omits implemented/verified items: " + ", ".join(sorted(missing))
            )
        if extra:
            errors.append(
                "Code Changes includes items not marked implemented/verified: "
                + ", ".join(sorted(extra))
            )

    verification_rows = markdown_rows(section(text, "Verification", "Post-Implementation Review"))
    verified_ids = {
        row[0] for row in verification_rows if row and re.fullmatch(r"(?:F|T|A|I)\d+", row[0])
    }
    for item_id, data in ledger.items():
        if data["implementation"] in {"Implemented", "Verified"} and item_id not in verified_ids:
            errors.append(f"{item_id} is implemented/verified but lacks Coordinator Verification")
    if field(text, "New changes staged") != "No":
        errors.append("New changes staged must be No")
    if field(text, "Pre-existing staged paths unchanged") not in {"yes", "Yes"}:
        errors.append("Pre-existing staged paths unchanged must be yes")

    budget = parse_int_field(text, "Post-review budget at intake", {0, 1}, errors)
    runs_used = parse_int_field(text, "Post-review runs used", {0, 1}, errors)
    expected_budget = 1 if source_generation == 0 else 0 if source_generation == 1 else None
    if expected_budget is not None and budget != expected_budget:
        errors.append(f"source generation {source_generation} must have post-review budget {expected_budget}")
    if budget is not None and runs_used is not None and runs_used > budget:
        errors.append("Post-review runs used exceeds the available budget")
    if field(text, "Automatic follow-on receiving") != "No":
        errors.append("Automatic follow-on receiving must be No")
    required = field(text, "Post-implementation review required")
    post_generation = field(text, "Post-review generation")
    post_scope = field(text, "Post-review scope")
    post_report_id = field(text, "Post-review report ID")
    post_report_path = field(text, "Post-review report path")
    post_recommendation = field(text, "Post-review recommendation")
    post_scope_fingerprint = field(text, "Post-review scope fingerprint")
    remaining_post_items = field(text, "Remaining review items after post-review")
    if required and required.startswith("yes"):
        if budget != 1 or runs_used != 1:
            errors.append("a required post-review must consume the one available run")
        if post_generation != "1":
            errors.append("a required post-review must be generation 1")
        if not post_scope or post_scope == "None" or "affected EC" not in post_scope:
            errors.append("post-review scope must be the implementation delta plus affected EC# chains")
        if not post_report_id or not REPORT_ID.fullmatch(post_report_id):
            errors.append("a required post-review must link a valid report ID")
        if post_recommendation not in {
            "Block",
            "Changes requested",
            "Discuss",
            "Pass with caveat",
            "Pass",
        }:
            errors.append("a required post-review must record its recommendation")
        resolved_post_path = resolve_report_path(post_report_path, args.resolution_report)
        if not resolved_post_path or not resolved_post_path.is_file():
            errors.append("a required post-review must link an existing report path")
        else:
            post_text = resolved_post_path.read_text(encoding="utf-8")
            for heading in POST_REVIEW_REQUIRED_HEADINGS:
                if not re.search(rf"^## {re.escape(heading)}\s*$", post_text, re.MULTILINE):
                    errors.append(f"Post-review report is missing required heading: ## {heading}")
            if field(post_text, "Report type") != "code-review":
                errors.append("Post-review report path must point to a code-review report")
            if field(post_text, "Report ID") != post_report_id:
                errors.append("Post-review report ID does not match linked report")
            if field(post_text, "Review chain ID") != review_chain_id:
                errors.append("Post-review report must use the same Review chain ID")
            if field(post_text, "Review generation") != "1":
                errors.append("Post-review report must be generation 1")
            if field(post_text, "Review trigger") != "post-implementation":
                errors.append("Post-review report must use the post-implementation trigger")
            if field(post_text, "Scope mode") != "implementation delta plus affected execution chains":
                errors.append("Post-review report must use implementation-delta execution-chain scope")
            if field(post_text, "Parent review report ID") != field(text, "Source report ID"):
                errors.append("Post-review report must link the consumed source review as parent")
            if field(post_text, "Parent resolution ID") != resolution_id:
                errors.append("Post-review report must link this resolution as parent")
            if field(post_text, "Automatic receiving permitted") != "No":
                errors.append("Post-review report must prohibit automatic receiving")
            if field(post_text, "Handoff status") != "Terminal post-review - return to user/owner":
                errors.append("Post-review report must use the terminal handoff")
            if field(post_text, "Recommendation") != post_recommendation:
                errors.append("Post-review recommendation does not match the linked report")
            if not post_scope_fingerprint or post_scope_fingerprint == "None":
                errors.append("a required post-review must record its scope fingerprint")
            elif field(post_text, "Scope fingerprint") != post_scope_fingerprint:
                errors.append("Post-review scope fingerprint does not match the linked report")

            post_item_ids = set(source_items(post_text))
            if ids_from_value(remaining_post_items) != post_item_ids:
                errors.append(
                    "Remaining review items after post-review must exactly match post-review F/T/Not-covered A items"
                )

            sibling_validator = (
                Path(__file__).resolve().parents[2]
                / "code-review"
                / "scripts"
                / "validate_review_report.py"
            )
            if not args.source_report or not args.source_report.is_file():
                errors.append("a required post-review needs the canonical generation-0 source report")
            elif not sibling_validator.is_file():
                errors.append("code-review validator is unavailable for terminal post-review validation")
            else:
                validation = subprocess.run(
                    [
                        sys.executable,
                        str(sibling_validator),
                        str(resolved_post_path),
                        "--parent-report",
                        str(args.source_report),
                        "--parent-resolution",
                        str(args.resolution_report),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if validation.returncode != 0:
                    errors.append(
                        "terminal post-review failed code-review validation: "
                        + (validation.stderr.strip() or validation.stdout.strip())
                    )
    elif required and required.startswith("no"):
        if runs_used != 0:
            errors.append("Post-review runs used must be 0 when review is not required")
        if post_generation != "None" or post_scope != "None":
            errors.append("unused post-review generation and scope must be None")
        if post_report_id != "None" or post_report_path != "None":
            errors.append("unused post-review report ID and path must be None")
        if post_recommendation != "Not applicable":
            errors.append("unused post-review recommendation must be Not applicable")
        if post_scope_fingerprint != "None":
            errors.append("unused post-review scope fingerprint must be None")
    else:
        errors.append("Post-implementation review required must start with yes or no")

    final_completion = field(text, "Completion")
    if final_completion not in {"Resolved", "Partially resolved", "Blocked"}:
        errors.append("Final State Completion must be Resolved, Partially resolved, or Blocked")
    report_status = field(text, "Status")
    if final_completion in {"Resolved", "Partially resolved", "Blocked"} and report_status != final_completion:
        errors.append("Report Contract Status must exactly match Final State Completion")
    chain_completion = field(text, "Review-chain completion")
    unfinished_items = {
        item_id
        for item_id, data in ledger.items()
        if data["verdict"] in UNRESOLVED_VERDICTS
        or data["action"] in EVIDENCE_ACTIONS
        or data["implementation"] in {"Not started", "Implemented", "Blocked", "Carried forward"}
        or (
            data["action"] in {"Fix required", "Test required"}
            and data["implementation"] != "Verified"
        )
    }
    if final_completion == "Resolved" and unfinished_items:
        errors.append(
            "Resolved completion is incompatible with unfinished items: "
            + ", ".join(sorted(unfinished_items))
        )
    if unfinished_items and chain_completion != "Awaiting explicit user decision":
        errors.append("unfinished items require Awaiting explicit user decision")
    expected_open_ids = {
        item_id for item_id, data in ledger.items() if data["verdict"] in UNRESOLVED_VERDICTS
    }
    if ids_from_value(field(text, "Open item IDs")) != expected_open_ids:
        errors.append("Final State Open item IDs must exactly match Open/Unverifiable dispositions")
    expected_carried_ids = {
        item_id for item_id, data in ledger.items() if data["action"] == "Carried forward"
    }
    if ids_from_value(field(text, "Carried-forward item IDs")) != expected_carried_ids:
        errors.append("Final State Carried-forward item IDs must exactly match carried actions")
    expected_challenged_ids = {
        item_id for item_id, data in ledger.items() if data["challenge"] != "None"
    }
    if ids_from_value(field(text, "Challenged item IDs")) != expected_challenged_ids:
        errors.append("Final State Challenged item IDs must exactly match challenge references")
    expected_implemented_ids = {
        item_id
        for item_id, data in ledger.items()
        if data["implementation"] in {"Implemented", "Verified"}
    }
    if ids_from_value(field(text, "Implemented item IDs")) != expected_implemented_ids:
        errors.append("Final State Implemented item IDs must match implementation states")
    expected_verified_ids = {
        item_id for item_id, data in ledger.items() if data["implementation"] == "Verified"
    }
    if ids_from_value(field(text, "Verified item IDs")) != expected_verified_ids:
        errors.append("Final State Verified item IDs must match Verified implementation states")
    expected_resolved_ids = set(ledger) - unfinished_items
    if ids_from_value(field(text, "Resolved item IDs")) != expected_resolved_ids:
        errors.append("Final State Resolved item IDs must exactly match finished dispositions")
    if remaining_post_items and remaining_post_items != "None":
        if final_completion == "Resolved":
            errors.append("remaining post-review items prevent Resolved completion")
        if chain_completion != "Awaiting explicit user decision":
            errors.append("remaining post-review items require Awaiting explicit user decision")
    elif chain_completion not in {"Terminal", "Awaiting explicit user decision"}:
        errors.append("Review-chain completion must record a terminal state")

    if re.search(r"^- `no` ", section(text, "Resolution Self-Check"), re.MULTILINE):
        errors.append("Resolution Self-Check contains a no result")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    source_count = len(source_expected) if source_text else "normalized-input"
    print(
        "Valid receiving-code-review resolution report: "
        f"{len(ledger)} dispositions, {len(challenge_cards)} challenges, "
        f"{len(chains)} execution chains, {len(actionable)} actionable items, "
        f"source_items={source_count}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
