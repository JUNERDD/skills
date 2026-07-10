#!/usr/bin/env python3
"""HTTP server for the local log collector."""

from __future__ import annotations

from collections import Counter
import json
import os
import secrets
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mimetypes import guess_type
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from collector_config import (
    CONFIG_FILE,
    ConfigError,
    build_config_response,
    get_stored_selected_ide,
    load_root_config,
    update_collector_selected_ide,
)
from collector_ide import (
    enrich_location_records,
    get_ide_option,
    get_ide_spec,
    list_ide_options,
    open_location_in_ide,
    resolve_location,
    resolve_selected_ide,
)
from collector_state import (
    DEFAULT_LOG_WINDOW_LIMIT,
    MAX_LOG_WINDOW_LIMIT,
    build_location_state_payload,
    build_log_detail_response,
    build_logs_response,
    build_ready_payload,
    build_service_payload,
    build_state_response,
    clear_log_file,
    index_new_log_data,
    schedule_location_state_file_write,
    sync_log_cache,
    sync_tracked_locations,
    write_location_state_file,
)

INGEST_CORS_ALLOW_HEADERS = 'Content-Type, X-Debug-Session-Id'
INGEST_CORS_ALLOW_METHODS = 'POST, OPTIONS'
INGEST_PATHS = {'/ingest', '/ingest/batch'}
MAX_JSON_BODY_BYTES = 4 * 1024 * 1024
DASHBOARD_TOKEN_HEADER = 'X-Debug-Dashboard-Token'
SENSITIVE_POST_PATHS = {
    '/api/clear',
    '/api/config',
    '/api/dashboard-open-failed',
    '/api/dashboard-opened',
    '/api/locations/sync',
    '/api/open-location',
    '/api/shutdown',
}
STATIC_DIR = Path(__file__).resolve().parent / 'static'


