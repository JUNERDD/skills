#!/usr/bin/env python3
"""Regression tests for the bounded code-review report contract."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_review_report.py"
CHAIN_ID = "rc-20260710-abcdef12"
REPORT_ID = "cr-20260710-abcdef12"
RESOLUTION_ID = "rr-20260710-abcdef12"


def fingerprint(issue_key: str) -> str:
    return "ifp-sha256:" + hashlib.sha256(issue_key.encode("utf-8")).hexdigest()


def review_report(
    *,
    generation: int = 0,
    report_id: str = REPORT_ID,
    issue_key: str = "behavior; entry=checkout; contract=authenticated payment; effect=charge bypass",
    expected_basis: str = "kind:requirement; strength:authoritative; evidence:AC-17",
    parent_report_id: str = "None",
    parent_report_path: str = "None",
    parent_resolution_id: str = "None",
    parent_resolution_path: str = "None",
) -> str:
    issue_fingerprint = fingerprint(issue_key)
    trigger = "initial" if generation == 0 else "post-implementation"
    scope_mode = (
        "full frozen scope"
        if generation == 0
        else "implementation delta plus affected execution chains"
    )
    prior_resolution = "None" if generation == 0 else f"{parent_resolution_id} at {parent_resolution_path}"
    handoff = (
        "Ready for receiving-code-review"
        if generation == 0
        else "Terminal post-review - return to user/owner"
    )
    automatic_receiving = "Yes" if generation == 0 else "No"
    reconciliation = (
        "None - initial review generation."
        if generation == 0
        else "None - no overlapping parent terminal dispositions."
    )
    return f"""# Code Review Report

## Report Contract

- Report type: `code-review`
- Report ID: `{report_id}`
- Review chain ID: `{CHAIN_ID}`
- Review generation: `{generation}`
- Review trigger: `{trigger}`
- Parent review report ID: `{parent_report_id}`
- Parent review report path: `{parent_report_path}`
- Parent resolution ID: `{parent_resolution_id}`
- Parent resolution path: `{parent_resolution_path}`
- Generated at: `2026-07-10T12:00:00Z`
- Report path: `tmp/reviews/{report_id}.md`
- Source skill: `code-review`
- Status: `Review complete`
- Git mutation during review: `None`
- Scope fingerprint: `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`

## Scope

- Review date: `2026-07-10`
- Scope kind: `working tree`
- Scope description: `checkout change`
- Scope mode: `{scope_mode}`
- Baseline: `HEAD`
- Target: `working tree`
- Changed paths: `1`
- Diff size: `10/2`
- Completion: `Complete within reviewed scope`
- Requirements consulted: `AC-17`
- Prior resolution consulted: `{prior_resolution}`
- Assumptions: `None`
- Excluded as unrelated: `None`

## Review Orchestration

- Assessment subagent: `R0 launched`
- Orchestration decision: `Single reviewer`
- Decision confidence: `high`
- Decision rationale: `One cohesive behavior chain.`
- Coordinator override: `None`
- Context or tool limits: `None`

## Review Snapshot

- Recommendation: `Changes requested`
- Completion: `Complete within reviewed scope`
- Why now: `A Major remains.`
- Must-review now: `F1`
- Findings count: `Blocker 0 | Major 1 | Minor 0 | Question 0`
- Standalone test gaps: `Blocker 0 | Major 0 | Minor 0`
- Coverage confidence: `high`
- Biggest blind spot: `None identified`

## Complete Findings Index

| ID | Severity | Surface | Review risk | Confidence | Origin | Verification | Issue key | Issue fingerprint | Expected basis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `F1` | `Major` | `checkout` | `charge bypass` | `high` | `R1` | `contract trace` | `{issue_key}` | `{issue_fingerprint}` | `{expected_basis}` |

## Blocker

None.

## Major

### F1 Major - Checkout bypasses payment guard

