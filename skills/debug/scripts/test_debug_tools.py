#!/usr/bin/env python3
"""Integration tests for the local debug lifecycle CLI and log summarizer."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import urllib.request

SCRIPT_DIR = Path(__file__).resolve().parent
DEBUG_SESSION = SCRIPT_DIR / "debug_session.py"
SUMMARIZER = SCRIPT_DIR / "summarize_debug_log.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import debug_session


class DebugToolTests(unittest.TestCase):
    def _run_json(self, *args: str, expect_ok: bool = True) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            [sys.executable, *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
        raw = result.stdout if result.returncode == 0 else result.stderr
        payload = json.loads(raw)
        if expect_ok:
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(payload.get("ok", True), msg=payload)
        return result, payload

    def _post_event(self, endpoint: str, payload: dict) -> None:
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 202)

    def test_start_parser_opens_dashboard_by_default_with_explicit_headless_opt_out(self) -> None:
        parser = debug_session.build_parser()
        default_args = parser.parse_args(["start"])
        headless_args = parser.parse_args(["start", "--no-open-dashboard"])
        alias_args = parser.parse_args(["start", "--headless"])

        self.assertTrue(default_args.open_dashboard)
        self.assertFalse(headless_args.open_dashboard)
        self.assertFalse(alias_args.open_dashboard)

    def test_load_locations_projects_coverage_plan_for_collector(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan_file = Path(temp_dir) / "coverage-plan.json"
            plan_file.write_text(
                json.dumps(
                    {
                        "schemaVersion": "debug-plan/v1",
                        "locations": [
                            {
                                "probeId": "stale.legacy",
                                "location": "src/stale.ts:1",
                                "hypothesisIds": ["H-stale"],
                            }
                        ],
                        "probes": [
                            {
                                "probeId": "flow.start",
                                "location": "src/app.ts:1",
                                "hypothesisIds": ["H1"],
                                "event": "flow_started",
                                "role": "flow-start",
                                "boundaryIds": ["B1"],
                                "expectedEvents": ["flow_started"],
                                "volumeControl": {"maxEvents": 1},
                                "dataFields": ["state"],
                                "redactions": ["secret"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                debug_session._load_locations(str(plan_file)),
                [
                    {
                        "location": "src/app.ts:1",
                        "hypothesisIds": ["H1"],
                        "probeId": "flow.start",
                    }
                ],
            )

    def test_load_locations_keeps_legacy_array_and_locations_object(self) -> None:
        locations = [
            {
                "location": "src/app.ts:1",
                "hypothesisIds": ["H1"],
                "probeId": "flow.start",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            locations_file = Path(temp_dir) / "locations.json"
            for payload in (locations, {"locations": locations}):
                with self.subTest(payload=payload):
                    locations_file.write_text(json.dumps(payload), encoding="utf-8")
                    self.assertEqual(
                        debug_session._load_locations(str(locations_file)), locations
                    )

    def test_load_locations_reports_invalid_coverage_plan_probes(self) -> None:
        cases = (
            ({"schemaVersion": "debug-plan/v1"}, "must contain.*probes array"),
            ({"probes": {}}, "coverage plan probes must be an array"),
            ({"probes": []}, "coverage plan probes must be a non-empty array"),
            ({"probes": ["src/app.ts:1"]}, "probe at index 0 must be an object"),
            (
                {"probes": [{"location": "src/app.ts:1", "hypothesisIds": []}]},
                "probe at index 0 must have a non-empty probeId",
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            plan_file = Path(temp_dir) / "coverage-plan.json"
            for payload, message in cases:
                with self.subTest(payload=payload):
                    plan_file.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaisesRegex(debug_session.SessionError, message):
                        debug_session._load_locations(str(plan_file))

    def test_open_dashboard_skips_when_frontend_is_already_recorded(self) -> None:
        ready_path = Path("/tmp/debug-ready.json")
        payload = {
            "healthUrl": "http://127.0.0.1:43125/health",
            "stateUrl": "http://127.0.0.1:43125/api/state",
            "dashboardUrl": "http://127.0.0.1:43125/",
        }
        args = mock.Mock(ready_file=str(ready_path), timeout=1.0, confirm_seconds=0.01)

        with mock.patch.object(debug_session, "_read_ready_file", return_value=(ready_path, payload)):
            with mock.patch.object(
                debug_session,
                "_http_json",
                side_effect=[{"ok": True}, {"service": {"dashboardFrontendOpenRecorded": True}}],
            ):
                with mock.patch.object(debug_session, "open_dashboard_in_browser") as open_mock:
                    result = debug_session.command_open_dashboard(args)

        self.assertTrue(result["skipped"])
        self.assertEqual(result["status"], "already_open")
        self.assertTrue(result["frontendConfirmed"])
        open_mock.assert_not_called()

    def test_open_dashboard_records_accepted_request_without_frontend_confirmation(self) -> None:
        ready_path = Path("/tmp/debug-ready.json")
        payload = {
            "healthUrl": "http://127.0.0.1:43125/health",
            "stateUrl": "http://127.0.0.1:43125/api/state",
            "dashboardUrl": "http://127.0.0.1:43125/",
            "dashboardFrontendOpenFailedUrl": "http://127.0.0.1:43125/api/dashboard-open-failed",
            "dashboardToken": "token",
        }
        args = mock.Mock(ready_file=str(ready_path), timeout=1.0, confirm_seconds=0.01)
        failed_calls: list[dict] = []

        def fake_http(url: str, **kwargs: object) -> dict:
            if url == payload["stateUrl"]:
                return {"service": {"dashboardFrontendOpenRecorded": False}}
            if url == payload["dashboardFrontendOpenFailedUrl"]:
                failed_calls.append(dict(kwargs))
                return {"ok": True}
            return {"ok": True}

        open_result = {
            "method": "xdg_open",
            "attempted": True,
            "succeeded": True,
            "error": "",
            "attempts": [],
        }
        with mock.patch.object(debug_session, "_read_ready_file", return_value=(ready_path, payload)):
            with mock.patch.object(debug_session, "_http_json", side_effect=fake_http):
                with mock.patch.object(
                    debug_session,
                    "open_dashboard_in_browser",
                    return_value=open_result,
                ):
                    result = debug_session.command_open_dashboard(args)

        self.assertEqual(result["status"], "frontend_not_confirmed")
        self.assertFalse(result["frontendConfirmed"])
        self.assertTrue(result["failureRecorded"])
        self.assertIn("not_confirmed", result["failureReason"])
        self.assertEqual(len(failed_calls), 1)

    def test_session_lifecycle_structured_counts_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            source_dir = workspace / "src"
            source_dir.mkdir()
            (source_dir / "app.ts").write_text("line 1\nline 2\nline 3\n", encoding="utf-8")

            ready_file: Path | None = None
            start_payload: dict = {}
            try:
                _, start_payload = self._run_json(
                    str(DEBUG_SESSION),
                    "start",
                    "--workspace-root",
                    str(workspace),
                    "--session-id",
                    "integration",
                    "--no-open-dashboard",
                    "--location-state-flush-ms",
                    "25",
                )
                ready_file = Path(start_payload["readyFile"])
                self.assertTrue(ready_file.exists())
                self.assertEqual(start_payload["lifecycleMode"], "local-cli")
                self.assertEqual(start_payload["locationStateFlushMs"], 25)
                self.assertTrue(start_payload["batchEndpoint"].endswith("/ingest/batch"))

                locations_file = workspace / "coverage-plan.json"
                locations_file.write_text(
                    json.dumps(
                        {
                            "schemaVersion": "debug-plan/v1",
                            "probes": [
                                {
                                    "location": "src/app.ts:1",
                                    "hypothesisIds": ["H1", "H2"],
                                    "probeId": "flow.start",
                                    "event": "start",
                                    "role": "flow-start",
                                    "boundaryIds": ["flow"],
                                    "expectedEvents": ["start"],
                                    "volumeControl": {"maxEvents": 1},
                                    "dataFields": ["version"],
                                    "redactions": [],
                                },
                                {
                                    "location": "src/app.ts:2",
                                    "hypothesisIds": ["H2"],
                                    "probeId": "flow.end",
                                    "event": "invariant_failed",
                                    "role": "flow-terminal",
                                    "boundaryIds": ["flow"],
                                    "expectedEvents": ["invariant_failed"],
                                    "volumeControl": {"maxEvents": 1},
                                    "dataFields": ["veryLong"],
                                    "redactions": [],
                                },
                                {
                                    "location": "src/app.ts:3",
                                    "hypothesisIds": ["H3"],
                                    "probeId": "flow.missing",
                                    "event": "state_observed",
                                    "role": "observation",
                                    "boundaryIds": ["flow"],
                                    "expectedEvents": ["state_observed"],
                                    "volumeControl": {"maxEvents": 1},
                                    "dataFields": ["state"],
                                    "redactions": [],
                                },
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                self._run_json(
                    str(DEBUG_SESSION),
                    "sync-locations",
                    "--ready-file",
                    str(ready_file),
                    "--locations-file",
                    str(locations_file),
                )

                base = {
                    "sessionId": "integration",
                    "runId": "initial",
                    "correlationId": "c1",
                    "phase": "flow",
                    "timestamp": int(time.time() * 1000),
                }
                self._post_event(
                    start_payload["endpoint"],
                    {
                        **base,
                        "sequence": 1,
                        "probeId": "flow.start",
                        "hypothesisIds": ["H1", "H2"],
                        "location": "src/app.ts:1",
                        "event": "start",
                        "message": "flow started",
                        "data": {"version": 1},
                    },
                )
                self._post_event(
                    start_payload["endpoint"],
                    {
                        **base,
                        "sequence": 3,
                        "probeId": "flow.end",
                        "hypothesisIds": ["H2"],
                        "location": "src/app.ts:2",
                        "event": "invariant_failed",
                        "level": "error",
                        "message": "flow ended with invalid state",
                        "data": {"veryLong": "x" * 1000},
                    },
                )

                deadline = time.monotonic() + 2
                location_state_file = Path(start_payload["locationStateFile"])
                while time.monotonic() < deadline:
                    state = json.loads(location_state_file.read_text(encoding="utf-8"))
                    if state.get("totalEntries") == 2:
                        break
                    time.sleep(0.025)
                else:
                    self.fail("debounced location state did not flush")

                _, state_payload = self._run_json(
                    str(DEBUG_SESSION),
                    "state",
                    "--ready-file",
                    str(ready_file),
                )
                summary = state_payload["state"]["summary"]
                self.assertEqual(summary["totalEntries"], 2)
                self.assertEqual(summary["probeCounts"][0]["name"], "flow.end")
                self.assertEqual(
                    {item["name"]: item["count"] for item in summary["hypothesisCounts"]},
                    {"H2": 2, "H1": 1},
                )
                self.assertEqual(summary["correlationCounts"], [{"name": "c1", "count": 2}])

                result = subprocess.run(
                    [
                        sys.executable,
                        str(SUMMARIZER),
                        start_payload["logFile"],
                        "--format",
                        "json",
                        "--run-id",
                        "initial",
                        "--expected-probes-file",
                        str(locations_file),
                        "--max-data-chars",
                        "40",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True,
                )
                log_summary = json.loads(result.stdout)
                self.assertEqual(log_summary["stats"]["matchedEvents"], 2)
                self.assertEqual(log_summary["missingExpectedProbeIds"], ["flow.missing"])
                self.assertEqual(log_summary["sequence"]["gapCount"], 1)
                self.assertEqual(len(log_summary["errorLikeEvents"]), 1)
                bounded = log_summary["errorLikeEvents"][0]["data"]["veryLong"]
                self.assertIn("omitted", bounded)

                self._run_json(
                    str(DEBUG_SESSION),
                    "clear",
                    "--ready-file",
                    str(ready_file),
                )
                _, cleared_payload = self._run_json(
                    str(DEBUG_SESSION),
                    "state",
                    "--ready-file",
                    str(ready_file),
                )
                self.assertEqual(cleared_payload["state"]["summary"]["totalEntries"], 0)
                self.assertEqual(
                    cleared_payload["state"]["summary"]["trackedLocationCount"],
                    3,
                )

                artifacts = [Path(path) for path in start_payload["ownedArtifacts"]]
                self._run_json(
                    str(DEBUG_SESSION),
                    "stop",
                    "--ready-file",
                    str(ready_file),
                )
                self.assertTrue(all(not path.exists() for path in artifacts))
                ready_file = None
            finally:
                if ready_file is not None and ready_file.exists():
                    subprocess.run(
                        [
                            sys.executable,
                            str(DEBUG_SESSION),
                            "stop",
                            "--ready-file",
                            str(ready_file),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

    def test_start_rejects_artifact_directory_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as workspace_dir, tempfile.TemporaryDirectory() as outside_dir:
            result, payload = self._run_json(
                str(DEBUG_SESSION),
                "start",
                "--workspace-root",
                workspace_dir,
                "--artifact-dir",
                outside_dir,
                "--session-id",
                "unsafe",
                expect_ok=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(payload["ok"])
            self.assertIn("inside workspace_root", payload["error"])

    def test_summarizer_scopes_sequences_by_run_and_correlation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "events.ndjson"
            events = [
                {"runId": "initial", "correlationId": "shared", "sequence": 1},
                {"runId": "initial", "correlationId": "shared", "sequence": 2},
                {"runId": "verification", "correlationId": "shared", "sequence": 1},
                {"runId": "verification", "correlationId": "shared", "sequence": 2},
            ]
            log_file.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

            _, summary = self._run_json(
                str(SUMMARIZER), str(log_file), "--format", "json"
            )

            self.assertEqual(summary["sequence"]["scopesWithSequence"], 2)
            self.assertEqual(summary["sequence"]["gapCount"], 0)
            self.assertEqual(summary["sequence"]["regressionOrDuplicateCount"], 0)

    def test_summarizer_expected_probes_prefers_coverage_plan_probes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            log_file = root / "events.ndjson"
            plan_file = root / "plan.json"
            log_file.write_text(
                json.dumps({"runId": "initial", "probeId": "flow.start"}) + "\n",
                encoding="utf-8",
            )
            plan_file.write_text(
                json.dumps(
                    {
                        "schemaVersion": "debug-plan/v1",
                        "locations": [{"probeId": "stale.legacy"}],
                        "probes": [
                            {"probeId": "flow.start"},
                            {"probeId": "flow.terminal"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            _, summary = self._run_json(
                str(SUMMARIZER),
                str(log_file),
                "--format",
                "json",
                "--expected-probes-file",
                str(plan_file),
            )

            self.assertEqual(summary["missingExpectedProbeIds"], ["flow.terminal"])

    def test_summarizer_rejects_invalid_coverage_plan_probes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            log_file = root / "events.ndjson"
            plan_file = root / "plan.json"
            log_file.write_text("", encoding="utf-8")
            cases = (
                ({"schemaVersion": "debug-plan/v1", "probes": []}, "non-empty probes"),
                (
                    {"schemaVersion": "debug-plan/v1", "probes": [{}]},
                    "must have a non-empty probeId",
                ),
                (
                    {
                        "schemaVersion": "debug-plan/v1",
                        "probes": [{"probeId": "p1"}, {"probeId": "p1"}],
                    },
                    "is duplicated",
                ),
            )

            for plan, message in cases:
                with self.subTest(plan=plan):
                    plan_file.write_text(json.dumps(plan), encoding="utf-8")
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(SUMMARIZER),
                            str(log_file),
                            "--expected-probes-file",
                            str(plan_file),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(message, result.stderr)

    def test_summarizer_filters_and_counts_extended_correlation_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "events.ndjson"
            events = [
                {
                    "runId": "r1",
                    "correlationId": "flow-1",
                    "parentCorrelationId": "parent-1",
                    "operationId": "operation-1",
                    "requestId": "request-1",
                    "probeId": "p1",
                    "event": "start",
                },
                {
                    "runId": "r1",
                    "correlationId": "flow-1",
                    "parentCorrelationId": "parent-1",
                    "operationId": "operation-2",
                    "requestId": "request-2",
                    "probeId": "p2",
                    "event": "request",
                },
                {
                    "runId": "r1",
                    "correlationId": "flow-2",
                    "parentCorrelationId": "parent-2",
                    "operationId": "operation-1",
                    "requestId": "request-3",
                    "probeId": "p3",
                    "event": "end",
                },
            ]
            log_file.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

            _, summary = self._run_json(
                str(SUMMARIZER), str(log_file), "--format", "json"
            )

            self.assertEqual(
                summary["counts"]["parentCorrelationIds"],
                [
                    {"name": "parent-1", "count": 2},
                    {"name": "parent-2", "count": 1},
                ],
            )
            self.assertEqual(
                summary["counts"]["operationIds"],
                [
                    {"name": "operation-1", "count": 2},
                    {"name": "operation-2", "count": 1},
                ],
            )
            self.assertEqual(
                summary["counts"]["requestIds"],
                [
                    {"name": "request-1", "count": 1},
                    {"name": "request-2", "count": 1},
                    {"name": "request-3", "count": 1},
                ],
            )
            self.assertEqual(summary["timeline"][0]["parentCorrelationId"], "parent-1")
            self.assertEqual(summary["timeline"][0]["operationId"], "operation-1")
            self.assertEqual(summary["timeline"][0]["requestId"], "request-1")

            cases = (
                ("--parent-correlation-id", "parent-1", "parentCorrelationId", 2),
                ("--operation-id", "operation-1", "operationId", 2),
                ("--request-id", "request-2", "requestId", 1),
            )
            for option, value, filter_name, expected_count in cases:
                with self.subTest(option=option):
                    _, filtered = self._run_json(
                        str(SUMMARIZER),
                        str(log_file),
                        "--format",
                        "json",
                        option,
                        value,
                    )
                    self.assertEqual(filtered["filters"][filter_name], value)
                    self.assertEqual(filtered["stats"]["matchedEvents"], expected_count)

    def test_summarizer_counts_invalid_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "events.ndjson"
            log_file.write_text(
                "not-json\n"
                + json.dumps(
                    {
                        "runId": "r1",
                        "probeId": "p1",
                        "hypothesisId": "H1",
                        "event": "ok",
                        "timestamp": 1,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SUMMARIZER), str(log_file), "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            summary = json.loads(result.stdout)
            self.assertEqual(summary["stats"]["invalidLines"], 1)
            self.assertEqual(summary["stats"]["validEvents"], 1)
            self.assertEqual(summary["stats"]["matchedEvents"], 1)


if __name__ == "__main__":
    unittest.main()
