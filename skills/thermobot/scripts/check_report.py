#!/usr/bin/env python3
"""Check that a Thermobot report directory is internally consistent.

Usage: python3 check_report.py <report-dir>

Confirms that the README contract, findings index, finding cards, severity
counts, recommendation, and ledgers agree with one another. It cannot judge
whether the review itself was complete; that stays with the reviewer.
Prints OK and exits 0 when consistent, prints one problem per line and exits 1
otherwise, and exits 2 when the path is not a report directory.
"""

import re
import sys
from pathlib import Path

SEVERITIES = ("Blocker", "Major", "Minor", "Question")
FILE_CLASSES = frozenset(("source", "test", "config", "docs", "generated", "vendored"))
REQUIRED_README_SECTIONS = ("Report Contract", "Scope", "Review Snapshot", "Findings Index", "Ledgers")
SNAPSHOT_FIELDS = ("Reviewed HEAD", "Input fingerprint", "Snapshot consistency")
COMMON_CARD_FIELDS = ("Surface", "Look here first", "Confidence", "Impact", "Structural failure", "Evidence")
ALL_CARD_LABELS = COMMON_CARD_FIELDS + ("Simpler path", "Needed context")

FENCE_OPEN = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
SEPARATOR = re.compile(r"^\|(\s*:?-+:?\s*\|)+$")
REPORT_ID_RE = re.compile(r"^tb-\d{8}-[a-z0-9]{4,}$")
COMPLETION_RE = re.compile(r"^(Complete|Incomplete)(?:\b|$)")
COUNTS_RE = re.compile(r"^Blocker\s*(\d+)\s*\|\s*Major\s*(\d+)\s*\|\s*Minor\s*(\d+)\s*\|\s*Question\s*(\d+)$")
CARD_HEADING_RE = re.compile(r"^#\s+(F\d+)\s+(?:`(\w+)`|\[(\w+)\]|(\w+))(?:\s|$|[-\u2013\u2014:])")

COV_FINDING_RE = re.compile(r"^(?i:Finding)\s+(F\d+(?:\s*,\s*F\d+)*)$")
COV_MERGED_RE = re.compile(r"^(?i:Merged into)\s+(F\d+)$")
COV_REVIEWED_RE = re.compile(r"^Reviewed\s*[-\u2013\u2014]\s*no issue$", re.IGNORECASE)
COV_NOT_RELEVANT_RE = re.compile(r"^Not review-relevant$", re.IGNORECASE)
COV_NOT_COVERED_RE = re.compile(r"^Not covered$", re.IGNORECASE)
COV_SOURCE_REF_RE = re.compile(r"(?i:discovered from)\s+(F\d+(?:\s*,\s*F\d+)*)\b")

THRESHOLD_RE = re.compile(r"^(under 350|crossed 350|already over 350|excluded)$", re.IGNORECASE)
FILE_FINDING_ANY_RE = re.compile(r"\b(?i:Finding|Merged into)\s+(F\d+(?:\s*,\s*F\d+)*)\b")
FILE_FINDING_SEG_RE = re.compile(r"^(?i:Finding|Merged into)\s+(F\d+(?:\s*,\s*F\d+)*)(?:\b|$)")
FILE_WAIVED_RE = re.compile(r"^waived\s*[-\u2013\u2014:]\s*\S", re.IGNORECASE)
FILE_EXCLUDED_RE = re.compile(r"^excluded\s*[-\u2013\u2014:]\s*\S", re.IGNORECASE)
FILE_REVIEWED_RE = re.compile(r"^reviewed\s*[-\u2013\u2014]\s*no issue\b", re.IGNORECASE)
FILE_NOT_COVERED_RE = re.compile(r"^not covered(?:\s*[-\u2013\u2014:]|\s*$)", re.IGNORECASE)
FILE_NOT_COVERED_REASON_RE = re.compile(r"^not covered\s*[-\u2013\u2014:]\s*\S", re.IGNORECASE)