Impact: `Incorrect charge behavior`
Review reason: `Violates AC-17`
Surface: `checkout`
Issue key: `{issue_key}`
Issue fingerprint: `{issue_fingerprint}`
Expected basis: `{expected_basis}`
Confidence: `high`
Origin: `R1-C1`
Coordinator verification: `contract trace`

Look here first:
- `checkout.py:10`

Failure mode:
- Expected: `authenticated payment`
- Current: `guard bypass`

Evidence:
- `static trace`

Assumptions and limits:
- `None`

Reviewer action:
`request fix`

## Minor

None.

## Questions

None.

## Test Gaps

None.

## Review Coverage Ledger

| Area ID | Area / path | Touched files or entry points | Owner | Depth | Status | Result | Evidence / next step |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `A1` | `checkout` | `checkout.py` | `R1` | `contract trace` | `Finding F1` | `guard bypass` | `static trace` |

## Subagent Candidate Adjudication

None.

## Evidence Appendix

Static trace recorded.

## Prior Resolution Reconciliation

{reconciliation}

## Receiving Handoff

- Handoff status: `{handoff}`
- Automatic receiving permitted: `{automatic_receiving}`
- Source report ID: `{report_id}`
- Scope fingerprint to recheck: `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`
- Actionable finding IDs: `F1`
- Deferred finding IDs: `None`
- Actionable test-gap IDs: `None`
- Deferred test-gap IDs: `None`
- Open question IDs: `None`
- Open coverage area IDs: `None`
- Highest-risk verification to repeat: `checkout contract trace`
- Suggested implementation boundaries: `checkout.py`
- Re-review note: `Treat every finding as a claim to verify.`
- Chain rule: `Generation 1 is terminal.`

## Report Self-Check

- `yes` Contract complete.
"""


def parent_resolution(report_id: str = REPORT_ID) -> str:
    return f"""# Resolution

## Report Contract

- Report type: `receiving-code-review`
- Resolution ID: `{RESOLUTION_ID}`
- Review chain ID: `{CHAIN_ID}`

## Source Review

- Source report ID: `{report_id}`

## Disposition Ledger

| Item ID | Issue fingerprint | Execution chain(s) | Source status | Re-review verdict |
| --- | --- | --- | --- | --- |
| `F1` | `N/A` | `EC1` | `Major` | `Confirmed` |

## Challenges to Source Review