class CollectorServer(ThreadingHTTPServer):
    """HTTP server that appends JSON payloads to a local NDJSON file."""

    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 1024

    def __init__(
        self,
        server_address: tuple[str, int],
        log_file: Path,
        workspace_root: Path,
        default_ide: str,
        location_state_file: Path | None,
        ready_file: Path | None,
        session_id: str | None,
        service_log_file: Path | None = None,
        location_state_flush_ms: int = 0,
    ) -> None:
        super().__init__(server_address, CollectorRequestHandler)
        self.log_file = log_file
        self.workspace_root = workspace_root
        self.default_ide = default_ide
        self.config_file = CONFIG_FILE
        self.dashboard_token = secrets.token_urlsafe(24)
        self.location_state_file = location_state_file
        self.ready_file = ready_file
        self.session_id = session_id
        self.service_log_file = service_log_file
        self.started_at = int(time.time() * 1000)
        self.max_json_body_bytes = MAX_JSON_BODY_BYTES
        # Keep ingestion file I/O independent from dashboard/index state work. The
        # request path performs one append and acknowledges immediately; a
        # background tailer updates the dashboard cache afterwards.
        self.ingest_lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.location_state_flush_ms = max(int(location_state_flush_ms), 0)
        self.location_state_schedule_lock = threading.Lock()
        self.location_state_timer: threading.Timer | None = None
        self.location_state_dirty = False
        self.location_state_last_write_monotonic = 0.0
        self.shutdown_requested_at: int | None = None
        self.entries: list[dict[str, Any]] = []
        self.run_counts = Counter()
        self.hypothesis_counts = Counter()
        self.probe_counts = Counter()
        self.correlation_counts = Counter()
        self.event_counts = Counter()
        self.location_counts = Counter()
        self.location_records: dict[str, dict[str, Any]] = {}
        self.tracked_location_records: dict[str, dict[str, Any]] = {}
        self.invalid_lines = 0
        self.last_event: dict[str, Any] | None = None
        self.file_size_bytes = 0
        self.file_updated_at: int | None = None
        self.location_state_updated_at: int | None = None
        self.physical_line_count = 0
        self.indexed_file_offset = 0
        self.ingest_request_count = 0
        self.ingest_accepted_event_count = 0
        self.ingest_accepted_bytes = 0
        self.ingest_last_accepted_at: int | None = None
        self.index_last_completed_at: int | None = None
        self.index_error_count = 0
        self.index_last_error = ''
        self.seen_transport_batch_ids: set[str] = set()
        self._index_wake_event = threading.Event()
        self._index_stop_event = threading.Event()
        self._index_thread: threading.Thread | None = None
        self.dashboard_open_attempted = False
        self.dashboard_open_succeeded: bool | None = None
        self.dashboard_open_error = ''
        self.dashboard_auto_open_enabled = False
        self.dashboard_open_pending = False
        self.dashboard_open_started_at: int | None = None
        self.dashboard_open_completed_at: int | None = None
        self.dashboard_open_method = ''
        self.dashboard_open_attempts: list[dict[str, Any]] = []
        self.dashboard_frontend_opened_at: int | None = None
        self.dashboard_frontend_open_failure_count = 0
        self.dashboard_frontend_open_last_failure_at: int | None = None
        self.dashboard_frontend_open_last_error = ''
        self.dashboard_frontend_open_last_failed_url = ''

    def start_background_workers(self) -> None:
        """Start the asynchronous file tailer once the initial cache is hydrated."""

        if self._index_thread is not None and self._index_thread.is_alive():
            return
        self._index_stop_event.clear()
        self._index_thread = threading.Thread(
            target=self._index_loop,
            name='debug-log-indexer',
            daemon=True,
        )
        self._index_thread.start()

    def stop_background_workers(self) -> None:
        self._index_stop_event.set()
        self._index_wake_event.set()
        thread = self._index_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5.0)
        self._index_thread = None
        # Catch up synchronously before the final state-sidecar flush.
        try:
            with self.write_lock:
                indexed = index_new_log_data(self)
                if indexed:
                    schedule_location_state_file_write(self)
        except OSError as exc:
            self.index_error_count += 1
            self.index_last_error = str(exc)

    def wake_indexer(self) -> None:
        self._index_wake_event.set()

    def _index_loop(self) -> None:
        while not self._index_stop_event.is_set():
            self._index_wake_event.wait(timeout=0.25)
            self._index_wake_event.clear()
            try:
                with self.write_lock:
                    indexed = index_new_log_data(self)
                    if indexed:
                        schedule_location_state_file_write(self)
                self.index_last_completed_at = int(time.time() * 1000)
                self.index_last_error = ''
            except OSError as exc:
                self.index_error_count += 1
                self.index_last_error = str(exc)
                time.sleep(0.05)

    def server_close(self) -> None:
        self.stop_background_workers()
        super().server_close()

    @property
    def base_url(self) -> str:
        return f'http://{self.server_address[0]}:{self.server_port}'

    @property
    def endpoint_url(self) -> str:
        return f'{self.base_url}/ingest'

    @property
    def batch_endpoint_url(self) -> str:
        return f'{self.base_url}/ingest/batch'

    @property
    def dashboard_url(self) -> str:
        return f'{self.base_url}/'

    @property
    def state_url(self) -> str:
        return f'{self.base_url}/api/state'

    @property
    def logs_url(self) -> str:
        return f'{self.base_url}/api/logs'

    @property
    def log_detail_url(self) -> str:
        return f'{self.base_url}/api/logs/detail'

    @property
    def locations_url(self) -> str:
        return f'{self.base_url}/api/locations'

    @property
    def config_url(self) -> str:
        return f'{self.base_url}/api/config'

    @property
    def dashboard_frontend_opened_url(self) -> str:
        return f'{self.base_url}/api/dashboard-opened'

    @property
    def dashboard_frontend_open_failed_url(self) -> str:
        return f'{self.base_url}/api/dashboard-open-failed'

    @property
    def sync_locations_url(self) -> str:
        return f'{self.base_url}/api/locations/sync'

    @property
    def open_location_url(self) -> str:
        return f'{self.base_url}/api/open-location'

    @property
    def clear_url(self) -> str:
        return f'{self.base_url}/api/clear'

    @property
    def shutdown_url(self) -> str:
        return f'{self.base_url}/api/shutdown'

    @property
    def health_url(self) -> str:
        return f'{self.base_url}/health'

    @property
    def owned_artifacts(self) -> list[str]:
        ordered_paths = [
            self.log_file,
            self.location_state_file,
            self.ready_file,
            self.service_log_file,
        ]
        unique_paths: list[str] = []
        seen: set[str] = set()
        for path in ordered_paths:
            if path is None:
                continue
            text = str(path)
            if text in seen:
                continue
            seen.add(text)
            unique_paths.append(text)
        return unique_paths

    def build_state(self) -> dict[str, Any]:
        return build_state_response(self)

    def build_health(self) -> dict[str, Any]:
        payload = build_service_payload(self)
        payload.update(
            {
                'ok': True,
                'status': 'stopping' if self.shutdown_requested_at else 'running',
            },
        )
        return payload

    def write_ready_file(self) -> None:
        if not self.ready_file:
            return

        payload = build_ready_payload(self)
        temp_path = self.ready_file.with_suffix(f'{self.ready_file.suffix}.tmp')
        temp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding='utf-8')
        os.replace(temp_path, self.ready_file)

    def record_dashboard_frontend_opened(self) -> None:
        if self.dashboard_frontend_opened_at is not None:
            return

        self.dashboard_frontend_opened_at = int(time.time() * 1000)
        self.write_ready_file()

    def record_dashboard_open_result(self, result: dict[str, Any]) -> None:
        """Record an OS/browser launch request without treating it as page-load proof."""

        self.dashboard_open_pending = False
        self.dashboard_open_completed_at = int(time.time() * 1000)
        self.dashboard_open_attempted = bool(result.get('attempted'))
        self.dashboard_open_succeeded = bool(result.get('succeeded'))
        self.dashboard_open_error = str(result.get('error') or '')
        self.dashboard_open_method = str(result.get('method') or '')
        raw_attempts = result.get('attempts')
        self.dashboard_open_attempts = raw_attempts if isinstance(raw_attempts, list) else []

        if not self.dashboard_open_succeeded and self.dashboard_frontend_opened_at is None:
            self.dashboard_frontend_open_failure_count += 1
            self.dashboard_frontend_open_last_failure_at = self.dashboard_open_completed_at
            self.dashboard_frontend_open_last_error = (
                self.dashboard_open_error or 'dashboard_auto_open_failed'
            )
            self.dashboard_frontend_open_last_failed_url = self.dashboard_url

        self.write_ready_file()

    def record_dashboard_frontend_open_failed(
        self,
        *,
        error: str,
        attempted_url: str,
    ) -> None:
        if self.dashboard_frontend_opened_at is not None:
            return

        self.dashboard_frontend_open_failure_count += 1
        self.dashboard_frontend_open_last_failure_at = int(time.time() * 1000)
        self.dashboard_frontend_open_last_error = error
        self.dashboard_frontend_open_last_failed_url = attempted_url
        self.write_ready_file()


