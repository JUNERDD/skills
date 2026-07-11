#!/usr/bin/env python3
"""Tests for the deterministic debug coverage-plan validator."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().with_name("debug_plan.py")


def valid_plan() -> dict:
    return {
        "schemaVersion": "debug-plan/v1",
        "failureContract": {
            "expected": "The latest request owns the displayed result.",
            "observed": "An older response sometimes replaces the latest result.",
            "trigger": "Issue two searches before the first response returns.",
            "scope": "Search results in the local browser build.",
            "frequency": "About one in five runs with delayed networking.",
            "timing": "The older request resolves after the newer request.",
            "lastKnownGood": "Unknown; capture the deployed build and source revision.",
            "reproductionCost": "One local browser run taking about 30 seconds.",
            "constraints": ["Do not log query text."],
        },
        "excludedCauseFamilies": [
            {
                "family": "cache-and-persistence",
                "reason": "The fixture has no cache or persistence layer.",
            }
        ],
        "run": {
            "runId": "initial-race-reproduction",
            "reproductionOwner": "agent",
            "steps": ["Open search.", "Issue two queries before the first returns."],
            "residualAmbiguities": [],
        },
        "boundaries": [
            {
                "id": "B-search-flow",
                "invariant": "Only the newest request generation may commit results.",
                "probeIds": ["search.commit"],
            }
        ],
        "hypotheses": [
            {
                "id": "H-stale-overwrite",
                "mechanism": "Request generation 1 resolves after generation 2 and commits without a generation guard.",
                "boundaryIds": ["B-search-flow"],
                "confirmedBy": ["Generation 1 commits after generation 2."],
                "rejectedBy": ["Every older generation is rejected before commit."],
                "probeIds": ["search.commit"],
                "status": "PENDING",
            }
        ],
        "probes": [
            {
                "probeId": "search.flow-start",
                "location": "src/search.ts:10",
                "event": "search flow started",
                "role": "flow-start",
                "boundaryIds": [],
                "hypothesisIds": [],
                "expectedEvents": ["Exactly once per correlated search flow."],
                "volumeControl": {"strategy": "once-per-flow", "estimatedEvents": 1},
                "dataFields": ["runId", "correlationId", "generation"],
                "redactions": ["query"],
            },
            {
                "probeId": "search.commit",
                "location": "src/search.ts:42",
                "event": "result commit decision",
                "role": "invariant",
                "boundaryIds": ["B-search-flow"],
                "hypothesisIds": ["H-stale-overwrite"],
                "expectedEvents": ["One event for every commit attempt, including rejection."],
                "volumeControl": "bounded fields; no count suppression",
                "dataFields": ["generation", "activeGeneration", "accepted"],
                "redactions": [],
            },
            {
                "probeId": "search.flow-terminal",
                "location": "src/search.ts:80",
                "event": "search flow completed or failed",
                "role": "flow-terminal",
                "boundaryIds": [],
                "hypothesisIds": [],
                "expectedEvents": ["Exactly one terminal outcome per correlated flow."],
                "volumeControl": {"strategy": "once-per-flow", "estimatedEvents": 1},
                "dataFields": ["outcome", "queuedEvents"],
                "redactions": [],
            },
        ],
        "coverage": {
            "causeFamiliesReviewed": True,
            "observerCostReviewed": True,
            "privacyReviewed": True,
            "transportChecked": True,
            "correlationChecked": True,
            "residualAmbiguities": [],
        },
    }


class DebugPlanTests(unittest.TestCase):
    def run_cli(self, plan: dict, *extra: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan_path = Path(temp_dir) / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), "validate", str(plan_path), *extra],
                capture_output=True,
                text=True,
                timeout=10,
            )

    def test_valid_plan_succeeds_with_counts(self) -> None:
        result = self.run_cli(valid_plan())
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["counts"]["boundaries"], 1)
        self.assertEqual(report["counts"]["hypotheses"], 1)
        self.assertEqual(report["counts"]["probes"], 3)
        self.assertEqual(report["counts"]["excludedCauseFamilies"], 1)

    def test_missing_required_fields_fail_validation(self) -> None:
        plan = valid_plan()
        del plan["failureContract"]["observed"]
        del plan["run"]["steps"]
        del plan["probes"][1]["dataFields"]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("failureContract.observed", errors)
        self.assertIn("run.steps", errors)
        self.assertIn("probes[1].dataFields", errors)

    def test_probe_location_must_be_workspace_relative_with_numeric_line(self) -> None:
        plan = valid_plan()
        plan["probes"][1]["location"] = "src/search.ts:commitResults"
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn(
            "probes[1].location: must be a workspace-relative source path followed by a positive line number",
            errors,
        )

    def test_duplicate_ids_are_rejected(self) -> None:
        plan = valid_plan()
        duplicate = deepcopy(plan["hypotheses"][0])
        plan["hypotheses"].append(duplicate)
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("hypotheses[1].id", errors)
        self.assertIn("duplicates", errors)

    def test_excluded_cause_families_require_unique_family_and_reason(self) -> None:
        plan = valid_plan()
        plan["excludedCauseFamilies"].append(
            {"family": "cache-and-persistence", "reason": "Duplicate exclusion."}
        )
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("duplicates excluded family", errors)

    def test_unknown_and_one_way_references_are_rejected(self) -> None:
        plan = valid_plan()
        plan["hypotheses"][0]["boundaryIds"] = ["B-missing"]
        plan["probes"][1]["hypothesisIds"] = ["H-missing"]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("unknown boundary 'B-missing'", errors)
        self.assertIn("unknown hypothesis 'H-missing'", errors)
        self.assertIn("not reciprocated", errors)

    def test_missing_flow_sentinel_is_rejected(self) -> None:
        plan = valid_plan()
        plan["probes"] = [
            probe for probe in plan["probes"] if probe["role"] != "flow-terminal"
        ]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("flow-terminal sentinel", errors)

    def test_unpassed_coverage_gate_is_rejected(self) -> None:
        plan = valid_plan()
        plan["coverage"]["privacyReviewed"] = False
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("coverage.privacyReviewed: must be true", errors)

    def test_residual_ambiguities_must_have_one_authoritative_value(self) -> None:
        plan = valid_plan()
        plan["run"]["residualAmbiguities"] = ["Read source is not yet distinguished."]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn(
            "run.residualAmbiguities: does not match coverage.residualAmbiguities",
            errors,
        )

    def test_markdown_output_is_human_readable(self) -> None:
        result = self.run_cli(valid_plan(), "--format", "markdown")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("# Debug Plan Validation", result.stdout)
        self.assertIn("Result: **PASS**", result.stdout)
        self.assertIn("| Hypotheses | 1 |", result.stdout)
        self.assertIn("## Errors", result.stdout)

    def test_malformed_json_is_a_format_error(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "validate", "-"],
            input="{not-json",
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("could not read valid JSON", report["errors"][0])


if __name__ == "__main__":
    unittest.main()
