#!/usr/bin/env python3
"""Validate the canonical code-review report, including bounded lineage."""

from __future__ import annotations

import argparse
import hashlib
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
    "Prior Resolution Reconciliation",
    "Receiving Handoff",
    "Report Self-Check",
]
SEVERITIES = {"Blocker", "Major", "Minor", "Question"}
RECOMMENDATIONS = {"Block", "Changes requested", "Discuss", "Pass with caveat", "Pass"}
ISSUE_FINGERPRINT = re.compile(r"ifp-sha256:[0-9a-f]{64}")
REPORT_ID = re.compile(r"cr-\d{8}-[a-z0-9]{6,32}")
CHAIN_ID = re.compile(r"rc-\d{8}-[a-z0-9]{6,32}")
RESOLUTION_ID = re.compile(r"rr-\d{8}-[a-z0-9]{6,32}")
BASIS = re.compile(
    r"kind:(owner-decision|requirement|public-contract|approved-design|hard-invariant|"
    r"test-evidence|code-history|product-intent); "
    r"strength:(authoritative|inferred|unavailable); evidence:(.+)"
)
PROTECTED_VERDICTS = {"Intentional", "Disproved", "Stale", "Duplicate"}
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


def finding_cards(text: str) -> dict[str, tuple[str, str]]:
    pattern = re.compile(
        r"^###\s+(F\d+)\s+(Blocker|Major|Minor|Question)\s+-\s+.+$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    cards: dict[str, tuple[str, str]] = {}
    for match in matches:
        rest = text[match.end() :]
        next_boundary = re.search(r"^(?:###\s+F\d+\s+|##\s+)", rest, re.MULTILINE)
        end = match.end() + (next_boundary.start() if next_boundary else len(rest))
        cards[match.group(1)] = (match.group(2), text[match.start() : end])
    return cards


def card_field(card: str, name: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}:\s*(?:`([^`]+)`|(.+))$", card, re.MULTILINE)
    if not match:
        return None
    return (match.group(1) or match.group(2)).strip()


def expected_fingerprint(issue_key: str) -> str:
    digest = hashlib.sha256(issue_key.encode("utf-8")).hexdigest()
    return f"ifp-sha256:{digest}"


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


def validate_identity(
    item_id: str,
    issue_key: str,
    fingerprint: str,
    expected_basis: str,
    *,
    question: bool,
    errors: list[str],
) -> None:
    key_pattern = TEST_GAP_KEY if item_id.startswith("T") else FINDING_KEY
    key_match = key_pattern.fullmatch(issue_key)
    if (
        not issue_key
        or "<" in issue_key
        or "[" in issue_key
        or LOCAL_IDENTITY.search(issue_key)
        or not key_match
    ):
        errors.append(f"{item_id} has a missing or placeholder Issue key")
    elif any(part.strip().lower() in {"", "none", "n/a", "unknown"} for part in key_match.groups()):
        errors.append(f"{item_id} Issue key contains an empty semantic component")
    if issue_key and fingerprint != expected_fingerprint(issue_key):
        errors.append(f"{item_id} issue fingerprint does not match sha256(Issue key)")
    if not ISSUE_FINGERPRINT.fullmatch(fingerprint):
        errors.append(f"{item_id} has invalid issue fingerprint")

    basis = BASIS.fullmatch(expected_basis)
    if not basis:
        errors.append(f"{item_id} has invalid Expected basis structure")
        return
    kind = basis.group(1)
    strength = basis.group(2)
    evidence = basis.group(3).strip().lower()
    if evidence in {"", "none", "n/a", "unknown"} or "<" in evidence or "[" in evidence:
        errors.append(f"{item_id} Expected basis lacks concrete evidence")
    if kind in AUTHORITATIVE_KINDS and strength != "authoritative":
        errors.append(f"{item_id} Expected basis kind {kind} must be authoritative")
    if kind in INFERRED_KINDS and strength == "authoritative":
        errors.append(f"{item_id} Expected basis kind {kind} cannot be authoritative")
    if not question and strength != "authoritative":
        errors.append(f"{item_id} requires authoritative Expected basis or Question severity")


def issue_map(report_text: str) -> dict[str, str]:
    identities: dict[str, str] = {}
    for row in markdown_rows(section(report_text, "Complete Findings Index", "Blocker")):
        if row and re.fullmatch(r"F\d+", row[0]) and len(row) >= 10:
            identities[row[7]] = row[8]
    for row in markdown_rows(section(report_text, "Test Gaps", "Review Coverage Ledger")):
        if row and re.fullmatch(r"T\d+", row[0]) and len(row) >= 10:
            identities[row[7]] = row[8]
    return identities


def protected_fingerprints(resolution_text: str) -> set[str]:
    protected: set[str] = set()
    rows = markdown_rows(section(resolution_text, "Disposition Ledger", "Challenges to Source Review"))
    for row in rows:
        if row and re.fullmatch(r"(?:F|T|A|I)\d+", row[0]) and len(row) >= 5:
            fingerprint = row[1]
            verdict = row[4]
            if verdict in PROTECTED_VERDICTS and ISSUE_FINGERPRINT.fullmatch(fingerprint):
                protected.add(fingerprint)
    return protected


def resolve_declared_path(raw_path: str | None, report_path: Path) -> Path | None:
    if not raw_path or raw_path == "None":
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (report_path.parent / path).resolve()


def validate_lineage(
    text: str,
    report_path: Path,
    parent_report_path: Path | None,
    parent_resolution_path: Path | None,
    errors: list[str],
) -> tuple[int | None, str | None, str | None]:
    chain_id = field(text, "Review chain ID")
    if not chain_id or not CHAIN_ID.fullmatch(chain_id):
        errors.append("Review chain ID must match rc-YYYYMMDD-<6-32 lowercase letters/digits>")

    generation_raw = field(text, "Review generation")
    generation = int(generation_raw) if generation_raw in {"0", "1"} else None
    if generation is None:
        errors.append("Review generation must be 0 or 1")

    trigger = field(text, "Review trigger")
    parent_review_id = field(text, "Parent review report ID")
    parent_review_field_path = field(text, "Parent review report path")
    parent_id = field(text, "Parent resolution ID")
    parent_path = field(text, "Parent resolution path")
    scope_mode = field(text, "Scope mode")
    prior_resolution = field(text, "Prior resolution consulted")
    handoff = field(text, "Handoff status")
    automatic_receiving = field(text, "Automatic receiving permitted")

    if generation == 0:
        if trigger != "initial":
            errors.append("generation 0 Review trigger must be initial")
        if (
            parent_review_id != "None"
            or parent_review_field_path != "None"
            or parent_id != "None"
            or parent_path != "None"
        ):
            errors.append("generation 0 must not have a parent review or resolution")
        if parent_report_path or parent_resolution_path:
            errors.append("generation 0 must not receive parent artifact arguments")
        if scope_mode != "full frozen scope":
            errors.append("generation 0 Scope mode must be full frozen scope")
        if prior_resolution != "None":
            errors.append("generation 0 Prior resolution consulted must be None")
        if handoff not in {"Ready for receiving-code-review", "Regenerate before implementation"}:
            errors.append("generation 0 must use a non-terminal receiving handoff")
        expected_receiving = "Yes" if handoff == "Ready for receiving-code-review" else "No"
        if automatic_receiving != expected_receiving:
            errors.append(
                f"generation 0 Automatic receiving permitted must be {expected_receiving} for its handoff"
            )
    elif generation == 1:
        if trigger != "post-implementation":
            errors.append("generation 1 Review trigger must be post-implementation")
        if not parent_review_id or not REPORT_ID.fullmatch(parent_review_id):
            errors.append("generation 1 must link a valid Parent review report ID")
        if not parent_review_field_path or parent_review_field_path == "None":
            errors.append("generation 1 must link a Parent review report path")
        if not parent_id or not RESOLUTION_ID.fullmatch(parent_id):
            errors.append("generation 1 must link a valid Parent resolution ID")
        if not parent_path or parent_path == "None":
            errors.append("generation 1 must link a Parent resolution path")
        if scope_mode != "implementation delta plus affected execution chains":
            errors.append(
                "generation 1 Scope mode must be implementation delta plus affected execution chains"
            )
        if not prior_resolution or prior_resolution == "None":
            errors.append("generation 1 must record the Prior resolution consulted")
        if handoff != "Terminal post-review - return to user/owner":
            errors.append("generation 1 must use the terminal post-review handoff")
        if automatic_receiving != "No":
            errors.append("generation 1 must set Automatic receiving permitted to No")
        reconciliation = section(text, "Prior Resolution Reconciliation", "Receiving Handoff").strip()
        if not reconciliation or reconciliation.lower() == "none":
            errors.append("generation 1 must record prior-resolution reconciliation")
        if not parent_report_path or not parent_report_path.is_file():
            errors.append("generation 1 validation requires --parent-report with an existing file")
        if not parent_resolution_path or not parent_resolution_path.is_file():
            errors.append("generation 1 validation requires --parent-resolution with an existing file")

    parent_report_text = None
    parent_resolution_text = None
    if generation == 1 and parent_report_path and parent_report_path.is_file():
        declared_parent_report = resolve_declared_path(parent_review_field_path, report_path)
        if declared_parent_report != parent_report_path.resolve():
            errors.append("Parent review report path does not match --parent-report")
        parent_report_text = parent_report_path.read_text(encoding="utf-8")
        if field(parent_report_text, "Report type") != "code-review":
            errors.append("--parent-report must have Report type code-review")
        if field(parent_report_text, "Report ID") != parent_review_id:
            errors.append("Parent review report ID does not match --parent-report")
        if field(parent_report_text, "Review chain ID") != chain_id:
            errors.append("Parent review report must use the same Review chain ID")
        if field(parent_report_text, "Review generation") != "0":
            errors.append("Parent review report must be generation 0")
    if generation == 1 and parent_resolution_path and parent_resolution_path.is_file():
        declared_parent_resolution = resolve_declared_path(parent_path, report_path)
        if declared_parent_resolution != parent_resolution_path.resolve():
            errors.append("Parent resolution path does not match --parent-resolution")
        parent_resolution_text = parent_resolution_path.read_text(encoding="utf-8")
        if field(parent_resolution_text, "Report type") != "receiving-code-review":
            errors.append("--parent-resolution must have Report type receiving-code-review")
        if field(parent_resolution_text, "Resolution ID") != parent_id:
            errors.append("Parent resolution ID does not match --parent-resolution")
        if field(parent_resolution_text, "Review chain ID") != chain_id:
            errors.append("Parent resolution must use the same Review chain ID")
        if field(parent_resolution_text, "Source report ID") != parent_review_id:
            errors.append("Parent resolution must consume the linked parent review report")

    return generation, parent_report_text, parent_resolution_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--parent-report", type=Path)
    parser.add_argument("--parent-resolution", type=Path)
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
    if not report_id or not REPORT_ID.fullmatch(report_id):
        errors.append("Report ID must match cr-YYYYMMDD-<6-32 lowercase letters/digits>")
    generation, parent_report_text, parent_resolution_text = validate_lineage(
        text, args.report, args.parent_report, args.parent_resolution, errors
    )

    if field(text, "Git mutation during review") != "None":
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

    index_rows = markdown_rows(section(text, "Complete Findings Index", "Blocker"))
    indexed: dict[str, dict[str, str]] = {}
    for row in index_rows:
        if not row or row[0] == "ID" or not re.fullmatch(r"F\d+", row[0]):
            continue
        finding_id = row[0]
        if len(row) < 10:
            errors.append(f"{finding_id} findings-index row has fewer than 10 columns")
            continue
        if row[1] not in SEVERITIES:
            errors.append(f"{finding_id} has invalid or missing severity in Complete Findings Index")
            continue
        if finding_id in indexed:
            errors.append(f"duplicate finding in Complete Findings Index: {finding_id}")
        indexed[finding_id] = {
            "severity": row[1],
            "issue_key": row[7],
            "fingerprint": row[8],
            "expected_basis": row[9],
        }
        validate_identity(
            finding_id,
            row[7],
            row[8],
            row[9],
            question=row[1] == "Question",
            errors=errors,
        )

    card_matches = re.findall(
        r"^###\s+(F\d+)\s+(Blocker|Major|Minor|Question)\s+-\s+.+$", text, re.MULTILINE
    )
    for finding_id in duplicates(finding_id for finding_id, _ in card_matches):
        errors.append(f"duplicate finding card: {finding_id}")
    cards = finding_cards(text)
    if set(indexed) != set(cards):
        missing_cards = sorted(set(indexed) - set(cards))
        missing_index = sorted(set(cards) - set(indexed))
        if missing_cards:
            errors.append(f"indexed findings missing cards: {', '.join(missing_cards)}")
        if missing_index:
            errors.append(f"finding cards missing from index: {', '.join(missing_index)}")
    for finding_id in sorted(set(indexed) & set(cards)):
        severity, card = cards[finding_id]
        if indexed[finding_id]["severity"] != severity:
            errors.append(
                f"severity mismatch for {finding_id}: index={indexed[finding_id]['severity']}, card={severity}"
            )
        card_fingerprint = card_field(card, "Issue fingerprint")
        card_issue_key = card_field(card, "Issue key")
        card_basis = card_field(card, "Expected basis")
        if card_issue_key != indexed[finding_id]["issue_key"]:
            errors.append(f"Issue key mismatch for {finding_id}")
        if card_fingerprint != indexed[finding_id]["fingerprint"]:
            errors.append(f"issue fingerprint mismatch for {finding_id}")
        if card_basis != indexed[finding_id]["expected_basis"]:
            errors.append(f"Expected basis mismatch for {finding_id}")
        if not card_basis:
            errors.append(f"{finding_id} card is missing Expected basis")

    test_rows = markdown_rows(section(text, "Test Gaps", "Review Coverage Ledger"))
    tests: dict[str, dict[str, str]] = {}
    for row in test_rows:
        if not row or row[0] == "ID" or not re.fullmatch(r"T\d+", row[0]):
            continue
        test_id = row[0]
        if len(row) < 10:
            errors.append(f"{test_id} test-gap row has fewer than 10 columns")
            continue
        if row[1] not in {"Blocker", "Major", "Minor"}:
            errors.append(f"{test_id} has invalid or missing severity")
            continue
        if test_id in tests:
            errors.append(f"duplicate test gap: {test_id}")
        tests[test_id] = {
            "severity": row[1],
            "issue_key": row[7],
            "fingerprint": row[8],
            "expected_basis": row[9],
        }
        validate_identity(
            test_id,
            row[7],
            row[8],
            row[9],
            question=False,
            errors=errors,
        )

    all_fingerprints = [item["fingerprint"] for item in indexed.values()] + [
        item["fingerprint"] for item in tests.values()
    ]
    for fingerprint in duplicates(all_fingerprints):
        errors.append(f"duplicate semantic issue fingerprint: {fingerprint}")

    current_identities = {
        item["issue_key"]: item["fingerprint"] for item in list(indexed.values()) + list(tests.values())
    }
    if generation == 1 and parent_report_text:
        for issue_key, fingerprint in current_identities.items():
            parent_fingerprint = issue_map(parent_report_text).get(issue_key)
            if parent_fingerprint and parent_fingerprint != fingerprint:
                errors.append(f"generation 1 changed the fingerprint for inherited Issue key: {issue_key}")

    if generation == 1 and parent_resolution_text:
        protected = protected_fingerprints(parent_resolution_text)
        reconciliation_rows = markdown_rows(
            section(text, "Prior Resolution Reconciliation", "Receiving Handoff")
        )
        reconciliation: dict[str, tuple[str, str]] = {}
        for row in reconciliation_rows:
            if len(row) >= 5 and ISSUE_FINGERPRINT.fullmatch(row[1]):
                reconciliation[row[1]] = (row[3], row[4])
        current_fingerprints = set(all_fingerprints)
        for fingerprint in protected & current_fingerprints:
            changed_evidence, decision = reconciliation.get(fingerprint, ("", ""))
            if not decision.lower().startswith("reopened"):
                errors.append(
                    f"protected issue fingerprint {fingerprint} requires an explicit reopened reconciliation"
                )
            if not valid_delta(changed_evidence):
                errors.append(
                    f"reopened protected issue fingerprint {fingerprint} requires changed code/contract/evidence"
                )
        for fingerprint, (_, decision) in reconciliation.items():
            if decision.lower().startswith("kept closed") and fingerprint in current_fingerprints:
                errors.append(f"kept-closed issue fingerprint appears in current findings: {fingerprint}")

    coverage_rows = markdown_rows(
        section(text, "Review Coverage Ledger", "Subagent Candidate Adjudication")
    )
    areas: dict[str, str] = {}
    valid_statuses = {"Reviewed - no issue found", "Not review-relevant", "Not covered"}
    for row in coverage_rows:
        if not row or row[0] == "Area ID" or not re.fullmatch(r"A\d+", row[0]):
            continue
        area_id = row[0]
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

    observed_severities = [item["severity"] for item in indexed.values()] + [
        item["severity"] for item in tests.values()
    ]
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

    actionable_findings = ids_from_field(field(text, "Actionable finding IDs"), "F")
    deferred_findings = ids_from_field(field(text, "Deferred finding IDs"), "F")
    required_findings = {
        item_id for item_id, item in indexed.items() if item["severity"] in {"Blocker", "Major"}
    }
    allowed_findings = {
        item_id for item_id, item in indexed.items() if item["severity"] != "Question"
    }
    if missing := required_findings - actionable_findings:
        errors.append(f"Actionable finding IDs omits Blocker/Major items: {', '.join(sorted(missing))}")
    if invalid := actionable_findings - allowed_findings:
        errors.append(f"Actionable finding IDs includes unknown or Question items: {', '.join(sorted(invalid))}")
    if actionable_findings & deferred_findings:
        errors.append("Actionable and Deferred finding IDs must be disjoint")
    if actionable_findings | deferred_findings != allowed_findings:
        errors.append("Actionable and Deferred finding IDs must partition every non-Question finding")

    open_questions = ids_from_field(field(text, "Open question IDs"), "F")
    expected_questions = {
        item_id for item_id, item in indexed.items() if item["severity"] == "Question"
    }
    if open_questions != expected_questions:
        errors.append("Open question IDs must exactly match Question findings")

    actionable_tests = ids_from_field(field(text, "Actionable test-gap IDs"), "T")
    deferred_tests = ids_from_field(field(text, "Deferred test-gap IDs"), "T")
    required_tests = {
        item_id for item_id, item in tests.items() if item["severity"] in {"Blocker", "Major"}
    }
    if missing := required_tests - actionable_tests:
        errors.append(f"Actionable test-gap IDs omits Blocker/Major items: {', '.join(sorted(missing))}")
    if invalid := actionable_tests - set(tests):
        errors.append(f"Actionable test-gap IDs references unknown items: {', '.join(sorted(invalid))}")
    if actionable_tests & deferred_tests:
        errors.append("Actionable and Deferred test-gap IDs must be disjoint")
    if actionable_tests | deferred_tests != set(tests):
        errors.append("Actionable and Deferred test-gap IDs must partition every standalone test gap")

    open_areas = ids_from_field(field(text, "Open coverage area IDs"), "A")
    expected_open_areas = {item_id for item_id, status in areas.items() if status == "Not covered"}
    if open_areas != expected_open_areas:
        errors.append("Open coverage area IDs must exactly match Not covered areas")
    if field(text, "Source report ID") != report_id:
        errors.append("Receiving Handoff Source report ID must match Report ID")
    if field(text, "Scope fingerprint to recheck") != field(text, "Scope fingerprint"):
        errors.append("Receiving Handoff scope fingerprint must match Report Contract")

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
