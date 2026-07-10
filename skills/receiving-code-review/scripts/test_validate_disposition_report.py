#!/usr/bin/env python3
"""Regression tests for receiving-code-review chain and disposition gates."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_disposition_report.py"
CODE_REVIEW_SCRIPTS = SCRIPT_DIR.parents[1] / "code-review" / "scripts"
if str(CODE_REVIEW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CODE_REVIEW_SCRIPTS))

from test_validate_review_report import review_report as build_code_review_report

CHAIN_ID = "rc-20260710-abcdef12"
SOURCE_REPORT_ID = "cr-20260710-abcdef12"
PARENT_RESOLUTION_ID = "rr-20260710-abcdef12"
RESOLUTION_ID = "rr-20260710-fedcba98"
ISSUE_KEY = "behavior; entry=guest checkout; contract=guest checkout allowed; effect=login required"
FINGERPRINT = "ifp-sha256:" + hashlib.sha256(ISSUE_KEY.encode("utf-8")).hexdigest()


def source_report(*, generation: int = 0) -> str:
    trigger = "initial" if generation == 0 else "post-implementation"
    parent_id = "None" if generation == 0 else PARENT_RESOLUTION_ID
    parent_path = "None" if generation == 0 else "parent-resolution.md"
    return f"""# Source review

## Report Contract

- Report type: `code-review`
- Report ID: `{SOURCE_REPORT_ID}`
- Review chain ID: `{CHAIN_ID}`
- Review generation: `{generation}`
- Review trigger: `{trigger}`
- Parent resolution ID: `{parent_id}`
- Parent resolution path: `{parent_path}`

## Complete Findings Index

| ID | Severity | Surface | Review risk | Confidence | Origin | Verification | Issue key | Issue fingerprint | Expected basis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `F1` | `Major` | `checkout` | `missing auth` | `high` | `R1` | `static trace` | `{ISSUE_KEY}` | `{FINGERPRINT}` | `kind:product-intent; strength:unavailable; evidence:owner decision missing` |

## Blocker

None.

## Test Gaps

None.

## Review Coverage Ledger

| Area ID | Area / path | Touched files or entry points | Owner | Depth | Status | Result | Evidence / next step |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `A1` | `checkout` | `checkout.py` | `R1` | `contract trace` | `Finding F1` | `auth question` | `static trace` |

## Subagent Candidate Adjudication

None.
"""


def resolution_report(
    *,
    source_generation: int = 0,
    resolution_id: str = PARENT_RESOLUTION_ID,
    lineage_state: str | None = None,
    chain_status: str = "Complete",
    verdict: str = "Intentional",
    action: str = "No change needed",
    implementation: str = "Not needed",
    execution_chain: str = "EC1",
    chain_basis: str = "kind:owner-decision; strength:authoritative; evidence:AC-Guest-1",
    actionable: bool = False,
    post_runs: int = 0,
    lineage_delta: str = "None",
    completion: str = "Resolved",
    chain_completion: str = "Terminal",
    emit_assignments: bool = True,
    emit_code_changes: bool = True,
) -> str:
    source_trigger = "initial" if source_generation == 0 else "post-implementation"
    source_parent_id = "None" if source_generation == 0 else PARENT_RESOLUTION_ID
    source_parent_path = "None" if source_generation == 0 else "parent-resolution.md"
    authority = (
        "Initial receiving handoff"
        if source_generation == 0
        else "Explicit current user instruction"
    )
    lineage_state = lineage_state or ("New" if source_generation == 0 else "Inherited")
    lineage_parent = "None" if source_generation == 0 else f"{PARENT_RESOLUTION_ID} / F1 / Intentional"
    lineage_evidence = "source report identity" if source_generation == 0 else "parent resolution ledger"
    post_budget = 1 if source_generation == 0 else 0
    actionable_ids = "F1" if actionable else "None"
    coding_stage = "Required" if actionable else "Not required - no actionable items"
    coding_subagent = "D1 launched" if actionable else "Not required"
    coding_mode = "Single coding agent" if actionable else "Not applicable"
    coding_assignments = (
        """| Coding agent | Actionable item IDs | File ownership | Expected result | Required verification | Status |
