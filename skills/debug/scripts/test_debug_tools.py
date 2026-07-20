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

    def _create_stop_fixture(
        self,
        workspace: Path,
    ) -> tuple[Path, dict, list[Path], debug_session._ProcessIdentity]:
        artifact_dir = workspace / ".debug-logs"
        artifact_dir.mkdir()
        log_file = artifact_dir / "stop.ndjson"
        location_file = artifact_dir / "stop.locations.json"
        ready_file = artifact_dir / "stop.json"
        service_log_file = artifact_dir / "stop.service.log"
        artifacts = [log_file, location_file, ready_file, service_log_file]
        for artifact in artifacts:
            artifact.write_text("fixture", encoding="utf-8")

        pid = 4242
        process_started_at = 1_000_000
        payload = {
            "sessionId": "stop",
            "workspaceRoot": str(workspace),
            "logFile": str(log_file),
            "readyFile": str(ready_file),
            "ownedArtifacts": [str(path) for path in artifacts],
            "shutdownUrl": "http://127.0.0.1:43125/api/shutdown",
            "healthUrl": "http://127.0.0.1:43125/health",
            "dashboardToken": "test-token",
            "pid": pid,
            "startedAt": process_started_at + 5_000,
        }
        ready_file.write_text(json.dumps(payload), encoding="utf-8")
        identity = debug_session._ProcessIdentity(
            pid=pid,
            started_at_ms=process_started_at,
            command_line=(
                f"{sys.executable} {debug_session.COLLECTOR_MAIN.resolve()} "
                f"--ready-file {ready_file.resolve()} --session-id stop"
            ),
        )
        return ready_file, payload, artifacts, identity

    def test_start_parser_opens_dashboard_by_default_with_explicit_headless_opt_out(self) -> None:
        parser = debug_session.build_parser()
        default_args = parser.parse_args(["start"])
        headless_args = parser.parse_args(["start", "--no-open-dashboard"])
        alias_args = parser.parse_args(["start", "--headless"])

        self.assertTrue(default_args.open_dashboard)
        self.assertFalse(headless_args.open_dashboard)
        self.assertFalse(alias_args.open_dashboard)

    def test_stop_waits_for_delayed_process_exit_before_deleting_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()
            ready_file, payload, artifacts, identity = self._create_stop_fixture(workspace)
            args = debug_session.build_parser().parse_args(
                [
                    "stop",
                    "--ready-file",
                    str(ready_file),
                    "--wait-seconds",
                    "1",
                ]
            )
            shutdown_returned = False
            identity_reads = 0

            def fake_http(*_args: object, **_kwargs: object) -> dict:
                nonlocal shutdown_returned
                shutdown_returned = True
                return {"ok": True, "status": "stopping"}

            def fake_identity(pid: int) -> debug_session._ProcessIdentity | None:
                nonlocal identity_reads
                identity_reads += 1
                self.assertEqual(pid, payload["pid"])
                if identity_reads == 1:
                    return identity
                self.assertTrue(shutdown_returned)
                self.assertTrue(all(path.exists() for path in artifacts))
                if identity_reads < 4:
                    return identity
                return None

            with mock.patch.object(
                debug_session,
                "_http_json",
                side_effect=fake_http,
            ) as http_mock:
                with mock.patch.object(
                    debug_session,
                    "_read_process_identity",
                    side_effect=fake_identity,
                ):
                    with mock.patch.object(debug_session.time, "sleep"):
                        result = debug_session.command_stop(args)

            self.assertEqual(result["status"], "stopped")
            self.assertEqual(identity_reads, 4)
            self.assertTrue(all(not path.exists() for path in artifacts))
            http_mock.assert_called_once_with(
                payload["shutdownUrl"],
                method="POST",
                token="test-token",
                timeout=args.timeout,
            )

    def test_stop_preserves_artifacts_when_original_process_does_not_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()
            ready_file, _payload, artifacts, identity = self._create_stop_fixture(workspace)
            args = debug_session.build_parser().parse_args(
                [
                    "stop",
                    "--ready-file",
                    str(ready_file),
                    "--wait-seconds",
                    "1",
                ]
            )

            with mock.patch.object(
                debug_session,
                "_http_json",
                return_value={"ok": True, "status": "stopping"},
            ):
                with mock.patch.object(
                    debug_session,
                    "_read_process_identity",
                    return_value=identity,
                ):
                    with mock.patch.object(
                        debug_session.time,
                        "monotonic",
                        side_effect=(0.0, 2.0),
                    ):
                        with self.assertRaisesRegex(
                            debug_session.SessionError,
                            "collector process is still running",
                        ):
                            debug_session.command_stop(args)

            self.assertTrue(all(path.exists() for path in artifacts))

    def test_stop_accepts_pid_reuse_as_original_process_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()
            ready_file, payload, artifacts, identity = self._create_stop_fixture(workspace)
            args = debug_session.build_parser().parse_args(
                ["stop", "--ready-file", str(ready_file), "--wait-seconds", "1"]
            )
            reused_identity = debug_session._ProcessIdentity(
                pid=payload["pid"],
                started_at_ms=identity.started_at_ms + 10_000,
                command_line="unrelated replacement process",
            )

            with mock.patch.object(
                debug_session,
                "_http_json",
                return_value={"ok": True, "status": "stopping"},
            ):
                with mock.patch.object(
                    debug_session,
                    "_read_process_identity",
                    side_effect=(identity, reused_identity),
                ):
                    result = debug_session.command_stop(args)

            self.assertEqual(result["status"], "stopped")
            self.assertTrue(all(not path.exists() for path in artifacts))

    def test_resume_reuses_healthy_ready_file_without_process_or_dashboard_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()
            artifact_dir = workspace / ".debug-logs"
            artifact_dir.mkdir()
            ready_file = artifact_dir / "resume.json"
            payload = {
                "sessionId": "resume",
                "workspaceRoot": str(workspace),
                "logFile": str(artifact_dir / "resume.ndjson"),
                "healthUrl": "http://127.0.0.1:43125/health",
                "endpoint": "http://127.0.0.1:43125/ingest",
                "dashboardUrl": "http://127.0.0.1:43125/",
                "dashboardToken": "test-token",
                "dashboardAutoOpenEnabled": True,
                "dashboardFrontendOpenRecorded": True,
                "pid": 4242,
                "port": 43125,
                "startedAt": 123456789,
                "readyFile": str(ready_file),
            }
            ready_file.write_text(json.dumps(payload), encoding="utf-8")
            health = {**payload, "ok": True, "status": "running"}
            args = debug_session.build_parser().parse_args(
                ["resume", "--ready-file", str(ready_file)]
            )

            with mock.patch.object(debug_session, "_http_json", return_value=health):
                with mock.patch.object(debug_session.subprocess, "Popen") as popen_mock:
                    with mock.patch.object(
                        debug_session,
                        "_recover_dashboard_after_start",
                    ) as recover_mock:
                        with mock.patch.object(
                            debug_session,
                            "open_dashboard_in_browser",
                        ) as open_mock:
                            result = debug_session.command_resume(args)

            self.assertEqual(result["sessionAction"], "reused")
            self.assertEqual(result["lifecycleMode"], "local-cli")
            self.assertEqual(result["dashboardRecovery"]["fallbackAttemptCount"], 0)
            self.assertEqual(result["dashboardRecovery"]["status"], "frontend_confirmed")
            self.assertTrue(result["dashboardRecovery"]["frontendConfirmed"])
            for key in ("sessionId", "pid", "port", "endpoint", "dashboardUrl", "startedAt"):
                self.assertEqual(result[key], payload[key])
            self.assertEqual(result["readyFile"], str(ready_file))
            popen_mock.assert_not_called()
            recover_mock.assert_not_called()
            open_mock.assert_not_called()

    def test_resume_rejects_copied_ready_file_without_health_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()
            artifact_dir = workspace / ".debug-logs"
            artifact_dir.mkdir()
            ready_file = artifact_dir / "copied.json"
            payload = {
                "sessionId": "resume",
                "workspaceRoot": str(workspace),
                "logFile": str(artifact_dir / "resume.ndjson"),
                "readyFile": str(artifact_dir / "original.json"),
                "healthUrl": "http://127.0.0.1:43125/health",
                "dashboardToken": "test-token",
                "pid": 4242,
                "startedAt": 123456789,
            }
            ready_file.write_text(json.dumps(payload), encoding="utf-8")
            args = debug_session.build_parser().parse_args(
                ["resume", "--ready-file", str(ready_file)]
            )

            with mock.patch.object(debug_session, "_http_json") as http_mock:
                with mock.patch.object(debug_session.subprocess, "Popen") as popen_mock:
                    with self.assertRaisesRegex(
                        debug_session.SessionError,
                        "does not match the requested ready file",
                    ):
                        debug_session.command_resume(args)

            http_mock.assert_not_called()
            popen_mock.assert_not_called()

    def test_resume_rejects_unhealthy_or_mismatched_session_without_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()
            artifact_dir = workspace / ".debug-logs"
            artifact_dir.mkdir()
            ready_file = artifact_dir / "resume.json"
            payload = {
                "sessionId": "resume",
                "workspaceRoot": str(workspace),
                "logFile": str(artifact_dir / "resume.ndjson"),
                "healthUrl": "http://127.0.0.1:43125/health",
                "dashboardToken": "test-token",
                "pid": 4242,
                "startedAt": 123456789,
                "readyFile": str(ready_file),
            }
            ready_file.write_text(json.dumps(payload), encoding="utf-8")
            original_ready = ready_file.read_text(encoding="utf-8")
            args = debug_session.build_parser().parse_args(
                ["resume", "--ready-file", str(ready_file)]
            )
            cases = (
                {**payload, "ok": True, "status": "stopping"},
                {**payload, "ok": True, "status": "running", "sessionId": "other"},
                {
                    **payload,
                    "ok": True,
                    "status": "running",
                    "workspaceRoot": str(workspace / "other"),
                },
                {
                    **payload,
                    "ok": True,
                    "status": "running",
                    "logFile": str(artifact_dir / "other.ndjson"),
                },
                {**payload, "ok": True, "status": "running", "pid": 4243},
                {**payload, "ok": True, "status": "running", "startedAt": 123456790},
                {
                    **payload,
                    "ok": True,
                    "status": "running",
                    "dashboardToken": "other-token",
                },
            )

            for health in cases:
                with self.subTest(health=health):
                    with mock.patch.object(debug_session, "_http_json", return_value=health):
                        with mock.patch.object(debug_session.subprocess, "Popen") as popen_mock:
                            with mock.patch.object(
                                debug_session,
                                "open_dashboard_in_browser",
                            ) as open_mock:
                                with self.assertRaises(debug_session.SessionError):
                                    debug_session.command_resume(args)
                    self.assertEqual(ready_file.read_text(encoding="utf-8"), original_ready)
                    popen_mock.assert_not_called()
                    open_mock.assert_not_called()

    def test_start_requires_explicit_resume_for_healthy_same_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()
            artifact_dir = workspace / ".debug-logs"
            artifact_dir.mkdir()
            ready_file = artifact_dir / "same-session.json"
            payload = {
                "sessionId": "same-session",
                "workspaceRoot": str(workspace),
                "logFile": str(artifact_dir / "same-session.ndjson"),
                "healthUrl": "http://127.0.0.1:43125/health",
                "dashboardUrl": "http://127.0.0.1:43125/",
                "dashboardToken": "test-token",
                "pid": 4242,
                "port": 43125,
                "startedAt": 123456789,
                "readyFile": str(ready_file),
            }
            ready_file.write_text(json.dumps(payload), encoding="utf-8")
            health = {**payload, "ok": True, "status": "running"}
            args = debug_session.build_parser().parse_args(
                [
                    "start",
                    "--workspace-root",
                    str(workspace),
                    "--session-id",
                    "same-session",
                ]
            )

            with mock.patch.object(debug_session, "_http_json", return_value=health):
                with mock.patch.object(debug_session.subprocess, "Popen") as popen_mock:
                    with mock.patch.object(
                        debug_session,
                        "_recover_dashboard_after_start",
                    ) as recover_mock:
                        with mock.patch.object(
                            debug_session,
                            "open_dashboard_in_browser",
                        ) as open_mock:
                            with self.assertRaisesRegex(
                                debug_session.SessionError,
                                "resume --ready-file",
                            ):
                                debug_session.command_start(args)

            popen_mock.assert_not_called()
            recover_mock.assert_not_called()
            open_mock.assert_not_called()

    def test_dashboard_startup_wait_tolerates_transient_ready_file_reads(self) -> None:
        ready_path = Path("/tmp/debug-ready.json")
        payload = {
            "sessionId": "transient",
            "dashboardOpenPending": False,
        }

        with mock.patch.object(
            debug_session,
            "_read_ready_file",
            side_effect=[
                debug_session.SessionError("ready file is being replaced"),
                (ready_path, payload),
            ],
        ):
            result = debug_session._wait_for_dashboard_startup(
                ready_path,
                session_id="transient",
                wait_seconds=0.2,
            )

        self.assertEqual(result, payload)

    def test_dashboard_startup_wait_preserves_initial_healthy_payload(self) -> None:
        ready_path = Path("/tmp/debug-ready.json")
        payload = {
            "sessionId": "healthy",
            "endpoint": "http://127.0.0.1:43125/ingest",
            "dashboardOpenPending": True,
        }

        with mock.patch.object(
            debug_session,
            "_read_ready_file",
            side_effect=debug_session.SessionError("ready file is being replaced"),
        ):
            result = debug_session._wait_for_dashboard_startup(
                ready_path,
                session_id="healthy",
                wait_seconds=0,
                initial_payload=payload,
            )

        self.assertEqual(result, payload)

    def test_start_confirms_and_recovers_default_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir).resolve()
            ready_file = workspace / ".debug-logs" / "auto-open.json"
            payload = {
                "sessionId": "auto-open",
                "healthUrl": "http://127.0.0.1:43125/health",
                "dashboardUrl": "http://127.0.0.1:43125/",
                "stateUrl": "http://127.0.0.1:43125/api/state",
            }
            recovered = {
                **payload,
                "dashboardRecovery": {
                    "status": "frontend_confirmed",
                    "frontendConfirmed": True,
                },
            }
            process = mock.Mock()
            process.poll.return_value = None

            def fake_popen(*_args: object, **_kwargs: object) -> mock.Mock:
                ready_file.write_text(json.dumps(payload), encoding="utf-8")
                return process

            args = debug_session.build_parser().parse_args(
                [
                    "start",
                    "--workspace-root",
                    str(workspace),
                    "--session-id",
                    "auto-open",
                ]
            )

            with mock.patch.object(
                debug_session.subprocess,
                "Popen",
                side_effect=fake_popen,
            ) as popen_mock:
                with mock.patch.object(debug_session, "_try_health", return_value=True):
                    with mock.patch.object(
                        debug_session,
                        "_wait_for_dashboard_startup",
                        return_value=payload,
                    ):
                        with mock.patch.object(
                            debug_session,
                            "_recover_dashboard_after_start",
                            return_value=recovered,
                        ) as recover_mock:
                            result = debug_session.command_start(args)

            command = popen_mock.call_args.args[0]
            self.assertNotIn("--no-open-dashboard", command)
            recover_mock.assert_called_once_with(ready_file, payload)
            self.assertTrue(result["dashboardRecovery"]["frontendConfirmed"])
            self.assertEqual(result["lifecycleMode"], "local-cli")

    def test_load_locations_projects_coverage_plan_for_collector(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan_file = Path(temp_dir) / "coverage-plan.json"
            plan_file.write_text(
                json.dumps(
                    {
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

    def test_load_locations_accepts_direct_array_and_locations_object(self) -> None:
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
            ({"probes": {}}, "coverage plan probes must be an array"),
            ({"probes": []}, "coverage plan probes must be a non-empty array"),
            ({"probes": ["src/app.ts:1"]}, "probe at index 0 must be an object"),
            (
                {
                    "probes": [{"location": "src/app.ts:1", "hypothesisIds": []}],
                },
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

    def test_dashboard_status_formats_handoff_line_for_each_session_state(self) -> None:
        ready_path = Path("/tmp/debug-ready.json")
        ready_payload = {"stateUrl": "http://127.0.0.1:43125/api/state"}
        args = mock.Mock(ready_file=str(ready_path), timeout=1.0)
        cases = (
            (
                {
                    "dashboardUrl": "http://127.0.0.1:43125/",
                    "dashboardAutoOpenEnabled": True,
                    "dashboardFrontendOpenRecorded": True,
                    "recordingFrozen": False,
                    "recordingGeneration": 0,
                },
                "frontend_confirmed",
                "Dashboard: frontend_confirmed — http://127.0.0.1:43125/ "
                "(frontend confirmed: true; recording: live)",
            ),
            (
                {
                    "dashboardUrl": "http://127.0.0.1:43125/",
                    "dashboardAutoOpenEnabled": False,
                    "dashboardFrontendOpenRecorded": False,
                    "recordingFrozen": False,
                },
                "disabled",
                "Dashboard: disabled — http://127.0.0.1:43125/ "
                "(frontend confirmed: false; recording: live)",
            ),
            (
                {
                    "dashboardUrl": "http://127.0.0.1:43125/",
                    "dashboardAutoOpenEnabled": True,
                    "dashboardFrontendOpenRecorded": False,
                    "recordingFrozen": True,
                    "recordingGeneration": 3,
                    "dashboardOpenError": "browser\nopen failed",
                },
                "frontend_not_confirmed",
                "Dashboard: frontend_not_confirmed — http://127.0.0.1:43125/ "
                "(frontend confirmed: false; recording: frozen) — error: browser open failed",
            ),
            (
                {},
                "unavailable",
                "Dashboard: unavailable — unavailable "
                "(frontend confirmed: unknown; recording: unknown)",
            ),
        )

        for service, expected_status, expected_line in cases:
            with self.subTest(expected_status=expected_status):
                with mock.patch.object(
                    debug_session,
                    "_read_ready_file",
                    return_value=(ready_path, ready_payload),
                ):
                    with mock.patch.object(
                        debug_session,
                        "_http_json",
                        return_value={"service": service},
                    ):
                        result = debug_session.command_dashboard_status(args)

                self.assertEqual(result["status"], expected_status)
                self.assertEqual(result["line"], expected_line)

        self.assertEqual(result["recordingStatus"], "unknown")

    def test_dashboard_status_falls_back_to_ready_payload_when_state_refresh_fails(self) -> None:
        ready_path = Path("/tmp/debug-ready.json")
        ready_payload = {
            "stateUrl": "http://127.0.0.1:43125/api/state",
            "dashboardUrl": "http://127.0.0.1:43125/",
            "dashboardAutoOpenEnabled": True,
            "dashboardFrontendOpenRecorded": True,
            "recordingFrozen": True,
            "recordingGeneration": 7,
        }
        args = mock.Mock(ready_file=str(ready_path), timeout=1.0)

        with mock.patch.object(
            debug_session,
            "_read_ready_file",
            return_value=(ready_path, ready_payload),
        ):
            with mock.patch.object(
                debug_session,
                "_http_json",
                side_effect=debug_session.SessionError("temporary\nstate failure"),
            ):
                result = debug_session.command_dashboard_status(args)

        self.assertEqual(result["status"], "frontend_confirmed")
        self.assertEqual(result["recordingStatus"], "frozen")
        self.assertEqual(result["recordingGeneration"], 7)
        self.assertIn("http://127.0.0.1:43125/", result["line"])
        self.assertIn("recording: frozen", result["line"])
        self.assertIn("temporary state failure", result["line"])

    def test_recording_commands_use_distinct_authenticated_endpoints(self) -> None:
        ready_path = Path("/tmp/debug-ready.json")
        ready_payload = {
            "freezeRecordingUrl": "http://127.0.0.1:43125/api/recording/freeze",
            "resumeRecordingUrl": "http://127.0.0.1:43125/api/recording/resume",
            "dashboardToken": "test-token",
        }
        args = mock.Mock(ready_file=str(ready_path), timeout=1.0)

        for frozen, command, url, generation in (
            (
                True,
                debug_session.command_freeze_recording,
                ready_payload["freezeRecordingUrl"],
                1,
            ),
            (
                False,
                debug_session.command_resume_recording,
                ready_payload["resumeRecordingUrl"],
                2,
            ),
        ):
            response = {
                "service": {
                    "recordingFrozen": frozen,
                    "recordingGeneration": generation,
                }
            }
            with self.subTest(frozen=frozen):
                with mock.patch.object(
                    debug_session,
                    "_read_ready_file",
                    return_value=(ready_path, ready_payload),
                ):
                    with mock.patch.object(
                        debug_session,
                        "_http_json",
                        return_value=response,
                    ) as request_mock:
                        result = command(args)

                request_mock.assert_called_once_with(
                    url,
                    method="POST",
                    token="test-token",
                    timeout=1.0,
                )
                self.assertEqual(result["recordingFrozen"], frozen)
                self.assertEqual(
                    result["recordingStatus"], "frozen" if frozen else "live"
                )
                self.assertEqual(result["recordingGeneration"], generation)

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

    def test_start_dashboard_recovery_retries_until_frontend_is_confirmed(self) -> None:
        ready_path = Path("/tmp/debug-ready.json")
        payload = {
            "dashboardUrl": "http://127.0.0.1:43125/",
            "stateUrl": "http://127.0.0.1:43125/api/state",
            "dashboardOpenSucceeded": True,
            "dashboardFrontendOpenRecorded": False,
        }
        failed_attempt = {
            "status": "frontend_not_confirmed",
            "frontendConfirmed": False,
            "failureReason": "frontend callback missing",
        }
        confirmed_attempt = {
            "status": "frontend_confirmed",
            "frontendConfirmed": True,
            "failureReason": "",
        }

        with mock.patch.object(
            debug_session,
            "_wait_for_dashboard_frontend",
            return_value=(False, ""),
        ):
            with mock.patch.object(
                debug_session,
                "_read_ready_file",
                return_value=(ready_path, payload),
            ):
                with mock.patch.object(
                    debug_session,
                    "_open_dashboard_attempt",
                    side_effect=[failed_attempt, confirmed_attempt],
                ) as open_mock:
                    result = debug_session._recover_dashboard_after_start(ready_path, payload)

        self.assertEqual(open_mock.call_count, 2)
        self.assertTrue(result["dashboardRecovery"]["frontendConfirmed"])
        self.assertEqual(result["dashboardRecovery"]["fallbackAttemptCount"], 2)
        self.assertEqual(result["dashboardRecovery"]["error"], "")

    def test_dashboard_frontend_wait_tolerates_transient_state_errors(self) -> None:
        payload = {"stateUrl": "http://127.0.0.1:43125/api/state"}

        with mock.patch.object(
            debug_session,
            "_http_json",
            side_effect=[
                debug_session.SessionError("temporary state read failure"),
                {"service": {"dashboardFrontendOpenRecorded": True}},
            ],
        ):
            confirmed, error = debug_session._wait_for_dashboard_frontend(
                payload,
                timeout=1.0,
                confirm_seconds=0.2,
            )

        self.assertTrue(confirmed)
        self.assertEqual(error, "")

    def test_start_dashboard_recovery_does_not_reopen_after_initial_confirmation(self) -> None:
        ready_path = Path("/tmp/debug-ready.json")
        payload = {
            "dashboardUrl": "http://127.0.0.1:43125/",
            "stateUrl": "http://127.0.0.1:43125/api/state",
            "dashboardOpenSucceeded": True,
            "dashboardFrontendOpenRecorded": False,
        }
        confirmed_payload = {
            **payload,
            "dashboardFrontendOpenRecorded": True,
        }

        with mock.patch.object(
            debug_session,
            "_wait_for_dashboard_frontend",
            return_value=(True, ""),
        ):
            with mock.patch.object(
                debug_session,
                "_read_ready_file",
                return_value=(ready_path, confirmed_payload),
            ):
                with mock.patch.object(
                    debug_session,
                    "_open_dashboard_attempt",
                ) as open_mock:
                    result = debug_session._recover_dashboard_after_start(ready_path, payload)

        open_mock.assert_not_called()
        self.assertTrue(result["dashboardRecovery"]["frontendConfirmed"])
        self.assertEqual(result["dashboardRecovery"]["fallbackAttemptCount"], 0)

    def test_start_dashboard_recovery_does_not_overlap_pending_initial_open(self) -> None:
        ready_path = Path("/tmp/debug-ready.json")
        payload = {
            "dashboardUrl": "http://127.0.0.1:43125/",
            "stateUrl": "http://127.0.0.1:43125/api/state",
            "dashboardOpenPending": True,
            "dashboardFrontendOpenRecorded": False,
        }

        with mock.patch.object(
            debug_session,
            "_wait_for_dashboard_frontend",
            return_value=(False, ""),
        ):
            with mock.patch.object(
                debug_session,
                "_read_ready_file",
                return_value=(ready_path, payload),
            ):
                with mock.patch.object(
                    debug_session,
                    "_open_dashboard_attempt",
                ) as open_mock:
                    result = debug_session._recover_dashboard_after_start(ready_path, payload)

        open_mock.assert_not_called()
        self.assertFalse(result["dashboardRecovery"]["frontendConfirmed"])
        self.assertEqual(result["dashboardRecovery"]["fallbackAttemptCount"], 0)
        self.assertEqual(
            result["dashboardRecovery"]["error"],
            "initial_dashboard_open_still_pending",
        )

    def test_start_dashboard_recovery_does_not_count_late_confirmation_as_open(self) -> None:
        ready_path = Path("/tmp/debug-ready.json")
        payload = {
            "dashboardUrl": "http://127.0.0.1:43125/",
            "stateUrl": "http://127.0.0.1:43125/api/state",
            "dashboardOpenSucceeded": True,
            "dashboardFrontendOpenRecorded": False,
        }
        already_open = {
            "status": "already_open",
            "skipped": True,
            "frontendConfirmed": True,
        }

        with mock.patch.object(
            debug_session,
            "_wait_for_dashboard_frontend",
            return_value=(False, ""),
        ):
            with mock.patch.object(
                debug_session,
                "_read_ready_file",
                return_value=(ready_path, payload),
            ):
                with mock.patch.object(
                    debug_session,
                    "_open_dashboard_attempt",
                    return_value=already_open,
                ):
                    result = debug_session._recover_dashboard_after_start(ready_path, payload)

        self.assertTrue(result["dashboardRecovery"]["frontendConfirmed"])
        self.assertEqual(result["dashboardRecovery"]["fallbackAttemptCount"], 0)

    def test_start_dashboard_recovery_is_non_blocking_after_bounded_failures(self) -> None:
        ready_path = Path("/tmp/debug-ready.json")
        payload = {
            "dashboardUrl": "http://127.0.0.1:43125/",
            "stateUrl": "http://127.0.0.1:43125/api/state",
            "dashboardOpenSucceeded": True,
            "dashboardFrontendOpenRecorded": False,
        }
        failed_attempt = {
            "status": "frontend_not_confirmed",
            "frontendConfirmed": False,
            "failureReason": "frontend callback missing",
        }

        with mock.patch.object(
            debug_session,
            "_wait_for_dashboard_frontend",
            return_value=(False, ""),
        ):
            with mock.patch.object(
                debug_session,
                "_read_ready_file",
                return_value=(ready_path, payload),
            ):
                with mock.patch.object(
                    debug_session,
                    "_open_dashboard_attempt",
                    return_value=failed_attempt,
                ) as open_mock:
                    result = debug_session._recover_dashboard_after_start(ready_path, payload)

        self.assertEqual(open_mock.call_count, debug_session.DASHBOARD_FALLBACK_ATTEMPTS)
        self.assertFalse(result["dashboardRecovery"]["frontendConfirmed"])
        self.assertEqual(
            result["dashboardRecovery"]["status"],
            "frontend_not_confirmed",
        )
        self.assertEqual(result["dashboardRecovery"]["error"], "frontend callback missing")

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
                self.assertEqual(start_payload["dashboardRecovery"]["status"], "disabled")
                self.assertEqual(
                    start_payload["dashboardRecovery"]["fallbackAttemptCount"],
                    0,
                )
                self.assertEqual(start_payload["sessionAction"], "started")

                _, resume_payload = self._run_json(
                    str(DEBUG_SESSION),
                    "resume",
                    "--ready-file",
                    str(ready_file),
                )
                self.assertEqual(resume_payload["sessionAction"], "reused")
                self.assertEqual(resume_payload["lifecycleMode"], "local-cli")
                self.assertEqual(resume_payload["dashboardRecovery"]["status"], "disabled")
                for key in (
                    "sessionId",
                    "pid",
                    "port",
                    "endpoint",
                    "dashboardUrl",
                    "startedAt",
                ):
                    self.assertEqual(resume_payload[key], start_payload[key])

                _, dashboard_status = self._run_json(
                    str(DEBUG_SESSION),
                    "dashboard-status",
                    "--ready-file",
                    str(ready_file),
                )
                self.assertEqual(dashboard_status["status"], "disabled")
                self.assertEqual(dashboard_status["dashboardUrl"], start_payload["dashboardUrl"])
                self.assertEqual(
                    dashboard_status["line"],
                    f"Dashboard: disabled — {start_payload['dashboardUrl']} "
                    "(frontend confirmed: false; recording: live)",
                )
                self.assertEqual(dashboard_status["recordingStatus"], "live")

                _, frozen_payload = self._run_json(
                    str(DEBUG_SESSION),
                    "freeze-recording",
                    "--ready-file",
                    str(ready_file),
                )
                self.assertTrue(frozen_payload["recordingFrozen"])
                self.assertEqual(frozen_payload["recordingStatus"], "frozen")

                _, reused_while_frozen = self._run_json(
                    str(DEBUG_SESSION),
                    "resume",
                    "--ready-file",
                    str(ready_file),
                )
                self.assertEqual(reused_while_frozen["sessionAction"], "reused")
                self.assertEqual(reused_while_frozen["pid"], start_payload["pid"])
                self.assertEqual(reused_while_frozen["port"], start_payload["port"])
                self.assertTrue(reused_while_frozen["recordingFrozen"])

                _, frozen_status = self._run_json(
                    str(DEBUG_SESSION),
                    "dashboard-status",
                    "--ready-file",
                    str(ready_file),
                )
                self.assertEqual(frozen_status["recordingStatus"], "frozen")
                self.assertIn("recording: frozen", frozen_status["line"])

                self._post_event(
                    start_payload["endpoint"],
                    {
                        "sessionId": "integration",
                        "runId": "discarded-while-frozen",
                        "probeId": "frozen.event",
                        "event": "state_observed",
                        "timestamp": int(time.time() * 1000),
                    },
                )
                _, frozen_state = self._run_json(
                    str(DEBUG_SESSION),
                    "state",
                    "--ready-file",
                    str(ready_file),
                )
                self.assertEqual(frozen_state["state"]["summary"]["totalEntries"], 0)

                _, cleared_while_frozen = self._run_json(
                    str(DEBUG_SESSION),
                    "clear",
                    "--ready-file",
                    str(ready_file),
                )
                self.assertEqual(cleared_while_frozen["state"]["status"], "frozen")
                self.assertTrue(
                    cleared_while_frozen["state"]["service"]["recordingFrozen"]
                )

                _, resumed_payload = self._run_json(
                    str(DEBUG_SESSION),
                    "resume-recording",
                    "--ready-file",
                    str(ready_file),
                )
                self.assertFalse(resumed_payload["recordingFrozen"])
                self.assertEqual(resumed_payload["recordingStatus"], "live")

                locations_file = workspace / "coverage-plan.json"
                locations_file.write_text(
                    json.dumps(
                        {
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

    def test_summarizer_reports_transport_sequence_gaps_and_regressions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "events.ndjson"
            events = [
                {
                    "runId": "initial",
                    "transportClientId": "client-a",
                    "transportId": "event-1",
                    "transportSequence": 1,
                },
                {
                    "runId": "initial",
                    "transportClientId": "client-b",
                    "transportId": "event-b1",
                    "transportSequence": 1,
                },
                {
                    "runId": "initial",
                    "transportClientId": "client-a",
                    "transportId": "event-2",
                    "transportSequence": 2,
                },
                {
                    "runId": "initial",
                    "transportClientId": "client-a",
                    "transportId": "event-4",
                    "transportSequence": 4,
                },
                {
                    "runId": "initial",
                    "transportClientId": "client-a",
                    "transportId": "event-4-retry",
                    "transportSequence": 4,
                },
            ]
            log_file.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

            _, summary = self._run_json(
                str(SUMMARIZER), str(log_file), "--format", "json"
            )

            continuity = summary["transportContinuity"]
            self.assertEqual(continuity["scope"], "full-log")
            self.assertEqual(continuity["eventsWithTransportSequence"], 5)
            self.assertEqual(continuity["clientsWithTransportSequence"], 2)
            self.assertEqual(continuity["gapCount"], 1)
            self.assertEqual(continuity["gaps"][0]["missingStart"], 3)
            self.assertEqual(continuity["gaps"][0]["missingEnd"], 3)
            self.assertEqual(continuity["regressionOrDuplicateSequenceCount"], 1)

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
                ({"probes": []}, "non-empty probes"),
                (
                    {"probes": [{}]},
                    "must have a non-empty probeId",
                ),
                (
                    {
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