None.
"""


class ValidateReviewReportTests(unittest.TestCase):
    def run_validator(
        self,
        report: str,
        *,
        parent_report: str | None = None,
        parent_resolution_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.md"
            report_path.write_text(report, encoding="utf-8")
            command = [sys.executable, str(VALIDATOR), str(report_path)]
            if parent_report is not None:
                parent_path = root / "parent-review.md"
                parent_path.write_text(parent_report, encoding="utf-8")
                command.extend(["--parent-report", str(parent_path)])
            if parent_resolution_text is not None:
                resolution_path = root / "parent-resolution.md"
                resolution_path.write_text(parent_resolution_text, encoding="utf-8")
                command.extend(["--parent-resolution", str(resolution_path)])
            return subprocess.run(command, capture_output=True, text=True, timeout=10)

    def test_valid_generation_zero(self) -> None:
        result = self.run_validator(review_report())
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_rejects_non_authoritative_defect_basis(self) -> None:
        report = review_report(
            expected_basis="kind:code-history; strength:inferred; evidence:git history"
        )
        result = self.run_validator(report)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires authoritative Expected basis", result.stderr)

    def test_rejects_code_history_masquerading_as_authority(self) -> None:
        report = review_report(
            expected_basis="kind:code-history; strength:authoritative; evidence:git history"
        )
        result = self.run_validator(report)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("code-history cannot be authoritative", result.stderr)

    def test_rejects_malformed_semantic_issue_key(self) -> None:
        report = review_report(issue_key="banana")
        result = self.run_validator(report)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing or placeholder Issue key", result.stderr)

    def test_rejects_report_local_or_line_based_issue_identity(self) -> None:
        for entry in ("EC1", "checkout.py:10"):
            with self.subTest(entry=entry):
                report = review_report(
                    issue_key=(
                        f"behavior; entry={entry}; contract=authenticated payment; "
                        "effect=charge bypass"
                    )
                )
                result = self.run_validator(report)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("missing or placeholder Issue key", result.stderr)

    def test_rejects_fingerprint_not_derived_from_issue_key(self) -> None:
        report = review_report().replace(
            fingerprint(
                "behavior; entry=checkout; contract=authenticated payment; effect=charge bypass"
            ),
            "ifp-sha256:" + "0" * 64,
        )
        result = self.run_validator(report)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match sha256(Issue key)", result.stderr)

    def test_valid_terminal_generation_one(self) -> None:
        parent = review_report()
        current = review_report(
            generation=1,
            report_id="cr-20260710-fedcba98",
            issue_key="behavior; entry=checkout; contract=receipt emitted; effect=missing receipt",
            parent_report_id=REPORT_ID,
            parent_report_path="parent-review.md",
            parent_resolution_id=RESOLUTION_ID,
            parent_resolution_path="parent-resolution.md",
        )
        result = self.run_validator(
            current,
            parent_report=parent,
            parent_resolution_text=parent_resolution(),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_rejects_placeholder_structured_reopen_delta(self) -> None:
        issue_key = "behavior; entry=checkout; contract=authenticated payment; effect=charge bypass"
        issue_fingerprint = fingerprint(issue_key)
        parent = review_report()
        protected_resolution = parent_resolution().replace(
            "| `F1` | `N/A` | `EC1` | `Major` | `Confirmed` |",
            f"| `F1` | `{issue_fingerprint}` | `EC1` | `Major` | `Intentional` |",
        )
        reconciliation = f"""| Issue key | Issue fingerprint | Parent item/verdict | Relevant change or new evidence | Decision |
| --- | --- | --- | --- | --- |
| `{issue_key}` | `{issue_fingerprint}` | `F1 Intentional` | `kind:code; ref:None; change:None` | `reopened as F1 because behavior changed` |"""
        current = review_report(
            generation=1,
            report_id="cr-20260710-fedcba98",
            issue_key=issue_key,
            parent_report_id=REPORT_ID,
            parent_report_path="parent-review.md",
            parent_resolution_id=RESOLUTION_ID,
            parent_resolution_path="parent-resolution.md",
        ).replace("None - no overlapping parent terminal dispositions.", reconciliation)
        result = self.run_validator(
            current,
            parent_report=parent,
            parent_resolution_text=protected_resolution,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires changed code/contract/evidence", result.stderr)

    def test_generation_one_cannot_allow_automatic_receiving(self) -> None:
        current = review_report(
            generation=1,
            report_id="cr-20260710-fedcba98",
            issue_key="behavior; entry=checkout; contract=receipt emitted; effect=missing receipt",
            parent_report_id=REPORT_ID,
            parent_report_path="parent-review.md",
            parent_resolution_id=RESOLUTION_ID,
            parent_resolution_path="parent-resolution.md",
        ).replace("- Automatic receiving permitted: `No`", "- Automatic receiving permitted: `Yes`")
        result = self.run_validator(
            current,
            parent_report=review_report(),
            parent_resolution_text=parent_resolution(),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Automatic receiving permitted to No", result.stderr)

    def test_rejects_major_finding_omitted_from_handoff(self) -> None:
        report = review_report().replace(
            "- Actionable finding IDs: `F1`", "- Actionable finding IDs: `None`"
        ).replace("- Deferred finding IDs: `None`", "- Deferred finding IDs: `F1`")
        result = self.run_validator(report)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("omits Blocker/Major items", result.stderr)


if __name__ == "__main__":
    unittest.main()