| --- | --- | --- | --- | --- | --- |
| `D1` | `F1` | `checkout.py` | `checkout behavior matches the authoritative contract` | `focused checkout test` | `Complete` |"""
        if actionable and emit_assignments
        else "None."
    )
    changed = implementation in {"Implemented", "Verified"}
    code_changes = (
        """| Item ID | Coding agent | Changed files | Focused change | Unrelated churn check |
| --- | --- | --- | --- | --- |
| `F1` | `D1` | `checkout.py` | `align checkout behavior with the contract` | `clean` |"""
        if changed and emit_code_changes
        else "None."
    )
    implemented_ids = "F1" if changed else "None"
    verified_ids = "F1" if implementation == "Verified" else "None"
    return f"""# Code Review Resolution Report

## Report Contract

- Report type: `receiving-code-review`
- Resolution ID: `{resolution_id}`
- Review chain ID: `{CHAIN_ID}`
- Generated at: `2026-07-10T12:00:00Z`
- Resolution path: `tmp/reviews/{resolution_id}.md`
- Source skill: `receiving-code-review`
- Status: `{completion}`
- Git index mutation by this workflow: `None`

## Source Review

- Source type: `code-review report`
- Source report ID: `{SOURCE_REPORT_ID}`
- Source report path: `source-review.md`
- Source recommendation: `Changes requested`
- Source completion: `Complete within reviewed scope`
- Source scope fingerprint: `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`
- Source review generation: `{source_generation}`
- Source review trigger: `{source_trigger}`
- Source parent resolution ID: `{source_parent_id}`
- Source parent resolution path: `{source_parent_path}`
- Continuation authority: `{authority}`
- Source item counts: `F 1 | T 0 | unresolved A 0 | intake I 0`

## Current Scope

- Scope kind: `working tree`
- Scope description: `guest checkout`
- Baseline: `HEAD`
- Target: `working tree`
- Current scope fingerprint: `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`
- Scope match: `Exact`
- Git state at intake: `clean`
- Pre-existing staged paths: `None`
- Environment limits: `None`

## Re-Review Orchestration

- Assessment subagent: `V0 launched`
- Orchestration decision: `Single verifier`
- Decision confidence: `high`
- Decision rationale: `One complete checkout chain.`
- Coordinator override: `None`

### Re-Review Synthesis

`The coordinator checked EC1 end to end.`

## Intake Integrity

- Index/card agreement: `yes`
- Test-gap enumeration agreement: `yes`
- Coverage/handoff agreement: `yes`
- Source/current scope agreement: `yes`
- Source report structurally valid: `yes`

### Intake Issues

None.

## Disposition Lineage

| Item ID | Issue key | Issue fingerprint | Parent resolution / item / verdict | Chain or evidence delta | Lineage state | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `F1` | `{ISSUE_KEY}` | `{FINGERPRINT}` | `{lineage_parent}` | `{lineage_delta}` | `{lineage_state}` | `{lineage_evidence}` |

## Execution Chain Reconstruction

| Chain ID | Item IDs | Trigger / entry | Guards / alternate paths | Propagation / dependencies | Terminal effect | Failure semantics | Expected basis | Evidence / gaps | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `EC1` | `F1` | `guest request -> checkout` | `guest feature flag; authenticated alternate` | `route -> policy -> order service -> persistence` | `guest order is accepted` | `validation error returns before persistence; cleanup is no-op` | `{chain_basis}` | `route and order-service trace` | `{chain_status}` |

## Disposition Ledger

| Item ID | Issue fingerprint | Execution chain(s) | Source status | Re-review verdict | Action state | Implementation state | Challenge | Evidence | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `F1` | `{FINGERPRINT}` | `{execution_chain}` | `Major` | `{verdict}` | `{action}` | `{implementation}` | `C1` | `EC1 proves guest checkout is deliberate end to end` | `None` |

## Challenges to Source Review

### C1 - Challenge to F1

Execution chains:
- `EC1`

Source claim:
`Guest checkout lacks required authentication.`

Source evidence:
- `route has no auth guard`

Counterclaim:
`Guest checkout is an intentional product path.`

Argument:
`AC-Guest-1 authorizes the EC1 guest path through order persistence.`

Counter-evidence:
- `AC-Guest-1 and the complete route-to-persistence trace`

Evidence supporting the source:
- `No auth guard exists`

Limits and residual uncertainty:
- `None`

Settlement criterion:
- `Product owner changes AC-Guest-1`

