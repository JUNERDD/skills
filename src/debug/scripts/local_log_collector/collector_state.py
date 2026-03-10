#!/usr/bin/env python3
"""State and log window helpers for the local log collector."""

from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_LOG_WINDOW_LIMIT = 120
MAX_LOG_WINDOW_LIMIT = 300


def compact_count_pairs(counter: Counter[str]) -> list[dict[str, Any]]:
    return [
        {'name': name, 'count': count}
        for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def _string_or_empty(value: Any) -> str:
    if value in (None, ''):
        return ''
    return str(value)


def _safe_timestamp(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    return None


def reset_log_cache(service: Any) -> None:
    service.entries = []
    service.run_counts = Counter()
    service.hypothesis_counts = Counter()
    service.invalid_lines = 0
    service.last_event = None
    service.file_size_bytes = 0
    service.file_updated_at = None
    service.physical_line_count = 0


def _build_entry_metadata(
    payload: dict[str, Any],
    *,
    entry_index: int,
    line_number: int,
    offset: int,
    size: int,
) -> dict[str, Any]:
    return {
        'entryIndex': entry_index,
        'lineNumber': line_number,
        'offset': offset,
        'size': size,
        'runId': _string_or_empty(payload.get('runId')),
        'hypothesisId': _string_or_empty(payload.get('hypothesisId')),
        'location': _string_or_empty(payload.get('location')),
        'message': _string_or_empty(payload.get('message')),
        'sessionId': _string_or_empty(payload.get('sessionId')),
        'timestamp': _safe_timestamp(payload.get('timestamp')),
    }


def append_entry_to_cache(
    service: Any,
    payload: dict[str, Any],
    *,
    offset: int,
    size: int,
    line_number: int | None = None,
) -> dict[str, Any]:
    if line_number is None:
        service.physical_line_count += 1
        line_number = service.physical_line_count
    else:
        service.physical_line_count = max(service.physical_line_count, line_number)

    entry = _build_entry_metadata(
        payload,
        entry_index=len(service.entries),
        line_number=line_number,
        offset=offset,
        size=size,
    )
    service.entries.append(entry)

    if entry['runId']:
        service.run_counts[entry['runId']] += 1
    if entry['hypothesisId']:
        service.hypothesis_counts[entry['hypothesisId']] += 1
    service.last_event = payload
    return entry


def hydrate_log_cache(service: Any) -> None:
    reset_log_cache(service)
    if not service.log_file.exists():
        return

    offset = 0
    with service.log_file.open('rb') as file:
        while True:
            raw_line = file.readline()
            if raw_line == b'':
                break

            current_offset = offset
            offset += len(raw_line)
            decoded_line = raw_line.decode('utf-8', errors='replace').strip()
            if not decoded_line:
                continue

            service.physical_line_count += 1
            line_number = service.physical_line_count

            try:
                payload: Any = json.loads(decoded_line)
            except json.JSONDecodeError:
                service.invalid_lines += 1
                continue

            if not isinstance(payload, dict):
                service.invalid_lines += 1
                continue

            append_entry_to_cache(
                service,
                payload,
                offset=current_offset,
                size=len(raw_line),
                line_number=line_number,
            )

    stat = service.log_file.stat()
    service.file_size_bytes = stat.st_size
    service.file_updated_at = int(stat.st_mtime * 1000)


def sync_log_cache(service: Any) -> None:
    if not service.log_file.exists():
        if service.entries or service.invalid_lines or service.file_size_bytes:
            reset_log_cache(service)
        return

    stat = service.log_file.stat()
    file_size_bytes = stat.st_size
    file_updated_at = int(stat.st_mtime * 1000)
    if file_size_bytes == service.file_size_bytes and file_updated_at == service.file_updated_at:
        return

    hydrate_log_cache(service)


def _read_payload_at_entry(log_file: Path, entry: dict[str, Any]) -> dict[str, Any] | None:
    with log_file.open('rb') as file:
        file.seek(entry['offset'])
        raw_line = file.read(entry['size'])

    try:
        payload = json.loads(raw_line.decode('utf-8', errors='replace').strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _build_log_list_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        'entryIndex': entry['entryIndex'],
        'lineNumber': entry['lineNumber'],
        'runId': entry['runId'],
        'hypothesisId': entry['hypothesisId'],
        'location': entry['location'],
        'message': entry['message'],
        'sessionId': entry['sessionId'],
        'timestamp': entry['timestamp'],
    }


def _slice_entries(
    entries: list[dict[str, Any]],
    *,
    offset: int,
    limit: int,
    order: str,
) -> list[dict[str, Any]]:
    if order == 'asc':
        return entries[offset: offset + limit]

    total_entries = len(entries)
    end = max(total_entries - offset, 0)
    start = max(end - limit, 0)
    window = entries[start:end]
    window.reverse()
    return window


def build_service_payload(service: Any) -> dict[str, Any]:
    return {
        'sessionId': service.session_id,
        'logFile': str(service.log_file),
        'endpoint': service.endpoint_url,
        'dashboardUrl': service.dashboard_url,
        'stateUrl': service.state_url,
        'logsUrl': service.logs_url,
        'logDetailUrl': service.log_detail_url,
        'clearUrl': service.clear_url,
        'shutdownUrl': service.shutdown_url,
        'healthUrl': service.health_url,
        'dashboardOpenAttempted': service.dashboard_open_attempted,
        'dashboardOpenSucceeded': service.dashboard_open_succeeded,
        'dashboardOpenError': service.dashboard_open_error,
        'pid': os.getpid(),
        'startedAt': service.started_at,
    }


def build_state_response(service: Any) -> dict[str, Any]:
    with service.write_lock:
        sync_log_cache(service)
        summary = {
            'totalEntries': len(service.entries),
            'invalidLines': service.invalid_lines,
            'fileSizeBytes': service.file_size_bytes,
            'fileUpdatedAt': service.file_updated_at,
            'lastEvent': service.last_event,
            'runCounts': compact_count_pairs(service.run_counts),
            'hypothesisCounts': compact_count_pairs(service.hypothesis_counts),
        }

    return {
        'ok': True,
        'status': 'stopping' if service.shutdown_requested_at else 'running',
        'service': build_service_payload(service),
        'summary': summary,
    }


def build_logs_response(
    service: Any,
    *,
    offset: int,
    limit: int,
    order: str = 'desc',
) -> dict[str, Any]:
    with service.write_lock:
        sync_log_cache(service)
        window = _slice_entries(service.entries, offset=offset, limit=limit, order=order)
        entries = [_build_log_list_entry(entry) for entry in window]
        total_entries = len(service.entries)

    return {
        'ok': True,
        'order': order,
        'offset': offset,
        'limit': limit,
        'totalEntries': total_entries,
        'entries': entries,
        'hasMore': offset + len(entries) < total_entries,
    }


def build_log_detail_response(service: Any, *, entry_index: int) -> dict[str, Any]:
    with service.write_lock:
        sync_log_cache(service)
        if entry_index < 0 or entry_index >= len(service.entries):
            return {'ok': False, 'error': 'entry_not_found'}

        entry = service.entries[entry_index]
        payload = _read_payload_at_entry(service.log_file, entry)
        payload_text = json.dumps(payload, ensure_ascii=False, indent=2) if payload is not None else ''

    return {
        'ok': True,
        'entry': {
            **_build_log_list_entry(entry),
            'payload': payload,
            'payloadText': payload_text,
        },
    }


def build_ready_payload(service: Any) -> dict[str, Any]:
    payload = build_service_payload(service)
    payload.update(
        {
            'host': service.server_address[0],
            'port': service.server_port,
            'readyFile': str(service.ready_file) if service.ready_file else None,
        },
    )
    return payload
