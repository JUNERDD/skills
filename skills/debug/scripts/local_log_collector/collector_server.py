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
    append_entry_to_cache,
    build_location_state_payload,
    build_log_detail_response,
    build_logs_response,
    build_ready_payload,
    build_service_payload,
    build_state_response,
    clear_log_file,
    sync_log_cache,
    sync_tracked_locations,
    write_location_state_file,
)

INGEST_CORS_ALLOW_HEADERS = 'Content-Type, X-Debug-Session-Id'
INGEST_CORS_ALLOW_METHODS = 'POST, OPTIONS'
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
        self.write_lock = threading.Lock()
        self.shutdown_requested_at: int | None = None
        self.entries: list[dict[str, Any]] = []
        self.run_counts = Counter()
        self.hypothesis_counts = Counter()
        self.location_counts = Counter()
        self.location_records: dict[str, dict[str, Any]] = {}
        self.tracked_location_records: dict[str, dict[str, Any]] = {}
        self.invalid_lines = 0
        self.last_event: dict[str, Any] | None = None
        self.file_size_bytes = 0
        self.file_updated_at: int | None = None
        self.location_state_updated_at: int | None = None
        self.physical_line_count = 0
        self.dashboard_open_attempted = False
        self.dashboard_open_succeeded: bool | None = None
        self.dashboard_open_error = ''
        self.dashboard_frontend_opened_at: int | None = None
        self.dashboard_frontend_open_failure_count = 0
        self.dashboard_frontend_open_last_failure_at: int | None = None
        self.dashboard_frontend_open_last_error = ''
        self.dashboard_frontend_open_last_failed_url = ''

    @property
    def base_url(self) -> str:
        return f'http://{self.server_address[0]}:{self.server_port}'

    @property
    def endpoint_url(self) -> str:
        return f'{self.base_url}/ingest'

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

    def do_OPTIONS(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        self.send_response(HTTPStatus.NO_CONTENT)
        if path == '/ingest':
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
        if path in SENSITIVE_POST_PATHS and not self._require_dashboard_access():
            return
        if path == '/api/clear':
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

        header_session_id = self.headers.get('X-Debug-Session-Id')
        if header_session_id and 'sessionId' not in payload:
            payload['sessionId'] = header_session_id
        elif self.server.session_id and 'sessionId' not in payload:
            payload['sessionId'] = self.server.session_id

        if 'timestamp' not in payload:
            payload['timestamp'] = int(time.time() * 1000)

        line = json.dumps(payload, ensure_ascii=True, separators=(',', ':'))
        encoded_line = f'{line}\n'.encode('utf-8')
        with self.server.write_lock:
            with self.server.log_file.open('ab') as file:
                offset = file.tell()
                file.write(encoded_line)
                file.flush()
                file_size_bytes = file.tell()
            self.server.file_size_bytes = file_size_bytes
            self.server.file_updated_at = int(time.time() * 1000)
            append_entry_to_cache(self.server, payload, offset=offset, size=len(encoded_line))
            write_location_state_file(self.server)

        self._json_response(HTTPStatus.ACCEPTED, {'ok': True}, cors_mode='ingest')

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
        self.wfile.write(body)

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
        self.wfile.write(body)

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
        content_length = int(self.headers.get('Content-Length', '0'))
        raw_body = self.rfile.read(content_length) if content_length else b''
        try:
            return json.loads(raw_body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return None

    def log_message(self, format: str, *args: Any) -> None:
        return