TEMPLATE_ANGLE_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_])<(?:random-id|report-dir|skill-folder|sha|hash|digest|commit-sha"
    r"|reason|blocker(?:\s+and\s+next\s+step)?|diagnosis|decision)>"
)
MD_LINK_RE = re.compile(r"\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\(([^)]+)\)")
_UPPER_HEAD_RE = r"(?:(?i:and|or)\s+)?F\d+(?:(?:\s*(?:/|&|(?i:\band\b|\bor\b))\s*|\s+)[Ff]\d+)*"
_ANY_HEAD_RE = r"(?:(?i:and|or)\s+)?[Ff]\d+(?:(?:\s*(?:/|&|(?i:\band\b|\bor\b))\s*|\s+)[Ff]\d+)*"
_NEXT_DESC_DELIM_RE = r"(?:\s+[-\u2013\u2014]+(?:\s|$)|\u2014(?!\s*[Ff]\d+\b)|\s*[:(])"
MUST_REVIEW_NEXT_ENTRY_RE = re.compile(
    r"^\s*(?:"
    + _UPPER_HEAD_RE
    + r"(?:\s*,\s*"
    + _ANY_HEAD_RE
    + r")*(?:\s*$|\s*;|"
    + _NEXT_DESC_DELIM_RE
    + r")|"
    + _ANY_HEAD_RE
    + r"(?:\s*,\s*"
    + _ANY_HEAD_RE
    + r")*"
    + _NEXT_DESC_DELIM_RE
    + r")"
)

README_PLACEHOLDER_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9_])<(?:random-id|report-dir|skill-folder|sha|hash|digest|commit-sha)>"),
    re.compile(r"tb-YYYYMMDD-<[^>]+>", re.IGNORECASE),
    re.compile(
        r"\[(?:absolute(?:\s+or\s+repository-relative)?\s+path\]"
        r"|Blocker,\s*Major,\s*Minor,\s*or\s*Question\]"
        r"|Complete within reviewed scope\s*\||Block\s*\|\s*Changes requested"
        r"|HEAD\s*\|\s*(?:merge-base|commit SHA)"
        r"|None\s*\|\s*settled intent|None found\s*\||None\s*\|\s*inferred scope"
        r"|one sentence|top 1-3 F#|high\s*(?:\||,)\s*medium|short phrase,"
        r"|If no findings exist,|candidate count by status\]"
        r"|file count;\s*files (?:over|>=) 350 lines\]"
        r"|read-only command|working tree\s*\||one-line risk)",
        re.IGNORECASE,
    ),
)

COVERAGE_PLACEHOLDER_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9_])<(?:reason|blocker(?:\s+and\s+next\s+step)?|random-id)>"),
    re.compile(
        r"\[(?:area or candidate\]|initial inventory,\s*discovered from F#"
        r"|file or entry-point links\]|Finding F#,"
        r"|concrete structural conclusion,|short conclusion,\s*or blocker)",
        re.IGNORECASE,
    ),
)

FILES_PLACEHOLDER_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9_])<(?:reason|blocker(?:\s+and\s+next\s+step)?|diagnosis|decision)>"),
    re.compile(
        r"\[(?:source,\s*test,\s*config,"
        r"|under 350,\s*crossed 350,|diagnosis;\s*Finding F#)",
        re.IGNORECASE,
    ),
)

CARD_PLACEHOLDER_PATTERNS = (
    re.compile(r"\[Short title\]", re.IGNORECASE),
    re.compile(r"\[Blocker,\s*Major,\s*Minor,\s*or\s*Question\]", re.IGNORECASE),
    re.compile(r"/abs/path/(?:file|other)\.ts\b"),
    re.compile(
        r"\[(?:file,\s*module,\s*component,\s*API,|high,\s*medium,\s*or\s*low"
        r"|one or two sentences:|simpler model,\s*canonical owner,"
        r"|what the reviewed change does instead|one to three sentences:"
        r"|the intent,\s*ownership,\s*or\s*constraint|file:line pointers,)",
        re.IGNORECASE,
    ),
)

COVERAGE_COLUMN_SPECS = (
    ("area", ("area", "candidate"), 0),
    ("source", ("source",), 1),
    ("entry", ("entry",), 2),
    ("status", ("status",), 3),
    ("evidence", ("evidence", "next step"), 4),
)

FILES_COLUMN_SPECS = (
    ("path", ("path", "file"), 0),
    ("cls", ("class",), 1),
    ("baseline", ("baseline", "base"), 2),
    ("current", ("current", "now"), 3),
    ("threshold", ("threshold",), 4),
    ("decision", ("boundary", "decision"), 5),
)


def _card_label_re(labels_pattern, capture_rest=False):
    tail = r"(?:\s+(.*)|\s*)$" if capture_rest else r"(?:\s|$)"
    return re.compile(
        r"^\s*(?:(?:#{2,6}\s+)(?:\*\*)?(?:" + labels_pattern + r")(?:\*\*)?:?"
        r"|(?:[-*]\s+)?(?:\*\*)?(?:" + labels_pattern + r")(?:\*\*)?:(?:\*\*)?)" + tail,
        re.IGNORECASE,
    )


