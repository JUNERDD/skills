#!/usr/bin/env python3
"""Check that a Thermobot report directory is internally consistent.

Usage: python3 check_report.py <report-dir>

Confirms that the README index, the finding files, the severity counts, the
recommendation, and the ledgers agree with one another. It cannot judge
whether the review itself was complete; that stays with the reviewer.
Prints OK and exits 0 when consistent, prints one problem per line and exits 1
otherwise, and exits 2 when the path is not a report directory.
"""

import re
import sys
from pathlib import Path

SEVERITIES = ("Blocker", "Major", "Minor", "Question")
# A coverage row's status: either a pointer at a finding or one of the closed outcomes.
STATUS = re.compile(
    r"^(?:(?:Finding|Merged into)\s+(F\d+)\b|(Reviewed - no issue|Not review-relevant|Not covered)\b)",
    re.IGNORECASE,
)
THRESHOLD = re.compile(r"^(under 350|crossed 350|already over 350|excluded)\b", re.IGNORECASE)
SEPARATOR = re.compile(r"^\|(\s*:?-+:?\s*\|)+$")


def plain(text):
    """Strip Markdown links, backticks, and emphasis so cells compare as plain tokens."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return text.replace("`", "").replace("*", "").strip()


def table_rows(text):
    """Return the body rows of every Markdown table in text, as lists of plain cells."""
    rows, in_body = [], False
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            in_body = False
            continue
        if SEPARATOR.match(line):
            in_body = True
            continue
        if in_body:
            cells = line.replace("\\|", "\0").strip("|").split("|")
            rows.append([plain(cell.replace("\0", "|")) for cell in cells])
    return rows


def field(text, name):
    """Return the value of a `- Name: value` bullet, preferring its first backticked span."""
    match = re.search(r"^\s*-\s*" + re.escape(name) + r":\s*(.+)$", text, re.MULTILINE)
    if not match:
        return ""
    ticked = re.search(r"`([^`]+)`", match.group(1))
    return (ticked.group(1) if ticked else plain(match.group(1))).strip()


def ledger_parts(report, name):
    """A ledger is `<name>.md`, or `<name>/*.md` when it was split by area."""
    parts = [report / (name + ".md")] if (report / (name + ".md")).is_file() else []
    if (report / name).is_dir():
        parts += sorted((report / name).glob("*.md"))
    return parts


def expected_recommendation(severities, incomplete):
    if "Blocker" in severities:
        return "Block"
    if "Major" in severities:
        return "Changes requested"
    if "Question" in severities or incomplete:
        return "Discuss"
    if "Minor" in severities:
        return "Pass with caveat"
    return "Pass"


def check(report):
    problems = []
    readme = (report / "README.md").read_text(encoding="utf-8")

    if field(readme, "Report type") != "thermobot":
        problems.append("README.md: Report type is not `thermobot`.")
    completion = field(readme, "Completion")
    if not completion.startswith(("Complete", "Incomplete")):
        problems.append("README.md: Completion must start with `Complete` or `Incomplete`.")
    incomplete = completion.startswith("Incomplete")

    index = {}
    for cells in table_rows(readme):
        if len(cells) < 2 or not re.fullmatch(r"F\d+", cells[0]):
            continue
        if cells[1] not in SEVERITIES:
            problems.append("README.md: {} has unknown severity `{}`.".format(cells[0], cells[1]))
        if cells[0] in index:
            problems.append("README.md: {} is indexed twice.".format(cells[0]))
        index[cells[0]] = cells[1]

    cards = {}
    findings = report / "findings"
    for path in sorted(findings.glob("*.md")) if findings.is_dir() else []:
        heading = next((line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("# ")), "")
        match = re.match(r"#\s+(F\d+)\s+(\w+)", heading)
        if not match or match.group(1) != path.stem:
            problems.append("findings/{}: heading must start with `# {} <Severity>`.".format(path.name, path.stem))
            continue
        cards[match.group(1)] = match.group(2)
    for fid, severity in index.items():
        if fid not in cards:
            problems.append("README.md: {} is indexed but findings/{}.md is missing.".format(fid, fid))
        elif cards[fid] != severity:
            problems.append("findings/{}.md: severity `{}` differs from the index (`{}`).".format(fid, cards[fid], severity))
    for fid in cards:
        if fid not in index:
            problems.append("findings/{}.md: card is missing from the README index.".format(fid))

    counts = re.search(
        r"Findings count:\s*`?Blocker\s*(\d+)\s*\|\s*Major\s*(\d+)\s*\|\s*Minor\s*(\d+)\s*\|\s*Question\s*(\d+)", readme
    )
    if not counts:
        problems.append("README.md: Findings count line is missing or malformed.")
    else:
        for severity, stated in zip(SEVERITIES, counts.groups()):
            actual = sum(1 for value in index.values() if value == severity)
            if int(stated) != actual:
                problems.append("README.md: Findings count says {} {}, the index has {}.".format(severity, stated, actual))
    expected = expected_recommendation(set(index.values()), incomplete)
    if field(readme, "Recommendation") != expected:
        problems.append(
            "README.md: Recommendation is `{}`, the mapping gives `{}`.".format(field(readme, "Recommendation"), expected)
        )

    coverage_rows = 0
    coverage = ledger_parts(report, "coverage")
    if not coverage:
        problems.append("coverage.md (or coverage/*.md) is missing.")
    for path in coverage:
        name = path.relative_to(report)
        for cells in table_rows(path.read_text(encoding="utf-8")):
            coverage_rows += 1
            status = next((STATUS.match(cell) for cell in cells if STATUS.match(cell)), None)
            if status is None:
                problems.append("{}: row `{}` has no recognized status.".format(name, cells[0]))
            elif status.group(1) and status.group(1) not in index:
                problems.append("{}: row `{}` points to {}, which is not indexed.".format(name, cells[0], status.group(1)))
            elif (status.group(2) or "").lower() == "not covered" and not incomplete:
                problems.append("{}: row `{}` is Not covered, so Completion must be Incomplete.".format(name, cells[0]))
    if coverage and coverage_rows == 0:
        problems.append("The coverage ledger has no rows.")

    inventory = ledger_parts(report, "files")
    if not inventory:
        problems.append("files.md (or files/*.md) is missing.")
    for path in inventory:
        name = path.relative_to(report)
        for cells in table_rows(path.read_text(encoding="utf-8")):
            threshold = next((THRESHOLD.match(cell).group(1).lower() for cell in cells if THRESHOLD.match(cell)), None)
            if threshold is None:
                problems.append("{}: row `{}` has no recognized threshold.".format(name, cells[0]))
            elif threshold in ("crossed 350", "already over 350"):
                refs = re.findall(r"\bF\d+\b", cells[-1])
                if not refs and not re.search(r"waive|exclude", cells[-1], re.IGNORECASE):
                    problems.append("{}: `{}` is {} but maps to no finding or waiver.".format(name, cells[0], threshold))
                for ref in refs:
                    if ref not in index:
                        problems.append("{}: `{}` points to {}, which is not indexed.".format(name, cells[0], ref))
    return problems, len(index), coverage_rows


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    report = Path(argv[1])
    if not (report / "README.md").is_file():
        print("{} is not a Thermobot report directory: README.md is missing.".format(report))
        return 2
    problems, findings, rows = check(report)
    if problems:
        print("\n".join(problems))
        return 1
    print("OK: {} findings, {} coverage rows.".format(findings, rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
