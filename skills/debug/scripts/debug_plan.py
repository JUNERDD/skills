#!/usr/bin/env python3
"""Validate a deterministic coverage-first debug plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


SCHEMA_VERSION = "debug-plan/v1"
HYPOTHESIS_STATUSES = {
    "PENDING",
    "CONFIRMED",
    "REJECTED",
    "INCONCLUSIVE",
    "NOT_REACHED",
    "SUPERSEDED",
}
PROBE_ROLES = {
    "flow-start",
    "flow-terminal",
    "boundary",
    "branch",
    "state",
    "async",
    "external",
    "exception",
    "invariant",
    "observation",
}
SENTINEL_ROLES = {"flow-start", "flow-terminal"}
COVERAGE_GATES = {
    "causeFamiliesReviewed",
    "observerCostReviewed",
    "privacyReviewed",
    "transportChecked",
    "correlationChecked",
}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_source_location(value: str) -> bool:
    path, separator, line = value.rpartition(":")
    if not separator or not path or not line.isdigit() or int(line) <= 0:
        return False
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or (
        len(normalized) >= 2 and normalized[0].isalpha() and normalized[1] == ":"
    ):
        return False
    return all(part not in {"", ".", ".."} for part in normalized.split("/"))


class _Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path: str, message: str) -> None:
        self.errors.append(f"{path}: {message}")

    def warning(self, path: str, message: str) -> None:
        self.warnings.append(f"{path}: {message}")

    def object_field(self, parent: dict[str, Any], key: str, path: str) -> dict[str, Any]:
        value = parent.get(key)
        field_path = f"{path}.{key}" if path else key
        if not isinstance(value, dict):
            self.error(field_path, "must be an object")
            return {}
        return value

    def string_field(self, parent: dict[str, Any], key: str, path: str) -> str:
        value = parent.get(key)
        field_path = f"{path}.{key}" if path else key
        if not _nonempty_string(value):
            self.error(field_path, "must be a non-empty string")
            return ""
        return value.strip()

    def string_list_field(
        self,
        parent: dict[str, Any],
        key: str,
        path: str,
        *,
        allow_empty: bool,
    ) -> list[str]:
        value = parent.get(key)
        field_path = f"{path}.{key}" if path else key
        if not isinstance(value, list):
            self.error(field_path, "must be an array of non-empty strings")
            return []
        if not value and not allow_empty:
            self.error(field_path, "must not be empty")

        result: list[str] = []
        seen: set[str] = set()
        for index, item in enumerate(value):
            item_path = f"{field_path}[{index}]"
            if not _nonempty_string(item):
                self.error(item_path, "must be a non-empty string")
                continue
            normalized = item.strip()
            if normalized in seen:
                self.error(item_path, f"duplicates {normalized!r}")
                continue
            seen.add(normalized)
            result.append(normalized)
        return result


def _indexed_objects(
    validator: _Validator,
    plan: dict[str, Any],
    key: str,
) -> list[tuple[int, dict[str, Any]]]:
    value = plan.get(key)
    if not isinstance(value, list):
        validator.error(key, "must be a non-empty array")
        return []
    if not value:
        validator.error(key, "must not be empty")
    result: list[tuple[int, dict[str, Any]]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            validator.error(f"{key}[{index}]", "must be an object")
            continue
        result.append((index, item))
    return result


def _index_unique_ids(
    validator: _Validator,
    items: list[tuple[int, dict[str, Any]]],
    collection: str,
    id_key: str,
) -> dict[str, tuple[int, dict[str, Any]]]:
    result: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, item in items:
        path = f"{collection}[{index}].{id_key}"
        value = item.get(id_key)
        if not _nonempty_string(value):
            validator.error(path, "must be a non-empty string")
            continue
        normalized = value.strip()
        if normalized in result:
            first_index = result[normalized][0]
            validator.error(path, f"duplicates {collection}[{first_index}].{id_key} {normalized!r}")
            continue
        result[normalized] = (index, item)
    return result


def _validate_references(
    validator: _Validator,
    refs: list[str],
    known: set[str],
    path: str,
    target_name: str,
) -> set[str]:
    valid: set[str] = set()
    for index, ref in enumerate(refs):
        if ref not in known:
            validator.error(f"{path}[{index}]", f"references unknown {target_name} {ref!r}")
        else:
            valid.add(ref)
    return valid


def _generic_mechanism(mechanism: str) -> bool:
    normalized = " ".join(mechanism.lower().replace("_", " ").replace("-", " ").split())
    return normalized in {
        "bug",
        "issue",
        "unknown",
        "state issue",
        "cache issue",
        "timing issue",
        "race",
        "race condition",
    }


def validate_plan(plan: Any) -> dict[str, Any]:
    """Return a stable validation report for a parsed plan."""
    validator = _Validator()
    if not isinstance(plan, dict):
        validator.error("plan", "must be a JSON object")
        return _report(validator, {})

    if plan.get("schemaVersion") != SCHEMA_VERSION:
        validator.error("schemaVersion", f"must equal {SCHEMA_VERSION!r}")

    failure_contract = validator.object_field(plan, "failureContract", "")
    for key in (
        "expected",
        "observed",
        "trigger",
        "scope",
        "frequency",
        "timing",
        "lastKnownGood",
        "reproductionCost",
    ):
        validator.string_field(failure_contract, key, "failureContract")
    validator.string_list_field(
        failure_contract,
        "constraints",
        "failureContract",
        allow_empty=True,
    )

    raw_exclusions = plan.get("excludedCauseFamilies")
    excluded_cause_family_count = 0
    if not isinstance(raw_exclusions, list):
        validator.error("excludedCauseFamilies", "must be an array")
    else:
        seen_families: set[str] = set()
        for index, exclusion in enumerate(raw_exclusions):
            path = f"excludedCauseFamilies[{index}]"
            if not isinstance(exclusion, dict):
                validator.error(path, "must be an object")
                continue
            family = validator.string_field(exclusion, "family", path)
            validator.string_field(exclusion, "reason", path)
            if family in seen_families:
                validator.error(f"{path}.family", f"duplicates excluded family {family!r}")
                continue
            if family:
                seen_families.add(family)
                excluded_cause_family_count += 1

    run = validator.object_field(plan, "run", "")
    validator.string_field(run, "runId", "run")
    owner = validator.string_field(run, "reproductionOwner", "run")
    if owner and owner not in {"agent", "user", "external"}:
        validator.error("run.reproductionOwner", "must be one of: agent, user, external")
    validator.string_list_field(run, "steps", "run", allow_empty=False)
    run_ambiguities = validator.string_list_field(
        run,
        "residualAmbiguities",
        "run",
        allow_empty=True,
    )

    boundary_items = _indexed_objects(validator, plan, "boundaries")
    hypothesis_items = _indexed_objects(validator, plan, "hypotheses")
    probe_items = _indexed_objects(validator, plan, "probes")
    boundaries = _index_unique_ids(validator, boundary_items, "boundaries", "id")
    hypotheses = _index_unique_ids(validator, hypothesis_items, "hypotheses", "id")
    probes = _index_unique_ids(validator, probe_items, "probes", "probeId")

    boundary_probe_refs: dict[str, list[str]] = {}
    for boundary_id, (index, boundary) in boundaries.items():
        path = f"boundaries[{index}]"
        validator.string_field(boundary, "invariant", path)
        boundary_probe_refs[boundary_id] = validator.string_list_field(
            boundary,
            "probeIds",
            path,
            allow_empty=False,
        )

    hypothesis_boundary_refs: dict[str, list[str]] = {}
    hypothesis_probe_refs: dict[str, list[str]] = {}
    for hypothesis_id, (index, hypothesis) in hypotheses.items():
        path = f"hypotheses[{index}]"
        mechanism = validator.string_field(hypothesis, "mechanism", path)
        if mechanism and _generic_mechanism(mechanism):
            validator.error(f"{path}.mechanism", "must name a concrete, falsifiable mechanism")
        hypothesis_boundary_refs[hypothesis_id] = validator.string_list_field(
            hypothesis,
            "boundaryIds",
            path,
            allow_empty=False,
        )
        validator.string_list_field(hypothesis, "confirmedBy", path, allow_empty=False)
        validator.string_list_field(hypothesis, "rejectedBy", path, allow_empty=False)
        hypothesis_probe_refs[hypothesis_id] = validator.string_list_field(
            hypothesis,
            "probeIds",
            path,
            allow_empty=False,
        )
        status = validator.string_field(hypothesis, "status", path)
        if status and status not in HYPOTHESIS_STATUSES:
            allowed = ", ".join(sorted(HYPOTHESIS_STATUSES))
            validator.error(f"{path}.status", f"must be one of: {allowed}")

    probe_boundary_refs: dict[str, list[str]] = {}
    probe_hypothesis_refs: dict[str, list[str]] = {}
    probe_roles: dict[str, str] = {}
    for probe_id, (index, probe) in probes.items():
        path = f"probes[{index}]"
        location = validator.string_field(probe, "location", path)
        if location and not _valid_source_location(location):
            validator.error(
                f"{path}.location",
                "must be a workspace-relative source path followed by a positive line number",
            )
        validator.string_field(probe, "event", path)
        role = validator.string_field(probe, "role", path)
        probe_roles[probe_id] = role
        if role and role not in PROBE_ROLES:
            validator.error(f"{path}.role", f"must be one of: {', '.join(sorted(PROBE_ROLES))}")
        probe_boundary_refs[probe_id] = validator.string_list_field(
            probe,
            "boundaryIds",
            path,
            allow_empty=True,
        )
        probe_hypothesis_refs[probe_id] = validator.string_list_field(
            probe,
            "hypothesisIds",
            path,
            allow_empty=role in SENTINEL_ROLES,
        )
        validator.string_list_field(probe, "expectedEvents", path, allow_empty=False)
        volume_control = probe.get("volumeControl")
        if not (
            _nonempty_string(volume_control)
            or isinstance(volume_control, dict) and bool(volume_control)
        ):
            validator.error(f"{path}.volumeControl", "must be a non-empty string or object")
        validator.string_list_field(probe, "dataFields", path, allow_empty=False)
        validator.string_list_field(probe, "redactions", path, allow_empty=True)

    boundary_ids = set(boundaries)
    hypothesis_ids = set(hypotheses)
    probe_ids = set(probes)

    for boundary_id, (index, _) in boundaries.items():
        valid_probes = _validate_references(
            validator,
            boundary_probe_refs.get(boundary_id, []),
            probe_ids,
            f"boundaries[{index}].probeIds",
            "probe",
        )
        if not valid_probes:
            validator.error(f"boundaries[{index}].probeIds", "must contain at least one existing probe")
        for probe_id in valid_probes:
            if boundary_id not in probe_boundary_refs.get(probe_id, []):
                validator.error(
                    f"boundaries[{index}].probeIds",
                    f"mapping to probe {probe_id!r} is not reciprocated by that probe's boundaryIds",
                )

    for hypothesis_id, (index, _) in hypotheses.items():
        _validate_references(
            validator,
            hypothesis_boundary_refs.get(hypothesis_id, []),
            boundary_ids,
            f"hypotheses[{index}].boundaryIds",
            "boundary",
        )
        valid_probes = _validate_references(
            validator,
            hypothesis_probe_refs.get(hypothesis_id, []),
            probe_ids,
            f"hypotheses[{index}].probeIds",
            "probe",
        )
        if not valid_probes:
            validator.error(f"hypotheses[{index}].probeIds", "must contain at least one existing probe")
        for probe_id in valid_probes:
            if hypothesis_id not in probe_hypothesis_refs.get(probe_id, []):
                validator.error(
                    f"hypotheses[{index}].probeIds",
                    f"mapping to probe {probe_id!r} is not reciprocated by that probe's hypothesisIds",
                )

    for probe_id, (index, _) in probes.items():
        valid_boundaries = _validate_references(
            validator,
            probe_boundary_refs.get(probe_id, []),
            boundary_ids,
            f"probes[{index}].boundaryIds",
            "boundary",
        )
        for boundary_id in valid_boundaries:
            if probe_id not in boundary_probe_refs.get(boundary_id, []):
                validator.error(
                    f"probes[{index}].boundaryIds",
                    f"mapping to boundary {boundary_id!r} is not reciprocated by that boundary's probeIds",
                )
        valid_hypotheses = _validate_references(
            validator,
            probe_hypothesis_refs.get(probe_id, []),
            hypothesis_ids,
            f"probes[{index}].hypothesisIds",
            "hypothesis",
        )
        if probe_roles.get(probe_id) not in SENTINEL_ROLES and not valid_hypotheses:
            validator.error(
                f"probes[{index}].hypothesisIds",
                "non-sentinel probes must map to at least one existing hypothesis",
            )
        for hypothesis_id in valid_hypotheses:
            if probe_id not in hypothesis_probe_refs.get(hypothesis_id, []):
                validator.error(
                    f"probes[{index}].hypothesisIds",
                    f"mapping to hypothesis {hypothesis_id!r} is not reciprocated by that hypothesis's probeIds",
                )

    role_values = list(probe_roles.values())
    if "flow-start" not in role_values:
        validator.error("probes", "must include at least one flow-start sentinel")
    if "flow-terminal" not in role_values:
        validator.error("probes", "must include at least one flow-terminal sentinel")

    coverage = validator.object_field(plan, "coverage", "")
    for gate in sorted(COVERAGE_GATES):
        if coverage.get(gate) is not True:
            validator.error(f"coverage.{gate}", "must be true before reproduction")
    coverage_ambiguities = validator.string_list_field(
        coverage,
        "residualAmbiguities",
        "coverage",
        allow_empty=True,
    )
    if coverage_ambiguities:
        validator.warning(
            "coverage.residualAmbiguities",
            f"contains {len(coverage_ambiguities)} unresolved ambiguity item(s)",
        )
    if run_ambiguities != coverage_ambiguities:
        validator.error(
            "run.residualAmbiguities",
            "does not match coverage.residualAmbiguities",
        )

    context = {
        "boundaryCount": len(boundary_items),
        "hypothesisCount": len(hypothesis_items),
        "probeCount": len(probe_items),
        "flowStartProbeCount": role_values.count("flow-start"),
        "flowTerminalProbeCount": role_values.count("flow-terminal"),
        "sharedProbeCount": sum(
            1 for refs in probe_hypothesis_refs.values() if len(set(refs)) > 1
        ),
        "residualAmbiguityCount": len(coverage_ambiguities),
        "excludedCauseFamilyCount": excluded_cause_family_count,
    }
    return _report(validator, context)


def _report(validator: _Validator, counts: dict[str, int]) -> dict[str, Any]:
    normalized_counts = {
        "boundaries": counts.get("boundaryCount", 0),
        "hypotheses": counts.get("hypothesisCount", 0),
        "probes": counts.get("probeCount", 0),
        "flowStartProbes": counts.get("flowStartProbeCount", 0),
        "flowTerminalProbes": counts.get("flowTerminalProbeCount", 0),
        "sharedProbes": counts.get("sharedProbeCount", 0),
        "residualAmbiguities": counts.get("residualAmbiguityCount", 0),
        "excludedCauseFamilies": counts.get("excludedCauseFamilyCount", 0),
    }
    ok = not validator.errors
    if ok:
        hypothesis_label = "hypothesis" if normalized_counts["hypotheses"] == 1 else "hypotheses"
        boundary_label = "boundary" if normalized_counts["boundaries"] == 1 else "boundaries"
        summary = (
            "PASS: debug coverage plan is valid "
            f"({normalized_counts['hypotheses']} {hypothesis_label}, "
            f"{normalized_counts['probes']} probes, "
            f"{normalized_counts['boundaries']} {boundary_label})"
        )
    else:
        summary = (
            f"FAIL: debug coverage plan has {len(validator.errors)} error(s) "
            f"and {len(validator.warnings)} warning(s)"
        )
    return {
        "ok": ok,
        "schemaVersion": SCHEMA_VERSION,
        "summary": summary,
        "counts": normalized_counts,
        "errors": validator.errors,
        "warnings": validator.warnings,
    }


def _format_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Debug Plan Validation",
        "",
        f"- Result: **{'PASS' if report['ok'] else 'FAIL'}**",
        f"- Summary: {report['summary']}",
        "",
        "## Counts",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
    ]
    labels = {
        "boundaries": "Boundaries",
        "hypotheses": "Hypotheses",
        "probes": "Probes",
        "flowStartProbes": "Flow-start probes",
        "flowTerminalProbes": "Flow-terminal probes",
        "sharedProbes": "Shared probes",
        "residualAmbiguities": "Residual ambiguities",
        "excludedCauseFamilies": "Excluded cause families",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | {report['counts'][key]} |")
    for heading, key in (("Errors", "errors"), ("Warnings", "warnings")):
        lines.extend(["", f"## {heading}", ""])
        entries = report[key]
        if entries:
            lines.extend(f"- `{entry}`" for entry in entries)
        else:
            lines.append("- None")
    return "\n".join(lines) + "\n"


def _emit(report: dict[str, Any], output_format: str) -> None:
    if output_format == "markdown":
        sys.stdout.write(_format_markdown(report))
    else:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")


def _load_plan(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _format_error_report(message: str) -> dict[str, Any]:
    validator = _Validator()
    validator.error("plan", message)
    return _report(validator, {})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="validate a JSON debug plan")
    validate_parser.add_argument("plan", metavar="PLAN", help="JSON plan path, or - for stdin")
    validate_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="report format (default: json)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = _load_plan(args.plan)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _emit(_format_error_report(f"could not read valid JSON: {exc}"), args.format)
        return 2

    report = validate_plan(plan)
    _emit(report, args.format)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