ANY_CARD_LABEL_RE = _card_label_re("|".join(re.escape(lbl) for lbl in ALL_CARD_LABELS))


def plain(text):
    """Strip Markdown links, backticks, and emphasis so cells compare as plain tokens."""
    text = MD_LINK_RE.sub(r"\1", text)
    return text.replace("`", "").replace("*", "").strip()


def iter_fence_lines(text):
    """Yield `(line, in_fence)` for each line, skipping fence delimiter lines themselves."""
    fence_char, fence_len = None, 0
    for line in text.splitlines():
        if fence_char is None:
            match = FENCE_OPEN.match(line)
            if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
                fence_char, fence_len = match.group(1)[0], len(match.group(1))
                continue
            yield line, False
        elif re.match(r"^\s*" + re.escape(fence_char) + "{" + str(fence_len) + r",}\s*$", line):
            fence_char, fence_len = None, 0
        else:
            yield line, True


def strip_fenced_blocks(text):
    """Remove fenced code blocks (backtick or tilde) from Markdown text."""
    if "```" not in text and "~~~" not in text:
        return text
    return "\n".join(line for line, in_fence in iter_fence_lines(text) if not in_fence)


def extract_section(clean_text, section_name):
    """Return lines belonging to a `## <section_name>` section up to the next level 1-2 heading."""
    target, out, in_section = section_name.strip().lower(), [], False
    for line in clean_text.splitlines():
        heading = re.match(r"^(#{1,2})\s+(.+?)\s*$", line)
        if heading:
            if in_section:
                break
            if len(heading.group(1)) == 2 and heading.group(2).rstrip("#").strip().lower() == target:
                in_section = True
            continue
        if in_section:
            out.append(line)
    return "\n".join(out)


def split_table_line(line):
    """Split a Markdown pipe row while preserving empty trailing cells and escaped pipes."""
    s = line.strip().replace("\\|", "\0")
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [cell.replace("\0", "|").strip() for cell in s.split("|")]


def parse_tables(text, section=None):
    """Return [(headers, raw_rows), ...] for Markdown tables, ignoring fenced code blocks."""
    clean = strip_fenced_blocks(text)
    body = extract_section(clean, section) if section is not None else clean
    tables, lines, i = [], body.splitlines(), 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and i + 1 < len(lines) and SEPARATOR.match(lines[i + 1].strip()):
            headers = [plain(c) for c in split_table_line(line)]
            rows = []
            i += 2
            while i < len(lines):
                row_line = lines[i].strip()
                if not row_line.startswith("|") or SEPARATOR.match(row_line):
                    break
                rows.append(split_table_line(row_line))
                i += 1
            tables.append((headers, rows))
        else:
            i += 1
    return tables


def table_rows(text, section=None):
    """Return the body rows of Markdown tables in text (optionally scoped to a `##` section)."""
    return [[plain(cell) for cell in row] for _, rows in parse_tables(text, section=section) for row in rows]


def field(text, name):
    """Return the value of a `- Name: value` bullet outside fenced blocks, without mid-line hijack."""
    clean = strip_fenced_blocks(text)
    pattern = r"^\s*-\s*(?:\*\*)?" + re.escape(name) + r"(?:\*\*)?:(?:\*\*)?\s*(.+)$"
    match = re.search(pattern, clean, re.MULTILINE)
    if not match:
        return ""
    val = match.group(1).strip()
    whole_ticked = re.fullmatch(r"`([^`]+)`", val)
    return whole_ticked.group(1).strip() if whole_ticked else plain(val)


def normalize_link_target(target):
    cleaned = target.strip().split("#", 1)[0].strip()
    return cleaned[2:] if cleaned.startswith("./") else cleaned


def resolve_columns(headers, specs):
    """Resolve logical column indices from header names, falling back to positional indices."""
    lowered = [h.lower() for h in headers]
    resolved, used = {}, set()
    for name, keywords, _ in specs:
        idx = next((i for i, h in enumerate(lowered) if i not in used and any(kw in h for kw in keywords)), None)
        if idx is not None:
            resolved[name] = idx
            used.add(idx)
    for name, _, default_idx in specs:
        if name not in resolved:
            idx = default_idx if default_idx not in used else next((i for i in range(len(headers)) if i not in used), default_idx)
            resolved[name] = idx
            used.add(idx)
    return resolved


