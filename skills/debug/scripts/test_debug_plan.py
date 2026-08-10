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


def payload_control(field_bounds: dict | None = None) -> dict:
    return {
        "maxEventBytes": 4096,
        "fieldBounds": field_bounds if field_bounds is not None else {},
        "overflowPolicy": "reject-run",
    }


def valid_plan() -> dict:
    return {
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
            "reproductionOwner": "user",
            "steps": ["Open search.", "Issue two queries before the first returns."],
        },
        "boundaries": [
            {
                "id": "B-search-flow",
                "invariant": "Only the newest request generation may commit results.",
            }
        ],
        "hypotheses": [
            {
                "id": "H-stale-overwrite",
                "mechanism": "Request generation 1 resolves after generation 2 and commits without a generation guard.",
                "boundaryIds": ["B-search-flow"],
                "confirmedBy": ["Generation 1 commits after generation 2."],
                "rejectedBy": ["Every older generation is rejected before commit."],
                "status": "PENDING",
            }
        ],
        "debuggerStrategy": {
            "mode": "attached",
            "reason": "The local source build supports debugger attachment.",
            "breakpoints": [
                {
                    "breakpointId": "breakpoint.search-commit",
                    "kind": "pause",
                    "location": "src/search.ts:42",
                    "activation": "initial",
                    "rationale": "Stop before the suspected stale result commit.",
                    "inspect": ["generation", "activeGeneration", "accepted"],
                    "boundaryIds": ["B-search-flow"],
                    "hypothesisIds": ["H-stale-overwrite"],
                    "condition": "generation != activeGeneration",
                },
                {
                    "breakpointId": "breakpoint.search-terminal",
                    "kind": "pause",
                    "location": "src/search.ts:80",
                    "activation": "initial",
                    "rationale": "Stop at terminal state to inspect the complete search outcome.",
                    "inspect": ["outcome", "queuedEvents"],
                    "boundaryIds": ["B-search-flow"],
                    "hypothesisIds": ["H-stale-overwrite"],
                },
            ],
        },
        "probes": [
            {
                "probeId": "search.flow-start",
                "location": "src/search.ts:10",
                "event": "search flow started",
                "role": "flow-start",
                "boundaryIds": [],
                "hypothesisIds": [],
                "expectedOccurrence": "every-execution",
                "eventPolicy": {
                    "mode": "all-occurrences",
                    "payloadControl": payload_control(
                        {
                            "runId": {"maxBytes": 128},
                            "correlationId": {"maxBytes": 128},
                        }
                    ),
                },
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
                "expectedOccurrence": "every-execution",
                "eventPolicy": {
                    "mode": "all-occurrences",
                    "payloadControl": payload_control(),
                },
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
                "expectedOccurrence": "every-execution",
                "eventPolicy": {
                    "mode": "all-occurrences",
                    "payloadControl": payload_control(
                        {"outcome": {"maxBytes": 256}}
                    ),
                },
                "dataFields": ["outcome", "queuedEvents"],
                "redactions": [],
            },
        ],
        "coverage": {
            "causeFamiliesReviewed": True,
            "firstPassBreakpointBatchReviewed": True,
            "observerCostReviewed": True,
            "privacyReviewed": True,
            "loggingPathChecked": True,
            "correlationChecked": True,
            "eventCardinalityReviewed": True,
            "residualAmbiguities": [],
        },
    }