class CollectorRequestHandler(BaseHTTPRequestHandler):
    server_version = 'DebugLogCollector/1.0'
    protocol_version = 'HTTP/1.1'

    def do_OPTIONS(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        self.send_response(HTTPStatus.NO_CONTENT)
        if path in INGEST_PATHS:
            self._send_ingest_cors_headers()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)
        static_asset = self._resolve_static_asset(path)
        if static_asset:
            asset_path, content_type = static_asset
            self._asset_response(asset_path, content_type)
            return
        if path in {'/health', '/healthz'}:
            self._json_response(HTTPStatus.OK, self.server.build_health())
            return
        if path == '/api/state':
            self._json_response(HTTPStatus.OK, self.server.build_state())
            return
        if path == '/api/logs':
            offset = self._parse_int(query.get('offset', ['0'])[0], default=0, minimum=0)
            limit = self._parse_int(
                query.get('limit', [str(DEFAULT_LOG_WINDOW_LIMIT)])[0],
                default=DEFAULT_LOG_WINDOW_LIMIT,
                minimum=1,
                maximum=MAX_LOG_WINDOW_LIMIT,
            )
            order = query.get('order', ['desc'])[0]
            if order not in {'asc', 'desc'}:
                order = 'desc'
            self._json_response(
                HTTPStatus.OK,
                build_logs_response(self.server, offset=offset, limit=limit, order=order),
            )
            return
        if path == '/api/logs/detail':
            entry_index = self._parse_int(query.get('entryIndex', ['-1'])[0], default=-1, minimum=-1)
            payload = build_log_detail_response(self.server, entry_index=entry_index)
            status = HTTPStatus.OK if payload.get('ok') else HTTPStatus.NOT_FOUND
            self._json_response(status, payload)
            return
        if path == '/api/locations':
            self._json_response(HTTPStatus.OK, self._build_locations_response())
            return
        if path == '/api/config':
            self._json_response(HTTPStatus.OK, self._build_config_payload())
            return
        if path == '/favicon.ico':
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        self._json_response(HTTPStatus.NOT_FOUND, {'ok': False, 'error': 'not_found'})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == '/ingest':
            self._handle_ingest()
            return
        if path == '/ingest/batch':
            self._handle_ingest_batch()
            return
        if path in SENSITIVE_POST_PATHS and not self._require_dashboard_access():
            return
        if path == '/api/clear':
            # Prevent append/clear races without blocking normal dashboard reads
            # behind ingestion file I/O.
            with self.server.ingest_lock:
                with self.server.write_lock:
                    clear_log_file(self.server)
            self._json_response(HTTPStatus.OK, self.server.build_state())
            return
        if path == '/api/config':
            self._handle_config_update()
            return
        if path == '/api/dashboard-open-failed':
            self._handle_dashboard_open_failed()
            return
        if path == '/api/dashboard-opened':
            self._handle_dashboard_opened()
            return
        if path == '/api/locations/sync':
            self._handle_locations_sync()
            return
        if path == '/api/open-location':
            self._handle_open_location()
            return
        if path == '/api/shutdown':
            self.server.shutdown_requested_at = int(time.time() * 1000)
            self._json_response(
                HTTPStatus.OK,
                {
                    'ok': True,
                    'status': 'stopping',
                    'dashboardUrl': self.server.dashboard_url,
                },
            )
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        self._json_response(HTTPStatus.NOT_FOUND, {'ok': False, 'error': 'not_found'})

    def _handle_ingest(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {'ok': False, 'error': 'invalid_json'},
                cors_mode='ingest',
            )
            return

        if not isinstance(payload, dict):
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {'ok': False, 'error': 'payload_must_be_object'},
                cors_mode='ingest',
            )
            return

        event = self._prepare_ingest_event(payload)
        persisted_bytes, _ = self._append_ingest_events([event])
        self._json_response(
            HTTPStatus.ACCEPTED,
            {'ok': True, 'accepted': 1, 'persistedBytes': persisted_bytes},
            cors_mode='ingest',
        )

    def _handle_ingest_batch(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {'ok': False, 'error': 'invalid_json'},
                cors_mode='ingest',
            )
            return

        raw_events = payload.get('events') if isinstance(payload, dict) else payload
        raw_batch_id = payload.get('batchId') if isinstance(payload, dict) else None
        batch_id = raw_batch_id.strip() if isinstance(raw_batch_id, str) else ''
        if not isinstance(raw_events, list):
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {'ok': False, 'error': 'events_must_be_array'},
                cors_mode='ingest',
            )
            return
        if not raw_events:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {'ok': False, 'error': 'events_required'},
                cors_mode='ingest',
            )
            return
        if any(not isinstance(item, dict) for item in raw_events):
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {'ok': False, 'error': 'event_must_be_object'},
                cors_mode='ingest',
            )
            return

        events = [self._prepare_ingest_event(item) for item in raw_events]
        if batch_id:
            for event in events:
                event.setdefault('transportBatchId', batch_id)
        persisted_bytes, duplicate_batch = self._append_ingest_events(
            events,
            batch_id=batch_id or None,
        )
        self._json_response(
            HTTPStatus.ACCEPTED,
            {
                'ok': True,
                'accepted': len(events),
                'persistedBytes': persisted_bytes,
                'persistedEvents': 0 if duplicate_batch else len(events),
                'duplicateBatch': duplicate_batch,
                'batchId': batch_id or None,
            },
            cors_mode='ingest',
        )

    def _prepare_ingest_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        event = dict(payload)
        header_session_id = self.headers.get('X-Debug-Session-Id')
        if header_session_id and 'sessionId' not in event:
            event['sessionId'] = header_session_id
        elif self.server.session_id and 'sessionId' not in event:
            event['sessionId'] = self.server.session_id
        if 'timestamp' not in event:
            event['timestamp'] = int(time.time() * 1000)
        return event

    def _append_ingest_events(
        self,
        events: list[dict[str, Any]],
        *,
        batch_id: str | None = None,
    ) -> tuple[int, bool]:
        encoded_events = [
            f"{json.dumps(event, ensure_ascii=True, separators=(',', ':'))}\n".encode('utf-8')
            for event in events
        ]
        encoded_blob = b''.join(encoded_events)
        accepted_at = int(time.time() * 1000)
        with self.server.ingest_lock:
            if batch_id and batch_id in self.server.seen_transport_batch_ids:
                return 0, True
            with self.server.log_file.open('ab') as file:
                file.write(encoded_blob)
                file.flush()
                self.server.file_size_bytes = file.tell()
            if batch_id:
                self.server.seen_transport_batch_ids.add(batch_id)
            self.server.file_updated_at = accepted_at
            self.server.ingest_request_count += 1
            self.server.ingest_accepted_event_count += len(events)
            self.server.ingest_accepted_bytes += len(encoded_blob)
            self.server.ingest_last_accepted_at = accepted_at
        self.server.wake_indexer()
        return len(encoded_blob), False

    def _handle_config_update(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            self._json_response(HTTPStatus.BAD_REQUEST, {'ok': False, 'error': 'invalid_json'})
            return
        if not isinstance(payload, dict):
            self._json_response(HTTPStatus.BAD_REQUEST, {'ok': False, 'error': 'payload_must_be_object'})
            return

        selected_ide = self._extract_selected_ide(payload)
        if selected_ide is None:
            self._json_response(HTTPStatus.BAD_REQUEST, {'ok': False, 'error': 'selected_ide_required'})
            return
        if not isinstance(selected_ide, str):
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {'ok': False, 'error': 'selected_ide_must_be_string'},
            )
            return

        normalized_ide = selected_ide.strip().lower()
        if normalized_ide and get_ide_spec(normalized_ide) is None:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {'ok': False, 'error': 'unsupported_ide', 'ide': normalized_ide},
            )
            return

        with self.server.write_lock:
            try:
                updated_config = update_collector_selected_ide(normalized_ide)
            except ConfigError as exc:
                self._json_response(
                    HTTPStatus.CONFLICT,
                    {'ok': False, 'error': str(exc), 'configFile': str(self.server.config_file)},
                )
                return

        self._json_response(HTTPStatus.OK, self._build_config_payload(root_config=updated_config))

    def _handle_dashboard_opened(self) -> None:
        with self.server.write_lock:
            self.server.record_dashboard_frontend_opened()

        self._json_response(HTTPStatus.OK, self.server.build_state())

    def _handle_dashboard_open_failed(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            self._json_response(HTTPStatus.BAD_REQUEST, {'ok': False, 'error': 'invalid_json'})
            return
        if not isinstance(payload, dict):
            self._json_response(HTTPStatus.BAD_REQUEST, {'ok': False, 'error': 'payload_must_be_object'})
            return

        raw_error = payload.get('error')
        raw_attempted_url = payload.get('attemptedUrl')
        error = raw_error if isinstance(raw_error, str) and raw_error else 'dashboard_open_failed'
        attempted_url = raw_attempted_url if isinstance(raw_attempted_url, str) else self.server.dashboard_url

        with self.server.write_lock:
            self.server.record_dashboard_frontend_open_failed(
                error=error,
                attempted_url=attempted_url,
            )

        self._json_response(HTTPStatus.OK, self.server.build_state())

    def _handle_open_location(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            self._json_response(HTTPStatus.BAD_REQUEST, {'ok': False, 'error': 'invalid_json'})
            return
        if not isinstance(payload, dict):
            self._json_response(HTTPStatus.BAD_REQUEST, {'ok': False, 'error': 'payload_must_be_object'})
            return

        location = payload.get('location')
        if not isinstance(location, str) or not location.strip():
            self._json_response(HTTPStatus.BAD_REQUEST, {'ok': False, 'error': 'location_required'})
            return

        _, selected_ide, _, _, _ = self._resolve_config_state()
        requested_ide = payload.get('ide')
        requested_ide_id = (
            requested_ide.strip().lower()
            if isinstance(requested_ide, str) and requested_ide.strip()
            else ''
        )
        if requested_ide_id and requested_ide_id != selected_ide:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {
                    'ok': False,
                    'error': 'ide_mismatch',
                    'ide': selected_ide,
                    'requestedIde': requested_ide_id,
                },
            )
            return

        ide_id = selected_ide
        resolved_location = resolve_location(location, self.server.workspace_root)

        try:
            open_result = open_location_in_ide(ide_id, resolved_location)
        except ValueError as exc:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {
                    'ok': False,
                    'error': str(exc),
                    'ide': ide_id,
                    'location': resolved_location,
                },
            )
            return
        except RuntimeError as exc:
            self._json_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    'ok': False,
                    'error': str(exc),
                    'ide': ide_id,
                    'location': resolved_location,
                },
            )
            return

        self._json_response(
            HTTPStatus.OK,
            {
                'ok': True,
                'ide': open_result['ide'],
                'label': open_result['label'],
                'launchStatus': open_result['launchStatus'],
                'confirmed': open_result['confirmed'],
                'location': resolved_location,
            },
        )

    def _handle_locations_sync(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            self._json_response(HTTPStatus.BAD_REQUEST, {'ok': False, 'error': 'invalid_json'})
            return
        if not isinstance(payload, dict):
            self._json_response(HTTPStatus.BAD_REQUEST, {'ok': False, 'error': 'payload_must_be_object'})
            return

        raw_locations = payload.get('locations')
        try:
            with self.server.write_lock:
                sync_tracked_locations(self.server, raw_locations)
        except ValueError as exc:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {'ok': False, 'error': str(exc)},
            )
            return

        self._json_response(HTTPStatus.OK, self._build_locations_response())

    def _resolve_config_state(
        self,
        *,
        root_config: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], str, str, list[dict[str, Any]], str]:
        config_error = ''
        if root_config is None:
            try:
                config = load_root_config()
            except ConfigError as exc:
                config = {}
                config_error = str(exc)
        else:
            config = root_config
        stored_selected_ide = get_stored_selected_ide(config)
        ide_options = list_ide_options(stored_selected_ide)
        selected_ide, selected_source = resolve_selected_ide(
            stored_selected_ide=stored_selected_ide,
            default_ide=self.server.default_ide,
            ide_options=ide_options,
        )
        return config, selected_ide, selected_source, ide_options, config_error

    def _build_config_payload(
        self,
        *,
        root_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        config, selected_ide, selected_source, ide_options, config_error = self._resolve_config_state(
            root_config=root_config,
        )
        selected_option = get_ide_option(selected_ide, ide_options)
        return build_config_response(
            config,
            selected_ide=selected_ide,
            selected_ide_available=bool(selected_option and selected_option['available']),
            selected_source=selected_source,
            ide_options=ide_options,
            config_error=config_error,
        )

    def _build_locations_response(self) -> dict[str, Any]:
        with self.server.write_lock:
            sync_log_cache(self.server)
            payload = build_location_state_payload(self.server)

        payload['ok'] = True
        payload['workspaceRoot'] = str(self.server.workspace_root)
        payload['locations'] = enrich_location_records(
            payload.get('locations', []),
            workspace_root=self.server.workspace_root,
        )
        config_payload = self._build_config_payload()
        payload['ide'] = config_payload['ide']
        payload['configError'] = config_payload.get('configError', '')
        return payload

    def _resolve_static_asset(self, path: str) -> tuple[Path, str] | None:
        if path in {'/', '/dashboard'}:
            return STATIC_DIR / 'index.html', 'text/html; charset=utf-8'

        if not path.startswith('/static/'):
            return None

        asset_name = path.removeprefix('/static/')
        asset_path = (STATIC_DIR / asset_name).resolve()
        if STATIC_DIR.resolve() not in asset_path.parents or not asset_path.is_file():
            return None

        content_type = guess_type(asset_path.name)[0] or 'application/octet-stream'
        if content_type.startswith('text/') or content_type in {'application/javascript', 'application/json'}:
            content_type = f'{content_type}; charset=utf-8'
        return asset_path, content_type

    def _asset_response(self, asset_path: Path, content_type: str) -> None:
        if not asset_path.exists():
            self._json_response(HTTPStatus.NOT_FOUND, {'ok': False, 'error': 'asset_not_found'})
            return

        body = asset_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            # The event may already be appended even if the caller
            # disconnects before reading the acknowledgement.
            pass

    def _json_response(
        self,
        status: HTTPStatus,
        payload: dict[str, Any],
        *,
        cors_mode: str = 'none',
    ) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode('utf-8')
        self.send_response(status)
        if cors_mode == 'ingest':
            self._send_ingest_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            # An ingest frame may already be appended even when the
            # client times out before reading the acknowledgement. A retry with
            # the same batchId is idempotent.
            pass

    def _send_ingest_cors_headers(self) -> None:
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', INGEST_CORS_ALLOW_HEADERS)
        self.send_header('Access-Control-Allow-Methods', INGEST_CORS_ALLOW_METHODS)
        self.send_header('Access-Control-Max-Age', '600')

    def _require_dashboard_access(self) -> bool:
        origin = self.headers.get('Origin', '').strip()
        if origin and origin != self.server.base_url:
            self._json_response(
                HTTPStatus.FORBIDDEN,
                {'ok': False, 'error': 'dashboard_origin_forbidden'},
            )
            return False

        provided_token = self.headers.get(DASHBOARD_TOKEN_HEADER, '').strip()
        if provided_token != self.server.dashboard_token:
            self._json_response(
                HTTPStatus.FORBIDDEN,
                {'ok': False, 'error': 'dashboard_token_required'},
            )
            return False

        return True

    def _extract_selected_ide(self, payload: dict[str, Any]) -> Any | None:
        direct_selected = payload.get('selectedIde')
        if direct_selected is not None:
            return direct_selected

        current: Any = payload
        for key in ('debug', 'collector', 'ide'):
            if not isinstance(current, dict):
                return None
            current = current.get(key)

        if not isinstance(current, dict) or 'selected' not in current:
            return None
        return current.get('selected')

    def _parse_int(
        self,
        value: str,
        *,
        default: int,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        if minimum is not None:
            parsed = max(parsed, minimum)
        if maximum is not None:
            parsed = min(parsed, maximum)
        return parsed

    def _read_json_body(self) -> Any | None:
        try:
            content_length = int(self.headers.get('Content-Length', '0'))
        except (TypeError, ValueError):
            return None
        if content_length < 0 or content_length > MAX_JSON_BODY_BYTES:
            return None
        raw_body = self.rfile.read(content_length) if content_length else b''
        try:
            return json.loads(raw_body.decode('utf-8') or '{}')
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def log_message(self, format: str, *args: Any) -> None:
        return
