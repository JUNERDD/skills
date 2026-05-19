#!/usr/bin/env python3
"""Extract items from a react-wide-api-review Markdown report.

This helper builds an intake inventory for receiving-react-wide-api-review. It is
heuristic and intended to catch missing dispositions, not to validate Markdown.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional, Sequence


@dataclass
class Item:
    kind: str
    id: str
    status: str
    line: int
    text: str


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def extract(text: str) -> List[Item]:
    items: List[Item] = []

    # Finding cards: ### F1 Block - title
    for match in re.finditer(r"^###\s+(F\d+)\s+(Block|Discuss|Watch)\s*-\s*(.+)$", text, flags=re.M):
        items.append(Item("finding-card", match.group(1), match.group(2), line_number(text, match.start()), match.group(3).strip()))

    # Index rows: | `F1` | `Block` | ...
    for match in re.finditer(r"^\|\s*`?(F\d+)`?\s*\|\s*`?(Block|Discuss|Watch)`?\s*\|(.+)$", text, flags=re.M):
        items.append(Item("finding-index", match.group(1), match.group(2), line_number(text, match.start()), match.group(0).strip()))

    # Intentional exceptions: - `I1` title
    for match in re.finditer(r"^[-*]\s+`?(I\d+)`?\s+(.+)$", text, flags=re.M):
        items.append(Item("intentional-exception", match.group(1), "Intentional Exception", line_number(text, match.start()), match.group(2).strip()))

    # Ledger rows with status keywords.
    ledger_statuses = (
        r"Finding F\d+|Intentional Exception I\d+|Intentional I\d+|Not covered|"
        r"Unused or unverified|Reviewed - no wide-API risk found|Not wide-relevant|"
        r"Not wide-api relevant"
    )
    for match in re.finditer(rf"^\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|.*?(?:{ledger_statuses}).*$", text, flags=re.M):
        row = match.group(0).strip()
        status_match = re.search(ledger_statuses, row)
        status = status_match.group(0) if status_match else "ledger-row"
        identifier = match.group(1).strip(" `")[:80]
        items.append(Item("ledger-row", identifier, status, line_number(text, match.start()), row))

    return items


def to_markdown(items: Sequence[Item]) -> str:
    lines = ["# React Wide API Report Intake", ""]
    if not items:
        lines.append("No report items found. Check whether the file is a react-wide-api-review report.")
        return "\n".join(lines) + "\n"
    lines.append(f"Extracted {len(items)} item(s).")
    lines.append("")
    lines.append("| Kind | ID / boundary | Status | Line | Text |")
    lines.append("| --- | --- | --- | ---: | --- |")
    for item in items:
        text = item.text.replace("|", "\\|")
        lines.append(f"| {item.kind} | {item.id} | {item.status} | {item.line} | {text} |")
    lines.append("")
    lines.append("Use this as the starting disposition ledger. Verify mismatches between index items, cards, intentional exceptions, and ledger rows before editing code.")
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", help="Path to react-wide-api-review Markdown report")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)

    text = Path(args.report).read_text(encoding="utf-8", errors="ignore")
    items = extract(text)

    if args.format == "json":
        print(json.dumps([asdict(item) for item in items], indent=2, ensure_ascii=False))
    else:
        print(to_markdown(items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