def is_placeholder_value(val):
    if not val or re.fullmatch(r"\[[^\[\]]+\]", val) or TEMPLATE_ANGLE_TOKEN_RE.search(val):
        return True
    return val.lower() in ("tbd", "todo", "xxx")


def _closes_angle_group(value, start):
    """Return True if `<` at `start` starts a balanced generic/tag closed by `>` before an entry boundary."""
    n = len(value)
    if start + 1 >= n or not re.match(r"[A-Za-z_$\[({]", value[start + 1]):
        return False
    angle, paren, bracket, brace = 1, 0, 0, 0
    for j in range(start + 1, n):
        ch = value[j]
        if ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
        elif ch == "[":
            bracket += 1
        elif ch == "]":
            bracket -= 1
        elif ch == "{":
            brace += 1
        elif ch == "}":
            brace -= 1
        if paren < 0 or bracket < 0 or brace < 0:
            return False

        if paren == 0 and bracket == 0 and brace == 0:
            if ch == ";" or ch == "\u2014":
                return False
            if ch == "," and MUST_REVIEW_NEXT_ENTRY_RE.match(value[j + 1 :]):
                return False
            if ch in ("-", "\u2013") and value[j - 1].isspace():
                k = j
                while k < n and value[k] in ("-", "\u2013", "\u2014"):
                    k += 1
                if k == n or value[k].isspace():
                    return False

        if ch == "<" and j + 1 < n and re.match(r"[A-Za-z_$\[({]", value[j + 1]):
            angle += 1
        elif ch == ">" and value[j - 1] not in ("=", "-") and not (j + 1 < n and value[j + 1] == "="):
            angle -= 1
            if angle == 0:
                return paren == 0 and bracket == 0 and brace == 0
    return False


def parse_must_review_entries(value):
    """Split a Must-review now value into `(entry, head_tokens)` pairs, preserving nested/prose commas."""
    entries, buf = [], []
    paren = angle = bracket = brace = 0
    in_desc = False
    n = len(value)
    for i, ch in enumerate(value):
        if ch == "(":
            paren += 1
        elif ch == ")":
            paren = max(0, paren - 1)
        elif ch == "[":
            bracket += 1
        elif ch == "]":
            bracket = max(0, bracket - 1)
        elif ch == "{":
            brace += 1
        elif ch == "}":
            brace = max(0, brace - 1)
        elif ch == "<" and _closes_angle_group(value, i):
            angle += 1
        elif ch == ">" and angle > 0 and not (i > 0 and value[i - 1] in ("=", "-")) and not (i + 1 < n and value[i + 1] == "="):
            angle -= 1

        top_level = paren == 0 and angle == 0 and bracket == 0 and brace == 0
        if top_level and ch == ";":
            chunk = "".join(buf).strip()
            if chunk:
                entries.append(chunk)
            buf, in_desc = [], False
            continue
        if top_level and ch == "," and (not in_desc or MUST_REVIEW_NEXT_ENTRY_RE.match(value[i + 1 :])):
            chunk = "".join(buf).strip()
            if chunk:
                entries.append(chunk)
            buf, in_desc = [], False
            continue
        if top_level and (
            ch == ":"
            or (ch in ("-", "\u2013", "\u2014") and i > 0 and value[i - 1].isspace())
            or (ch == "\u2014" and not re.match(r"\s*[Ff]\d+\b", value[i + 1 :]))
        ):
            in_desc = True
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        entries.append(tail)

    parsed = []
    for raw_entry in entries:
        cleaned = re.sub(r"^(?:and|or)\s+", "", raw_entry, flags=re.IGNORECASE).strip()
        head = re.split(_NEXT_DESC_DELIM_RE, cleaned, maxsplit=1)[0].strip()
        tokens = [t for t in re.split(r"(?:\s*(?:/|&|\band\b|\bor\b)\s*|\s+)", head, flags=re.IGNORECASE) if t]
        parsed.append((cleaned, tokens))
    return parsed


def find_placeholder_matches(clean_text, patterns):
    found = []
    for pattern in patterns:
        for match in pattern.finditer(clean_text):
            if match.group(0) not in found:
                found.append(match.group(0))
    return found


def ledger_parts(report, name):
    """A ledger is `<name>.md`, or `<name>/*.md` when it was split by area."""
    parts = [report / (name + ".md")] if (report / (name + ".md")).is_file() else []
    if (report / name).is_dir():
        parts += sorted((report / name).glob("*.md"))
    return parts


