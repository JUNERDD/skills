#!/usr/bin/env python3
"""HTTP server for the local log collector."""

from __future__ import annotations

from collections import Counter
import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mimetypes import guess_type
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from collector_state import (
    DEFAULT_LOG_WINDOW_LIMIT,
    MAX_LOG_WINDOW_LIMIT,
    append_entry_to_cache,
    build_log_detail_response,
    build_logs_response,
    build_service_payload,
    build_state_response,
)

CORS_ALLOW_HEADERS = 'Content-Type, X-Debug-Session-Id'
CORS_ALLOW_METHODS = 'GET, POST, OPTIONS'
STATIC_DIR = Path(__file__).resolve().parent / 'static'


class CollectorServer(ThreadingHTTPServer):
    """HTTP server that appends JSON payloads to a local NDJSON file."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        log_file: Path,
        ready_file: Path | None,
        session_id: str | None,
    ) -> None:
        super().__init__(server_address, CollectorRequestHandler)
        self.log_file = log_file
        self.ready_file = ready_file
        self.session_id = session_id
        self.started_at = int(time.time() * 1000)
        self.write_lock = threading.Lock()
        self.shutdown_requested_at: int | None = None
        self.entries: list[dict[str, Any]] = []
        self.run_counts = Counter()
        self.hypothesis_counts = Counter()
        self.invalid_lines = 0
        self.last_event: dict[str, Any] | None = None
        self.file_size_bytes = 0
        self.file_updated_at: int | None = None
        self.physical_line_count = 0
        self.dashboard_open_attempted = False
        self.dashboard_open_succeeded: bool | None = None
        self.dashboard_open_error = ''

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
    def clear_url(self) -> str:
        return f'{self.base_url}/api/clear'

    @property
    def shutdown_url(self) -> str:
        return f'{self.base_url}/api/shutdown'

    @property
    def health_url(self) -> str:
        return f'{self.base_url}/health'

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


class CollectorRequestHandler(BaseHTTPRequestHandler):
    server_version = 'DebugLogCollector/1.0'

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
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
        if path == '/favicon.ico':
            self.send_response(HTTPStatus.NO_CONTENT)
            self._send_cors_headers()
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        self._json_response(HTTPStatus.NOT_FOUND, {'ok': False, 'error': 'not_found'})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == '/ingest':
            self._handle_ingest()
            return
        if path == '/api/clear':
            with self.server.write_lock:
                self.server.log_file.write_text('', encoding='utf-8')
            self._json_response(HTTPStatus.OK, self.server.build_state())
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
        content_length = int(self.headers.get('Content-Length', '0'))
        raw_body = self.rfile.read(content_length) if content_length else b''

        try:
            payload: Any = json.loads(raw_body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            self._json_response(HTTPStatus.BAD_REQUEST, {'ok': False, 'error': 'invalid_json'})
            return

        if not isinstance(payload, dict):
            self._json_response(HTTPStatus.BAD_REQUEST, {'ok': False, 'error': 'payload_must_be_object'})
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

        self._json_response(HTTPStatus.ACCEPTED, {'ok': True})

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
        self._send_cors_headers()
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_response(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode('utf-8')
        self.send_response(status)
        self._send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_headers(self) -> None:
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', CORS_ALLOW_HEADERS)
        self.send_header('Access-Control-Allow-Methods', CORS_ALLOW_METHODS)
        self.send_header('Access-Control-Max-Age', '600')

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

    def log_message(self, format: str, *args: Any) -> None:
        return
