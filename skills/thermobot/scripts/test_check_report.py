"""Regression tests for check_report.py. Run with `python3 -B -m unittest` from this folder."""

import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_report  # noqa: E402


def make_card(fid, severity, heading=None, extra_body=None):
    """Build a minimal valid finding card matching the Thermobot contract."""
    title_line = heading or "# {} {} - Structural risk in module".format(fid, severity)
    if severity == "Question":
        action_line = "Needed context: Confirm whether the legacy caller still owns retries."
    else:
        action_line = "Simpler path: Move retry ownership into the existing client boundary."
    body = [
        title_line,
        "",
        "- Surface: `src/a.js`",
        "- Look here first: [primary](src/a.js#L10)",
        "- Confidence: `high`",
        "",
        "Impact: Mixed orchestration and pricing rules increase change cost.",
        "",
        "Structural failure:",
        "",
        "- Expected: One cohesive owner per concern.",
        "- Current: Checkout handler mixes promotions and transport retries.",
        "",
        action_line,
        "",
        "Evidence:",
        "",
        "- `src/a.js:10-42` (379 lines, crossed 350).",
    ]
    if extra_body:
        body.append(extra_body)
    return "\n".join(body) + "\n"


def write_report(
    root,
    findings,
    recommendation,
    completion="Complete within reviewed scope",
    coverage=None,
    files=None,
    report_id="tb-20261120-a1b2c3d4",
    scope_reviewed="working tree",
    reviewed_head="36ed179abc12",
    input_fingerprint="sha256:9f86d081884c7d65",
    snapshot_consistency="Verified unchanged before handoff",
    parent_report=None,
    inherited_settlements=None,
    must_review=None,
    extra_readme="",
    ledger_links=None,
):
    """Write a complete valid report directory; findings maps IDs such as F1 to severities."""
    counts = " | ".join("{} {}".format(s, sum(v == s for v in findings.values())) for s in check_report.SEVERITIES)
    if findings:
        index_rows = "\n".join(
            "| [`{0}`](findings/{0}.md) | `{1}` | `src/a.js` | `risk` | `high` |".format(fid, sev)
            for fid, sev in findings.items()
        )
        index_block = (
            "| ID | Severity | Surface | Structural risk | Confidence |\n"
            "| --- | --- | --- | --- | --- |\n"
            + index_rows
        )
    else:
        index_block = "No structural findings identified in the reviewed scope."

    if must_review is None:
        must_review = ", ".join(list(findings.keys())[:3]) if findings else "None"

    if ledger_links is None:
        ledger_links = [
            "- [Recursive coverage ledger](coverage.md): `1 reviewed`",
            "- [File inventory](files.md): `1 file`",
        ]

    readme_text = "\n".join(
        [
            "# Thermobot Report",
            "",
            "## Report Contract",
            "",
            "- Report type: `thermobot`",
            "- Report ID: `{}`".format(report_id),
            "- Review date: `2026-11-20`",
            "- Report directory: `tmp/reviews/2026-11-20-thermobot-report-a1b2c3d4`",
            "- Repository root: `/repo`",
            "- Artifact status: `Fixed review input; do not rewrite during repair`",
            "",
            "## Scope",
            "",
            "- Scope reviewed: `{}`".format(scope_reviewed),
            "- Baseline: `HEAD`",
            "- Reviewed HEAD: `{}`".format(reviewed_head),
            "- Input fingerprint: `{}`".format(input_fingerprint),
            "- Snapshot consistency: `{}`".format(snapshot_consistency),
            *(["- Parent report: `{}`".format(parent_report)] if parent_report is not None else []),
            *(
                ["- Inherited settlements: `{}`".format(inherited_settlements)]
                if inherited_settlements is not None
                else []
            ),
            "- Intent sources: `None found`",
            "- Completion: `{}`".format(completion),
            "- Assumptions: `None`",
            "",
            "## Review Snapshot",
            "",
            "- Recommendation: `{}`".format(recommendation),
            "- Why now: `Structural gate evaluated across changed modules.`",
            "- Findings count: `{}`".format(counts),
            "- Must-review now: `{}`".format(must_review),
            "- Coverage confidence: `high`",
            "- Biggest blind spot: `None identified`",
            "",
            "## Findings Index",
            "",
            index_block,
            "",
            "## Ledgers",
            "",
            "\n".join(ledger_links),
            "",
            "## Verification Commands",
            "",
            "- `git status --short` -> `1 modified file`",
        ]
    )
    if extra_readme:
        readme_text += "\n\n" + extra_readme
    (root / "README.md").write_text(readme_text + "\n", encoding="utf-8")

    if findings:
        (root / "findings").mkdir(exist_ok=True)
    for fid, sev in findings.items():
        (root / "findings" / (fid + ".md")).write_text(make_card(fid, sev), encoding="utf-8")

    if coverage is None:
        if findings:
            coverage_rows = [
                "| `area-{0}` | `initial inventory` | `src/a.js` | `Finding {0}` | `traced` |".format(fid)
                for fid in findings
            ]
        else:
            coverage_rows = [
                "| `checkout` | `initial inventory` | `src/a.js` | `Reviewed - no issue` | `clean` |"
            ]
    else:
        coverage_rows = coverage
    (root / "coverage.md").write_text(
        "# Recursive Coverage Ledger\n\n| Area / candidate | Source | Entry points | Status | Evidence / next step |\n"
        "| --- | --- | --- | --- | --- |\n"
        + ("\n".join(coverage_rows) + "\n" if coverage_rows else ""),
        encoding="utf-8",
    )

    if files is None:
        if findings:
            first_fid = next(iter(findings))
            file_rows = [
                "| `src/a.js` | `source` | 247 | 379 | `crossed 350` | `promotions mixed in; Finding {}` |".format(
                    first_fid
                )
            ]
        else:
            file_rows = ["| `src/a.js` | `source` | 10 | 12 | `under 350` | `reviewed - no issue` |"]
    else:
        file_rows = files
    (root / "files.md").write_text(
        "# File Inventory\n\n| Path | Class | Baseline lines | Current lines | Threshold | Boundary diagnosis and decision |\n"
        "| --- | --- | ---: | ---: | --- | --- |\n"
        + ("\n".join(file_rows) + "\n" if file_rows else ""),
        encoding="utf-8",
    )


class CheckReportTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root)

    def reset_root(self):
        shutil.rmtree(self.root)
        self.root.mkdir()

    def problems(self):
        return check_report.check(self.root)[0]

    # --- Existing core regression cases (preserved and strengthened) ---

    def test_consistent_report_passes(self):
        write_report(self.root, {"F1": "Blocker", "F2": "Major"}, "Block")
        self.assertEqual(self.problems(), [])
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = check_report.main(["check_report.py", str(self.root)])
        self.assertEqual(code, 0)
        self.assertIn("OK: 2 findings, 2 coverage rows.", buf.getvalue())

    def test_missing_and_unindexed_cards_are_reported(self):
        write_report(self.root, {"F1": "Blocker", "F2": "Major"}, "Block")
        (self.root / "findings" / "F2.md").rename(self.root / "findings" / "F3.md")
        text = "\n".join(self.problems())
        self.assertIn("F2 is indexed but findings/F2.md is missing", text)
        self.assertIn("heading must start with `# F3", text)

    def test_counts_and_recommendation_follow_the_index(self):
        write_report(self.root, {"F1": "Major"}, "Pass")
        readme = self.root / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8").replace("Major 1", "Major 2"), encoding="utf-8")
        text = "\n".join(self.problems())
        self.assertIn("Findings count says Major 2, the index has 1", text)
        self.assertIn("the mapping gives `Changes requested`", text)

    def test_not_covered_requires_incomplete_completion(self):
        coverage = ["| `payments` | `trace` | `src/pay.js` | `Not covered` | `needs staging logs` |"]
        files = ["| `src/a.js` | `source` | 10 | 12 | `under 350` | `reviewed - no issue` |"]
        write_report(self.root, {}, "Pass", coverage=coverage, files=files)
        self.assertIn("Completion must be Incomplete", "\n".join(self.problems()))
        self.reset_root()
        write_report(self.root, {}, "Discuss", completion="Incomplete - payments", coverage=coverage, files=files)
        self.assertEqual(self.problems(), [])

    def test_large_file_needs_a_finding_or_waiver(self):
        write_report(
            self.root,
            {"F1": "Minor"},
            "Pass with caveat",
            files=["| `src/big.js` | `source` | 400 | 420 | `already over 350` | `reviewed - no issue` |"],
        )
        self.assertIn("maps to no finding or waiver", "\n".join(self.problems()))

    def test_split_ledgers_and_dangling_references(self):
        write_report(
            self.root,
            {"F1": "Blocker"},
            "Block",
            ledger_links=[
                "- [API coverage](coverage/api.md): `1 row`",
                "- [File inventory](files.md): `1 file`",
            ],
        )
        (self.root / "coverage.md").unlink()
        (self.root / "coverage").mkdir()
        (self.root / "coverage" / "api.md").write_text(
            "| Area | Source | Entry | Status | Evidence |\n| --- | --- | --- | --- | --- |\n"
            "| `api` | `trace` | `src/api.js` | `Merged into F9` | `dup` |\n",
            encoding="utf-8",
        )
        text = "\n".join(self.problems())
        self.assertIn("points to F9, which is not indexed", text)
        self.assertIn("F1 is indexed but not referenced in the coverage ledger", text)

    def test_non_report_path_exits_2(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = check_report.main(["check_report.py", str(self.root)])
        self.assertEqual(code, 2)

    # --- P0: field() backtick hijack, Completion word-boundary, bold keys ---

    def test_field_parsing_prevents_backtick_hijack_and_supports_bold_keys(self):
        text = (
            "- **Report type**: `thermobot`\n"
            "- **Completion:** `Incomplete` - uncovered `packages/auth`\n"
            "- Notes: Incomplete - skipped `CompleteOrderService`\n"
            "- Bad: `CompleteOrderService`\n"
        )
        self.assertEqual(check_report.field(text, "Report type"), "thermobot")
        self.assertEqual(check_report.field(text, "Completion"), "Incomplete - uncovered packages/auth")
        self.assertEqual(check_report.field(text, "Notes"), "Incomplete - skipped CompleteOrderService")
        self.assertEqual(check_report.field(text, "Bad"), "CompleteOrderService")

    def test_completion_backtick_hijack_and_prefix_collision_caught(self):
        # Backticked CompleteOrderService in Incomplete completion must stay Incomplete.
        coverage = ["| `orders` | `trace` | `src/orders.ts` | `Not covered` | `blocked` |"]
        files = ["| `src/orders.ts` | `source` | 20 | 30 | `under 350` | `reviewed - no issue` |"]
        write_report(self.root, {}, "Discuss", coverage=coverage, files=files)
        readme = self.root / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8").replace(
                "- Completion: `Complete within reviewed scope`",
                "- Completion: Incomplete - skipped `CompleteOrderService`",
            ),
            encoding="utf-8",
        )
        self.assertEqual(self.problems(), [])

        # CompleteOrderService alone must NOT pass as Complete.
        self.reset_root()
        write_report(self.root, {}, "Pass", completion="CompleteOrderService")
        self.assertIn("Completion must start with `Complete` or `Incomplete`", "\n".join(self.problems()))

    # --- P0: column-bound matching & pipe splitting ---

    def test_column_bound_matching_blocks_cross_column_bypass(self):
        # Filename contains `excluded`, threshold is `crossed 350` -> must NOT treat row as excluded.
        write_report(
            self.root,
            {"F1": "Major"},
            "Changes requested",
            files=["| `src/excluded-list.ts` | `source` | 200 | 380 | `crossed 350` | `reviewed - no issue` |"],
        )
        self.assertIn("maps to no finding or waiver", "\n".join(self.problems()))

        # Coverage Area is `Not covered`, Status is invalid `Pending` -> must NOT match Area as Status.
        self.reset_root()
        write_report(
            self.root,
            {},
            "Discuss",
            completion="Incomplete - pending",
            coverage=["| `Not covered` | `trace` | `src/a.ts` | `Pending` | `waiting` |"],
            files=["| `src/a.ts` | `source` | 10 | 20 | `under 350` | `reviewed - no issue` |"],
        )
        self.assertIn("has no recognized status", "\n".join(self.problems()))

    def test_split_table_line_preserves_empty_trailing_cells_and_escaped_pipes(self):
        self.assertEqual(check_report.split_table_line("| a | b\\|c | d ||"), ["a", "b|c", "d", ""])
        self.assertEqual(check_report.split_table_line("| a | b | c | d | |"), ["a", "b", "c", "d", ""])

    def test_reordered_ledger_columns_resolve_by_header_name(self):
        write_report(self.root, {"F1": "Major"}, "Changes requested")
        (self.root / "coverage.md").write_text(
            "# Coverage\n\n| Area | Status | Source | Entry | Evidence |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| `auth` | `Finding F1` | `initial inventory` | `src/a.js` | `traced` |\n",
            encoding="utf-8",
        )
        (self.root / "files.md").write_text(
            "# Files\n\n| Path | Threshold | Class | Base | Now | Decision |\n"
            "| --- | --- | --- | ---: | ---: | --- |\n"
            "| `src/a.js` | `crossed 350` | `source` | 200 | 380 | `Finding F1` |\n",
            encoding="utf-8",
        )
        self.assertEqual(self.problems(), [])

    # --- P0/P1: files.md decisions, not covered, finding refs, waivers, numeric line counts ---

    def test_files_crossed_350_not_covered_requires_incomplete_and_reason(self):
        files = [
            "| `src/big.ts` | `source` | 300 | 420 | `crossed 350` | `mixed concerns; not covered - blocked on schema` |"
        ]
        coverage = ["| `big` | `initial inventory` | `src/big.ts` | `Not covered` | `blocked on schema` |"]
        write_report(self.root, {}, "Pass", coverage=coverage, files=files)
        text = "\n".join(self.problems())
        self.assertIn("files.md: `src/big.ts` is not covered, so Completion must be Incomplete", text)

        self.reset_root()
        write_report(self.root, {}, "Discuss", completion="Incomplete - big.ts", coverage=coverage, files=files)
        self.assertEqual(self.problems(), [])

        # Bare `not covered` without reason must fail even when Incomplete.
        self.reset_root()
        bare_files = ["| `src/big.ts` | `source` | 300 | 420 | `crossed 350` | `not covered` |"]
        write_report(self.root, {}, "Discuss", completion="Incomplete - big.ts", coverage=coverage, files=bare_files)
        self.assertIn("must include a blocker or reason", "\n".join(self.problems()))

    def test_files_finding_refs_and_explicit_decision_clauses(self):
        # Dangling F99 on `under 350` row must be caught.
        write_report(
            self.root,
            {},
            "Pass",
            files=["| `src/small.ts` | `source` | 10 | 20 | `under 350` | `Finding F99` |"],
        )
        self.assertIn("points to F99, which is not indexed", "\n".join(self.problems()))

        # `F12 key handler` is NOT a finding ref and must pass on `under 350` with `reviewed - no issue`.
        self.reset_root()
        write_report(
            self.root,
            {},
            "Pass",
            files=["| `src/keys.ts` | `source` | 40 | 55 | `under 350` | `F12 key handler; reviewed - no issue` |"],
        )
        self.assertEqual(self.problems(), [])

        # `F12 key handler`, `cannot waive`, bare `waived`, and `excluded - ...` are rejected on `crossed 350`.
        for bad_decision in (
            "F12 key handler",
            "cannot waive",
            "waived",
            "excluded - legacy",
        ):
            self.reset_root()
            write_report(
                self.root,
                {"F1": "Major"},
                "Changes requested",
                files=[
                    "| `src/big.ts` | `source` | 300 | 380 | `crossed 350` | `{}` |".format(bad_decision)
                ],
            )
            self.assertIn("maps to no finding or waiver", "\n".join(self.problems()), bad_decision)

        # `waived - <reason>` passes on `already over 350`.
        self.reset_root()
        write_report(
            self.root,
            {},
            "Pass",
            files=[
                "| `src/parser.ts` | `source` | 410 | 390 | `already over 350` | `single cohesive state machine; waived - reduced from 410 to 390` |"
            ],
        )
        self.assertEqual(self.problems(), [])

        # `excluded` rejects `do not exclude` and `reviewed - no issue`, accepts `excluded - <reason>`.
        self.reset_root()
        write_report(
            self.root,
            {},
            "Pass",
            files=[
                "| `src/gen.ts` | `generated` | 10 | 500 | `excluded` | `do not exclude` |",
                "| `src/snap.ts` | `test` | 10 | 500 | `excluded` | `reviewed - no issue` |",
            ],
        )
        text = "\n".join(self.problems())
        self.assertIn("needs an `excluded - <reason>`", text)
        self.assertIn("is excluded and cannot use `reviewed - no issue`", text)

        self.reset_root()
        write_report(
            self.root,
            {},
            "Pass",
            files=["| `src/gen.ts` | `generated` | 10 | 500 | `excluded` | `excluded - generated protobuf output` |"],
        )
        self.assertEqual(self.problems(), [])

    def test_files_numeric_threshold_crosscheck_and_class_validation(self):
        # 200 -> 500 labeled `under 350`, 349 -> 350 exact boundary labeled `under 350`,
        # 350 -> 360 labeled `crossed 350`, and invalid class `binary`.
        write_report(
            self.root,
            {"F1": "Major"},
            "Changes requested",
            files=[
                "| `src/a.ts` | `source` | 200 | 500 | `under 350` | `reviewed - no issue` |",
                "| `src/b.ts` | `source` | 349 | 350 | `under 350` | `reviewed - no issue` |",
                "| `src/c.ts` | `source` | 350 | 360 | `crossed 350` | `Finding F1` |",
                "| `src/d.bin` | `binary` | 10 | 20 | `under 350` | `reviewed - no issue` |",
            ],
        )
        text = "\n".join(self.problems())
        self.assertIn("`src/a.ts` has lines 200 -> 500, which conflicts with threshold `under 350`", text)
        self.assertIn("`src/b.ts` has lines 349 -> 350, which conflicts with threshold `under 350`", text)
        self.assertIn("`src/c.ts` has lines 350 -> 360, which conflicts with threshold `crossed 350`", text)
        self.assertIn("`src/d.bin` has unrecognized class `binary`", text)

        # Exact 350 boundary: 349 -> 350 is `crossed 350`, 350 -> 360 is `already over 350`.
        self.reset_root()
        write_report(
            self.root,
            {"F1": "Major"},
            "Changes requested",
            files=[
                "| `src/b.ts` | `source` | 349 | 350 | `crossed 350` | `Finding F1` |",
                "| `src/c.ts` | `source` | 350 | 360 | `already over 350` | `waived - cohesive` |",
            ],
        )
        self.assertEqual(self.problems(), [])

    # --- P0/P1: fenced blocks, section scoping, index links, malformed/non-consecutive IDs ---

    def test_fenced_blocks_and_other_section_tables_are_ignored(self):
        extra = (
            "## Appendix\n\n"
            "| ID | Note |\n| --- | --- |\n| `F1` | `extra table outside Findings Index` |\n\n"
            "```markdown\n"
            "## Findings Index\n"
            "| [`F99`](findings/F99.md) | `Blocker` | `fake` | `fake` | `high` |\n"
            "- Completion: `Incomplete`\n"
            "```\n\n"
            "~~~\n"
            "- Report type: `wrong`\n"
            "| `F88` | `Major` |\n"
            "~~~\n"
        )
        write_report(self.root, {"F1": "Minor"}, "Pass with caveat", extra_readme=extra)
        self.assertEqual(self.problems(), [])

    def test_findings_index_link_mismatch_malformed_id_and_gaps_caught(self):
        write_report(self.root, {"F1": "Blocker", "F2": "Major"}, "Block")
        readme = self.root / "README.md"
        text = readme.read_text(encoding="utf-8")
        # Break F1's link to point to F2.md and inject a malformed row.
        text = text.replace("[`F1`](findings/F1.md)", "[`F1`](findings/F2.md)")
        text = text.replace(
            "| [`F2`](findings/F2.md) | `Major` | `src/a.js` | `risk` | `high` |",
            "| [`F2`](findings/F2.md) | `Major` | `src/a.js` | `risk` | `high` |\n"
            "| `BAD` | `Minor` | `src/x.js` | `malformed` | `low` |",
        )
        readme.write_text(text, encoding="utf-8")
        problems_text = "\n".join(self.problems())
        self.assertIn("F1 links to `findings/F2.md`, expected `findings/F1.md`", problems_text)
        self.assertIn("Findings Index has malformed finding ID `BAD`", problems_text)

        # Non-consecutive numbering F1, F3 caught.
        self.reset_root()
        write_report(self.root, {"F1": "Blocker", "F3": "Minor"}, "Block")
        self.assertIn("Findings Index IDs must be consecutive (F1..F2), got F1, F3", "\n".join(self.problems()))

    # --- P0/P2: card H1 variants, body sections, fenced blocks in cards, placeholders ---

    def test_card_heading_variants_and_required_body_sections(self):
        write_report(self.root, {"F1": "Blocker", "F2": "Major", "F3": "Question"}, "Block")
        (self.root / "findings" / "F1.md").write_text(make_card("F1", "Blocker", "# F1 Blocker - Plain"), encoding="utf-8")
        (self.root / "findings" / "F2.md").write_text(make_card("F2", "Major", "# F2 `Major` - Ticked"), encoding="utf-8")
        (self.root / "findings" / "F3.md").write_text(make_card("F3", "Question", "# F3 [Question] - Bracketed"), encoding="utf-8")
        self.assertEqual(self.problems(), [])

        # Missing required sections and unfilled placeholders caught.
        (self.root / "findings" / "F1.md").write_text(
            "```markdown\n# F1 Blocker - Fake inside fence\nImpact: fake\n```\n\n"
            "# F1 Blocker - [Short title]\n\n"
            "- Surface: `src/a.js`\n"
            "- Look here first: [primary](/abs/path/file.ts#L10)\n"
            "- Confidence: `high`\n"
            "Impact:\n\n"
            "Structural failure:\n\n"
            "Evidence:\n",
            encoding="utf-8",
        )
        problems_text = "\n".join(self.problems())
        self.assertIn("findings/F1.md: missing or empty `Impact` section", problems_text)
        self.assertIn("findings/F1.md: missing or empty `Structural failure` section", problems_text)
        self.assertIn("findings/F1.md: missing or empty `Simpler path` section", problems_text)
        self.assertIn("findings/F1.md: missing or empty `Evidence` section", problems_text)
        self.assertIn("unfilled template placeholder `[Short title]`", problems_text)
        self.assertIn("unfilled template placeholder `/abs/path/file.ts`", problems_text)

    def test_card_evidence_with_fenced_block_counts_as_non_empty(self):
        write_report(self.root, {"F1": "Minor"}, "Pass with caveat")
        (self.root / "findings" / "F1.md").write_text(
            "# F1 Minor - Helper duplication\n\n"
            "- Surface: `src/a.js`\n"
            "- Look here first: [a.js](src/a.js#L5)\n"
            "- Confidence: `high`\n\n"
            "Impact: Duplicate formatter logic.\n\n"
            "Structural failure:\n\n"
            "- Expected: Reuse shared formatter.\n"
            "- Current: Reimplemented inline.\n\n"
            "Simpler path: Import `formatDate` from `src/date.js`.\n\n"
            "Evidence:\n\n"
            "```text\n"
            "src/a.js:5-20 duplicates src/date.js:12-28\n"
            "```\n",
            encoding="utf-8",
        )
        self.assertEqual(self.problems(), [])

    # --- P1/P2: coverage.md multi-finding, case-sensitive F#, Source ref, reverse coverage, en-dash ---

    def test_coverage_multi_finding_case_sensitivity_source_and_reverse_check(self):
        # Valid multi-finding + Unicode en-dash + valid discovered-from source.
        write_report(
            self.root,
            {"F1": "Major", "F2": "Minor"},
            "Changes requested",
            coverage=[
                "| `checkout` | `initial inventory` | `src/a.js` | `Finding F1, F2` | `both issues` |",
                "| `pricing` | `discovered from F1` | `src/p.js` | `Reviewed \u2013 no issue` | `verified caller` |",
            ],
        )
        self.assertEqual(self.problems(), [])

        # Dangling multi-finding, lowercase `f1`, bad `discovered from F9`, empty evidence, reverse gap on F2.
        self.reset_root()
        write_report(
            self.root,
            {"F1": "Major", "F2": "Minor"},
            "Changes requested",
            completion="Incomplete - billing",
            coverage=[
                "| `checkout` | `initial inventory` | `src/a.js` | `Finding F1, F99` | `traced` |",
                "| `lower` | `initial inventory` | `src/b.js` | `Finding f1` | `bad case` |",
                "| `caller` | `discovered from F9` | `src/c.js` | `Reviewed - no issue` | `` |",
                "| `billing` | `trace` | `src/d.js` | `Not covered` | `` |",
            ],
        )
        text = "\n".join(self.problems())
        self.assertIn("points to F99, which is not indexed", text)
        self.assertIn("has no recognized status (`Finding f1`)", text)
        self.assertIn("source references F9, which is not indexed", text)
        self.assertIn("is Reviewed - no issue but Evidence / next step is empty", text)
        self.assertIn("is Not covered but Evidence / next step is empty", text)
        self.assertIn("F2 is indexed but not referenced in the coverage ledger", text)

    # --- P1/P2: empty files.md, split-ledger link check, README contract/placeholders/Must-review ---

    def test_empty_files_ledger_and_unlinked_split_ledgers_caught(self):
        write_report(self.root, {}, "Pass", files=[])
        self.assertIn("file inventory has no rows", "\n".join(self.problems()))

        self.reset_root()
        write_report(self.root, {}, "Pass")
        (self.root / "coverage.md").unlink()
        (self.root / "coverage").mkdir()
        (self.root / "coverage" / "api.md").write_text(
            "| Area | Source | Entry | Status | Evidence |\n| --- | --- | --- | --- | --- |\n"
            "| `api` | `initial` | `src/api.ts` | `Reviewed - no issue` | `ok` |\n",
            encoding="utf-8",
        )
        (self.root / "files.md").unlink()
        (self.root / "files").mkdir()
        (self.root / "files" / "api.md").write_text(
            "| Path | Class | Base | Now | Threshold | Decision |\n| --- | --- | ---: | ---: | --- | --- |\n"
            "| `src/api.ts` | `source` | 10 | 20 | `under 350` | `reviewed - no issue` |\n",
            encoding="utf-8",
        )
        text = "\n".join(self.problems())
        self.assertIn("split ledger `coverage/api.md` is not linked from README.md", text)
        self.assertIn("split ledger `files/api.md` is not linked from README.md", text)

    def test_readme_contract_snapshot_placeholders_and_must_review(self):
        # Pasted code N/A for Reviewed HEAD and Input fingerprint passes.
        write_report(
            self.root,
            {},
            "Pass",
            reviewed_head="N/A for pasted code",
            input_fingerprint="N/A for pasted code",
        )
        self.assertEqual(self.problems(), [])

        # Unfilled Report ID, placeholders, missing snapshot values, and dangling Must-review now caught.
        self.reset_root()
        write_report(
            self.root,
            {"F1": "Major"},
            "Changes requested",
            report_id="tb-YYYYMMDD-<random-id>",
            reviewed_head="[commit SHA | N/A for pasted code]",
            input_fingerprint="sha256:<hash>",
            snapshot_consistency="",
            must_review="F1, F9",
            extra_readme="Run `python3 <skill-folder>/scripts/check_report.py <report-dir>` at `[absolute path]`.",
        )
        text = "\n".join(self.problems())
        self.assertIn("Report ID `tb-YYYYMMDD-<random-id>` must match", text)
        self.assertIn("Reviewed HEAD is missing or an unfilled placeholder", text)
        self.assertIn("Input fingerprint is missing or an unfilled placeholder", text)
        self.assertIn("Snapshot consistency is missing or an unfilled placeholder", text)
        self.assertIn("Must-review now references F9, which is not indexed", text)
        self.assertIn("unfilled template placeholder `<random-id>`", text)
        self.assertIn("unfilled template placeholder `<skill-folder>`", text)
        self.assertIn("unfilled template placeholder `[absolute path]`", text)

    def test_missing_required_readme_sections_reported(self):
        write_report(self.root, {}, "Pass")
        readme = self.root / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8").replace("## Ledgers", "## Notes"), encoding="utf-8")
        self.assertIn("missing required section `## Ledgers`", "\n".join(self.problems()))

    # --- Second-lens audit regressions (#18 / #19) ---

    def test_files_not_covered_in_diagnosis_prose_does_not_false_positive(self):
        write_report(
            self.root,
            {"F1": "Major"},
            "Changes requested",
            files=[
                "| `src/foo.ts` | `source` | 50 | 80 | `under 350` | `not covered by shared schema validator; Finding F1` |",
                "| `src/bar.ts` | `source` | 50 | 80 | `under 350` | `not covered by shared schema validator; reviewed - no issue` |",
            ],
        )
        self.assertEqual(self.problems(), [])

        # Trailing delimiter without a reason (`not covered -`) still forces Incomplete and flags missing reason.
        self.reset_root()
        write_report(
            self.root,
            {},
            "Pass",
            files=["| `src/baz.ts` | `source` | 50 | 80 | `under 350` | `not covered -` |"],
        )
        text = "\n".join(self.problems())
        self.assertIn("is not covered, so Completion must be Incomplete", text)
        self.assertIn("must include a blocker or reason", text)

    def test_post_fix_delta_requires_parent_report_and_inherited_settlements(self):
        # Omitted Parent report and Inherited settlements fail.
        write_report(
            self.root,
            {},
            "Pass",
            scope_reviewed="post-fix delta of tb-20261120-00001111",
        )
        text = "\n".join(self.problems())
        self.assertIn("Parent report `` is required for post-fix delta reports", text)
        self.assertIn("Inherited settlements is required for post-fix delta reports", text)

        # Parent report `None` and placeholder Inherited settlements fail.
        self.reset_root()
        write_report(
            self.root,
            {},
            "Pass",
            scope_reviewed="post-fix delta of tb-20261120-00001111",
            parent_report="None",
            inherited_settlements="[None | settled intent and disproved claims carried forward]",
        )
        text = "\n".join(self.problems())
        self.assertIn("Parent report `None` is required for post-fix delta reports", text)
        self.assertIn("Inherited settlements is required for post-fix delta reports", text)

        # Valid Parent report ID and non-placeholder Inherited settlements pass.
        self.reset_root()
        write_report(
            self.root,
            {},
            "Pass",
            scope_reviewed="post-fix delta of tb-20261120-00001111",
            parent_report="tb-20261120-00001111",
            inherited_settlements="Carried forward F2 waiver on legacy adapter",
        )
        self.assertEqual(self.problems(), [])

    def test_partial_numeric_files_threshold_crosscheck(self):
        write_report(
            self.root,
            {"F1": "Major"},
            "Changes requested",
            files=[
                "| `snippet.ts` | `source` | - | 420 | `under 350` | `reviewed - no issue` |",
                "| `snippet2.ts` | `source` | N/A | 200 | `crossed 350` | `Finding F1` |",
            ],
        )
        text = "\n".join(self.problems())
        self.assertIn("`snippet.ts` has lines - -> 420, which conflicts with threshold `under 350`", text)
        self.assertIn("`snippet2.ts` has lines N/A -> 200, which conflicts with threshold `crossed 350`", text)

        self.reset_root()
        write_report(
            self.root,
            {"F1": "Major"},
            "Changes requested",
            files=[
                "| `snippet.ts` | `source` | - | 42 | `under 350` | `reviewed - no issue` |",
                "| `snippet2.ts` | `source` | - | 350 | `crossed 350` | `Finding F1` |",
            ],
        )
        self.assertEqual(self.problems(), [])

    def test_ledger_and_extended_readme_placeholders_caught(self):
        write_report(
            self.root,
            {},
            "Pass",
            coverage=[
                "| `[area or candidate]` | `initial inventory` | `src/a.ts` | `Reviewed - no issue` | `[concrete structural conclusion, or blocker]` |"
            ],
            files=[
                "| `[path]` | `source` | 400 | 420 | `already over 350` | `waived - <reason>` |"
            ],
        )
        readme = self.root / "README.md"
        text = readme.read_text(encoding="utf-8")
        text = text.replace("- Review date: `2026-11-20`", "- Review date: `YYYY-MM-DD`")
        text = text.replace("- Baseline: `HEAD`", "- Baseline: `[HEAD | merge-base commit SHA]`")
        text = text.replace("- Intent sources: `None found`", "- Intent sources: `[None found | requirements]`")
        text = text.replace("- Assumptions: `None`", "- Assumptions: `[None | inferred scope]`")
        text += "- Inherited settlements: `[None | settled intent and disproved claims]`\n"
        readme.write_text(text, encoding="utf-8")

        problems_text = "\n".join(self.problems())
        self.assertIn("files.md: contains unfilled template placeholder `<reason>`", problems_text)
        self.assertIn("files.md: contains unfilled template placeholder `[path]`", problems_text)
        self.assertIn("coverage.md: contains unfilled template placeholder `[area or candidate]`", problems_text)
        self.assertIn("coverage.md: contains unfilled template placeholder `[concrete structural conclusion,`", problems_text)
        self.assertIn("README.md: Review date contains unfilled template placeholder `YYYY-MM-DD`", problems_text)
        self.assertIn("README.md: contains unfilled template placeholder `[HEAD | merge-base`", problems_text)
        self.assertIn("README.md: contains unfilled template placeholder `[None | settled intent`", problems_text)
        self.assertIn("README.md: contains unfilled template placeholder `[None found |`", problems_text)
        self.assertIn("README.md: contains unfilled template placeholder `[None | inferred scope`", problems_text)

    def test_must_review_lowercase_and_unescaped_pipe_truncation_caught(self):
        write_report(
            self.root,
            {"F1": "Major"},
            "Changes requested",
            must_review="f1, f99",
            files=[
                '| `src/a.js` | `source` | 200 | 380 | `crossed 350` | `waived - Status = "a" | "b"; Finding F99` |'
            ],
        )
        text = "\n".join(self.problems())
        self.assertIn("Must-review now has malformed lowercase finding ID `f1`", text)
        self.assertIn("Must-review now has malformed lowercase finding ID `f99`", text)
        self.assertIn("Must-review now references f99, which is not indexed", text)
        self.assertIn("files.md: row `src/a.js` has 7 columns, expected 6", text)

        # Escaping the literal pipe parses 6 columns cleanly and still catches dangling Finding F99.
        self.reset_root()
        write_report(
            self.root,
            {"F1": "Major"},
            "Changes requested",
            files=[
                '| `src/a.js` | `source` | 200 | 380 | `crossed 350` | `waived - Status = "a" \\| "b"; Finding F99` |'
            ],
        )
        self.assertIn("files.md: `src/a.js` points to F99, which is not indexed", "\n".join(self.problems()))

    # --- Round-2 false-positive & Must-review regressions (#24 / #25) ---

    def test_generics_html_tags_dynamic_routes_and_date_prose_do_not_false_positive(self):
        write_report(
            self.root,
            {},
            "Pass",
            scope_reviewed="post-fix delta of tb-20261120-00001111",
            parent_report="tb-20261120-00001111",
            inherited_settlements="Carried forward F2 waiver on Promise<void> retry queue",
            snapshot_consistency="Matches snapshot after Array<string> check",
            coverage=[
                "| `EntityStore<Id>` | `initial inventory` | `src/store.ts` | `Reviewed - no issue` | `checked take<N> and <area> tag` |"
            ],
            files=[
                "| `[path](src/path.ts)` | `source` | 40 | 55 | `under 350` | `cohesive helpers; reviewed - no issue` |",
                "| `src/pages/docs/[path].tsx` | `source` | 40 | 55 | `under 350` | `typed Route<Path>, Tuple<N>, and Reject<Reason>; reviewed - no issue` |",
            ],
            extra_readme="- Verified `YYYY-MM-DD` parser reuse alongside `<base>` and `Tuple<N>`.",
        )
        self.assertEqual(self.problems(), [])

        # Report directory leaving literal YYYY-MM-DD is still caught.
        readme = self.root / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8").replace(
                "2026-11-20-thermobot-report-a1b2c3d4", "YYYY-MM-DD-thermobot-report-a1b2c3d4"
            ),
            encoding="utf-8",
        )
        self.assertIn("Report directory contains unfilled template placeholder `YYYY-MM-DD`", "\n".join(self.problems()))

    def test_must_review_omission_non_id_and_trailing_context_tokens(self):
        # Trailing lowercase tokens like `f32` or `src/f2.ts` after a valid ID must pass.
        write_report(
            self.root,
            {"F1": "Blocker", "F2": "Major"},
            "Block",
            must_review="F1 - duplicate f32 quantizer; F2 (src/f2.ts)",
        )
        self.assertEqual(self.problems(), [])

        # Parenthesized comma context passes cleanly.
        self.reset_root()
        write_report(
            self.root,
            {"F1": "Blocker", "F2": "Major"},
            "Block",
            must_review="F1 (Blocker, src/f2.ts), F2 (Major)",
        )
        self.assertEqual(self.problems(), [])

        # Omitted Must-review now fails.
        self.reset_root()
        write_report(self.root, {"F1": "Major"}, "Changes requested")
        readme = self.root / "README.md"
        readme.write_text(
            "\n".join(line for line in readme.read_text(encoding="utf-8").splitlines() if "Must-review now:" not in line)
            + "\n",
            encoding="utf-8",
        )
        self.assertIn("Must-review now is missing or an unfilled placeholder", "\n".join(self.problems()))

        # `TBD` and non-ID prose fail.
        for bad_val, expected_msg in (
            ("TBD", "Must-review now is missing or an unfilled placeholder"),
            ("Check auth module", "contains non-finding token `Check`"),
            ("F1, f2", "malformed lowercase finding ID `f2`"),
            ("F1 and F99", "references F99, which is not indexed"),
            ("F1 F99", "references F99, which is not indexed"),
            ("F1 / f2", "malformed lowercase finding ID `f2`"),
            ("F1 and f2", "malformed lowercase finding ID `f2`"),
        ):
            self.reset_root()
            write_report(self.root, {"F1": "Blocker", "F2": "Major"}, "Block", must_review=bad_val)
            self.assertIn(expected_msg, "\n".join(self.problems()), bad_val)

    # --- Round-3 audit regressions (#30 / #31) ---

    def test_html5_details_pascalcase_jsx_separate_brackets_and_nested_ledger_links_pass(self):
        write_report(
            self.root,
            {"F1": "Major"},
            "Changes requested",
            scope_reviewed="post-fix delta of tb-20261120-00001111",
            parent_report="tb-20261120-00001111",
            inherited_settlements="[F2] waiver carried forward for pages/[path] and <details> / <Id>(x: Id) => Id",
            snapshot_consistency="Matches reviewed snapshot; verified <details> toggle and <Decision> unchanged",
            must_review="F1 - broken <details> disclosure controller and <Reason> banner",
            coverage=[
                "| `disclosure` | `initial inventory` | `src/ui.tsx` | `Finding F1` | `checked <Decision>, <Reason>, <Diagnosis>, <Blocker>, <Hash>, <Digest>, <Sha>` |"
            ],
            ledger_links=[
                "- [Recursive coverage ledger](coverage.md): `1 row`",
                "- [Dynamic [path] routes](files/routes.md): `1 file`",
            ],
        )
        (self.root / "files.md").unlink()
        (self.root / "files").mkdir()
        (self.root / "files" / "routes.md").write_text(
            "# File Inventory\n\n| Path | Class | Baseline lines | Current lines | Threshold | Boundary diagnosis and decision |\n"
            "| --- | --- | ---: | ---: | --- | --- |\n"
            "| [`[path].tsx`](src/pages/docs/[path].tsx) | `source` | 40 | 55 | `under 350` | `renders <Decision> and <Diagnosis>; Finding F1` |\n",
            encoding="utf-8",
        )
        self.assertEqual(self.problems(), [])

        # Lowercase template angle tokens are still caught.
        (self.root / "files" / "routes.md").write_text(
            "# File Inventory\n\n| Path | Class | Baseline lines | Current lines | Threshold | Boundary diagnosis and decision |\n"
            "| --- | --- | ---: | ---: | --- | --- |\n"
            "| `src/a.ts` | `source` | 400 | 420 | `already over 350` | `waived - <reason>` |\n",
            encoding="utf-8",
        )
        self.assertIn("files/routes.md: contains unfilled template placeholder `<reason>`", "\n".join(self.problems()))

    def test_must_review_oxford_comma_generics_and_prose_commas_pass(self):
        for valid_val in (
            "F1, F2, and F3",
            "F1, F2 and F3",
            "F1 - unbounded Map<string, Promise<void>> cache",
            "F1 - mixed checkout, retry, and auth",
            "F1 - duplicate f32 quantizer",
            "F1 (src/f2.ts)",
            "F1 - first, F2 - second",
            "F1 - first, and F2 - second",
            "F1 - inline { a: string; b: number } prop type",
            "F1 - leaked Promise<{ cb: () => void; ok: boolean }> state",
            "F1 - Callback<() => void, f32, f64> overflow",
            "F1 - duplicate f32, f64, and f16 quantizers",
            "F1 - supports f32, f64",
            "F1 - parses f32, f64 --strict flag",
            "F1 - offset f32, f64 -1 alignment",
            "F1 - handles F12, F11 --help flag",
            "F1 -- mixed checkout, retry, and auth",
            "F1\u2014mixed checkout, retry, and auth",
            "None",
        ):
            self.reset_root()
            write_report(
                self.root,
                {"F1": "Blocker", "F2": "Major", "F3": "Minor"},
                "Block",
                must_review=valid_val,
            )
            self.assertEqual(self.problems(), [], valid_val)

    def test_must_review_tight_comparisons_and_multi_id_secondary_entries_caught(self):
        for bad_val, findings, expected_msg in (
            ("F1 - retry when attempt<3; F99 - missing timeout", {"F1": "Blocker"}, "references F99, which is not indexed"),
            ("F1 - threshold <350 check, F99 - missing waiver", {"F1": "Blocker"}, "references F99, which is not indexed"),
            ("F1 - off-by-one i<len; f2 - bad casing", {"F1": "Blocker", "F2": "Major"}, "malformed lowercase finding ID `f2`"),
            ("F1 - off-by-one i<len; F99 - count>0", {"F1": "Blocker"}, "references F99, which is not indexed"),
            ("F1 - off-by-one i<len, F99 - count>0", {"F1": "Blocker"}, "references F99, which is not indexed"),
            ("F1 - off-by-one i<len, F99: count>0", {"F1": "Blocker"}, "references F99, which is not indexed"),
            ("F1 - off-by-one i<len, f2: count>0", {"F1": "Blocker", "F2": "Major"}, "malformed lowercase finding ID `f2`"),
            ("F1 - off-by-one i<len, F99 (retry): count>0", {"F1": "Blocker"}, "references F99, which is not indexed"),
            ("F1 - check a<b, F99: broken </details> tag", {"F1": "Blocker"}, "references F99, which is not indexed"),
            ("F1 - checkout boundary, F2 & F99 - retry duplication", {"F1": "Blocker", "F2": "Major"}, "references F99, which is not indexed"),
            ("F1 - checkout boundary, f2 & f3 - retry duplication", {"F1": "Blocker", "F2": "Major", "F3": "Minor"}, "malformed lowercase finding ID `f2`"),
            ("F1 - checkout boundary, F2 F99 - retry duplication", {"F1": "Blocker", "F2": "Major"}, "references F99, which is not indexed"),
        ):
            self.reset_root()
            write_report(self.root, findings, "Block", must_review=bad_val)
            self.assertIn(expected_msg, "\n".join(self.problems()), bad_val)


if __name__ == "__main__":
    unittest.main()