def iter_ledger_rows(report, ledger_name, specs, label, problems, placeholder_patterns=()):
    """Yield `(rel_path, row_dict)` across a ledger's file(s), reporting missing/empty/malformed tables."""
    parts = ledger_parts(report, ledger_name)
    if not parts:
        problems.append("{0}.md (or {0}/*.md) is missing.".format(ledger_name))
        return
    min_headers = len(specs)
    for path in parts:
        name = path.relative_to(report).as_posix()
        raw_text = path.read_text(encoding="utf-8")
        clean_text = strip_fenced_blocks(raw_text)
        for token in find_placeholder_matches(clean_text, placeholder_patterns):
            problems.append("{}: contains unfilled template placeholder `{}`.".format(name, token))
        file_rows = 0
        for headers, raw_rows in parse_tables(clean_text):
            if len(headers) < min_headers:
                problems.append("{}: table must have at least {} columns.".format(name, min_headers))
                continue
            cols = resolve_columns(headers, specs)
            min_cols = max(cols.values()) + 1
            for raw_cells in raw_rows:
                file_rows += 1
                cells = [plain(c) for c in raw_cells]
                if len(cells) < min_cols:
                    problems.append("{}: row `{}` has fewer than {} columns.".format(name, cells[0] if cells else "", min_cols))
                    continue
                if len(cells) > len(headers):
                    problems.append(
                        "{}: row `{}` has {} columns, expected {} (escape literal `|` as `\\|`).".format(
                            name, cells[0] if cells else "", len(cells), len(headers)
                        )
                    )
                    continue
                yield name, {key: cells[idx] for key, idx in cols.items()}
        if file_rows == 0:
            problems.append("{}: {} has no rows.".format(name, label))


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


def card_field_has_content(raw_card, label):
    """Return True if a finding card defines `label` with non-empty content."""
    label_re = _card_label_re(re.escape(label), capture_rest=True)
    collecting = False
    for line, in_fence in iter_fence_lines(raw_card):
        if in_fence:
            if collecting and line.strip():
                return True
            continue
        if collecting:
            if re.match(r"^\s*#{1,6}\s+", line) or ANY_CARD_LABEL_RE.match(line):
                return False
            stripped = re.sub(r"^\s*[-*]\s*", "", line).strip()
            if stripped and stripped != "``":
                return True
            continue
        match = label_re.match(line)
        if match:
            inline = (match.group(1) or "").strip()
            if inline and inline != "``":
                return True
            collecting = True
    return False


