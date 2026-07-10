#!/usr/bin/env python3
"""State and log window helpers for the local log collector."""

from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import threading
import time
from typing import Any

from collector_ide import resolve_location

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
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _safe_sequence(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _normalize_payload_hypothesis_ids(payload: dict[str, Any]) -> list[str]:
    normalized: list[str] = []
    singular = payload.get('hypothesisId')
    if isinstance(singular, str) and singular.strip():
        normalized.append(singular.strip())

    plural = payload.get('hypothesisIds')
    if isinstance(plural, list):
        for item in plural:
            if not isinstance(item, str):
                continue
            text = item.strip()
            if text and text not in normalized:
                normalized.append(text)
    return normalized


def reset_log_cache(service: Any) -> None:
    service.entries = []
    service.run_counts = Counter()
    service.hypothesis_counts = Counter()
    service.probe_counts = Counter()
    service.correlation_counts = Counter()
    service.event_counts = Counter()
    service.location_counts = Counter()
    service.location_records: dict[str, dict[str, Any]] = {}
    if not hasattr(service, 'tracked_location_records'):
        service.tracked_location_records = {}
    service.invalid_lines = 0
    service.last_event = None
    service.file_size_bytes = 0
    service.file_updated_at = None
    service.location_state_updated_at = None
    service.physical_line_count = 0


def _build_entry_metadata(
    payload: dict[str, Any],
    *,
    entry_index: int,
    line_number: int,
    offset: int,
    size: int,
) -> dict[str, Any]:
    hypothesis_ids = _normalize_payload_hypothesis_ids(payload)
    return {
        'entryIndex': entry_index,
        'lineNumber': line_number,
        'offset': offset,
        'size': size,
        'runId': _string_or_empty(payload.get('runId')),
        'correlationId': _string_or_empty(payload.get('correlationId')),
        'sequence': _safe_sequence(payload.get('sequence')),
        'probeId': _string_or_empty(payload.get('probeId')),
        'hypothesisId': hypothesis_ids[0] if hypothesis_ids else '',
        'hypothesisIds': hypothesis_ids,
        'location': _string_or_empty(payload.get('location')),
        'phase': _string_or_empty(payload.get('phase')),
        'event': _string_or_empty(payload.get('event')),
        'level': _string_or_empty(payload.get('level')),
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
    if entry['correlationId']:
        service.correlation_counts[entry['correlationId']] += 1
    if entry['probeId']:
        service.probe_counts[entry['probeId']] += 1
    if entry['event']:
        service.event_counts[entry['event']] += 1
    for hypothesis_id in entry['hypothesisIds']:
        service.hypothesis_counts[hypothesis_id] += 1
    _update_location_cache(service, entry)
    service.last_event = payload
    return entry


def _update_location_cache(service: Any, entry: dict[str, Any]) -> None:
    location = entry['location']
    if not location:
        return

    service.location_counts[location] += 1
    record = service.location_records.get(location)
    if record is None:
        record = {
            'location': location,
            'count': 0,
            'lastTimestamp': None,
            'lastEntryIndex': -1,
            'lastLineNumber': None,
            'runIds': set(),
            'hypothesisIds': set(),
            'probeIds': set(),
        }
        service.location_records[location] = record

    record['count'] += 1
    record['lastTimestamp'] = entry['timestamp']
    record['lastEntryIndex'] = entry['entryIndex']
    record['lastLineNumber'] = entry['lineNumber']

    if entry['runId']:
        record['runIds'].add(entry['runId'])
    record['hypothesisIds'].update(entry['hypothesisIds'])
    if entry['probeId']:
        record['probeIds'].add(entry['probeId'])


def _normalize_string_list(
    value: Any,
    *,
    array_error: str,
    item_error: str,
) -> list[str]:
    if value in (None, ''):
        return []
    if not isinstance(value, list):
        raise ValueError(array_error)

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError(item_error)
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _normalize_probe_ids(item: dict[str, Any]) -> list[str]:
    probe_ids = _normalize_string_list(
        item.get('probeIds'),
        array_error='tracked_location_probe_ids_must_be_array',
        item_error='tracked_location_probe_id_must_be_string',
    )
    singular = item.get('probeId')
    if singular not in (None, ''):
        if not isinstance(singular, str):
            raise ValueError('tracked_location_probe_id_must_be_string')
        text = singular.strip()
        if text and text not in probe_ids:
            probe_ids.append(text)
    return probe_ids


def _normalize_tracked_location_item(item: Any) -> dict[str, Any]:
    if isinstance(item, str):
        location = item.strip()
        if not location:
            raise ValueError('tracked_location_required')
        return {
            'location': location,
            'hypothesisIds': [],
            'probeIds': [],
        }

    if not isinstance(item, dict):
        raise ValueError('tracked_location_item_must_be_string_or_object')

    location = item.get('location')
    if not isinstance(location, str) or not location.strip():
        raise ValueError('tracked_location_required')

    return {
        'location': location.strip(),
        'hypothesisIds': _normalize_string_list(
            item.get('hypothesisIds'),
            array_error='tracked_location_hypothesis_ids_must_be_array',
            item_error='tracked_location_hypothesis_id_must_be_string',
        ),
        'probeIds': _normalize_probe_ids(item),
    }


def _validate_tracked_location(service: Any, item: dict[str, Any]) -> None:
    resolved_location = resolve_location(item['location'], service.workspace_root)
    parse_error = resolved_location.get('parseError') or ''
    if parse_error:
        raise ValueError(f'tracked_location_invalid: {item["location"]}: {parse_error}')
    if not resolved_location.get('exists'):
        raise ValueError(f'tracked_location_missing_file: {item["location"]}')


def load_tracked_locations(service: Any) -> None:
    if not getattr(service, 'location_state_file', None):
        service.tracked_location_records = {}
        return

    if not service.location_state_file.exists():
        service.tracked_location_records = {}
        return

    try:
        payload: Any = json.loads(service.location_state_file.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        service.tracked_location_records = {}
        return

    if not isinstance(payload, dict):
        service.tracked_location_records = {}
        return

    payload_session_id = payload.get('sessionId')
    if payload_session_id not in (None, '', service.session_id):
        service.tracked_location_records = {}
        return

    payload_log_file = payload.get('logFile')
    if payload_log_file not in (None, '', str(service.log_file)):
        service.tracked_location_records = {}
        return

    raw_locations = payload.get('trackedLocations')
    if not isinstance(raw_locations, list):
        service.tracked_location_records = {}
        return

    tracked_records: dict[str, dict[str, Any]] = {}
    for raw_item in raw_locations:
        try:
            item = _normalize_tracked_location_item(raw_item)
            _validate_tracked_location(service, item)
        except ValueError:
            continue

        record = tracked_records.get(item['location'])
        if record is None:
            tracked_records[item['location']] = {
                'location': item['location'],
                'hypothesisIds': set(item['hypothesisIds']),
                'probeIds': set(item['probeIds']),
                'registeredAt': _safe_timestamp(raw_item.get('registeredAt'))
                if isinstance(raw_item, dict)
                else None,
                'updatedAt': _safe_timestamp(raw_item.get('updatedAt'))
                if isinstance(raw_item, dict)
                else None,
            }
            continue

        record['hypothesisIds'].update(item['hypothesisIds'])
        record['probeIds'].update(item['probeIds'])
        if record['registeredAt'] is None and isinstance(raw_item, dict):
            record['registeredAt'] = _safe_timestamp(raw_item.get('registeredAt'))
        if isinstance(raw_item, dict):
            next_updated_at = _safe_timestamp(raw_item.get('updatedAt'))
            if next_updated_at is not None:
                record['updatedAt'] = next_updated_at

    service.tracked_location_records = tracked_records


def sync_tracked_locations(service: Any, raw_locations: Any) -> None:
    if not isinstance(raw_locations, list):
        raise ValueError('locations_must_be_array')

    updated_at = int(time.time() * 1000)
    existing_records = getattr(service, 'tracked_location_records', {})
    tracked_records: dict[str, dict[str, Any]] = {}

    for raw_item in raw_locations:
        item = _normalize_tracked_location_item(raw_item)
        _validate_tracked_location(service, item)
        record = tracked_records.get(item['location'])
        if record is None:
            existing_record = existing_records.get(item['location'])
            existing_registered_at = (
                existing_record.get('registeredAt')
                if isinstance(existing_record, dict)
                else None
            )
            tracked_records[item['location']] = {
                'location': item['location'],
                'hypothesisIds': set(item['hypothesisIds']),
                'probeIds': set(item['probeIds']),
                'registeredAt': (
                    existing_registered_at
                    if existing_registered_at is not None
                    else updated_at
                ),
                'updatedAt': updated_at,
            }
            continue

        record['hypothesisIds'].update(item['hypothesisIds'])
        record['probeIds'].update(item['probeIds'])
        record['updatedAt'] = updated_at

    service.tracked_location_records = tracked_records
    write_location_state_file(service)


def hydrate_log_cache(service: Any) -> None:
    load_tracked_locations(service)
    reset_log_cache(service)
    if not service.log_file.exists():
        write_location_state_file(service)
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
    write_location_state_file(service)


def sync_log_cache(service: Any) -> None:
    if not service.log_file.exists():
        if service.entries or service.invalid_lines or service.file_size_bytes:
            reset_log_cache(service)
            write_location_state_file(service)
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
        'correlationId': entry['correlationId'],
        'sequence': entry['sequence'],
        'probeId': entry['probeId'],
        'hypothesisId': entry['hypothesisId'],
        'hypothesisIds': entry['hypothesisIds'],
        'location': entry['location'],
        'phase': entry['phase'],
        'event': entry['event'],
        'level': entry['level'],
        'message': entry['message'],
        'sessionId': entry['sessionId'],
        'timestamp': entry['timestamp'],
    }


def _location_sort_key(record: dict[str, Any]) -> tuple[int, int, str]:
    last_timestamp = record['lastTimestamp']
    tracked_timestamp = record.get('updatedAt') or record.get('registeredAt')
    timestamp_key = -(last_timestamp if last_timestamp is not None else tracked_timestamp or -1)
    return (-record['lastEntryIndex'], timestamp_key, record['location'])


def _build_tracked_location_list(service: Any) -> list[dict[str, Any]]:
    ordered_records = sorted(
        service.tracked_location_records.values(),
        key=lambda record: (
            -((record.get('updatedAt') or record.get('registeredAt')) or -1),
            record['location'],
        ),
    )
    return [
        {
            'location': record['location'],
            'hypothesisIds': sorted(record['hypothesisIds']),
            'probeIds': sorted(record.get('probeIds', set())),
            'registeredAt': record.get('registeredAt'),
            'updatedAt': record.get('updatedAt'),
        }
        for record in ordered_records
    ]


def _build_active_location_records(service: Any) -> list[dict[str, Any]]:
    active_records: dict[str, dict[str, Any]] = {}

    for tracked_record in service.tracked_location_records.values():
        active_record = {
            'location': tracked_record['location'],
            'count': 0,
            'lastTimestamp': None,
            'lastEntryIndex': -1,
            'lastLineNumber': None,
            'runIds': set(),
            'hypothesisIds': set(tracked_record['hypothesisIds']),
            'probeIds': set(tracked_record.get('probeIds', set())),
            'tracked': True,
            'registeredAt': tracked_record.get('registeredAt'),
            'updatedAt': tracked_record.get('updatedAt'),
        }
        runtime_record = service.location_records.get(tracked_record['location'])
        if runtime_record is not None:
            active_record['count'] = runtime_record['count']
            active_record['lastTimestamp'] = runtime_record['lastTimestamp']
            active_record['lastEntryIndex'] = runtime_record['lastEntryIndex']
            active_record['lastLineNumber'] = runtime_record['lastLineNumber']
            active_record['runIds'].update(runtime_record['runIds'])
            active_record['hypothesisIds'].update(runtime_record['hypothesisIds'])
            active_record['probeIds'].update(runtime_record.get('probeIds', set()))
        active_records[tracked_record['location']] = active_record

    return sorted(active_records.values(), key=_location_sort_key)


def _build_location_list(service: Any) -> list[dict[str, Any]]:
    ordered_records = _build_active_location_records(service)
    return [
        {
            'location': record['location'],
            'count': record['count'],
            'lastTimestamp': record['lastTimestamp'],
            'lastEntryIndex': record['lastEntryIndex'],
            'lastLineNumber': record['lastLineNumber'],
            'runIds': sorted(record['runIds']),
            'hypothesisIds': sorted(record['hypothesisIds']),
            'probeIds': sorted(record.get('probeIds', set())),
            'tracked': bool(record.get('tracked')),
            'registeredAt': record.get('registeredAt'),
            'updatedAt': record.get('updatedAt'),
        }
        for record in ordered_records
    ]


def build_location_state_payload(service: Any) -> dict[str, Any]:
    merged_locations = _build_location_list(service)
    return {
        'sessionId': service.session_id,
        'logFile': str(service.log_file),
        'locationStateFile': (
            str(service.location_state_file) if service.location_state_file else None
        ),
        'fileUpdatedAt': service.file_updated_at,
        'invalidLines': service.invalid_lines,
        'updatedAt': int(time.time() * 1000),
        'totalEntries': len(service.entries),
        'uniqueLocations': len(merged_locations),
        'trackedLocationCount': len(service.tracked_location_records),
        'lastEntry': _build_log_list_entry(service.entries[-1]) if service.entries else None,
        'trackedLocations': _build_tracked_location_list(service),
        'locations': merged_locations,
    }


def _mark_location_state_written(service: Any) -> None:
    schedule_lock = getattr(service, 'location_state_schedule_lock', None)
    timer = None
    if schedule_lock is None:
        service.location_state_dirty = False
        service.location_state_last_write_monotonic = time.monotonic()
        return

    with schedule_lock:
        service.location_state_dirty = False
        service.location_state_last_write_monotonic = time.monotonic()
        timer = getattr(service, 'location_state_timer', None)
        service.location_state_timer = None

    if timer is not None and timer is not threading.current_thread():
        timer.cancel()


def write_location_state_file(service: Any) -> None:
    if not getattr(service, 'location_state_file', None):
        return

    payload = build_location_state_payload(service)
    temp_path = service.location_state_file.with_suffix(f'{service.location_state_file.suffix}.tmp')
    temp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding='utf-8')
    os.replace(temp_path, service.location_state_file)
    service.location_state_updated_at = payload['updatedAt']
    _mark_location_state_written(service)


def _scheduled_location_state_flush(service: Any) -> None:
    with service.write_lock:
        schedule_lock = getattr(service, 'location_state_schedule_lock', None)
        if schedule_lock is None:
            write_location_state_file(service)
            return
        with schedule_lock:
            service.location_state_timer = None
            dirty = bool(getattr(service, 'location_state_dirty', False))
        if dirty:
            write_location_state_file(service)


def schedule_location_state_file_write(service: Any) -> None:
    if not getattr(service, 'location_state_file', None):
        return

    flush_ms = max(int(getattr(service, 'location_state_flush_ms', 0)), 0)
    if flush_ms == 0:
        write_location_state_file(service)
        return

    schedule_lock = getattr(service, 'location_state_schedule_lock', None)
    if schedule_lock is None:
        write_location_state_file(service)
        return

    write_now = False
    with schedule_lock:
        service.location_state_dirty = True
        existing_timer = getattr(service, 'location_state_timer', None)
        if existing_timer is not None and existing_timer.is_alive():
            return

        last_write = float(getattr(service, 'location_state_last_write_monotonic', 0.0))
        elapsed = time.monotonic() - last_write
        delay = max((flush_ms / 1000.0) - elapsed, 0.0)
        if delay <= 0:
            service.location_state_timer = None
            write_now = True
        else:
            timer = threading.Timer(delay, _scheduled_location_state_flush, args=(service,))
            timer.daemon = True
            service.location_state_timer = timer
            timer.start()

    if write_now:
        write_location_state_file(service)


def flush_location_state_file(service: Any) -> None:
    with service.write_lock:
        if getattr(service, 'location_state_dirty', False):
            write_location_state_file(service)
        elif getattr(service, 'location_state_file', None) and not service.location_state_file.exists():
            write_location_state_file(service)


def clear_log_file(service: Any) -> None:
    service.log_file.write_text('', encoding='utf-8')
    reset_log_cache(service)
    stat = service.log_file.stat()
    service.file_size_bytes = stat.st_size
    service.file_updated_at = int(stat.st_mtime * 1000)
    write_location_state_file(service)


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
        'workspaceRoot': str(service.workspace_root),
        'configFile': str(service.config_file),
        'locationStateFile': (
            str(service.location_state_file) if service.location_state_file else None
        ),
        'locationStateFlushMs': int(getattr(service, 'location_state_flush_ms', 0)),
        'serviceLogFile': str(service.service_log_file) if service.service_log_file else None,
        'ownedArtifacts': service.owned_artifacts,
        'endpoint': service.endpoint_url,
        'batchEndpoint': service.batch_endpoint_url,
        'dashboardUrl': service.dashboard_url,
        'dashboardToken': service.dashboard_token,
        'stateUrl': service.state_url,
        'logsUrl': service.logs_url,
        'logDetailUrl': service.log_detail_url,
        'locationsUrl': service.locations_url,
        'syncLocationsUrl': service.sync_locations_url,
        'configUrl': service.config_url,
        'dashboardFrontendOpenedUrl': service.dashboard_frontend_opened_url,
        'dashboardFrontendOpenFailedUrl': service.dashboard_frontend_open_failed_url,
        'dashboardFrontendOpenRecorded': service.dashboard_frontend_opened_at is not None,
        'dashboardFrontendOpenedAt': service.dashboard_frontend_opened_at,
        'dashboardFrontendOpenFailureCount': service.dashboard_frontend_open_failure_count,
        'dashboardFrontendOpenLastFailureAt': service.dashboard_frontend_open_last_failure_at,
        'dashboardFrontendOpenLastError': service.dashboard_frontend_open_last_error,
        'dashboardFrontendOpenLastFailedUrl': service.dashboard_frontend_open_last_failed_url,
        'openLocationUrl': service.open_location_url,
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
        merged_locations = _build_active_location_records(service)
        summary = {
            'totalEntries': len(service.entries),
            'uniqueLocations': len(merged_locations),
            'trackedLocationCount': len(service.tracked_location_records),
            'invalidLines': service.invalid_lines,
            'fileSizeBytes': service.file_size_bytes,
            'fileUpdatedAt': service.file_updated_at,
            'locationStateUpdatedAt': service.location_state_updated_at,
            'lastEvent': service.last_event,
            'runCounts': compact_count_pairs(service.run_counts),
            'correlationCounts': compact_count_pairs(service.correlation_counts),
            'probeCounts': compact_count_pairs(service.probe_counts),
            'hypothesisCounts': compact_count_pairs(service.hypothesis_counts),
            'eventCounts': compact_count_pairs(service.event_counts),
            'locationCounts': compact_count_pairs(service.location_counts),
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