Decision authority:
- `AC-Guest-1`

Reopen condition:
- `The guest-checkout contract or affected execution chain changes`

Verdict effect:
- Re-review verdict: `{verdict}`
- Severity/action effect: `{action}`
- Independent adversarial verifier: `Not required`

## Implementation Plan and Delegation

- Actionable IDs: `{actionable_ids}`
- Coding stage: `{coding_stage}`
- Coding subagent: `{coding_subagent}`
- Coding mode: `{coding_mode}`
- Allowed files or surfaces: `Not applicable`
- Affected execution chains: `EC1`
- Prohibited scope: `unrelated refactors and staging`
- Regression/security/contract risk assessment: `No implementation planned`
- Required verification: `EC1 contract trace`
- Staging rule: `Preserve pre-existing staged state; leave new changes unstaged.`

### Coding Assignments

{coding_assignments}

## Code Changes

{code_changes}

## Verification

### Coordinator Verification

| Item ID / surface | Command or method | Result | Confidence | Remaining gap |
| --- | --- | --- | --- | --- |
| `F1` | `contract and full-chain trace` | `intent confirmed` | `high` | `None` |

### Coding Subagent Verification

None.

### Git State Verification

- Pre-existing staged paths unchanged: `yes`
- New changes staged: `No`
- Final unstaged changed paths: `None`
- Final untracked paths: `None`

## Post-Implementation Review

- Post-review budget at intake: `{post_budget}`
- Post-review runs used: `{post_runs}`
- Post-implementation review required: `no - no implementation changes`
- Post-review generation: `None`
- Post-review scope: `None`
- Post-review report ID: `None`
- Post-review report path: `None`
- Post-review recommendation: `Not applicable`
- Post-review scope fingerprint: `None`
- Remaining review items after post-review: `None`
- Automatic follow-on receiving: `No`
- Terminal handoff: `Return remaining findings to the user or product owner; do not invoke receiving-code-review automatically.`
- Termination reason: `no post-review needed`

## Residual Risks

None.

## Final State

- Completion: `{completion}`
- Resolved item IDs: `F1`
- Challenged item IDs: `F1`
- Implemented item IDs: `{implemented_ids}`
- Verified item IDs: `{verified_ids}`
- Carried-forward item IDs: `None`
- Open item IDs: `None`
- Final source recommendation effect: `weakened`
- Review-chain completion: `{chain_completion}`
- Git index mutation by this workflow: `None`

## Resolution Self-Check

- `yes` Contract complete.
"""


def resolution_with_post_review() -> str:
    return (
        resolution_report(completion="Partially resolved", chain_completion="Awaiting explicit user decision")
        .replace("- Post-review runs used: `0`", "- Post-review runs used: `1`")
        .replace(
            "- Post-implementation review required: `no - no implementation changes`",
            "- Post-implementation review required: `yes - independent high-risk verification`",
        )
        .replace("- Post-review generation: `None`", "- Post-review generation: `1`")
        .replace(
            "- Post-review scope: `None`",
            "- Post-review scope: `implementation delta plus affected EC1 chains`",
        )
        .replace("- Post-review report ID: `None`", "- Post-review report ID: `cr-20260710-fedcba98`")
        .replace("- Post-review report path: `None`", "- Post-review report path: `post-review.md`")
        .replace(
            "- Post-review recommendation: `Not applicable`",
            "- Post-review recommendation: `Changes requested`",
        )
        .replace(
            "- Post-review scope fingerprint: `None`",
            "- Post-review scope fingerprint: `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`",
        )
        .replace(
            "- Remaining review items after post-review: `None`",
            "- Remaining review items after post-review: `F1`",
        )
        .replace("- Termination reason: `no post-review needed`", "- Termination reason: `terminal generation completed`")
    )


def terminal_post_review() -> str:
    return build_code_review_report(
        generation=1,
        report_id="cr-20260710-fedcba98",
        issue_key="behavior; entry=checkout; contract=receipt emitted; effect=missing receipt",
        parent_report_id=SOURCE_REPORT_ID,
        parent_report_path="source.md",
        parent_resolution_id=PARENT_RESOLUTION_ID,
        parent_resolution_path="resolution.md",
    )


def terminal_post_review_stub() -> str:
    return f"""# Terminal post-review

## Report Contract