def check_readme(report, readme_clean, problems):
    """Validate README.md contract fields, index table, counts, recommendation, and links."""
    headings = {m.group(1).rstrip("#").strip().lower() for m in re.finditer(r"^##\s+(.+?)\s*$", readme_clean, re.MULTILINE)}
    for section in REQUIRED_README_SECTIONS:
        if section.lower() not in headings:
            problems.append("README.md: missing required section `## {}`.".format(section))

    if field(readme_clean, "Report type") != "thermobot":
        problems.append("README.md: Report type is not `thermobot`.")

    report_id = field(readme_clean, "Report ID")
    if not REPORT_ID_RE.fullmatch(report_id):
        problems.append("README.md: Report ID `{}` must match `tb-YYYYMMDD-<random-id>`.".format(report_id))

    review_date = field(readme_clean, "Review date")
    if review_date:
        if "YYYY-MM-DD" in review_date:
            problems.append("README.md: Review date contains unfilled template placeholder `YYYY-MM-DD`.")
        elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", review_date):
            problems.append("README.md: Review date `{}` must match `YYYY-MM-DD`.".format(review_date))

    report_dir = field(readme_clean, "Report directory")
    if report_dir and "YYYY-MM-DD" in report_dir:
        problems.append("README.md: Report directory contains unfilled template placeholder `YYYY-MM-DD`.")

    for snap_field in SNAPSHOT_FIELDS:
        if is_placeholder_value(field(readme_clean, snap_field)):
            problems.append("README.md: {} is missing or an unfilled placeholder.".format(snap_field))

    scope_reviewed = field(readme_clean, "Scope reviewed")
    if re.match(r"^post-fix delta\b", scope_reviewed, re.IGNORECASE):
        parent_report = field(readme_clean, "Parent report")
        if not REPORT_ID_RE.fullmatch(parent_report):
            problems.append(
                "README.md: Parent report `{}` is required for post-fix delta reports and must match `tb-YYYYMMDD-<random-id>`.".format(
                    parent_report
                )
            )
        if is_placeholder_value(field(readme_clean, "Inherited settlements")):
            problems.append(
                "README.md: Inherited settlements is required for post-fix delta reports and cannot be empty or a placeholder."
            )

    completion = field(readme_clean, "Completion")
    if not COMPLETION_RE.match(completion):
        problems.append("README.md: Completion must start with `Complete` or `Incomplete`.")
    incomplete = completion.startswith("Incomplete")

    index = {}
    for headers, raw_rows in parse_tables(readme_clean, section="Findings Index"):
        for raw_cells in raw_rows:
            cells = [plain(c) for c in raw_cells]
            if len(cells) < 2:
                problems.append("README.md: Findings Index row `{}` has fewer than 2 columns.".format(" | ".join(cells)))
                continue
            if len(cells) > len(headers):
                problems.append(
                    "README.md: Findings Index row `{}` has {} columns, expected {} (escape literal `|` as `\\|`).".format(
                        cells[0], len(cells), len(headers)
                    )
                )
                continue
            fid, sev = cells[0], cells[1]
            if not re.fullmatch(r"F\d+", fid):
                problems.append("README.md: Findings Index has malformed finding ID `{}`.".format(fid))
                continue
            link_match = re.search(r"\[[^\]]*\]\(([^)]+)\)", raw_cells[0])
            if link_match:
                target = normalize_link_target(link_match.group(1))
                expected_target = "findings/{}.md".format(fid)
                if target != expected_target:
                    problems.append("README.md: {} links to `{}`, expected `{}`.".format(fid, target, expected_target))
            if sev not in SEVERITIES:
                problems.append("README.md: {} has unknown severity `{}`.".format(fid, sev))
            if fid in index:
                problems.append("README.md: {} is indexed twice.".format(fid))
            else:
                index[fid] = sev

    if index:
        nums = sorted(int(fid[1:]) for fid in index)
        if nums != list(range(1, len(nums) + 1)):
            problems.append(
                "README.md: Findings Index IDs must be consecutive (F1..F{}), got {}.".format(
                    len(nums), ", ".join("F{}".format(n) for n in nums)
                )
            )

    must_review = field(readme_clean, "Must-review now")
    if is_placeholder_value(must_review):
        problems.append("README.md: Must-review now is missing or an unfilled placeholder.")
    elif not re.fullmatch(r"none(?:\s*\([^)]*\))?\.?", must_review, re.IGNORECASE):
        parsed_entries = parse_must_review_entries(must_review)
        if not parsed_entries:
            problems.append("README.md: Must-review now must list finding IDs or `None`.")
        for entry, tokens in parsed_entries:
            if not tokens:
                problems.append(
                    "README.md: Must-review now entry `{}` must start with a finding ID (such as `F1`) or be `None`.".format(
                        entry
                    )
                )
                continue
            for token in tokens:
                if not re.fullmatch(r"[Ff]\d+", token):
                    problems.append(
                        "README.md: Must-review now entry `{}` contains non-finding token `{}` (expected finding IDs like `F1` or `None`).".format(
                            entry, token
                        )
                    )
                    continue
                if not token.startswith("F"):
                    problems.append(
                        "README.md: Must-review now has malformed lowercase finding ID `{}` (use `{}`).".format(
                            token, token.upper()
                        )
                    )
                if token.upper() not in index:
                    problems.append("README.md: Must-review now references {}, which is not indexed.".format(token))

    counts = COUNTS_RE.match(field(readme_clean, "Findings count"))
    if not counts:
        problems.append("README.md: Findings count line is missing or malformed.")
    else:
        for severity, stated in zip(SEVERITIES, counts.groups()):
            actual = sum(1 for value in index.values() if value == severity)
            if int(stated) != actual:
                problems.append("README.md: Findings count says {} {}, the index has {}.".format(severity, stated, actual))

    expected = expected_recommendation({s for s in index.values() if s in SEVERITIES}, incomplete)
    rec = field(readme_clean, "Recommendation")
    if rec != expected:
        problems.append("README.md: Recommendation is `{}`, the mapping gives `{}`.".format(rec, expected))

    readme_links = {normalize_link_target(m.group(2)) for m in MD_LINK_RE.finditer(readme_clean)}
    for ledger_name in ("coverage", "files"):
        ledger_dir = report / ledger_name
        if ledger_dir.is_dir():
            for part in sorted(ledger_dir.glob("*.md")):
                rel = part.relative_to(report).as_posix()
                if rel not in readme_links:
                    problems.append("README.md: split ledger `{}` is not linked from README.md.".format(rel))

    for token in find_placeholder_matches(readme_clean, README_PLACEHOLDER_PATTERNS):
        problems.append("README.md: contains unfilled template placeholder `{}`.".format(token))

    return index, incomplete


