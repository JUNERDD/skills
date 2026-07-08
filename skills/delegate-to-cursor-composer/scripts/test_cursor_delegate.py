#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("cursor_delegate.py")


def load_cursor_delegate():
    spec = importlib.util.spec_from_file_location("cursor_delegate", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CursorDelegateTests(unittest.TestCase):
    def test_readonly_copy_preserves_executable_bits_and_removes_write_bits(self) -> None:
        cursor_delegate = load_cursor_delegate()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "repo"
            workspace.mkdir()

            script = workspace / "run-check.sh"
            script.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
            script.chmod(0o755)

            regular = workspace / "notes.txt"
            regular.write_text("notes\n", encoding="utf-8")
            regular.chmod(0o644)

            copied = cursor_delegate.make_readonly_copy(workspace)

            self.assertEqual(0o555, stat.S_IMODE((copied / "run-check.sh").stat().st_mode))
            self.assertEqual(0o444, stat.S_IMODE((copied / "notes.txt").stat().st_mode))

    def test_dry_run_explains_workspace_copy_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "repo"
            workspace.mkdir()

            task_file = Path(temp_dir) / "task.md"
            task_file.write_text(
                "# Cursor Direct Implementation Task Packet\n\n"
                "## Master Direct Implementation Instructions\n"
                "Inspect only.\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--workspace",
                    str(workspace),
                    "--task-file",
                    str(task_file),
                    "--dry-run",
                    "--inspect-only",
                    "--prompt-transport",
                    "stdin",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("Workspace copy: yes", result.stdout)
            self.assertIn("Dry-run note: no temporary workspace copy is created during dry-run", result.stdout)


if __name__ == "__main__":
    unittest.main()