- Report type: `code-review`
- Report ID: `cr-20260710-fedcba98`
- Review chain ID: `{CHAIN_ID}`
- Review generation: `1`
- Parent resolution ID: `{PARENT_RESOLUTION_ID}`

## Receiving Handoff

- Automatic receiving permitted: `No`
"""


class ValidateDispositionReportTests(unittest.TestCase):
    def run_validator(
        self,
        resolution: str,
        source: str,
        *,
        parent: str | None = None,
        post_review: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            resolution_path = root / "resolution.md"
            source_path = root / "source.md"
            resolution_path.write_text(resolution, encoding="utf-8")
            source_path.write_text(source, encoding="utf-8")
            command = [
                sys.executable,
                str(VALIDATOR),
                str(resolution_path),
                "--source-report",
                str(source_path),
            ]
            if parent is not None:
                parent_path = root / "parent-resolution.md"
                parent_path.write_text(parent, encoding="utf-8")
                command.extend(["--parent-resolution", str(parent_path)])
            if post_review is not None:
                (root / "post-review.md").write_text(post_review, encoding="utf-8")
            return subprocess.run(command, capture_output=True, text=True, timeout=10)

    def test_valid_intentional_disposition_with_complete_chain(self) -> None:
        result = self.run_validator(resolution_report(), source_report())
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_rejects_intentional_fix_action(self) -> None:
        result = self.run_validator(
            resolution_report(
                action="Fix required",
                implementation="Not started",
                actionable=True,
            ),
            source_report(),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires No change needed + Not needed", result.stderr)

    def test_rejects_confirmed_item_on_blocked_chain(self) -> None:
        result = self.run_validator(
            resolution_report(
                chain_status="Blocked",
                verdict="Confirmed",
                action="Fix required",
                implementation="Not started",
                actionable=True,
            ),
            source_report(),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Blocked execution chain", result.stderr)

    def test_rejects_item_without_execution_chain_reference(self) -> None:
        result = self.run_validator(
            resolution_report(execution_chain="N/A"),
            source_report(),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must reference at least one EC#", result.stderr)

    def test_rejects_empty_complete_execution_chain(self) -> None:
        report = resolution_report().replace(
            "| `EC1` | `F1` | `guest request -> checkout` | `guest feature flag; authenticated alternate` | `route -> policy -> order service -> persistence` | `guest order is accepted` | `validation error returns before persistence; cleanup is no-op` |",
            "| `EC1` | `F1` | `` | `` | `` | `` | `` |",
        )
        result = self.run_validator(report, source_report())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Complete chain lacks concrete", result.stderr)

    def test_rejects_code_history_as_intent_authority(self) -> None:
        result = self.run_validator(
            resolution_report(
                chain_basis="kind:code-history; strength:authoritative; evidence:git history"
            ),
            source_report(),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("code-history cannot be authoritative", result.stderr)

    def test_rejects_resolved_fix_that_is_not_verified(self) -> None:
        result = self.run_validator(
            resolution_report(
                verdict="Confirmed",
                action="Fix required",
                implementation="Not started",
                actionable=True,
            ),
            source_report(),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Resolved completion is incompatible", result.stderr)

    def test_rejects_malformed_lineage_issue_key(self) -> None:
        bad_fingerprint = "ifp-sha256:" + hashlib.sha256(b"banana").hexdigest()
        report = resolution_report().replace(ISSUE_KEY, "banana").replace(
            FINGERPRINT, bad_fingerprint
        )
        source = source_report().replace(ISSUE_KEY, "banana").replace(
            FINGERPRINT, bad_fingerprint
        )
        result = self.run_validator(report, source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid semantic Issue key", result.stderr)

    def test_rejects_report_local_or_line_based_lineage_identity(self) -> None:
        for entry in ("EC1", "checkout.py:10"):
            with self.subTest(entry=entry):
                bad_key = (
                    f"behavior; entry={entry}; contract=guest checkout allowed; "
                    "effect=login required"
                )
                bad_fingerprint = "ifp-sha256:" + hashlib.sha256(
                    bad_key.encode("utf-8")
                ).hexdigest()
                report = resolution_report().replace(ISSUE_KEY, bad_key).replace(
                    FINGERPRINT, bad_fingerprint
                )
                source = source_report().replace(ISSUE_KEY, bad_key).replace(
                    FINGERPRINT, bad_fingerprint
                )
                result = self.run_validator(report, source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("invalid semantic Issue key", result.stderr)

    def test_rejects_post_review_run_when_not_required(self) -> None:
        result = self.run_validator(
            resolution_report(post_runs=1),
            source_report(),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be 0 when review is not required", result.stderr)

    def test_generation_one_inherits_protected_intentional_decision(self) -> None:
        parent = resolution_report()
        current = resolution_report(
            source_generation=1,
            resolution_id=RESOLUTION_ID,
            lineage_state="Inherited",
        )
        result = self.run_validator(
            current,
            source_report(generation=1),
            parent=parent,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_generation_one_cannot_mark_protected_decision_new(self) -> None:
        parent = resolution_report()
        current = resolution_report(
            source_generation=1,
            resolution_id=RESOLUTION_ID,
            lineage_state="New",
        )
        result = self.run_validator(
            current,
            source_report(generation=1),
            parent=parent,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be Inherited or Reopened", result.stderr)

    def test_rejects_bare_changed_reopen_delta(self) -> None:
        parent = resolution_report()
        current = resolution_report(
            source_generation=1,
            resolution_id=RESOLUTION_ID,
            lineage_state="Reopened",
            lineage_delta="Changed",
            verdict="Confirmed",
            action="Fix required",
            implementation="Not started",
            actionable=True,
            completion="Partially resolved",
            chain_completion="Awaiting explicit user decision",
        )
        result = self.run_validator(
            current,
            source_report(generation=1),
            parent=parent,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires structured code/contract/evidence delta", result.stderr)

    def test_rejects_placeholder_structured_reopen_delta(self) -> None:
        parent = resolution_report()
        current = resolution_report(
            source_generation=1,
            resolution_id=RESOLUTION_ID,
            lineage_state="Reopened",
            lineage_delta="kind:code; ref:None; change:None",
        )
        result = self.run_validator(
            current,
            source_report(generation=1),
            parent=parent,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires structured code/contract/evidence delta", result.stderr)

    def test_accepts_structured_reopen_delta(self) -> None:
        parent = resolution_report()
        current = resolution_report(
            source_generation=1,
            resolution_id=RESOLUTION_ID,
            lineage_state="Reopened",
            lineage_delta=(
                "kind:contract; ref:AC-GUEST-1; "
                "change:guest-checkout wording changed and was re-evaluated"
            ),
        )
        result = self.run_validator(
            current,
            source_report(generation=1),
            parent=parent,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_accepts_verified_action_with_assignment_and_change_evidence(self) -> None:
        result = self.run_validator(
            resolution_report(
                verdict="Confirmed",
                action="Fix required",
                implementation="Verified",
                actionable=True,
            ),
            source_report(),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_rejects_verified_action_without_assignment_or_change_evidence(self) -> None:
        report = resolution_report(
            verdict="Confirmed",
            action="Fix required",
            implementation="Verified",
            actionable=True,
            emit_assignments=False,
            emit_code_changes=False,
        ).replace("- Coding mode: `Single coding agent`", "- Coding mode: `Not applicable`")
        result = self.run_validator(report, source_report())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Coding Assignments omits actionable items", result.stderr)
        self.assertIn("Code Changes omits implemented/verified items", result.stderr)

    def test_rejects_challenge_effect_that_disagrees_with_ledger(self) -> None:
        report = resolution_report().replace(
            "- Severity/action effect: `No change needed`",
            "- Severity/action effect: `Fix required`",
        )
        result = self.run_validator(report, source_report())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("action-state effect disagrees", result.stderr)

    def test_rejects_report_status_that_disagrees_with_final_completion(self) -> None:
        report = resolution_report().replace(
            "- Status: `Resolved`", "- Status: `Partially resolved`"
        )
        result = self.run_validator(report, source_report())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Status must exactly match", result.stderr)

    def test_valid_single_terminal_post_review_link(self) -> None:
        result = self.run_validator(
            resolution_with_post_review(),
            source_report(),
            post_review=terminal_post_review(),
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_rejects_terminal_post_review_stub(self) -> None:
        result = self.run_validator(
            resolution_with_post_review(),
            source_report(),
            post_review=terminal_post_review_stub(),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing required heading", result.stderr)


if __name__ == "__main__":
    unittest.main()
