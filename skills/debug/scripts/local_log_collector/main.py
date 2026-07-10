#!/usr/bin/env python3
"""Entrypoint for the local log collector app."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import threading

from collector_browser import open_dashboard_in_browser
from collector_server import CollectorServer
from collector_state import build_ready_payload, flush_location_state_file, hydrate_log_cache


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Start a local NDJSON log collector.')
    parser.add_argument('--host', default='127.0.0.1', help='Interface to bind. Defaults to 127.0.0.1.')
    parser.add_argument(
        '--port',
        type=int,
        default=0,
        help='Port to bind. Use 0 to auto-select a free port. Defaults to 0.',
    )
    parser.add_argument('--log-file', required=True, help='Target NDJSON log file.')
    parser.add_argument(
        '--location-state-file',
        help=(
            'Optional JSON file populated with the latest instrumented code locations. '
            'Defaults to <ready-file>.locations.json or <log-file>.locations.json.'
        ),
    )
    parser.add_argument(
        '--ready-file',
        help='Optional JSON file populated with the bound endpoint and log path.',
    )
    parser.add_argument(
        '--session-id',
        help='Optional default sessionId inserted when requests omit one.',
    )
    parser.add_argument(
        '--workspace-root',
        help='Optional workspace root used to resolve relative log locations. Defaults to the current working directory.',
    )
    parser.add_argument(
        '--default-ide',
        help='Optional default IDE id used when ~/.junerdd/config.json does not set one.',
    )
    parser.add_argument(
        '--service-log-file',
        help='Optional path used for collector stdout/stderr redirection metadata.',
    )
    parser.add_argument(
        '--location-state-flush-ms',
        type=int,
        default=250,
        help=(
            'Debounce interval for location-state runtime updates. '
            'Use 0 to rewrite the sidecar after every accepted event.'
        ),
    )
    parser.add_argument(
        '--no-open-dashboard',
        action='store_true',
        help='Do not open the dashboard in a browser on startup.',
    )
    return parser.parse_args()


def ensure_parent_dirs(
    log_file: Path,
    location_state_file: Path | None,
    ready_file: Path | None,
    service_log_file: Path | None,
) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.touch(exist_ok=True)
    if location_state_file:
        location_state_file.parent.mkdir(parents=True, exist_ok=True)
    if ready_file:
        ready_file.parent.mkdir(parents=True, exist_ok=True)
    if service_log_file:
        service_log_file.parent.mkdir(parents=True, exist_ok=True)


def resolve_location_state_file(
    log_file: Path,
    ready_file: Path | None,
    configured_path: str | None,
) -> Path:
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    if ready_file:
        return ready_file.with_suffix('.locations.json')
    return log_file.with_suffix('.locations.json')


def install_signal_handlers(server: CollectorServer) -> None:
    def _shutdown(_signum: int, _frame: object) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)


def main() -> int:
    args = parse_args()
    log_file = Path(args.log_file).expanduser().resolve()
    ready_file = Path(args.ready_file).expanduser().resolve() if args.ready_file else None
    workspace_root = (
        Path(args.workspace_root).expanduser().resolve()
        if args.workspace_root
        else Path.cwd().resolve()
    )
    default_ide = (
        args.default_ide
        or os.environ.get('JUNERDD_DEBUG_DEFAULT_IDE', '')
    )
    location_state_file = resolve_location_state_file(
        log_file,
        ready_file,
        args.location_state_file,
    )
    service_log_file = (
        Path(args.service_log_file).expanduser().resolve() if args.service_log_file else None
    )

    ensure_parent_dirs(log_file, location_state_file, ready_file, service_log_file)
    server = CollectorServer(
        (args.host, args.port),
        log_file,
        workspace_root,
        default_ide,
        location_state_file,
        ready_file,
        args.session_id,
        service_log_file,
        args.location_state_flush_ms,
    )
    hydrate_log_cache(server)
    install_signal_handlers(server)

    if not args.no_open_dashboard:
        open_result = open_dashboard_in_browser(server.dashboard_url)
        server.dashboard_open_attempted = bool(open_result['attempted'])
        server.dashboard_open_succeeded = bool(open_result['succeeded'])
        server.dashboard_open_error = str(open_result['error'])
        if server.dashboard_open_attempted and not server.dashboard_open_succeeded:
            server.record_dashboard_frontend_open_failed(
                error=server.dashboard_open_error or 'dashboard_auto_open_failed',
                attempted_url=server.dashboard_url,
            )

    server.write_ready_file()

    print(json.dumps(build_ready_payload(server), ensure_ascii=True), flush=True)

    try:
        server.serve_forever()
    finally:
        flush_location_state_file(server)
        server.server_close()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