def check_cards(report, index, problems):
    """Validate findings/F<n>.md cards against the README index and card contract."""
    cards = {}
    findings_dir = report / "findings"
    for path in sorted(findings_dir.glob("*.md")) if findings_dir.is_dir() else []:
        raw_card = path.read_text(encoding="utf-8")
        clean_card = strip_fenced_blocks(raw_card)
        heading = next((line.strip() for line in clean_card.splitlines() if line.lstrip().startswith("# ")), "")
        match = CARD_HEADING_RE.match(heading)
        if not match or match.group(1) != path.stem:
            problems.append("findings/{}: heading must start with `# {} <Severity>`.".format(path.name, path.stem))
            severity = None
        else:
            severity = match.group(2) or match.group(3) or match.group(4)
            if severity not in SEVERITIES:
                problems.append("findings/{}: unknown severity `{}`.".format(path.name, severity))
            cards[match.group(1)] = severity

        required = list(COMMON_CARD_FIELDS)
        if severity == "Question":
            required.append("Needed context")
        elif severity in ("Blocker", "Major", "Minor"):
            required.append("Simpler path")

        for label in required:
            if not card_field_has_content(raw_card, label):
                problems.append("findings/{}: missing or empty `{}` section.".format(path.name, label))
        for token in find_placeholder_matches(clean_card, CARD_PLACEHOLDER_PATTERNS):
            problems.append("findings/{}: contains unfilled template placeholder `{}`.".format(path.name, token))

    for fid, severity in index.items():
        if fid not in cards:
            problems.append("README.md: {} is indexed but findings/{}.md is missing.".format(fid, fid))
        elif cards[fid] != severity:
            problems.append("findings/{}.md: severity `{}` differs from the index (`{}`).".format(fid, cards[fid], severity))
    for fid in cards:
        if fid not in index:
            problems.append("findings/{}.md: card is missing from the README index.".format(fid))


def check_coverage(report, index, incomplete, problems):
    """Validate coverage.md / coverage/*.md rows and reverse finding coverage."""
    coverage_rows, covered_findings = 0, set()
    has_parts = bool(ledger_parts(report, "coverage"))

    for name, row in iter_ledger_rows(
        report, "coverage", COVERAGE_COLUMN_SPECS, "coverage ledger", problems, COVERAGE_PLACEHOLDER_PATTERNS
    ):
        coverage_rows += 1
        area, source, status, evidence = row["area"], row["source"], row["status"], row["evidence"]

        for src_match in COV_SOURCE_REF_RE.finditer(source):
            for fid in (f.strip() for f in src_match.group(1).split(",")):
                if fid not in index:
                    problems.append("{}: row `{}` source references {}, which is not indexed.".format(name, area, fid))

        finding_match = COV_FINDING_RE.match(status) or COV_MERGED_RE.match(status)
        if finding_match:
            for fid in (f.strip() for f in finding_match.group(1).split(",")):
                if fid not in index:
                    problems.append("{}: row `{}` points to {}, which is not indexed.".format(name, area, fid))
                else:
                    covered_findings.add(fid)
        elif COV_REVIEWED_RE.match(status):
            if not evidence:
                problems.append("{}: row `{}` is Reviewed - no issue but Evidence / next step is empty.".format(name, area))
        elif COV_NOT_RELEVANT_RE.match(status):
            pass
        elif COV_NOT_COVERED_RE.match(status):
            if not incomplete:
                problems.append("{}: row `{}` is Not covered, so Completion must be Incomplete.".format(name, area))
            if not evidence:
                problems.append("{}: row `{}` is Not covered but Evidence / next step is empty.".format(name, area))
        else:
            problems.append("{}: row `{}` has no recognized status (`{}`).".format(name, area, status))

    if has_parts:
        for fid in index:
            if fid not in covered_findings:
                problems.append("README.md: {} is indexed but not referenced in the coverage ledger.".format(fid))
    return coverage_rows


