#!/usr/bin/env python3
"""Summarize structured debug NDJSON without loading the full log into model context."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ERROR_TOKENS = (
    "error",
    "exception",
    "failed",
    "failure",
    "fatal",
    "timeout",
    "invariant",
    "fallback",
    "rejected",
    "cancelled",
    "canceled",
)


def _text(value: Any) -> str:
    if value in (None, ""):
        return ""
    return str(value)


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _timestamp_or_none(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _hypothesis_ids(payload: dict[str, Any]) -> list[str]:
    values: list[str] = []
    singular = payload.get("hypothesisId")
    if isinstance(singular, str) and singular.strip():
        values.append(singular.strip())
    plural = payload.get("hypothesisIds")
    if isinstance(plural, list):
        for item in plural:
            if isinstance(item, str) and item.strip():
                values.append(item.strip())
    return list(dict.fromkeys(values))


def _bounded_value(value: Any, *, max_chars: int, depth: int = 0) -> Any:
    if depth >= 3:
        return "<max-depth>"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if len(value) <= max_chars:
            return value
        return value[:max_chars] + f"…<{len(value) - max_chars} chars omitted>"
    if isinstance(value, list):
        items = [_bounded_value(item, max_chars=max_chars, depth=depth + 1) for item in value[:12]]
        if len(value) > 12:
            items.append(f"<{len(value) - 12} items omitted>")
        return items
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        keys = list(value.keys())
        for key in keys[:20]:
            result[_text(key)] = _bounded_value(value[key], max_chars=max_chars, depth=depth + 1)
        if len(keys) > 20:
            result["<omittedKeys>"] = len(keys) - 20
        return result
    text = repr(value)
    return text if len(text) <= max_chars else text[:max_chars] + "…"


def _compact_event(
    payload: dict[str, Any],
    *,
    line_number: int,
    max_data_chars: int,
) -> dict[str, Any]:
    return {
        "lineNumber": line_number,
        "runId": _text(payload.get("runId")),
        "correlationId": _text(payload.get("correlationId")),
        "sequence": _int_or_none(payload.get("sequence")),
        "probeId": _text(payload.get("probeId")),
        "hypothesisIds": _hypothesis_ids(payload),
        "location": _text(payload.get("location")),
        "phase": _text(payload.get("phase")),
        "event": _text(payload.get("event")),
        "level": _text(payload.get("level")),
        "message": _text(payload.get("message")),
        "timestamp": _timestamp_or_none(payload.get("timestamp")),
        "data": _bounded_value(payload.get("data", {}), max_chars=max_data_chars),
    }


def _matches(payload: dict[str, Any], args: argparse.Namespace) -> bool:
    if args.run_id and _text(payload.get("runId")) != args.run_id:
        return False
    if args.correlation_id and _text(payload.get("correlationId")) != args.correlation_id:
        return False
    if args.probe_id and _text(payload.get("probeId")) != args.probe_id:
        return False
    if args.hypothesis_id and args.hypothesis_id not in _hypothesis_ids(payload):
        return False
    return True


def _is_error_like(payload: dict[str, Any]) -> bool:
    level = _text(payload.get("level")).lower()
    if level in {"error", "fatal"}:
        return True
    combined = " ".join(
        (
            _text(payload.get("event")),
            _text(payload.get("message")),
            _text(payload.get("phase")),
        )
    ).lower()
    return any(token in combined for token in ERROR_TOKENS)


def _count_pairs(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    return [
        {"name": name, "count": count}
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _load_expected_probe_ids(path_text: str) -> list[str]:
    if not path_text:
        return []
    path = Path(path_text).expanduser().resolve()
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read expected probes file {path}: {exc}") from exc

    candidates: list[Any]
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("probeIds"), list):
            candidates = payload["probeIds"]
        elif isinstance(payload.get("locations"), list):
            candidates = payload["locations"]
        elif isinstance(payload.get("probes"), list):
            candidates = payload["probes"]
        else:
            candidates = []
    else:
        candidates = []

    result: list[str] = []
    for item in candidates:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
        elif isinstance(item, dict):
            probe_id = item.get("probeId")
            if isinstance(probe_id, str) and probe_id.strip():
                result.append(probe_id.strip())
    return list(dict.fromkeys(result))


def summarize(args: argparse.Namespace) -> dict[str, Any]:
    log_file = Path(args.log_file).expanduser().resolve()
    if not log_file.exists():
        raise FileNotFoundError(f"log file not found: {log_file}")
    if not log_file.is_file():
        raise ValueError(f"log path is not a file: {log_file}")

    expected_probe_ids = _load_expected_probe_ids(args.expected_probes_file)

    physical_lines = 0
    valid_events = 0
    invalid_lines = 0
    matched_events = 0
    first_timestamp: float | int | None = None
    last_timestamp: float | int | None = None

    run_counts: Counter[str] = Counter()
    correlation_counts: Counter[str] = Counter()
    probe_counts: Counter[str] = Counter()
    hypothesis_counts: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    phase_counts: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()
    location_counts: Counter[str] = Counter()

    probe_metadata: dict[str, dict[str, Any]] = {}
    hypothesis_probes: dict[str, set[str]] = defaultdict(set)
    hypothesis_locations: dict[str, set[str]] = defaultdict(set)
    last_sequence: dict[str, int] = {}
    sequence_gaps: list[dict[str, Any]] = []
    sequence_regressions: list[dict[str, Any]] = []
    error_events: list[dict[str, Any]] = []

    first_limit = max(args.timeline_limit // 2, 0)
    last_limit = max(args.timeline_limit - first_limit, 0)
    first_timeline: list[dict[str, Any]] = []
    last_timeline: deque[dict[str, Any]] = deque(maxlen=last_limit or 1)

    with log_file.open("r", encoding="utf-8", errors="replace") as handle:
        for physical_lines, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload: Any = json.loads(line)
            except json.JSONDecodeError:
                invalid_lines += 1
                continue
            if not isinstance(payload, dict):
                invalid_lines += 1
                continue
            valid_events += 1
            if not _matches(payload, args):
                continue

            matched_events += 1
            event = _compact_event(
                payload,
                line_number=physical_lines,
                max_data_chars=args.max_data_chars,
            )
            timestamp = event["timestamp"]
            if timestamp is not None:
                first_timestamp = timestamp if first_timestamp is None else min(first_timestamp, timestamp)
                last_timestamp = timestamp if last_timestamp is None else max(last_timestamp, timestamp)

            run_id = event["runId"] or "<missing>"
            correlation_id = event["correlationId"] or "<missing>"
            probe_id = event["probeId"] or "<missing>"
            event_name = event["event"] or "<missing>"
            phase = event["phase"] or "<missing>"
            level = event["level"] or "<missing>"
            location = event["location"] or "<missing>"

            run_counts[run_id] += 1
            correlation_counts[correlation_id] += 1
            probe_counts[probe_id] += 1
            event_counts[event_name] += 1
            phase_counts[phase] += 1
            level_counts[level] += 1
            location_counts[location] += 1

            for hypothesis_id in event["hypothesisIds"]:
                hypothesis_counts[hypothesis_id] += 1
                hypothesis_probes[hypothesis_id].add(probe_id)
                hypothesis_locations[hypothesis_id].add(location)

            metadata = probe_metadata.get(probe_id)
            if metadata is None:
                metadata = {
                    "probeId": probe_id,
                    "count": 0,
                    "hypothesisIds": set(),
                    "locations": set(),
                    "events": set(),
                    "phases": set(),
                    "correlationIds": set(),
                    "firstTimestamp": timestamp,
                    "lastTimestamp": timestamp,
                    "examples": [],
                }
                probe_metadata[probe_id] = metadata
            metadata["count"] += 1
            metadata["hypothesisIds"].update(event["hypothesisIds"])
            metadata["locations"].add(location)
            metadata["events"].add(event_name)
            metadata["phases"].add(phase)
            metadata["correlationIds"].add(correlation_id)
            if timestamp is not None:
                metadata["firstTimestamp"] = (
                    timestamp
                    if metadata["firstTimestamp"] is None
                    else min(metadata["firstTimestamp"], timestamp)
                )
                metadata["lastTimestamp"] = (
                    timestamp
                    if metadata["lastTimestamp"] is None
                    else max(metadata["lastTimestamp"], timestamp)
                )
            if len(metadata["examples"]) < args.max_examples:
                metadata["examples"].append(event)

            sequence = event["sequence"]
            if sequence is not None:
                scope = event["correlationId"] or f"<missing>:{run_id}"
                previous = last_sequence.get(scope)
                if previous is not None:
                    if sequence > previous + 1:
                        sequence_gaps.append(
                            {
                                "scope": scope,
                                "previous": previous,
                                "current": sequence,
                                "missingStart": previous + 1,
                                "missingEnd": sequence - 1,
                                "lineNumber": physical_lines,
                                "probeId": probe_id,
                            }
                        )
                    elif sequence <= previous:
                        sequence_regressions.append(
                            {
                                "scope": scope,
                                "previous": previous,
                                "current": sequence,
                                "lineNumber": physical_lines,
                                "probeId": probe_id,
                            }
                        )
                last_sequence[scope] = sequence

            if _is_error_like(payload) and len(error_events) < args.error_limit:
                error_events.append(event)

            if args.timeline_limit > 0:
                if len(first_timeline) < first_limit:
                    first_timeline.append(event)
                else:
                    last_timeline.append(event)

    if args.timeline_limit <= 0:
        timeline: list[dict[str, Any]] = []
    elif matched_events <= args.timeline_limit:
        timeline = first_timeline + list(last_timeline)
    else:
        timeline = first_timeline + [
            {
                "omittedEvents": matched_events - len(first_timeline) - len(last_timeline)
            }
        ] + list(last_timeline)

    probe_coverage: list[dict[str, Any]] = []
    for metadata in sorted(
        probe_metadata.values(), key=lambda item: (-item["count"], item["probeId"])
    )[: args.group_limit]:
        probe_coverage.append(
            {
                "probeId": metadata["probeId"],
                "count": metadata["count"],
                "hypothesisIds": sorted(metadata["hypothesisIds"]),
                "locations": sorted(metadata["locations"]),
                "events": sorted(metadata["events"]),
                "phases": sorted(metadata["phases"]),
                "correlationIds": sorted(metadata["correlationIds"]),
                "firstTimestamp": metadata["firstTimestamp"],
                "lastTimestamp": metadata["lastTimestamp"],
                "examples": metadata["examples"],
            }
        )

    hypothesis_coverage = [
        {
            "hypothesisId": hypothesis_id,
            "eventCount": hypothesis_counts[hypothesis_id],
            "probeIds": sorted(hypothesis_probes[hypothesis_id]),
            "locations": sorted(hypothesis_locations[hypothesis_id]),
        }
        for hypothesis_id in sorted(
            hypothesis_counts,
            key=lambda name: (-hypothesis_counts[name], name),
        )[: args.group_limit]
    ]

    observed_probe_ids = {name for name in probe_counts if name != "<missing>"}
    missing_expected = [probe for probe in expected_probe_ids if probe not in observed_probe_ids]

    return {
        "logFile": str(log_file),
        "filters": {
            "runId": args.run_id or None,
            "correlationId": args.correlation_id or None,
            "hypothesisId": args.hypothesis_id or None,
            "probeId": args.probe_id or None,
        },
        "stats": {
            "physicalLines": physical_lines,
            "validEvents": valid_events,
            "invalidLines": invalid_lines,
            "matchedEvents": matched_events,
            "firstTimestamp": first_timestamp,
            "lastTimestamp": last_timestamp,
            "expectedProbeCount": len(expected_probe_ids),
            "observedExpectedProbeCount": len(expected_probe_ids) - len(missing_expected),
        },
        "missingExpectedProbeIds": missing_expected,
        "counts": {
            "runIds": _count_pairs(run_counts, args.group_limit),
            "correlationIds": _count_pairs(correlation_counts, args.group_limit),
            "probeIds": _count_pairs(probe_counts, args.group_limit),
            "hypothesisIds": _count_pairs(hypothesis_counts, args.group_limit),
            "events": _count_pairs(event_counts, args.group_limit),
            "phases": _count_pairs(phase_counts, args.group_limit),
            "levels": _count_pairs(level_counts, args.group_limit),
            "locations": _count_pairs(location_counts, args.group_limit),
        },
        "probeCoverage": probe_coverage,
        "hypothesisCoverage": hypothesis_coverage,
        "sequence": {
            "scopesWithSequence": len(last_sequence),
            "gapCount": len(sequence_gaps),
            "regressionOrDuplicateCount": len(sequence_regressions),
            "gaps": sequence_gaps[: args.sequence_limit],
            "regressionsOrDuplicates": sequence_regressions[: args.sequence_limit],
        },
        "errorLikeEvents": error_events,
        "timeline": timeline,
    }


def _md_escape(value: Any, limit: int = 180) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    elif value is None:
        text = ""
    else:
        text = str(value)
    text = text.replace("|", "\\|").replace("\n", " ")
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def _markdown_count_table(title: str, pairs: Iterable[dict[str, Any]]) -> list[str]:
    rows = list(pairs)
    lines = [f"### {title}", "", "| Name | Count |", "| --- | ---: |"]
    if not rows:
        lines.append("| _none_ | 0 |")
    else:
        for item in rows:
            lines.append(f"| `{_md_escape(item['name'])}` | {item['count']} |")
    lines.append("")
    return lines


def to_markdown(summary: dict[str, Any]) -> str:
    stats = summary["stats"]
    filters = {key: value for key, value in summary["filters"].items() if value is not None}
    lines = [
        "# Debug Log Summary",
        "",
        f"- Log file: `{_md_escape(summary['logFile'], 500)}`",
        f"- Filters: `{_md_escape(filters or {'all': True}, 500)}`",
        f"- Physical lines: `{stats['physicalLines']}`",
        f"- Valid events: `{stats['validEvents']}`",
        f"- Invalid lines: `{stats['invalidLines']}`",
        f"- Matched events: `{stats['matchedEvents']}`",
        f"- Time range: `{stats['firstTimestamp']}` to `{stats['lastTimestamp']}`",
        "",
    ]

    if stats["expectedProbeCount"]:
        lines.extend(
            [
                "## Expected Probe Coverage",
                "",
                f"- Expected: `{stats['expectedProbeCount']}`",
                f"- Observed: `{stats['observedExpectedProbeCount']}`",
                f"- Missing: `{len(summary['missingExpectedProbeIds'])}`",
                "",
            ]
        )
        if summary["missingExpectedProbeIds"]:
            lines.append("Missing probe IDs: " + ", ".join(f"`{_md_escape(item)}`" for item in summary["missingExpectedProbeIds"]))
            lines.append("")

    lines.append("## Coverage Counts")
    lines.append("")
    for title, key in (
        ("Runs", "runIds"),
        ("Correlations", "correlationIds"),
        ("Probes", "probeIds"),
        ("Hypotheses", "hypothesisIds"),
        ("Events", "events"),
    ):
        lines.extend(_markdown_count_table(title, summary["counts"][key]))

    lines.extend(
        [
            "## Probe Coverage",
            "",
            "| Probe | Count | Hypotheses | Locations | Events | Correlations |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
    )
    if not summary["probeCoverage"]:
        lines.append("| _none_ | 0 |  |  |  |  |")
    else:
        for item in summary["probeCoverage"]:
            lines.append(
                "| `{}` | {} | {} | {} | {} | {} |".format(
                    _md_escape(item["probeId"]),
                    item["count"],
                    _md_escape(item["hypothesisIds"]),
                    _md_escape(item["locations"]),
                    _md_escape(item["events"]),
                    _md_escape(item["correlationIds"]),
                )
            )
    lines.append("")

    sequence = summary["sequence"]
    lines.extend(
        [
            "## Sequence Checks",
            "",
            f"- Scopes with sequence: `{sequence['scopesWithSequence']}`",
            f"- Gaps: `{sequence['gapCount']}`",
            f"- Regressions or duplicates: `{sequence['regressionOrDuplicateCount']}`",
            "",
        ]
    )
    if sequence["gaps"] or sequence["regressionsOrDuplicates"]:
        lines.extend(
            [
                "| Type | Scope | Previous | Current | Line | Probe |",
                "| --- | --- | ---: | ---: | ---: | --- |",
            ]
        )
        for item in sequence["gaps"]:
            lines.append(
                f"| gap | `{_md_escape(item['scope'])}` | {item['previous']} | {item['current']} | {item['lineNumber']} | `{_md_escape(item['probeId'])}` |"
            )
        for item in sequence["regressionsOrDuplicates"]:
            lines.append(
                f"| regression/duplicate | `{_md_escape(item['scope'])}` | {item['previous']} | {item['current']} | {item['lineNumber']} | `{_md_escape(item['probeId'])}` |"
            )
        lines.append("")

    lines.extend(
        [
            "## Error-Like Events",
            "",
            "| Line | Correlation | Seq | Probe | Event | Message | Data |",
            "| ---: | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    if not summary["errorLikeEvents"]:
        lines.append("|  |  |  | _none_ |  |  |  |")
    else:
        for event in summary["errorLikeEvents"]:
            lines.append(
                "| {} | `{}` | {} | `{}` | `{}` | {} | `{}` |".format(
                    event["lineNumber"],
                    _md_escape(event["correlationId"]),
                    event["sequence"] if event["sequence"] is not None else "",
                    _md_escape(event["probeId"]),
                    _md_escape(event["event"]),
                    _md_escape(event["message"]),
                    _md_escape(event["data"], 240),
                )
            )
    lines.append("")

    lines.extend(
        [
            "## Bounded Timeline",
            "",
            "| Line | Time | Correlation | Seq | Probe | Event | Message | Data |",
            "| ---: | ---: | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    if not summary["timeline"]:
        lines.append("|  |  |  |  | _none_ |  |  |  |")
    else:
        for event in summary["timeline"]:
            if "omittedEvents" in event:
                lines.append(f"|  |  |  |  | _{event['omittedEvents']} events omitted_ |  |  |  |")
                continue
            lines.append(
                "| {} | {} | `{}` | {} | `{}` | `{}` | {} | `{}` |".format(
                    event["lineNumber"],
                    event["timestamp"] if event["timestamp"] is not None else "",
                    _md_escape(event["correlationId"]),
                    event["sequence"] if event["sequence"] is not None else "",
                    _md_escape(event["probeId"]),
                    _md_escape(event["event"]),
                    _md_escape(event["message"]),
                    _md_escape(event["data"], 240),
                )
            )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize structured debug NDJSON with bounded output."
    )
    parser.add_argument("log_file", help="NDJSON log file.")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--correlation-id", default="")
    parser.add_argument("--hypothesis-id", default="")
    parser.add_argument("--probe-id", default="")
    parser.add_argument(
        "--expected-probes-file",
        default="",
        help="Optional JSON list/object containing probe IDs for missing-probe checks.",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--timeline-limit", type=int, default=80)
    parser.add_argument("--max-examples", type=int, default=2)
    parser.add_argument("--max-data-chars", type=int, default=240)
    parser.add_argument("--group-limit", type=int, default=100)
    parser.add_argument("--error-limit", type=int, default=50)
    parser.add_argument("--sequence-limit", type=int, default=100)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    for name in (
        "timeline_limit",
        "max_examples",
        "max_data_chars",
        "group_limit",
        "error_limit",
        "sequence_limit",
    ):
        if getattr(args, name) < 0:
            print(f"{name.replace('_', '-')} must be non-negative", file=sys.stderr)
            return 2
    try:
        summary = summarize(args)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(to_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
