"""Regression tests for check_report.py. Run with `python3 -m unittest` from this folder."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_report  # noqa: E402


def write_report(root, findings, recommendation, completion="Complete within reviewed scope", coverage=None, files=None):
    """Write a minimal report directory; findings maps IDs such as F1 to severities."""
    counts = " | ".join("{} {}".format(s, sum(v == s for v in findings.values())) for s in check_report.SEVERITIES)
    index = "\n".join(
        "| [`{0}`](findings/{0}.md) | `{1}` | `src/a.js` | `risk` | `high` |".format(fid, sev) for fid, sev in findings.items()
    )
    (root / "README.md").write_text(
        "# Thermobot Report\n\n- Report type: `thermobot`\n- Completion: `{}`\n- Recommendation: `{}`\n"
        "- Findings count: `{}`\n\n| ID | Severity | Surface | Structural risk | Confidence |\n"
        "| --- | --- | --- | --- | --- |\n{}\n".format(completion, recommendation, counts, index),
        encoding="utf-8",
    )
    if findings:
        (root / "findings").mkdir()
    for fid, sev in findings.items():
        (root / "findings" / (fid + ".md")).write_text("# {} {} - Title\n\nImpact: x\n".format(fid, sev), encoding="utf-8")
    rows = coverage or ["| `checkout` | `initial inventory` | `src/a.js` | `Finding F1` | `ok` |"]
    (root / "coverage.md").write_text(
        "# Recursive Coverage Ledger\n\n| Area | Source | Entry | Status | Evidence |\n| --- | --- | --- | --- | --- |\n"
        + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    rows = files or ["| `src/a.js` | `source` | 247 | 379 | `crossed 350` | `promotions mixed in; Finding F1` |"]
    (root / "files.md").write_text(
        "# File Inventory\n\n| Path | Class | Base | Now | Threshold | Decision |\n| --- | --- | ---: | ---: | --- | --- |\n"
        + "\n".join(rows) + "\n",
        encoding="utf-8",
    )


class CheckReportTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root)

    def problems(self):
        return check_report.check(self.root)[0]

    def test_consistent_report_passes(self):
        write_report(self.root, {"F1": "Blocker", "F2": "Major"}, "Block")
        self.assertEqual(self.problems(), [])

    def test_missing_and_unindexed_cards_are_reported(self):
        write_report(self.root, {"F1": "Blocker", "F2": "Major"}, "Block")
        (self.root / "findings" / "F2.md").rename(self.root / "findings" / "F3.md")
        text = "\n".join(self.problems())
        self.assertIn("F2 is indexed but findings/F2.md is missing", text)
        self.assertIn("heading must start with `# F3", text)

    def test_counts_and_recommendation_follow_the_index(self):
        write_report(self.root, {"F1": "Major"}, "Pass")
        readme = self.root / "README.md"
        readme.write_text(readme.read_text().replace("Major 1", "Major 2"))
        text = "\n".join(self.problems())
        self.assertIn("Findings count says Major 2, the index has 1", text)
        self.assertIn("the mapping gives `Changes requested`", text)

    def test_not_covered_requires_incomplete_completion(self):
        coverage = ["| `payments` | `trace` | `src/pay.js` | `Not covered` | `needs staging logs` |"]
        files = ["| `src/a.js` | `source` | 10 | 12 | `under 350` | `reviewed - no issue` |"]
        write_report(self.root, {}, "Pass", coverage=coverage, files=files)
        self.assertIn("Completion must be Incomplete", "\n".join(self.problems()))
        shutil.rmtree(self.root)
        self.root.mkdir()
        write_report(self.root, {}, "Discuss", completion="Incomplete - payments", coverage=coverage, files=files)
        self.assertEqual(self.problems(), [])

    def test_large_file_needs_a_finding_or_waiver(self):
        write_report(self.root, {"F1": "Minor"}, "Pass with caveat",
                     files=["| `src/big.js` | `source` | 400 | 420 | `already over 350` | `reviewed - no issue` |"])
        self.assertIn("maps to no finding or waiver", "\n".join(self.problems()))

    def test_split_ledgers_and_dangling_references(self):
        write_report(self.root, {"F1": "Blocker"}, "Block")
        (self.root / "coverage.md").unlink()
        (self.root / "coverage").mkdir()
        (self.root / "coverage" / "api.md").write_text(
            "| Area | Source | Entry | Status | Evidence |\n| --- | --- | --- | --- | --- |\n"
            "| `api` | `trace` | `src/api.js` | `Merged into F9` | `dup` |\n"
        )
        self.assertIn("points to F9, which is not indexed", "\n".join(self.problems()))

    def test_non_report_path_exits_2(self):
        self.assertEqual(check_report.main(["check_report.py", str(self.root)]), 2)


if __name__ == "__main__":
    unittest.main()
