#!/usr/bin/env python3
"""Validate a deterministic coverage-first debug plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


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
    "observation-checkpoint",
    "boundary",
    "branch",
    "state",
    "async",
    "external",
    "exception",
    "invariant",
    "observation",
}
SENTINEL_ROLES = {"flow-start", "flow-terminal", "observation-checkpoint"}
COMPLETION_MODES = {"flow-terminal", "observation-checkpoint"}
DELEGATION_SCOPES = {"single-run", "remaining-runs"}
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
    run_id = validator.string_field(run, "runId", "run")
    owner = validator.string_field(run, "reproductionOwner", "run")
    if owner and owner not in {"agent", "user", "external"}:
        validator.error("run.reproductionOwner", "must be one of: agent, user, external")
    delegation_present = "reproductionDelegation" in run
    raw_delegation = run.get("reproductionDelegation")
    if owner == "user" and delegation_present:
        validator.error(
            "run.reproductionDelegation",
            "must be omitted when run.reproductionOwner is user",
        )
    elif owner in {"agent", "external"}:
        if not isinstance(raw_delegation, dict):
            validator.error(
                "run.reproductionDelegation",
                "must be an object recording the current user's explicit delegation for non-user ownership",
            )
        else:
            target = validator.string_field(
                raw_delegation, "target", "run.reproductionDelegation"
            )
            scope = validator.string_field(
                raw_delegation, "scope", "run.reproductionDelegation"
            )
            effective_run_id = validator.string_field(
                raw_delegation, "effectiveRunId", "run.reproductionDelegation"
            )
            validator.string_field(
                raw_delegation,
                "currentUserDirective",
                "run.reproductionDelegation",
            )
            if target and target != owner:
                validator.error(
                    "run.reproductionDelegation.target",
                    "must match run.reproductionOwner",
                )
            if scope and scope not in DELEGATION_SCOPES:
                validator.error(
                    "run.reproductionDelegation.scope",
                    "must be one of: remaining-runs, single-run",
                )
            if effective_run_id and run_id and effective_run_id != run_id:
                validator.error(
                    "run.reproductionDelegation.effectiveRunId",
                    "must match run.runId",
                )
    validator.string_list_field(run, "steps", "run", allow_empty=False)
    completion_mode = "flow-terminal"
    raw_completion = run.get("completion")
    if raw_completion is not None:
        if not isinstance(raw_completion, dict):
            validator.error("run.completion", "must be an object")
        else:
            completion_mode = validator.string_field(raw_completion, "mode", "run.completion")
            if completion_mode and completion_mode not in COMPLETION_MODES:
                validator.error(
                    "run.completion.mode",
                    f"must be one of: {', '.join(sorted(COMPLETION_MODES))}",
                )
            if completion_mode == "observation-checkpoint":
                validator.string_field(raw_completion, "condition", "run.completion")

    boundary_items = _indexed_objects(validator, plan, "boundaries")
    hypothesis_items = _indexed_objects(validator, plan, "hypotheses")
    probe_items = _indexed_objects(validator, plan, "probes")
    boundaries = _index_unique_ids(validator, boundary_items, "boundaries", "id")
    hypotheses = _index_unique_ids(validator, hypothesis_items, "hypotheses", "id")
    probes = _index_unique_ids(validator, probe_items, "probes", "probeId")

    for _, (index, boundary) in boundaries.items():
        path = f"boundaries[{index}]"
        validator.string_field(boundary, "invariant", path)

    hypothesis_boundary_refs: dict[str, list[str]] = {}
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

    for hypothesis_id, (index, _) in hypotheses.items():
        _validate_references(
            validator,
            hypothesis_boundary_refs.get(hypothesis_id, []),
            boundary_ids,
            f"hypotheses[{index}].boundaryIds",
            "boundary",
        )

    observed_boundary_ids: set[str] = set()
    observed_hypothesis_ids: set[str] = set()
    for probe_id, (index, _) in probes.items():
        valid_boundaries = _validate_references(
            validator,
            probe_boundary_refs.get(probe_id, []),
            boundary_ids,
            f"probes[{index}].boundaryIds",
            "boundary",
        )
        observed_boundary_ids.update(valid_boundaries)
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
        observed_hypothesis_ids.update(valid_hypotheses)

    for boundary_id, (index, _) in boundaries.items():
        if boundary_id not in observed_boundary_ids:
            validator.error(
                f"boundaries[{index}]",
                "must be referenced by at least one probe boundaryIds entry",
            )

    for hypothesis_id, (index, _) in hypotheses.items():
        if hypothesis_id not in observed_hypothesis_ids:
            validator.error(
                f"hypotheses[{index}]",
                "must be referenced by at least one probe hypothesisIds entry",
            )

    role_values = list(probe_roles.values())
    if "flow-start" not in role_values:
        validator.error("probes", "must include at least one flow-start sentinel")
    if completion_mode == "observation-checkpoint":
        if "observation-checkpoint" not in role_values:
            validator.error(
                "probes",
                "must include at least one observation-checkpoint sentinel for run.completion.mode",
            )
    elif "flow-terminal" not in role_values:
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
    context = {
        "boundaryCount": len(boundary_items),
        "hypothesisCount": len(hypothesis_items),
        "probeCount": len(probe_items),
        "flowStartProbeCount": role_values.count("flow-start"),
        "flowTerminalProbeCount": role_values.count("flow-terminal"),
        "observationCheckpointProbeCount": role_values.count("observation-checkpoint"),
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
        "observationCheckpointProbes": counts.get("observationCheckpointProbeCount", 0),
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
        "observationCheckpointProbes": "Observation-checkpoint probes",
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
