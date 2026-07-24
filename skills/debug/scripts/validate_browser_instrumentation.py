#!/usr/bin/env python3
"""Conservatively reject browser probes that can bypass loss-auditable delivery."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


SOURCE_SUFFIXES = {".js", ".jsx", ".mjs", ".mts", ".ts", ".tsx"}
IDENTIFIER = r"[A-Za-z_$][\w$]*"
ASSIGNMENT_PREFIX = re.compile(rf"\b(?P<name>{IDENTIFIER})\s*=")
FETCH_CALLEE = re.compile(r"\b(?:(?:globalThis|window|self)\.)?fetch\s*\(")
FETCH_CALL = re.compile(
    r"\b(?:(?:globalThis|window|self)\.)?fetch\s*\(\s*(?P<argument>[^,\n)]+)"
)
KEEPALIVE_TRUE = re.compile(r"\bkeepalive\s*:\s*true\b")
SEND_BEACON = re.compile(r"\b(?:(?:globalThis|window|self)\.)?(?:navigator\.)?sendBeacon\s*\(")
SILENT_PROMISE_CATCH = re.compile(
    r"\.catch\s*\(\s*(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>\s*"
    r"(?:\{\s*\}|undefined|null|void\s+0)\s*\)"
)
OCCURRENCE_REDUCTION_MARKER = re.compile(
    r"\b(?:"
    r"last[A-Za-z0-9_$]*(?:ProbeKey|AuditKey)"
    r"|checkpointEmitted[A-Za-z0-9_$]*"
    r"|flowStarted[A-Za-z0-9_$]*"
    r"|[A-Za-z0-9_$]*(?:Sampled|Suppressed|Deduplicated|Coalesced)[A-Za-z0-9_$]*"
    r")\b"
)
IMPORT_PREFIX = re.compile(
    r"\bimport\s*\{(?P<specifiers>[^}]*)\}\s*from\b",
    re.DOTALL,
)
TRANSPORT_FACTORY_APIS = {
    "getOrCreateBrowserDebugTransport",
    "createBrowserDebugTransport",
}
SHARED_PRODUCER_APIS = {
    "installRealmDebugProducer",
    "instrumentGlobalFetch",
}
REGISTRY_TRANSPORT_CALL = re.compile(
    r"\b(?:getOrCreateBrowserDebugTransport|createBrowserDebugTransport)\s*\("
)
TRANSPORT_BINDING = re.compile(
    rf"\b(?:export\s+)?const\s+(?P<name>{IDENTIFIER})\s*=\s*"
    r"(?:getOrCreateBrowserDebugTransport|createBrowserDebugTransport)\s*\("
)
VARIABLE_BINDING = re.compile(
    rf"\b(?:const|let|var)\s+(?P<name>{IDENTIFIER})\b"
)
LOCAL_TRANSPORT_DEFINITION = re.compile(
    r"\b(?:export\s+)?(?:async\s+)?function\s+"
    r"(?:getOrCreateBrowserDebugTransport|createBrowserDebugTransport)\s*\("
)
RECORD_SAFE_CALL = re.compile(r"\.recordSafe\s*\(")
RECORD_SINK = re.compile(
    r"(?:\.recordSafe|\b(?:emit|record|report|publish|send|log)[A-Za-z0-9_$]*)\s*\("
)
IF_CONDITION = re.compile(
    r"\bif\s*\((?P<condition>(?:[^()]|\([^()]*\))*)\)",
    re.DOTALL,
)
STATE_COLLECTION_BINDING = re.compile(
    rf"\b(?:const|let|var)\s+(?P<name>{IDENTIFIER})\s*=\s*new\s+(?:Set|Map)\b"
)
STATE_BOOLEAN_BINDING = re.compile(
    rf"\b(?:const|let|var)\s+(?P<name>{IDENTIFIER})"
    r"(?:\s*:\s*boolean)?\s*=\s*(?:true|false)\b"
)
STATE_REF_BINDING = re.compile(
    rf"\b(?:const|let|var)\s+(?P<name>{IDENTIFIER})\s*=\s*"
    r"(?:React\.)?useRef(?:<[^>]+>)?\s*\("
)
STATE_HINT = re.compile(
    r"(?:seen|once|emit|sent|start|checkpoint|flow|last|prev|previous|change|"
    r"dedup|suppress|coalesc|recorded|reported)",
    re.IGNORECASE,
)
ONCE_WRAPPER = re.compile(
    r"\b(?:once|runOnce|useEffectOnce|useMount)\s*\([\s\S]{0,800}?"
    r"(?:\.recordSafe|\b(?:emit|record|report|publish|send|log)[A-Za-z0-9_$]*)\s*\("
)
REDUCING_WRAPPER = re.compile(
    r"\b(?:"
    r"throttle|throttleTime|useThrottle|useThrottleFn|"
    r"debounce|debounceTime|useDebounce|useDebounceFn|"
    r"sample|sampleTime|auditTime|rateLimit|pThrottle|"
    r"distinctUntilChanged|dedupe|deduplicate|coalesce|memoizeOne"
    r")\s*\([\s\S]{0,800}?"
    r"(?:\.recordSafe|\b(?:emit|record|report|publish|send|log)[A-Za-z0-9_$]*)\s*\("
)
OCCURRENCE_SELECTION_CONDITION = re.compile(
    r"Math\.random\s*\("
    r"|\b(?:sourceSequence|sequence|ordinal|occurrenceCount|eventCount|index|counter|"
    r"[A-Za-z_$][\w$]*(?:Sequence|Count|Index|Ordinal|Counter))\b\s*%"
    r"|\b(?:sourceSequence|sequence|ordinal|occurrenceCount|eventCount|index|counter|"
    r"[A-Za-z_$][\w$]*(?:Sequence|Count|Index|Ordinal|Counter))\b\s*"
    r"(?:<=|>=|<|>|={2,3}|!={1,2})\s*\d+"
    r"|\b(?:sample|firstN|everyOther|changeOnly|shouldEmit|rateLimit)[A-Za-z0-9_$]*\b",
    re.IGNORECASE,
)
REGEX_PREFIX_KEYWORDS = {
    "await",
    "case",
    "delete",
    "do",
    "else",
    "in",
    "instanceof",
    "new",
    "of",
    "return",
    "throw",
    "typeof",
    "void",
    "yield",
}
CONTROL_CONDITION_KEYWORDS = {"catch", "for", "if", "switch", "while", "with"}


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _mask_js_comments(text: str) -> str:
    """Mask JavaScript comments while preserving strings, offsets, and lines."""

    result = list(text)
    index = 0
    quote: str | None = None
    while index < len(text):
        character = text[index]
        if quote is not None:
            if character == "\\":
                index += 2
                continue
            if character == quote:
                quote = None
            index += 1
            continue
        if character in {"'", '"', "`"}:
            quote = character
            index += 1
            continue
        if character == "/" and index + 1 < len(text):
            next_character = text[index + 1]
            if next_character == "/":
                while index < len(text) and text[index] not in {"\n", "\r"}:
                    result[index] = " "
                    index += 1
                continue
            if next_character == "*":
                result[index] = " "
                result[index + 1] = " "
                index += 2
                while index < len(text):
                    if text[index] == "*" and index + 1 < len(text) and text[index + 1] == "/":
                        result[index] = " "
                        result[index + 1] = " "
                        index += 2
                        break
                    if text[index] not in {"\n", "\r"}:
                        result[index] = " "
                    index += 1
                continue
        index += 1
    return "".join(result)


def _mask_js_strings(text: str) -> str:
    """Mask literal text so wiring regexes can only observe executable code."""

    result = list(text)
    index = 0
    while index < len(text):
        quote = text[index]
        if quote not in {"'", '"', "`"}:
            index += 1
            continue
        result[index] = " "
        index += 1
        while index < len(text):
            character = text[index]
            if character not in {"\n", "\r"}:
                result[index] = " "
            if character == "\\":
                index += 1
                if index < len(text) and text[index] not in {"\n", "\r"}:
                    result[index] = " "
                index += 1
                continue
            index += 1
            if character == quote:
                break
    return "".join(result)


def _regex_literal_end(text: str, start: int) -> int | None:
    """Return the offset after a complete JavaScript regex literal and flags."""

    index = start + 1
    in_character_class = False
    while index < len(text):
        character = text[index]
        if character in {"\n", "\r"}:
            return None
        if character == "\\":
            index += 2
            continue
        if character == "[":
            in_character_class = True
        elif character == "]" and in_character_class:
            in_character_class = False
        elif character == "/" and not in_character_class:
            index += 1
            while index < len(text) and text[index].isalpha():
                index += 1
            return index
        index += 1
    return None


def _mask_js_regex_literals(text: str) -> str:
    """Mask regex literals without confusing ordinary division operators."""

    result = list(text)
    index = 0
    expression_can_start = True
    last_identifier: str | None = None
    parenthesis_contexts: list[str | None] = []

    while index < len(text):
        character = text[index]
        if character.isspace():
            index += 1
            continue

        if character in {"'", '"', "`"}:
            quote = character
            index += 1
            while index < len(text):
                current = text[index]
                if current == "\\":
                    index += 2
                    continue
                index += 1
                if current == quote:
                    break
            expression_can_start = False
            last_identifier = None
            continue

        if character.isalpha() or character in {"_", "$"}:
            end = index + 1
            while end < len(text) and (
                text[end].isalnum() or text[end] in {"_", "$"}
            ):
                end += 1
            last_identifier = text[index:end]
            expression_can_start = last_identifier in REGEX_PREFIX_KEYWORDS
            index = end
            continue

        if character.isdigit():
            index += 1
            while index < len(text) and (
                text[index].isalnum() or text[index] in {"_", "."}
            ):
                index += 1
            expression_can_start = False
            last_identifier = None
            continue

        if character == "(":
            parenthesis_contexts.append(
                last_identifier
                if last_identifier in CONTROL_CONDITION_KEYWORDS
                else None
            )
            expression_can_start = True
            last_identifier = None
            index += 1
            continue
        if character == ")":
            context = parenthesis_contexts.pop() if parenthesis_contexts else None
            expression_can_start = context in CONTROL_CONDITION_KEYWORDS
            last_identifier = None
            index += 1
            continue

        if character == "/" and expression_can_start:
            literal_end = _regex_literal_end(text, index)
            if literal_end is not None:
                for literal_index in range(index, literal_end):
                    if result[literal_index] not in {"\n", "\r"}:
                        result[literal_index] = " "
                index = literal_end
                expression_can_start = False
                last_identifier = None
                continue

        if character in {")", "]", "}"}:
            expression_can_start = False
        elif character == ".":
            expression_can_start = False
        elif character in {"+", "-"} and index + 1 < len(text) and text[index + 1] == character:
            expression_can_start = False
            index += 1
        else:
            expression_can_start = True
        last_identifier = None
        index += 1

    return "".join(result)


def _ambiguous_slash_brace_offsets(text: str) -> list[int]:
    """Find unmasked same-line slash pairs that can corrupt brace depth."""

    offsets: list[int] = []
    line_start = 0
    for line in text.splitlines(keepends=True):
        slash_offsets = [
            offset for offset, character in enumerate(line) if character == "/"
        ]
        for start, end in zip(slash_offsets, slash_offsets[1:]):
            if "{" in line[start + 1 : end] or "}" in line[start + 1 : end]:
                offsets.append(line_start + start)
        line_start += len(line)
    return offsets


def _literal_after(text: str, offset: int) -> tuple[str, int] | None:
    index = offset
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] not in {"'", '"', "`"}:
        return None

    quote = text[index]
    value: list[str] = []
    index += 1
    while index < len(text):
        character = text[index]
        if character == "\\" and index + 1 < len(text):
            value.extend((character, text[index + 1]))
            index += 2
            continue
        if character == quote:
            return "".join(value), index + 1
        value.append(character)
        index += 1
    return None


def _is_transport_module(module: str) -> bool:
    normalized = module.replace("\\", "/")
    return bool(
        re.search(r"(?:^|/)browser-debug-transport(?:\.mjs)?$", normalized)
    )


def _transport_import_specifiers(comment_source: str, code_source: str) -> list[str]:
    specifiers: list[str] = []
    for match in IMPORT_PREFIX.finditer(code_source):
        module_literal = _literal_after(comment_source, match.end())
        if not module_literal or not _is_transport_module(module_literal[0]):
            continue
        specifiers.extend(
            specifier.strip()
            for specifier in match.group("specifiers").split(",")
            if specifier.strip()
        )
    return specifiers


def _brace_depth_at(code_source: str, offset: int) -> int:
    depth = 0
    for character in code_source[:offset]:
        if character == "{":
            depth += 1
        elif character == "}":
            depth = max(depth - 1, 0)
    return depth


def _matching_parenthesis(code_source: str, open_offset: int) -> int | None:
    depth = 0
    for index in range(open_offset, len(code_source)):
        character = code_source[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def _parameter_regions(code_source: str) -> list[tuple[int, int]]:
    regions: set[tuple[int, int]] = set()

    for pattern in (
        re.compile(rf"\bfunction\s*\*?(?:\s+{IDENTIFIER})?\s*\("),
        re.compile(r"\bcatch\s*\("),
    ):
        for match in pattern.finditer(code_source):
            open_offset = code_source.rfind("(", match.start(), match.end())
            close_offset = _matching_parenthesis(code_source, open_offset)
            if close_offset is not None:
                regions.add((open_offset + 1, close_offset))

    for open_offset, character in enumerate(code_source):
        if character != "(":
            continue
        close_offset = _matching_parenthesis(code_source, open_offset)
        if close_offset is None:
            continue
        following = close_offset + 1
        while following < len(code_source) and code_source[following].isspace():
            following += 1
        if code_source.startswith("=>", following):
            regions.add((open_offset + 1, close_offset))

    method_open = re.compile(rf"\b(?P<method>{IDENTIFIER})\s*\(")
    control_keywords = {"catch", "for", "if", "switch", "while", "with"}
    for match in method_open.finditer(code_source):
        if match.group("method") in control_keywords:
            continue
        open_offset = code_source.rfind("(", match.start(), match.end())
        close_offset = _matching_parenthesis(code_source, open_offset)
        if close_offset is None:
            continue
        following = close_offset + 1
        while following < len(code_source) and code_source[following].isspace():
            following += 1
        if following < len(code_source) and code_source[following] == "{":
            regions.add((open_offset + 1, close_offset))

    return sorted(regions)


def _import_binding_offsets(code_source: str, binding: str) -> list[int]:
    offsets: set[int] = set()
    for match in IMPORT_PREFIX.finditer(code_source):
        specifiers = match.group("specifiers")
        for specifier_match in re.finditer(
            rf"(?:^|,)\s*(?:type\s+)?(?:{IDENTIFIER}\s+as\s+)?"
            rf"(?P<local>{IDENTIFIER})\s*(?=,|$)",
            specifiers,
        ):
            if specifier_match.group("local") == binding:
                offsets.add(
                    match.start("specifiers") + specifier_match.start("local")
                )

    for pattern in (
        re.compile(rf"\bimport\s+(?!type\b)(?P<local>{IDENTIFIER})\s*(?=,|from\b)"),
        re.compile(rf"\bimport\s*\*\s*as\s*(?P<local>{IDENTIFIER})\b"),
    ):
        for match in pattern.finditer(code_source):
            if match.group("local") == binding:
                offsets.add(match.start("local"))
    return sorted(offsets)


def _binding_shadow_offsets(
    code_source: str,
    binding: str,
    canonical_name_offset: int | None,
) -> list[int]:
    """Find common declarations that can shadow the canonical transport."""

    offsets: set[int] = set()
    for match in VARIABLE_BINDING.finditer(code_source):
        if match.group("name") != binding:
            continue
        if canonical_name_offset is not None and match.start("name") == canonical_name_offset:
            continue
        offsets.add(match.start("name"))

    for pattern in (
        re.compile(
            rf"\b(?:async\s+)?function\s*\*?\s*(?P<name>{IDENTIFIER})\b"
        ),
        re.compile(
            rf"\b(?:class|enum|namespace|module)\s+(?P<name>{IDENTIFIER})\b"
        ),
    ):
        for match in pattern.finditer(code_source):
            if match.group("name") == binding:
                offsets.add(match.start("name"))

    for start, end in _parameter_regions(code_source):
        binding_match = re.search(
            rf"\b{re.escape(binding)}\b",
            code_source[start:end],
        )
        if binding_match:
            offsets.add(start + binding_match.start())

    destructuring_pattern = re.compile(
        r"\b(?:const|let|var)\s*(?P<pattern>[\{\[][^\n;=]*[\}\]])\s*=",
    )
    for match in destructuring_pattern.finditer(code_source):
        binding_match = re.search(
            rf"\b{re.escape(binding)}\b",
            match.group("pattern"),
        )
        if binding_match:
            offsets.add(match.start("pattern") + binding_match.start())

    for match in re.finditer(rf"\b{re.escape(binding)}\s*=>", code_source):
        offsets.add(match.start())
    offsets.update(_import_binding_offsets(code_source, binding))
    return sorted(offsets)


def _source_files(paths: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved.is_file() and resolved.suffix in SOURCE_SUFFIXES:
            files.add(resolved)
            continue
        if resolved.is_dir():
            for candidate in resolved.rglob("*"):
                if (
                    candidate.is_file()
                    and candidate.suffix in SOURCE_SUFFIXES
                    and "node_modules" not in candidate.parts
                ):
                    files.add(candidate.resolve())
    return sorted(files)


def _issue(
    path: Path,
    text: str,
    match: re.Match[str],
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "path": str(path),
        "line": _line_number(text, match.start()),
        "message": message,
    }


def _issue_at(path: Path, text: str, offset: int, code: str, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "path": str(path),
        "line": _line_number(text, offset),
        "message": message,
    }


def _registry_import_count(specifiers: list[str]) -> int:
    """Count direct, unaliased imports of registry-backed factory APIs."""

    return sum(specifier in TRANSPORT_FACTORY_APIS for specifier in specifiers)


def _collector_endpoint_names(comment_source: str, code_source: str) -> set[str]:
    """Find simple variables that are statically known to reference collector ingestion."""

    endpoint_names: set[str] = set()
    for match in ASSIGNMENT_PREFIX.finditer(code_source):
        literal = _literal_after(comment_source, match.end())
        if literal and re.search(r"/ingest(?:/batch)?(?:[/?#]|$)", literal[0]):
            endpoint_names.add(match.group("name"))

    assignment = re.compile(
        rf"\b(?:const|let|var)[ \t]+(?P<target>{IDENTIFIER})[ \t]*="
        rf"[ \t]*(?P<source>{IDENTIFIER})\b"
    )

    # Follow straightforward aliases so `const target = DEBUG_ENDPOINT` cannot
    # hide a direct collector fetch from the gate.
    changed = True
    while changed:
        changed = False
        for match in assignment.finditer(code_source):
            if (
                match.group("source") in endpoint_names
                and match.group("target") not in endpoint_names
            ):
                endpoint_names.add(match.group("target"))
                changed = True
    return endpoint_names


def _direct_ingest_fetch_offsets(comment_source: str, code_source: str) -> list[int]:
    offsets: list[int] = []
    for match in FETCH_CALLEE.finditer(code_source):
        literal = _literal_after(comment_source, match.end())
        if literal and re.search(r"/ingest(?:/batch)?(?:[/?#]|$)", literal[0]):
            offsets.append(match.start())
    return offsets


def _top_level_object_segments(code_source: str, object_start: int) -> list[str] | None:
    if object_start >= len(code_source) or code_source[object_start] != "{":
        return None

    segments: list[str] = []
    segment_start = object_start + 1
    brace_depth = 1
    paren_depth = 0
    bracket_depth = 0
    for index in range(object_start + 1, len(code_source)):
        character = code_source[index]
        if character == "{":
            brace_depth += 1
        elif character == "}":
            brace_depth -= 1
            if brace_depth == 0:
                segments.append(code_source[segment_start:index])
                return segments
        elif character == "(":
            paren_depth += 1
        elif character == ")":
            paren_depth = max(paren_depth - 1, 0)
        elif character == "[":
            bracket_depth += 1
        elif character == "]":
            bracket_depth = max(bracket_depth - 1, 0)
        elif (
            character == ","
            and brace_depth == 1
            and paren_depth == 0
            and bracket_depth == 0
        ):
            segments.append(code_source[segment_start:index])
            segment_start = index + 1
    return None


def _producer_call_uses_transport(
    code_source: str,
    call_end: int,
    transport_binding: str,
) -> bool:
    object_start = call_end
    while object_start < len(code_source) and code_source[object_start].isspace():
        object_start += 1
    segments = _top_level_object_segments(code_source, object_start)
    if segments is None:
        return False

    for segment in segments:
        compact = " ".join(segment.split())
        if re.fullmatch(
            rf"transport\s*:\s*{re.escape(transport_binding)}",
            compact,
        ):
            return True
        if transport_binding == "transport" and compact == "transport":
            return True
    return False


def _shared_producer_calls(
    code_source: str,
    imported_specifiers: list[str],
    transport_binding: str | None,
) -> tuple[list[int], list[int]]:
    verified: list[int] = []
    unverified: list[int] = []
    for api in sorted(set(imported_specifiers) & SHARED_PRODUCER_APIS):
        for match in re.finditer(rf"\b{re.escape(api)}\s*\(", code_source):
            if transport_binding and _producer_call_uses_transport(
                code_source,
                match.end(),
                transport_binding,
            ):
                verified.append(match.start())
            else:
                unverified.append(match.start())
    return verified, unverified


def _fetch_uses_collector_endpoint(argument: str, endpoint_names: set[str]) -> bool:
    compact = argument.strip()
    if any(re.search(rf"\b{re.escape(name)}\b", compact) for name in endpoint_names):
        return True

    # These names are collector-specific in debug instrumentation. A generic
    # application `endpoint` remains outside this conservative name check.
    return bool(
        re.search(
            r"\b(?:debug|collector|ingest)[A-Za-z0-9_$]*(?:Endpoint|Url)?\b"
            r"|\b(?:batchEndpoint|ingestEndpoint)\b",
            compact,
            re.IGNORECASE,
        )
    )


def _occurrence_state_names(text: str) -> set[str]:
    names: set[str] = set()
    for pattern in (
        STATE_COLLECTION_BINDING,
        STATE_BOOLEAN_BINDING,
        STATE_REF_BINDING,
    ):
        names.update(match.group("name") for match in pattern.finditer(text))

    declaration = re.compile(rf"\b(?:const|let|var)\s+(?P<name>{IDENTIFIER})\b")
    names.update(
        match.group("name")
        for match in declaration.finditer(text)
        if STATE_HINT.search(match.group("name"))
    )
    return names


def _guarded_statement(statement: str) -> tuple[str, str]:
    """Return a bounded if-body approximation and the following source."""

    leading = len(statement) - len(statement.lstrip())
    start = leading
    if start >= len(statement):
        return "", ""
    if statement[start] != "{":
        end = statement.find(";", start)
        if end == -1:
            end = statement.find("\n", start)
        if end == -1:
            end = min(len(statement), start + 1000)
        else:
            end += 1
        return statement[start:end], statement[end:]

    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start, min(len(statement), start + 4000)):
        character = statement[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"', "`"}:
            quote = character
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return statement[start : index + 1], statement[index + 1 :]
    return statement[start : start + 1000], statement[start + 1000 :]


def _occurrence_gate_offsets(text: str) -> list[int]:
    """Locate conservative, syntax-shaped occurrence gates around probe sinks.

    This is not a JavaScript proof engine. It rejects common remembered-state
    gates and requires review when those shapes control an emitter call.
    """

    offsets: set[int] = {
        match.start()
        for pattern in (ONCE_WRAPPER, REDUCING_WRAPPER)
        for match in pattern.finditer(text)
    }
    state_names = _occurrence_state_names(text)
    collection_names = {
        match.group("name") for match in STATE_COLLECTION_BINDING.finditer(text)
    }

    for match in IF_CONDITION.finditer(text):
        condition = match.group("condition")
        condition_names = set(re.findall(rf"\b{IDENTIFIER}\b", condition))
        remembered_state = condition_names & state_names
        membership_state = {
            name
            for name in collection_names
            if re.search(rf"\b{re.escape(name)}\.(?:has|get)\s*\(", condition)
        }
        selects_occurrences = bool(OCCURRENCE_SELECTION_CONDITION.search(condition))
        if not remembered_state and not membership_state and not selects_occurrences:
            continue

        body, following = _guarded_statement(text[match.end() :])
        body_has_sink = bool(RECORD_SINK.search(body))
        returns_before_following_sink = (
            bool(re.search(r"\breturn\b", body))
            and bool(RECORD_SINK.search(following[:1600]))
        )
        if body_has_sink or returns_before_following_sink:
            offsets.add(match.start())

    return sorted(offsets)


def validate(paths: list[Path]) -> dict[str, Any]:
    files = _source_files(paths)
    issues: list[dict[str, Any]] = []
    transport_imports = 0
    transport_calls = 0
    record_safe_calls = 0
    shared_producer_calls = 0
    source_views: list[tuple[Path, str, str, str, list[str]]] = []
    transport_bindings: list[tuple[Path, str, re.Match[str]]] = []
    nested_transport_bindings: list[tuple[Path, str, re.Match[str]]] = []

    for input_path in paths:
        resolved = input_path.resolve()
        if not resolved.exists():
            issues.append(
                {
                    "code": "missing_source_path",
                    "path": str(resolved),
                    "line": 1,
                    "message": "every declared instrumentation source path must exist",
                }
            )
        elif resolved.is_file() and resolved.suffix not in SOURCE_SUFFIXES:
            issues.append(
                {
                    "code": "unsupported_source_path",
                    "path": str(resolved),
                    "line": 1,
                    "message": "instrumentation source files must be JavaScript or TypeScript",
                }
            )

    # 1. Build lexical views first so comments and literal text cannot satisfy
    # wiring checks, while endpoint rules can still inspect real code strings.
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(
                {
                    "code": "unreadable_source",
                    "path": str(path),
                    "line": 1,
                    "message": str(exc),
                }
            )
            continue

        # The copied transport owns acknowledged collector I/O, queueing, and
        # replay protection. This validator audits only instrumentation callers.
        if path.name == "browser-debug-transport.mjs":
            continue

        comment_source = _mask_js_comments(text)
        code_source = _mask_js_strings(_mask_js_regex_literals(comment_source))
        imported_specifiers = _transport_import_specifiers(
            comment_source,
            code_source,
        )
        source_views.append(
            (path, text, comment_source, code_source, imported_specifiers)
        )
        transport_imports += _registry_import_count(imported_specifiers)
        definition_matches = list(LOCAL_TRANSPORT_DEFINITION.finditer(code_source))
        transport_calls += max(
            len(REGISTRY_TRANSPORT_CALL.findall(code_source)) - len(definition_matches),
            0,
        )
        for match in TRANSPORT_BINDING.finditer(code_source):
            target = transport_bindings if _brace_depth_at(
                code_source,
                match.start(),
            ) == 0 else nested_transport_bindings
            target.append((path, text, match))

    transport_binding = (
        transport_bindings[0][2].group("name")
        if len(transport_bindings) == 1
        else None
    )

    # 2. Audit usage and forbidden shapes against executable-code views only.
    for path, text, comment_source, code_source, imported_specifiers in source_views:
        for offset in _ambiguous_slash_brace_offsets(code_source):
            issues.append(
                _issue_at(
                    path,
                    text,
                    offset,
                    "ambiguous_regex_brace",
                    (
                        "an unclassified slash-delimited expression contains a brace; "
                        "rewrite it so canonical transport scope can fail closed"
                    ),
                )
            )

        definition_matches = list(LOCAL_TRANSPORT_DEFINITION.finditer(code_source))
        for match in definition_matches:
            issues.append(
                _issue(
                    path,
                    text,
                    match,
                    "local_transport_factory",
                    "use the registry-backed API imported from browser-debug-transport.mjs",
                )
            )

        if transport_binding:
            canonical_name_offset = None
            canonical_path, _, canonical_match = transport_bindings[0]
            if path == canonical_path:
                canonical_name_offset = canonical_match.start("name")
            for offset in _binding_shadow_offsets(
                code_source,
                transport_binding,
                canonical_name_offset,
            ):
                issues.append(
                    _issue_at(
                        path,
                        text,
                        offset,
                        "transport_binding_shadow",
                        "the canonical shared transport binding cannot be redeclared or used as a parameter",
                    )
                )

        if transport_binding:
            record_safe_calls += len(
                re.findall(
                    rf"\b{re.escape(transport_binding)}\.recordSafe\s*\(",
                    code_source,
                )
            )
        verified_producers, unverified_producers = _shared_producer_calls(
            code_source,
            imported_specifiers,
            transport_binding,
        )
        shared_producer_calls += len(verified_producers)
        for offset in unverified_producers:
            issues.append(
                _issue_at(
                    path,
                    text,
                    offset,
                    "producer_transport_binding",
                    "producer API options.transport must directly reference the shared transport binding",
                )
            )

        endpoint_names = _collector_endpoint_names(comment_source, code_source)
        direct_fetch_offsets = set(
            _direct_ingest_fetch_offsets(comment_source, code_source)
        )
        for offset in sorted(direct_fetch_offsets):
            issues.append(
                _issue_at(
                    path,
                    text,
                    offset,
                    "direct_ingest_fetch",
                    "post browser evidence through the shared acknowledged transport",
                )
            )
        for match in FETCH_CALL.finditer(code_source):
            if match.start() in direct_fetch_offsets:
                continue
            if _fetch_uses_collector_endpoint(match.group("argument"), endpoint_names):
                issues.append(
                    _issue(
                        path,
                        text,
                        match,
                        "direct_ingest_fetch",
                        "collector ingestion fetch bypasses the shared acknowledged transport",
                    )
                )
        for pattern, code, message in (
            (
                KEEPALIVE_TRUE,
                "steady_keepalive",
                "steady browser evidence delivery must use keepalive: false",
            ),
            (
                SEND_BEACON,
                "send_beacon",
                "sendBeacon cannot provide the required persisted acknowledgement",
            ),
            (
                SILENT_PROMISE_CATCH,
                "silent_transport_error",
                "surface transport failure and mark the run incomplete",
            ),
            (
                OCCURRENCE_REDUCTION_MARKER,
                "occurrence_reduction",
                "remove probe occurrence gating; emit every active probe occurrence",
            ),
        ):
            for match in pattern.finditer(code_source):
                issues.append(_issue(path, text, match, code, message))
        marker_offsets = {
            match.start()
            for match in OCCURRENCE_REDUCTION_MARKER.finditer(code_source)
        }
        for offset in _occurrence_gate_offsets(code_source):
            if offset in marker_offsets:
                continue
            issues.append(
                _issue_at(
                    path,
                    text,
                    offset,
                    "occurrence_reduction",
                    (
                        "remembered-state gate controls a probe emitter; static validation "
                        "cannot prove all occurrences survive"
                    ),
                )
            )

    if not files:
        issues.append(
            {
                "code": "no_sources",
                "path": "",
                "line": 1,
                "message": "provide the complete browser instrumentation source set",
            }
        )
    if transport_imports != 1:
        issues.append(
            {
                "code": "transport_import_count",
                "path": "",
                "line": 1,
                "message": (
                    "directly import exactly one registry-backed browser transport API "
                    "outside the copied asset "
                    f"(found {transport_imports})"
                ),
            }
        )
    if transport_calls != 1:
        issues.append(
            {
                "code": "transport_instance_count",
                "path": "",
                "line": 1,
                "message": (
                    "acquire the registry-backed browser transport at exactly one call site "
                    f"(found {transport_calls})"
                ),
            }
        )
    if len(transport_bindings) != 1:
        issues.append(
            {
                "code": "transport_binding_count",
                "path": "",
                "line": 1,
                "message": (
                    "assign the single registry acquisition directly to exactly one "
                    "canonical `const` binding "
                    f"(found {len(transport_bindings)})"
                ),
            }
        )
    for path, text, match in nested_transport_bindings:
        issues.append(
            _issue(
                path,
                text,
                match,
                "transport_binding_scope",
                "the registry acquisition must be assigned to a top-level canonical const binding",
            )
        )
    if record_safe_calls == 0 and shared_producer_calls == 0:
        issues.append(
            {
                "code": "transport_unused",
                "path": "",
                "line": 1,
                "message": (
                    "active probes must call the shared transport.recordSafe or install "
                    "a shared producer through the bundled API"
                ),
            }
        )

    return {
        "ok": not issues,
        "assurance": "conservative-static-gate-not-runtime-proof",
        "filesChecked": len(files),
        "transportImports": transport_imports,
        "transportInstances": transport_calls,
        "recordSafeCallSites": record_safe_calls,
        "sharedProducerCallSites": shared_producer_calls,
        "issues": issues,
    }


def _format_text(report: dict[str, Any]) -> str:
    result = "PASS" if report["ok"] else "FAIL"
    lines = [
        f"{result}: browser debug instrumentation validation",
        f"files checked: {report['filesChecked']}",
        f"transport imports: {report['transportImports']}",
        f"registry acquisition call sites: {report['transportInstances']}",
        f"recordSafe call sites: {report['recordSafeCallSites']}",
        f"shared producer call sites: {report['sharedProducerCallSites']}",
        "scope: conservative static gate; runtime ACK/cardinality proof is still required",
    ]
    for issue in report["issues"]:
        location = issue["path"] or "<source-set>"
        lines.append(
            f"- {location}:{issue['line']} [{issue['code']}] {issue['message']}"
        )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate(args.paths)
    if args.format == "json":
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(_format_text(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
