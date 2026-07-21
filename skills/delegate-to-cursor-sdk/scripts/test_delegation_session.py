#!/usr/bin/env python3
"""Regression tests for the delegate-to-cursor-sdk session lifecycle helper."""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest

import delegation_session as session_helper


SCRIPT = Path(__file__).resolve().parent / "delegation_session.py"


class DelegationSessionTests(unittest.TestCase):
    def _run(
        self,
        *args: str,
        temp_root: Path,
        check: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        environment = dict(os.environ)
        environment["TMPDIR"] = str(temp_root)
        environment.update(extra_env or {})
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            env=environment,
            timeout=10,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(f"command failed ({result.returncode}): {result.stderr or result.stdout}")
        payload_text = result.stdout if result.returncode == 0 else result.stderr
        payload = json.loads(payload_text)
        return result, payload

    def _start(self, workspace: Path, temp_root: Path) -> dict[str, object]:
        _, payload = self._run(
            "start",
            "--workspace",
            str(workspace),
            temp_root=temp_root,
        )
        return payload

    def _write_terminal_run(
        self,
        logs_dir: Path,
        *,
        state: str = "succeeded",
        log_name: str = "root",
        run_name: str = "20260717T120000000Z-deadbeef",
        task_hash: str = "task-hash",
        extra_status: dict[str, object] | None = None,
    ) -> Path:
        log_base = logs_dir / log_name
        run_dir = log_base / run_name
        run_dir.mkdir(parents=True)
        status = run_dir / "status.json"
        status_payload: dict[str, object] = {
            "state": state,
            "task_packet_sha256": task_hash,
            **(extra_status or {}),
        }
        status.write_text(json.dumps(status_payload), encoding="utf-8")
        (run_dir / "metadata.json").write_text("{}\n", encoding="utf-8")
        (run_dir / "prompt.txt").write_text("prompt\n", encoding="utf-8")
        (run_dir / "stream.ndjson").write_text("{}\n", encoding="utf-8")
        (run_dir / "snapshot.v2.json").write_text("{}\n", encoding="utf-8")
        (log_base / "latest").write_text(f"{run_dir}\n", encoding="utf-8")
        return status

    def test_accepted_cleanup_removes_owned_packets_and_logs_only(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            user_file = workspace / "user-plan.md"
            user_file.write_text("keep me\n", encoding="utf-8")

            started = self._start(workspace, temp_root)
            session_root = Path(str(started["sessionRoot"]))
            session_file = Path(str(started["sessionFile"]))
            packets_dir = Path(str(started["packetsDir"]))
            logs_dir = Path(str(started["logsDir"]))
            self.assertEqual(stat.S_IMODE(session_root.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(session_file.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(packets_dir.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(logs_dir.stat().st_mode), 0o700)
            (packets_dir / "initial.md").write_text("packet\n", encoding="utf-8")
            self._write_terminal_run(logs_dir)

            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")
            self.assertFalse(session_root.exists())
            self.assertTrue(user_file.exists())

            repeated_result, repeated = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(repeated_result.returncode, 2)
            self.assertIn("cannot be re-proven", str(repeated["error"]))

    def test_needs_input_can_reconcile_to_a_later_success_for_the_same_agent(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            logs_dir = Path(str(started["logsDir"]))
            paused = self._write_terminal_run(
                logs_dir,
                state="needs_input",
                task_hash="initial-hash",
                extra_status={"agent_id": "agent-1"},
            )
            time.sleep(0.01)
            self._write_terminal_run(
                logs_dir,
                log_name="resume",
                run_name="20260717T120001000Z-feedface",
                task_hash="follow-up-hash",
                extra_status={"agent_id": "agent-1"},
            )

            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                "--allow-status",
                str(paused),
                "--override-reason",
                "same agent resumed with a bounded follow-up packet and succeeded",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")

    def test_reconciliation_rejects_a_different_agent_in_the_same_workstream(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            logs_dir = Path(str(started["logsDir"]))
            paused = self._write_terminal_run(
                logs_dir,
                state="interrupted",
                task_hash="initial-hash",
                extra_status={"agent_id": "agent-1", "workstream_id": "workstream-a"},
            )
            time.sleep(0.01)
            self._write_terminal_run(
                logs_dir,
                log_name="wrong-agent",
                run_name="20260717T120001000Z-feedface",
                task_hash="follow-up-hash",
                extra_status={"agent_id": "agent-2", "workstream_id": "workstream-a"},
            )

            result, payload = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                "--allow-status",
                str(paused),
                "--override-reason",
                "reviewed follow-up must correlate to the exact agent and workstream",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("matching agent/workstream", str(payload["error"]))
            self.assertTrue(session_file.exists())

            time.sleep(0.01)
            self._write_terminal_run(
                logs_dir,
                log_name="right-agent",
                run_name="20260717T120002000Z-cafebabe",
                task_hash="second-follow-up-hash",
                extra_status={"agent_id": "agent-1", "workstream_id": "workstream-a"},
            )
            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                "--allow-status",
                str(paused),
                "--override-reason",
                "the exact interrupted agent and workstream later succeeded",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")

    def test_cleanup_refuses_active_or_unreconciled_status(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            logs_dir = Path(str(started["logsDir"]))
            status = self._write_terminal_run(logs_dir, state="needs_authorization")

            result, payload = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--allow-status", str(payload["error"]))

            time.sleep(0.01)
            self._write_terminal_run(
                logs_dir,
                log_name="root-auth-rerun",
                run_name="20260717T120001000Z-feedface",
            )
            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                "--allow-status",
                str(status),
                "--override-reason",
                "superseded by a reviewed successful authorization rerun",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")

    def test_cleanup_never_overrides_running_state(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            logs_dir = Path(str(started["logsDir"]))
            status = self._write_terminal_run(logs_dir, state="running")

            result, payload = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                "--allow-status",
                str(status),
                "--override-reason",
                "not sufficient",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("while a run is running", str(payload["error"]))
            self.assertTrue(session_file.exists())

    def test_cleanup_refuses_a_live_frontend_pid(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            logs_dir = Path(str(started["logsDir"]))
            status = self._write_terminal_run(logs_dir)
            status.write_text(
                json.dumps(
                    {
                        "state": "succeeded",
                        "task_packet_sha256": "task-hash",
                        "frontend": {"pid": os.getpid()},
                    }
                ),
                encoding="utf-8",
            )

            result, payload = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("frontend process is alive", str(payload["error"]))
            self.assertTrue(session_file.exists())

            status.write_text(
                json.dumps({"state": "succeeded", "task_packet_sha256": "task-hash"}),
                encoding="utf-8",
            )
            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")

    def test_start_refuses_a_workspace_as_the_temp_root(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            workspace = Path(outer) / "workspace"
            workspace.mkdir()
            result, payload = self._run(
                "start",
                "--workspace",
                str(workspace),
                temp_root=workspace,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("protected path", str(payload["error"]))

    def test_first_cleanup_never_treats_a_missing_lease_directory_as_prior_progress(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            Path(str(started["leasesDir"])).rmdir()

            result, payload = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("leases directory does not exist", str(payload["error"]))
            marker_payload = json.loads(session_file.read_text(encoding="utf-8"))
            self.assertNotIn("cleanupState", marker_payload)

    def test_cleanup_refuses_an_incomplete_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            run_dir = (
                Path(str(started["logsDir"]))
                / "root"
                / "20260717T120000000Z-deadbeef"
            )
            run_dir.mkdir(parents=True)
            (run_dir / "prompt.txt").write_text("prompt\n", encoding="utf-8")

            result, payload = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--allow-incomplete-run", str(payload["error"]))
            self.assertTrue(session_file.exists())

            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "abandoned",
                "--allow-incomplete-run",
                str(run_dir),
                "--override-reason",
                "owning CLI exited before status creation and no remote run was created",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")

    def test_error_is_a_cleanable_terminal_state(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            self._write_terminal_run(Path(str(started["logsDir"])), state="error")

            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "abandoned",
                "--override-reason",
                "reviewed terminal SDK error; no run remains active",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")

    def test_cleanup_requires_an_exact_runtime_atomic_temp_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            status = self._write_terminal_run(Path(str(started["logsDir"])))
            residue = status.parent / "status.json.123.12345678-1234-4abc-8def-1234567890ab.tmp"
            residue.write_text('{"state":', encoding="utf-8")

            result, payload = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--allow-temp-artifact", str(payload["error"]))
            self.assertTrue(residue.exists())

            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                "--allow-temp-artifact",
                str(residue),
                "--override-reason",
                "owning CLI exited and left the exact runtime atomic JSON temp",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")

    def test_run_lease_blocks_cleanup_until_the_cli_exits(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            bin_dir = outer_path / "bin"
            workspace.mkdir()
            temp_root.mkdir()
            bin_dir.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            packets_dir = Path(str(started["packetsDir"]))
            leases_dir = Path(str(started["leasesDir"]))
            packet = packets_dir / "initial.md"
            packet.write_text("packet\n", encoding="utf-8")
            hold = outer_path / "hold"
            ready = outer_path / "ready.json"
            hold.write_text("hold\n", encoding="utf-8")
            fake_cli = bin_dir / "cursor-delegate"
            fake_cli.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, sys, time\n"
                "args = sys.argv[1:]\n"
                "log_dir = pathlib.Path(args[args.index('--log-dir') + 1])\n"
                "pathlib.Path(os.environ['FAKE_READY']).write_text(json.dumps({'logDir': str(log_dir)}))\n"
                "hold = pathlib.Path(os.environ['FAKE_HOLD'])\n"
                "while hold.exists(): time.sleep(0.02)\n",
                encoding="utf-8",
            )
            fake_cli.chmod(0o755)
            environment = dict(os.environ)
            environment["TMPDIR"] = str(temp_root)
            environment["PATH"] = f"{bin_dir}{os.pathsep}{environment.get('PATH', '')}"
            environment["FAKE_READY"] = str(ready)
            environment["FAKE_HOLD"] = str(hold)
            runner = subprocess.Popen(
                [
                    sys.executable,
                    str(SCRIPT),
                    "run",
                    "--session-file",
                    str(session_file),
                    "--log-name",
                    "root-01",
                    "--",
                    "cursor-delegate",
                    "--workspace",
                    str(workspace),
                    "--task-file",
                    str(packet),
                    "--dry-run",
                ],
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                deadline = time.monotonic() + 5
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(ready.exists(), "fake CLI did not start")
                self.assertEqual(len(list(leases_dir.iterdir())), 1)

                result, payload = self._run(
                    "cleanup",
                    "--session-file",
                    str(session_file),
                    "--verdict",
                    "accepted",
                    temp_root=temp_root,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("owning CLI lease is alive", str(payload["error"]))
            finally:
                hold.unlink(missing_ok=True)
                runner.communicate(timeout=5)
            self.assertEqual(runner.returncode, 0)
            self.assertEqual(list(leases_dir.iterdir()), [])

            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")

    def test_cleanup_requires_exact_reconciliation_for_a_dead_stale_lease(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            leases_dir = Path(str(started["leasesDir"]))
            logs_dir = Path(str(started["logsDir"]))

            finished = subprocess.Popen([sys.executable, "-c", "pass"])
            finished.wait(timeout=5)
            stale_lease = leases_dir / "stale-01.json"
            stale_lease.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "owner": "delegate-to-cursor-sdk",
                        "sessionId": started["sessionId"],
                        "leaseId": "stale-test-lease",
                        "wrapperPid": finished.pid,
                        "childPid": finished.pid,
                        "logBase": str(logs_dir / "stale-01"),
                        "logOwnership": "session-owned",
                        "phase": "starting-child",
                    }
                ),
                encoding="utf-8",
            )

            result, payload = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--allow-lease", str(payload["error"]))
            self.assertTrue(stale_lease.exists())

            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                "--allow-lease",
                str(stale_lease),
                "--override-reason",
                "wrapper and child PIDs are reaped; no Cursor run was created",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")

    def test_retained_log_directory_is_wrapper_created_leased_and_never_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            bin_dir = outer_path / "bin"
            workspace.mkdir()
            temp_root.mkdir()
            bin_dir.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            session_root = Path(str(started["sessionRoot"]))
            packet = Path(str(started["packetsDir"])) / "initial.md"
            packet.write_text("packet\n", encoding="utf-8")
            existing = outer_path / "existing-audit"
            existing.mkdir()

            for rejected, expected in (
                (str(existing), "must not already exist"),
                ("relative-audit", "absolute path"),
                (str(session_root / "inside-audit"), "outside the owned session"),
            ):
                result, payload = self._run(
                    "run",
                    "--session-file",
                    str(session_file),
                    "--log-name",
                    "retained-validation",
                    "--retained-log-dir",
                    rejected,
                    "--",
                    "cursor-delegate",
                    "--dry-run",
                    temp_root=temp_root,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn(expected, str(payload["error"]))

            retained = outer_path / "caller-retained-audit"
            hold = outer_path / "retained-hold"
            ready = outer_path / "retained-ready.json"
            hold.write_text("hold\n", encoding="utf-8")
            fake_cli = bin_dir / "cursor-delegate"
            fake_cli.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, sys, time\n"
                "args = sys.argv[1:]\n"
                "log_dir = pathlib.Path(args[args.index('--log-dir') + 1])\n"
                "(log_dir / 'audit.txt').write_text('caller retained')\n"
                "pathlib.Path(os.environ['FAKE_READY']).write_text(json.dumps({'logDir': str(log_dir)}))\n"
                "hold = pathlib.Path(os.environ['FAKE_HOLD'])\n"
                "while hold.exists(): time.sleep(0.02)\n",
                encoding="utf-8",
            )
            fake_cli.chmod(0o755)
            environment = dict(os.environ)
            environment["TMPDIR"] = str(temp_root)
            environment["PATH"] = f"{bin_dir}{os.pathsep}{environment.get('PATH', '')}"
            environment["FAKE_READY"] = str(ready)
            environment["FAKE_HOLD"] = str(hold)
            runner = subprocess.Popen(
                [
                    sys.executable,
                    str(SCRIPT),
                    "run",
                    "--session-file",
                    str(session_file),
                    "--log-name",
                    "retained-01",
                    "--retained-log-dir",
                    str(retained),
                    "--",
                    "cursor-delegate",
                    "--workspace",
                    str(workspace),
                    "--task-file",
                    str(packet),
                    "--dry-run",
                ],
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                deadline = time.monotonic() + 5
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(ready.exists(), "retained-log fake CLI did not start")
                resolved_retained = retained.resolve()
                self.assertEqual(json.loads(ready.read_text())["logDir"], str(resolved_retained))
                leases = list(Path(str(started["leasesDir"])).iterdir())
                self.assertEqual(len(leases), 1)
                lease_payload = json.loads(leases[0].read_text(encoding="utf-8"))
                self.assertEqual(lease_payload["logOwnership"], "caller-retained")
                self.assertEqual(lease_payload["logBase"], str(resolved_retained))
                self.assertEqual(list(Path(str(started["logsDir"])).iterdir()), [])
            finally:
                hold.unlink(missing_ok=True)
                runner.communicate(timeout=5)
            self.assertEqual(runner.returncode, 0)
            self.assertEqual(list(Path(str(started["leasesDir"])).iterdir()), [])

            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")
            self.assertFalse(session_root.exists())
            self.assertEqual((retained / "audit.txt").read_text(encoding="utf-8"), "caller retained")

    @unittest.skipUnless(os.name == "posix", "POSIX signal forwarding test")
    def test_run_forwards_sigterm_and_reaps_the_cli(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            bin_dir = outer_path / "bin"
            workspace.mkdir()
            temp_root.mkdir()
            bin_dir.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            packet = Path(str(started["packetsDir"])) / "initial.md"
            packet.write_text("packet\n", encoding="utf-8")
            ready = outer_path / "ready"
            receipt = outer_path / "signal"
            fake_cli = bin_dir / "cursor-delegate"
            fake_cli.write_text(
                "#!/usr/bin/env python3\n"
                "import os, pathlib, signal, sys, time\n"
                "ready = pathlib.Path(os.environ['FAKE_READY'])\n"
                "receipt = pathlib.Path(os.environ['FAKE_SIGNAL'])\n"
                "def stop(signum, frame):\n"
                "    receipt.write_text(str(signum))\n"
                "    raise SystemExit(130 if signum == signal.SIGINT else 143)\n"
                "signal.signal(signal.SIGINT, stop)\n"
                "signal.signal(signal.SIGTERM, stop)\n"
                "ready.write_text('ready')\n"
                "while True: time.sleep(0.1)\n",
                encoding="utf-8",
            )
            fake_cli.chmod(0o755)
            environment = dict(os.environ)
            environment["TMPDIR"] = str(temp_root)
            environment["PATH"] = f"{bin_dir}{os.pathsep}{environment.get('PATH', '')}"
            environment["FAKE_READY"] = str(ready)
            environment["FAKE_SIGNAL"] = str(receipt)
            runner = subprocess.Popen(
                [
                    sys.executable,
                    str(SCRIPT),
                    "run",
                    "--session-file",
                    str(session_file),
                    "--log-name",
                    "signal-01",
                    "--",
                    "cursor-delegate",
                    "--workspace",
                    str(workspace),
                    "--task-file",
                    str(packet),
                    "--dry-run",
                ],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            deadline = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(ready.exists(), "fake CLI did not start")
            runner.terminate()
            self.assertEqual(runner.wait(timeout=5), 143)
            self.assertEqual(receipt.read_text(encoding="utf-8"), str(15))
            self.assertEqual(list(Path(str(started["leasesDir"])).iterdir()), [])

            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")

    @unittest.skipUnless(hasattr(signal, "SIGHUP"), "SIGHUP is unavailable")
    def test_run_forwards_sighup_and_reaps_the_cli(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            bin_dir = outer_path / "bin"
            workspace.mkdir()
            temp_root.mkdir()
            bin_dir.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            packet = Path(str(started["packetsDir"])) / "initial.md"
            packet.write_text("packet\n", encoding="utf-8")
            ready = outer_path / "hup-ready"
            receipt = outer_path / "hup-signal"
            fake_cli = bin_dir / "cursor-delegate"
            fake_cli.write_text(
                "#!/usr/bin/env python3\n"
                "import os, pathlib, signal, time\n"
                "ready = pathlib.Path(os.environ['FAKE_READY'])\n"
                "receipt = pathlib.Path(os.environ['FAKE_SIGNAL'])\n"
                "def stop(signum, frame):\n"
                "    receipt.write_text(str(signum))\n"
                "    raise SystemExit(128 + signum)\n"
                "signal.signal(signal.SIGHUP, stop)\n"
                "ready.write_text('ready')\n"
                "while True: time.sleep(0.1)\n",
                encoding="utf-8",
            )
            fake_cli.chmod(0o755)
            environment = dict(os.environ)
            environment["TMPDIR"] = str(temp_root)
            environment["PATH"] = f"{bin_dir}{os.pathsep}{environment.get('PATH', '')}"
            environment["FAKE_READY"] = str(ready)
            environment["FAKE_SIGNAL"] = str(receipt)
            runner = subprocess.Popen(
                [
                    sys.executable,
                    str(SCRIPT),
                    "run",
                    "--session-file",
                    str(session_file),
                    "--log-name",
                    "hup-01",
                    "--",
                    "cursor-delegate",
                    "--workspace",
                    str(workspace),
                    "--task-file",
                    str(packet),
                    "--dry-run",
                ],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            deadline = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(ready.exists(), "fake CLI did not start for SIGHUP")
            runner.send_signal(signal.SIGHUP)
            self.assertEqual(runner.wait(timeout=5), 128 + signal.SIGHUP)
            self.assertEqual(receipt.read_text(encoding="utf-8"), str(int(signal.SIGHUP)))
            self.assertEqual(list(Path(str(started["leasesDir"])).iterdir()), [])

            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")

    @unittest.skipUnless(os.name == "posix", "POSIX permission semantics required")
    def test_partial_cleanup_failure_is_retryable_without_recreating_owned_directories(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            packet = Path(str(started["packetsDir"])) / "initial.md"
            packet.write_text("packet\n", encoding="utf-8")
            status = self._write_terminal_run(Path(str(started["logsDir"])))
            run_dir = status.parent
            run_dir.chmod(0o500)
            try:
                result, payload = self._run(
                    "cleanup",
                    "--session-file",
                    str(session_file),
                    "--verdict",
                    "accepted",
                    temp_root=temp_root,
                    check=False,
                )
            finally:
                run_dir.chmod(0o700)
            self.assertEqual(result.returncode, 2)
            self.assertIn("filesystem operation failed", str(payload["error"]))
            self.assertFalse(packet.exists(), "the fixture must exercise a partial deletion")
            self.assertTrue(session_file.exists(), "the ownership marker must survive partial failure")
            marker_payload = json.loads(session_file.read_text(encoding="utf-8"))
            self.assertEqual(marker_payload["cleanupState"]["phase"], "deleting")

            status_backup = outer_path / "status-backup.json"
            status.rename(status_backup)
            status.write_text('{"state":"succeeded"}\n', encoding="utf-8")
            changed_result, changed_payload = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(changed_result.returncode, 2)
            self.assertIn("changed identity", str(changed_payload["error"]))
            status.unlink()
            status_backup.rename(status)

            Path(str(started["packetsDir"])).rmdir()
            Path(str(started["leasesDir"])).rmdir()
            unknown = Path(str(started["sessionRoot"])) / "appeared-after-validation.txt"
            unknown.write_text("not in manifest\n", encoding="utf-8")

            retry_result, retry_payload = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(retry_result.returncode, 2)
            self.assertIn("unowned new entry", str(retry_payload["error"]))
            unknown.unlink()

            _, cleaned = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
            )
            self.assertEqual(cleaned["status"], "cleaned")

    @unittest.skipUnless(os.name == "posix", "POSIX cleanup locking test")
    def test_concurrent_cleanup_has_one_owner_and_never_double_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            protected = workspace / "caller-owned.md"
            protected.write_text("keep\n", encoding="utf-8")
            started = self._start(workspace, temp_root)
            session_root = Path(str(started["sessionRoot"]))
            session_file = Path(str(started["sessionFile"]))
            packets = Path(str(started["packetsDir"]))
            for index in range(300):
                (packets / f"packet-{index:03d}.md").write_text("owned\n", encoding="utf-8")

            environment = dict(os.environ)
            environment["TMPDIR"] = str(temp_root)
            command = [
                sys.executable,
                str(SCRIPT),
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
            ]
            runners = [
                subprocess.Popen(
                    command,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for _ in range(2)
            ]
            outputs = [runner.communicate(timeout=10) for runner in runners]
            self.assertEqual(sorted(runner.returncode for runner in runners), [0, 2], outputs)
            self.assertFalse(session_root.exists())
            self.assertEqual(protected.read_text(encoding="utf-8"), "keep\n")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_descriptor_relative_delete_refuses_a_swapped_parent_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            root = outer_path / "owned-root"
            packets = root / "packets"
            external = outer_path / "caller-owned"
            packets.mkdir(parents=True)
            external.mkdir()
            owned = packets / "valuable.md"
            owned.write_text("owned\n", encoding="utf-8")
            caller_file = external / "valuable.md"
            caller_file.write_text("caller\n", encoding="utf-8")

            root_entry = session_helper.OwnedEntry.from_stat(root, root.lstat())
            packets_entry = session_helper.OwnedEntry.from_stat(packets, packets.lstat())
            file_entry = session_helper.OwnedEntry.from_stat(owned, owned.lstat())
            root_fd = session_helper._open_verified_directory(root, root_entry)
            original_packets = root / "packets-original"
            packets.rename(original_packets)
            os.symlink(external, packets)
            try:
                with self.assertRaises(session_helper.SessionError):
                    session_helper._remove_owned_entry(
                        root_fd,
                        root,
                        file_entry,
                        {("packets",): packets_entry},
                        directory=False,
                    )
            finally:
                os.close(root_fd)
            self.assertEqual(caller_file.read_text(encoding="utf-8"), "caller\n")
            self.assertEqual((original_packets / "valuable.md").read_text(encoding="utf-8"), "owned\n")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_cleanup_refuses_symlinks_and_unknown_files(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            workspace = outer_path / "workspace"
            temp_root = outer_path / "tmp"
            workspace.mkdir()
            temp_root.mkdir()
            started = self._start(workspace, temp_root)
            session_file = Path(str(started["sessionFile"]))
            packets_dir = Path(str(started["packetsDir"]))
            target = workspace / "valuable.md"
            target.write_text("valuable\n", encoding="utf-8")
            os.symlink(target, packets_dir / "linked.md")

            result, payload = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("symlink", str(payload["error"]))
            self.assertTrue(target.exists())

            (packets_dir / "linked.md").unlink()
            (Path(str(started["sessionRoot"])) / "unknown.txt").write_text(
                "unknown\n", encoding="utf-8"
            )
            result, payload = self._run(
                "cleanup",
                "--session-file",
                str(session_file),
                "--verdict",
                "accepted",
                temp_root=temp_root,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("unowned entries", str(payload["error"]))


if __name__ == "__main__":
    unittest.main()