def valid_observation_checkpoint_plan() -> dict:
    plan = valid_plan()
    plan["run"]["completion"] = {
        "mode": "observation-checkpoint",
        "condition": "Stop after the stale commit is observed or after the bounded 30-second window.",
    }
    plan["probes"][-1] = {
        "probeId": "search.observation-checkpoint",
        "location": "src/search.ts:80",
        "event": "observation checkpoint reached",
        "role": "observation-checkpoint",
        "boundaryIds": [],
        "hypothesisIds": [],
        "expectedOccurrence": "every-execution",
        "eventPolicy": {
            "mode": "all-occurrences",
            "payloadControl": payload_control(
                {
                    "observationWindowId": {"maxBytes": 128},
                    "checkpointReason": {"maxBytes": 512},
                    "businessStreamState": {"maxBytes": 256, "maxDepth": 4},
                }
            ),
        },
        "dataFields": [
            "observationWindowId",
            "checkpointReason",
            "businessStreamState",
            "observedEventCount",
        ],
        "redactions": [],
    }
    return plan


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
        self.assertEqual(report["counts"]["initialBreakpoints"], 2)
        self.assertEqual(report["counts"]["deferredBreakpoints"], 0)
        self.assertEqual(report["counts"]["excludedCauseFamilies"], 1)

    def test_attached_debugger_accepts_initial_and_deferred_breakpoints(self) -> None:
        plan = valid_plan()
        deferred = plan["debuggerStrategy"]["breakpoints"][1]
        deferred["activation"] = "deferred"
        deferred["deferReason"] = "privacy-risk"
        deferred["activateWhen"] = (
            "Enable a redacted locals view that cannot expose private payloads."
        )
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        counts = json.loads(result.stdout)["counts"]
        self.assertEqual(
            (counts["initialBreakpoints"], counts["deferredBreakpoints"]),
            (1, 1),
        )

    def test_debugger_mode_and_reason_are_required_and_validated(self) -> None:
        mutations = (
            lambda strategy: strategy.pop("mode"),
            lambda strategy: strategy.update({"mode": "sometimes-attached"}),
            lambda strategy: strategy.pop("reason"),
            lambda strategy: strategy.update({"reason": "  "}),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                plan = valid_plan()
                mutation(plan["debuggerStrategy"])
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                self.assertIn("debuggerStrategy.", result.stdout)

    def test_debugger_strategy_is_required(self) -> None:
        plan = valid_plan()
        del plan["debuggerStrategy"]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        self.assertIn("debuggerStrategy: must be an object", result.stdout)

    def test_attached_debugger_requires_an_initial_breakpoint(self) -> None:
        plan = valid_plan()
        for breakpoint in plan["debuggerStrategy"]["breakpoints"]:
            breakpoint["activation"] = "deferred"
            breakpoint["deferReason"] = "observer-risk"
            breakpoint["activateWhen"] = "Pausing no longer perturbs the failing race."
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must include at least one initial breakpoint", result.stdout)

    def test_non_attached_debugger_accepts_complete_deferred_candidates(self) -> None:
        for mode, defer_reason in (
            ("unavailable", "tool-unavailable"),
            ("unsafe", "observer-risk"),
        ):
            with self.subTest(mode=mode):
                plan = valid_plan()
                plan["debuggerStrategy"]["mode"] = mode
                for breakpoint in plan["debuggerStrategy"]["breakpoints"]:
                    breakpoint["activation"] = "deferred"
                    breakpoint["deferReason"] = defer_reason
                    breakpoint["activateWhen"] = (
                        "Attach safely once the recorded deferral condition clears."
                    )
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
                counts = json.loads(result.stdout)["counts"]
                self.assertEqual(counts["initialBreakpoints"], 0)
                self.assertEqual(counts["deferredBreakpoints"], 2)

    def test_non_attached_empty_candidate_batch_fails_coverage(self) -> None:
        for mode in ("unavailable", "unsafe"):
            with self.subTest(mode=mode):
                plan = valid_plan()
                plan["debuggerStrategy"]["mode"] = mode
                plan["debuggerStrategy"]["breakpoints"] = []
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                errors = "\n".join(json.loads(result.stdout)["errors"])
                self.assertIn("must include at least one deferred breakpoint", errors)
                self.assertIn(
                    "must be referenced by at least one concrete debugger breakpoint",
                    errors,
                )

    def test_non_attached_debugger_rejects_initial_breakpoints(self) -> None:
        for mode in ("unavailable", "unsafe"):
            with self.subTest(mode=mode):
                plan = valid_plan()
                plan["debuggerStrategy"]["mode"] = mode
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    f"{mode} mode must not include initial breakpoints",
                    result.stdout,
                )

    def test_duplicate_breakpoint_ids_are_rejected(self) -> None:
        plan = valid_plan()
        duplicate = deepcopy(plan["debuggerStrategy"]["breakpoints"][0])
        plan["debuggerStrategy"]["breakpoints"].append(duplicate)
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        self.assertIn("debuggerStrategy.breakpoints[2].breakpointId", result.stdout)
        self.assertIn("duplicates", result.stdout)

    def test_duplicate_physical_breakpoints_are_rejected_and_counted_once(self) -> None:
        plan = valid_plan()
        original = plan["debuggerStrategy"]["breakpoints"][0]
        duplicate = deepcopy(original)
        duplicate["breakpointId"] = "breakpoint.search-commit-duplicate"
        duplicate["location"] = "src\\search.ts:042"
        duplicate["condition"] = "generation < activeGeneration"
        plan["debuggerStrategy"]["breakpoints"] = [original, duplicate]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertIn("duplicates the physical breakpoint", "\n".join(report["errors"]))
        self.assertEqual(report["counts"]["initialBreakpoints"], 1)

    def test_debugger_breakpoints_must_be_pause_kind(self) -> None:
        for value in (None, "logpoint"):
            with self.subTest(value=value):
                plan = valid_plan()
                breakpoint = plan["debuggerStrategy"]["breakpoints"][0]
                if value is None:
                    del breakpoint["kind"]
                else:
                    breakpoint["kind"] = value
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                self.assertIn("breakpoints[0].kind", result.stdout)
                if value == "logpoint":
                    self.assertIn(
                        "evidence-bearing logpoints belong in probes",
                        result.stdout,
                    )

    def test_breakpoint_content_and_references_are_validated(self) -> None:
        plan = valid_plan()
        breakpoint = plan["debuggerStrategy"]["breakpoints"][0]
        breakpoint["location"] = "/tmp/search.ts:42"
        breakpoint["rationale"] = ""
        breakpoint["inspect"] = []
        breakpoint["boundaryIds"] = ["B-missing"]
        breakpoint["hypothesisIds"] = ["H-missing"]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("debuggerStrategy.breakpoints[0].location", errors)
        self.assertIn("debuggerStrategy.breakpoints[0].rationale", errors)
        self.assertIn("debuggerStrategy.breakpoints[0].inspect", errors)
        self.assertIn("unknown boundary 'B-missing'", errors)
        self.assertIn("unknown hypothesis 'H-missing'", errors)

    def test_deferred_breakpoint_requires_condition_and_reason(self) -> None:
        for field in ("activateWhen", "deferReason"):
            for value in (None, ""):
                with self.subTest(field=field, value=value):
                    plan = valid_plan()
                    breakpoint = plan["debuggerStrategy"]["breakpoints"][1]
                    breakpoint["activation"] = "deferred"
                    breakpoint["activateWhen"] = (
                        "Enable a redacted locals view that cannot expose private payloads."
                    )
                    breakpoint["deferReason"] = "privacy-risk"
                    if value is None:
                        del breakpoint[field]
                    else:
                        breakpoint[field] = value
                    result = self.run_cli(plan)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(
                        f"debuggerStrategy.breakpoints[1].{field}",
                        result.stdout,
                    )

    def test_initial_breakpoint_rejects_deferred_fields(self) -> None:
        plan = valid_plan()
        plan["debuggerStrategy"]["breakpoints"][0]["activateWhen"] = "Later."
        plan["debuggerStrategy"]["breakpoints"][0][
            "deferReason"
        ] = "privacy-risk"
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("breakpoints[0].activateWhen", errors)
        self.assertIn("breakpoints[0].deferReason", errors)
        self.assertEqual(errors.count("must be omitted for an initial breakpoint"), 2)

    def test_prior_breakpoint_inconclusive_is_not_a_deferral_reason(self) -> None:
        plan = valid_plan()
        breakpoint = plan["debuggerStrategy"]["breakpoints"][1]
        breakpoint["activation"] = "deferred"
        breakpoint["activateWhen"] = "The prior breakpoint is inconclusive."
        breakpoint["deferReason"] = "privacy-risk"
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn(
            "do not defer until an earlier breakpoint is inconclusive",
            errors,
        )

    def test_breakpoint_boundary_ids_require_an_existing_boundary(self) -> None:
        plan = valid_plan()
        plan["debuggerStrategy"]["breakpoints"][0]["boundaryIds"] = []
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        self.assertIn("breakpoints[0].boundaryIds: must not be empty", result.stdout)

    def test_multi_boundary_breakpoint_requires_shared_rationale(self) -> None:
        plan = valid_plan()
        plan["boundaries"].append(
            {
                "id": "B-commit-ownership",
                "invariant": "The active generation owns the pending result commit.",
            }
        )
        plan["debuggerStrategy"]["breakpoints"][0]["boundaryIds"] = [
            "B-search-flow",
            "B-commit-ownership",
        ]
        plan["debuggerStrategy"]["breakpoints"][1]["boundaryIds"] = [
            "B-commit-ownership"
        ]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "breakpoints[0].sharedBoundaryRationale: must be a non-empty string",
            result.stdout,
        )

    def test_single_boundary_breakpoint_rejects_shared_rationale(self) -> None:
        plan = valid_plan()
        plan["debuggerStrategy"]["breakpoints"][0][
            "sharedBoundaryRationale"
        ] = "Unnecessary for one boundary."
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "must be omitted unless boundaryIds contains multiple boundaries",
            result.stdout,
        )

    def test_non_attached_mode_rejects_incompatible_defer_reason(self) -> None:
        for mode, defer_reason in (
            ("unavailable", "observer-risk"),
            ("unsafe", "tool-unavailable"),
        ):
            with self.subTest(mode=mode, defer_reason=defer_reason):
                plan = valid_plan()
                plan["debuggerStrategy"]["mode"] = mode
                for breakpoint in plan["debuggerStrategy"]["breakpoints"]:
                    breakpoint["activation"] = "deferred"
                    breakpoint["activateWhen"] = "The deferral condition clears."
                    breakpoint["deferReason"] = defer_reason
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    f"is not permitted when debuggerStrategy.mode is {mode}",
                    result.stdout,
                )

    def test_shared_frame_can_cover_multiple_boundaries_with_rationale(self) -> None:
        plan = valid_plan()
        plan["boundaries"].append(
            {
                "id": "B-commit-ownership",
                "invariant": "The active generation owns the pending result commit.",
            }
        )
        plan["hypotheses"].append(
            {
                "id": "H-ownership-mismatch",
                "mechanism": "The commit frame retains an owner that differs from the active request generation.",
                "boundaryIds": ["B-commit-ownership"],
                "confirmedBy": ["The pending owner differs from the active generation."],
                "rejectedBy": ["The pending owner always equals the active generation."],
                "status": "PENDING",
            }
        )
        shared = plan["debuggerStrategy"]["breakpoints"][0]
        shared["boundaryIds"] = ["B-search-flow", "B-commit-ownership"]
        shared["hypothesisIds"] = ["H-stale-overwrite", "H-ownership-mismatch"]
        shared["sharedBoundaryRationale"] = (
            "The same pre-commit frame exposes both generation ordering and result ownership."
        )
        plan["probes"][1]["boundaryIds"] = [
            "B-search-flow",
            "B-commit-ownership",
        ]
        plan["probes"][1]["hypothesisIds"] = [
            "H-stale-overwrite",
            "H-ownership-mismatch",
        ]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_debugger_and_breakpoint_unknown_fields_are_rejected(self) -> None:
        plan = valid_plan()
        plan["debuggerStrategy"]["retry"] = True
        plan["debuggerStrategy"]["breakpoints"][0]["eventPolicy"] = {
            "mode": "all-occurrences"
        }
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("debuggerStrategy: contains unsupported fields: retry", errors)
        self.assertIn("debuggerStrategy.breakpoints[0]: contains unsupported fields: eventPolicy", errors)

    def test_breakpoints_do_not_change_or_satisfy_probe_counts(self) -> None:
        plan = valid_plan()
        plan["probes"][1]["boundaryIds"] = []
        plan["probes"][1]["hypothesisIds"] = []
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["probes"], 3)
        self.assertEqual(report["counts"]["initialBreakpoints"], 2)
        self.assertEqual(report["counts"]["deferredBreakpoints"], 0)
        errors = "\n".join(report["errors"])
        self.assertIn("must be referenced by at least one probe", errors)

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

    def test_agent_reproduction_requires_current_user_delegation(self) -> None:
        plan = valid_plan()
        plan["run"]["reproductionOwner"] = "agent"
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("run.reproductionDelegation", errors)

        plan["run"]["reproductionDelegation"] = {
            "target": "agent",
            "scope": "remaining-runs",
            "effectiveRunId": plan["run"]["runId"],
            "currentUserDirective": (
                "Have the agent investigate this runtime failure."
            ),
        }
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_reproduction_delegation_must_match_non_user_owner(self) -> None:
        plan = valid_plan()
        plan["run"]["reproductionDelegation"] = None
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("must be omitted", errors)

        plan = valid_plan()
        plan["run"]["reproductionDelegation"] = {
            "target": "agent",
            "scope": "single-run",
            "effectiveRunId": plan["run"]["runId"],
            "currentUserDirective": "Investigate this yourself.",
        }
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("must be omitted", errors)

        plan = valid_plan()
        plan["run"]["reproductionOwner"] = "external"
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("run.reproductionDelegation", errors)

        plan["run"]["reproductionDelegation"] = {
            "target": "agent",
            "scope": "single-run",
            "effectiveRunId": plan["run"]["runId"],
            "currentUserDirective": "Ask the designated external operator to reproduce.",
        }
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("must match run.reproductionOwner", errors)

        plan["run"]["reproductionDelegation"]["target"] = "external"
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_reproduction_delegation_is_scoped_to_current_run(self) -> None:
        plan = valid_plan()
        plan["run"]["reproductionOwner"] = "agent"
        plan["run"]["reproductionDelegation"] = {
            "target": "agent",
            "scope": "future",
            "effectiveRunId": "different-run",
            "currentUserDirective": "Have the agent run the verification.",
        }
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("run.reproductionDelegation.scope", errors)
        self.assertIn("must match run.runId", errors)

        plan["run"]["reproductionDelegation"]["scope"] = "single-run"
        plan["run"]["reproductionDelegation"]["effectiveRunId"] = plan["run"][
            "runId"
        ]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

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

    def test_probe_event_policy_is_required_and_strict(self) -> None:
        plan = valid_plan()
        del plan["probes"][1]["eventPolicy"]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("probes[1].eventPolicy: must be an object", errors)

        plan = valid_plan()
        plan["probes"][1]["eventPolicy"]["payloadControl"] = (
            "emit every other occurrence"
        )
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("eventPolicy.payloadControl: must be an object", errors)

    def test_expected_occurrence_is_required_and_fixed(self) -> None:
        plan = valid_plan()
        del plan["probes"][1]["expectedOccurrence"]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("probes[1].expectedOccurrence: must be a non-empty string", errors)

        for value in ("every-other-execution", "once-per-key", "when-value-changes"):
            with self.subTest(value=value):
                plan = valid_plan()
                plan["probes"][1]["expectedOccurrence"] = value
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                errors = "\n".join(json.loads(result.stdout)["errors"])
                self.assertIn("must be 'every-execution'", errors)

    def test_probe_event_policy_rejects_every_suppressing_mode(self) -> None:
        for mode in (
            "sampled",
            "once-per-key",
            "change-only",
            "aggregated",
            "suppressed",
            "deduplicated",
        ):
            with self.subTest(mode=mode):
                plan = valid_plan()
                plan["probes"][1]["eventPolicy"]["mode"] = mode
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                errors = "\n".join(json.loads(result.stdout)["errors"])
                self.assertIn("must be 'all-occurrences'", errors)

    def test_legacy_free_text_occurrence_policy_is_always_rejected(self) -> None:
        smuggled_policies = (
            "emit every other occurrence",
            "only emit when the value changes",
            "filter occurrences by key",
            "keep events whose sequence is even",
            "只记录值发生变化的事件",
        )
        for value in smuggled_policies:
            with self.subTest(legacy_field="expectedEvents", value=value):
                plan = valid_plan()
                plan["probes"][1]["expectedEvents"] = [value]
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                errors = "\n".join(json.loads(result.stdout)["errors"])
                self.assertIn("legacy free-text occurrence policy is forbidden", errors)

            with self.subTest(legacy_field="payloadControl", value=value):
                plan = valid_plan()
                plan["probes"][1]["eventPolicy"]["payloadControl"] = value
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                errors = "\n".join(json.loads(result.stdout)["errors"])
                self.assertIn("payloadControl: must be an object", errors)

    def test_structured_payload_control_accepts_only_payload_bounds(self) -> None:
        plan = valid_plan()
        plan["probes"][1]["eventPolicy"]["payloadControl"] = payload_control(
            {
                "generation": {"maxBytes": 32, "maxItems": 4, "maxDepth": 2},
                "accepted": {"maxBytes": 8},
            }
        )
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        invalid_max_values = (0, -1, True, 1.5, "4096")
        for value in invalid_max_values:
            with self.subTest(maxEventBytes=value):
                plan = valid_plan()
                plan["probes"][1]["eventPolicy"]["payloadControl"][
                    "maxEventBytes"
                ] = value
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                errors = "\n".join(json.loads(result.stdout)["errors"])
                self.assertIn("maxEventBytes: must be a positive integer", errors)

        plan = valid_plan()
        plan["probes"][1]["eventPolicy"]["payloadControl"]["fieldBounds"] = {
            "unlistedField": {"maxBytes": 64}
        }
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("must name a field listed in probes[1].dataFields", errors)

        for field_bound in ({}, {"maxEvents": 1}, {"maxBytes": 0}):
            with self.subTest(field_bound=field_bound):
                plan = valid_plan()
                plan["probes"][1]["eventPolicy"]["payloadControl"][
                    "fieldBounds"
                ] = {"generation": field_bound}
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)

        plan = valid_plan()
        plan["probes"][1]["eventPolicy"]["payloadControl"][
            "overflowPolicy"
        ] = "drop-event"
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("must be 'reject-run'", errors)

    def test_unsafe_extra_policy_keys_are_rejected_at_every_level(self) -> None:
        mutations = (
            lambda probe: probe.update({"samplingPolicy": "every other event"}),
            lambda probe: probe["eventPolicy"].update({"sampleRate": 0.5}),
            lambda probe: probe["eventPolicy"]["payloadControl"].update(
                {"maxEvents": 10}
            ),
            lambda probe: probe["eventPolicy"]["payloadControl"][
                "fieldBounds"
            ].update({"generation": {"eventLimit": 10}}),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                plan = valid_plan()
                mutation(plan["probes"][1])
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                errors = "\n".join(json.loads(result.stdout)["errors"])
                self.assertTrue(
                    "unsupported fields" in errors or "unexpected:" in errors,
                    errors,
                )

    def test_occurrence_controls_cannot_move_to_other_schema_objects(self) -> None:
        cases = (
            ("plan", lambda plan: plan.update({"sampleRate": 0.5})),
            (
                "failureContract",
                lambda plan: plan["failureContract"].update({"firstN": 10}),
            ),
            (
                "excludedCauseFamilies[0]",
                lambda plan: plan["excludedCauseFamilies"][0].update(
                    {"deduplicate": True}
                ),
            ),
            (
                "run",
                lambda plan: plan["run"].update(
                    {"samplingPolicy": "every-other"}
                ),
            ),
            (
                "boundaries[0]",
                lambda plan: plan["boundaries"][0].update({"maxEvents": 1}),
            ),
            (
                "hypotheses[0]",
                lambda plan: plan["hypotheses"][0].update({"changeOnly": True}),
            ),
            ("coverage", lambda plan: plan["coverage"].update({"oncePerKey": True})),
        )
        for expected_path, mutation in cases:
            with self.subTest(expected_path=expected_path):
                plan = valid_plan()
                mutation(plan)
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                errors = "\n".join(json.loads(result.stdout)["errors"])
                self.assertIn(f"{expected_path}: contains unsupported fields", errors)

        plan = valid_observation_checkpoint_plan()
        plan["run"]["completion"]["sampled"] = True
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("run.completion: contains unsupported fields", errors)

        plan = valid_plan()
        plan["run"]["reproductionOwner"] = "agent"
        plan["run"]["reproductionDelegation"] = {
            "target": "agent",
            "scope": "single-run",
            "effectiveRunId": plan["run"]["runId"],
            "currentUserDirective": "Investigate this run yourself.",
            "sampleRate": 0.5,
        }
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn(
            "run.reproductionDelegation: contains unsupported fields",
            errors,
        )

    def test_legacy_volume_control_is_rejected(self) -> None:
        plan = valid_plan()
        plan["probes"][1]["volumeControl"] = {
            "strategy": "sampled",
            "maxEvents": 1,
        }
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("probes[1].volumeControl", errors)
        self.assertIn("legacy event filtering is forbidden", errors)

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

    def test_unknown_and_uncovered_references_are_rejected(self) -> None:
        plan = valid_plan()
        plan["hypotheses"][0]["boundaryIds"] = ["B-missing"]
        plan["probes"][1]["boundaryIds"] = []
        plan["probes"][1]["hypothesisIds"] = ["H-missing"]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("unknown boundary 'B-missing'", errors)
        self.assertIn("unknown hypothesis 'H-missing'", errors)
        self.assertIn("boundaries[0]: must be referenced by at least one probe", errors)
        self.assertIn("hypotheses[0]: must be referenced by at least one probe", errors)

    def test_missing_flow_sentinel_is_rejected(self) -> None:
        plan = valid_plan()
        plan["probes"] = [
            probe for probe in plan["probes"] if probe["role"] != "flow-terminal"
        ]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("flow-terminal sentinel", errors)

    def test_observation_checkpoint_can_close_a_long_lived_run(self) -> None:
        result = self.run_cli(valid_observation_checkpoint_plan())
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["flowTerminalProbes"], 0)
        self.assertEqual(report["counts"]["observationCheckpointProbes"], 1)

    def test_checkpoint_does_not_replace_terminal_without_explicit_completion_mode(self) -> None:
        plan = valid_observation_checkpoint_plan()
        del plan["run"]["completion"]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("flow-terminal sentinel", errors)

    def test_observation_checkpoint_requires_condition_and_probe(self) -> None:
        plan = valid_observation_checkpoint_plan()
        plan["run"]["completion"]["condition"] = ""
        plan["probes"] = [
            probe for probe in plan["probes"] if probe["role"] != "observation-checkpoint"
        ]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("run.completion.condition", errors)
        self.assertIn("observation-checkpoint sentinel", errors)

    def test_completion_shape_and_mode_are_validated(self) -> None:
        plan = valid_plan()
        plan["run"]["completion"] = "until done"
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        self.assertIn("run.completion: must be an object", result.stdout)

        plan = valid_plan()
        plan["run"]["completion"] = {"mode": "stream-never-ends"}
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        self.assertIn("run.completion.mode: must be one of", result.stdout)

    def test_unpassed_coverage_gate_is_rejected(self) -> None:
        plan = valid_plan()
        plan["coverage"]["privacyReviewed"] = False
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("coverage.privacyReviewed: must be true", errors)

    def test_event_cardinality_review_is_required(self) -> None:
        plan = valid_plan()
        del plan["coverage"]["eventCardinalityReviewed"]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("coverage.eventCardinalityReviewed: must be true", errors)

    def test_first_pass_breakpoint_batch_review_is_required_and_true(self) -> None:
        for value in (None, False):
            with self.subTest(value=value):
                plan = valid_plan()
                if value is None:
                    del plan["coverage"]["firstPassBreakpointBatchReviewed"]
                else:
                    plan["coverage"]["firstPassBreakpointBatchReviewed"] = value
                result = self.run_cli(plan)
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    "coverage.firstPassBreakpointBatchReviewed: must be true",
                    result.stdout,
                )

    def test_residual_ambiguities_warn_from_the_coverage_gate(self) -> None:
        plan = valid_plan()
        plan["coverage"]["residualAmbiguities"] = ["Read source is not yet distinguished."]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["residualAmbiguities"], 1)
        self.assertIn("contains 1 unresolved ambiguity", report["warnings"][0])

    def test_residual_ambiguity_does_not_replace_concrete_breakpoint_coverage(self) -> None:
        plan = valid_plan()
        plan["boundaries"].append(
            {
                "id": "B-render-dispatch",
                "invariant": "The render target resolves to the active view instance.",
            }
        )
        plan["hypotheses"].append(
            {
                "id": "H-dynamic-render-target",
                "mechanism": "Dynamic dispatch selects a stale view instance after the result commit.",
                "boundaryIds": ["B-render-dispatch"],
                "confirmedBy": ["The resolved view instance is stale."],
                "rejectedBy": ["The resolved view instance is always active."],
                "status": "PENDING",
            }
        )
        plan["probes"][1]["boundaryIds"].append("B-render-dispatch")
        plan["probes"][1]["hypothesisIds"].append("H-dynamic-render-target")
        plan["coverage"]["residualAmbiguities"] = [
            "The dynamic render implementation path:line is not yet resolved."
        ]
        result = self.run_cli(plan)
        self.assertEqual(result.returncode, 1)
        errors = "\n".join(json.loads(result.stdout)["errors"])
        self.assertIn("residualAmbiguities does not waive coverage", errors)

    def test_markdown_output_is_human_readable(self) -> None:
        result = self.run_cli(valid_plan(), "--format", "markdown")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("# Debug Plan Validation", result.stdout)
        self.assertIn("Result: **PASS**", result.stdout)
        self.assertIn("| Hypotheses | 1 |", result.stdout)
        self.assertIn("| Observation-checkpoint probes | 0 |", result.stdout)
        self.assertIn("| Initial breakpoints | 2 |", result.stdout)
        self.assertIn("| Deferred breakpoints | 0 |", result.stdout)
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
