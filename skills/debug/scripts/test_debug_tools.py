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
import urllib.request

SCRIPT_DIR = Path(__file__).resolve().parent
DEBUG_SESSION = SCRIPT_DIR / "debug_session.py"
SUMMARIZER = SCRIPT_DIR / "summarize_debug_log.py"


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
                    "--location-state-flush-ms",
                    "25",
                )
                ready_file = Path(start_payload["readyFile"])
                self.assertTrue(ready_file.exists())
                self.assertEqual(start_payload["lifecycleMode"], "local-cli")
                self.assertEqual(start_payload["locationStateFlushMs"], 25)
                self.assertTrue(start_payload["batchEndpoint"].endswith("/ingest/batch"))

                locations_file = workspace / "locations.json"
                locations_file.write_text(
                    json.dumps(
                        {
                            "locations": [
                                {
                                    "location": "src/app.ts:1",
                                    "hypothesisIds": ["H1", "H2"],
                                    "probeId": "flow.start",
                                },
                                {
                                    "location": "src/app.ts:2",
                                    "hypothesisIds": ["H2"],
                                    "probeId": "flow.end",
                                },
                                {
                                    "location": "src/app.ts:3",
                                    "hypothesisIds": ["H3"],
                                    "probeId": "flow.missing",
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
