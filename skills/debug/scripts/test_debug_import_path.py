#!/usr/bin/env python3
"""Regression tests for debug helper import resolution."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parent / "debug_import_path.py"


class DebugImportPathTests(unittest.TestCase):
    def _fixture(self, workspace: Path) -> tuple[Path, Path]:
        importer = (
            workspace
            / "web/src/storyboard/_features/canvas-adapter/_helpers/storeFactory.ts"
        )
        target = workspace / "web/src/storyboard/_debug/agentLogIngest.ts"
        importer.parent.mkdir(parents=True)
        target.parent.mkdir(parents=True)
        importer.write_text("export {}\n", encoding="utf-8")
        target.write_text("export const emitAgentLog = () => {}\n", encoding="utf-8")
        return importer, target

    def _run(
        self,
        workspace: Path,
        importer: Path,
        target: Path,
        *extra: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--workspace-root",
                str(workspace),
                "--importer",
                str(importer),
                "--target",
                str(target),
                *extra,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_resolves_from_importing_file_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            importer, target = self._fixture(workspace)

            result = self._run(
                workspace,
                importer,
                target,
                "--strip-extension",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(result.stdout.strip(), "../../../_debug/agentLogIngest")

    def test_same_directory_specifier_keeps_dot_slash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            importer = workspace / "src/store.ts"
            target = workspace / "src/debugLog.ts"
            importer.parent.mkdir(parents=True)
            importer.write_text("export {}\n", encoding="utf-8")
            target.write_text("export {}\n", encoding="utf-8")

            result = self._run(
                workspace,
                importer,
                target,
                "--strip-extension",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(result.stdout.strip(), "./debugLog")

    def test_rejects_a_wrong_injected_specifier_and_reports_expected_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            importer, target = self._fixture(workspace)

            result = self._run(
                workspace,
                importer,
                target,
                "--strip-extension",
                "--specifier",
                "../../_debug/agentLogIngest",
                "--format",
                "json",
            )

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stderr)
            self.assertFalse(payload["ok"])
            self.assertIn("../../../_debug/agentLogIngest", payload["error"])

    def test_accepts_the_injected_extensionless_specifier(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            importer, target = self._fixture(workspace)

            result = self._run(
                workspace,
                importer,
                target,
                "--strip-extension",
                "--specifier",
                "../../../_debug/agentLogIngest",
                "--format",
                "json",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(
                payload["verifiedSpecifier"],
                "../../../_debug/agentLogIngest",
            )

    def test_rejects_a_target_outside_the_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "workspace"
            outside = root / "outside"
            workspace.mkdir()
            outside.mkdir()
            importer = workspace / "src/store.ts"
            target = outside / "agentLogIngest.ts"
            importer.parent.mkdir()
            importer.write_text("export {}\n", encoding="utf-8")
            target.write_text("export {}\n", encoding="utf-8")

            result = self._run(workspace, importer, target)

            self.assertEqual(result.returncode, 1)
            self.assertIn("target is outside workspace root", result.stderr)


if __name__ == "__main__":
    unittest.main()