def check_files(report, index, incomplete, problems):
    """Validate files.md / files/*.md classes, line-count thresholds, and decisions."""
    for name, row in iter_ledger_rows(
        report, "files", FILES_COLUMN_SPECS, "file inventory", problems, FILES_PLACEHOLDER_PATTERNS
    ):
        file_path, file_class, decision = row["path"], row["cls"], row["decision"]
        baseline_raw, current_raw, threshold_raw = row["baseline"], row["current"], row["threshold"]

        if file_path.lower() == "[path]":
            problems.append("{}: contains unfilled template placeholder `[path]`.".format(name))

        if file_class.lower() not in FILE_CLASSES:
            problems.append("{}: `{}` has unrecognized class `{}`.".format(name, file_path, file_class))

        for col_label, raw_count in (("Baseline lines", baseline_raw), ("Current lines", current_raw)):
            if re.fullmatch(r"\[[^\[\]]+\]", raw_count):
                problems.append("{}: `{}` has unfilled placeholder `{}` in {}.".format(name, file_path, raw_count, col_label))

        threshold_match = THRESHOLD_RE.match(threshold_raw)
        threshold = threshold_match.group(1).lower() if threshold_match else None
        if threshold is None:
            problems.append("{}: `{}` has no recognized threshold (`{}`).".format(name, file_path, threshold_raw))

        if threshold and threshold != "excluded" and re.fullmatch(r"\d+", current_raw):
            current = int(current_raw)
            if re.fullmatch(r"\d+", baseline_raw):
                baseline = int(baseline_raw)
                consistent = (
                    (threshold == "under 350" and current < 350)
                    or (threshold == "crossed 350" and baseline < 350 and current >= 350)
                    or (threshold == "already over 350" and baseline >= 350 and current >= 350)
                )
            else:
                consistent = (
                    (threshold == "under 350" and current < 350)
                    or (threshold in ("crossed 350", "already over 350") and current >= 350)
                )
            if not consistent:
                problems.append(
                    "{}: `{}` has lines {} -> {}, which conflicts with threshold `{}`.".format(
                        name, file_path, baseline_raw, current, threshold
                    )
                )

        for ref_match in FILE_FINDING_ANY_RE.finditer(decision):
            for fid in (f.strip() for f in ref_match.group(1).split(",")):
                if fid not in index:
                    problems.append("{}: `{}` points to {}, which is not indexed.".format(name, file_path, fid))

        segments = [seg.strip() for seg in decision.split(";") if seg.strip()]
        has_finding = any(FILE_FINDING_SEG_RE.match(seg) for seg in segments)
        has_waiver = any(FILE_WAIVED_RE.match(seg) for seg in segments)
        has_excluded = any(FILE_EXCLUDED_RE.match(seg) for seg in segments)
        has_reviewed_ok = any(FILE_REVIEWED_RE.match(seg) for seg in segments)
        has_not_covered = any(FILE_NOT_COVERED_RE.match(seg) for seg in segments)

        if has_not_covered:
            if not incomplete:
                problems.append("{}: `{}` is not covered, so Completion must be Incomplete.".format(name, file_path))
            if not any(FILE_NOT_COVERED_REASON_RE.match(seg) for seg in segments):
                problems.append(
                    "{}: `{}` is not covered and must include a blocker or reason (`not covered - <reason>`).".format(
                        name, file_path
                    )
                )

        if threshold in ("crossed 350", "already over 350") and not (has_finding or has_waiver or has_not_covered):
            problems.append("{}: `{}` is {} but maps to no finding or waiver (or not-covered note).".format(name, file_path, threshold))
        elif threshold == "excluded":
            if has_reviewed_ok:
                problems.append("{}: `{}` is excluded and cannot use `reviewed - no issue`.".format(name, file_path))
            elif not (has_excluded or has_finding or has_not_covered):
                problems.append("{}: `{}` is excluded and needs an `excluded - <reason>`, finding, or not-covered decision.".format(name, file_path))
        elif threshold == "under 350" and not (has_reviewed_ok or has_finding or has_waiver or has_not_covered):
            problems.append("{}: `{}` is under 350 and has no recognized decision.".format(name, file_path))


def check(report):
    problems = []
    readme_clean = strip_fenced_blocks((report / "README.md").read_text(encoding="utf-8"))
    index, incomplete = check_readme(report, readme_clean, problems)
    check_cards(report, index, problems)
    coverage_rows = check_coverage(report, index, incomplete, problems)
    check_files(report, index, incomplete, problems)
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
