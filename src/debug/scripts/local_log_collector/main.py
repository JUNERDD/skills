#!/usr/bin/env python3
"""Entrypoint for the local log collector app."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal

from collector_browser import open_dashboard_in_browser
from collector_server import CollectorServer
from collector_state import build_ready_payload, hydrate_log_cache


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
        '--ready-file',
        help='Optional JSON file populated with the bound endpoint and log path.',
    )
    parser.add_argument(
        '--session-id',
        help='Optional default sessionId inserted when requests omit one.',
    )
    parser.add_argument(
        '--no-open-dashboard',
        action='store_true',
        help='Do not open the dashboard in a browser on startup.',
    )
    return parser.parse_args()


def ensure_parent_dirs(log_file: Path, ready_file: Path | None) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.touch(exist_ok=True)
    if ready_file:
        ready_file.parent.mkdir(parents=True, exist_ok=True)


def install_signal_handlers(server: CollectorServer) -> None:
    def _shutdown(_signum: int, _frame: object) -> None:
        server.shutdown()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)


def write_ready_file(server: CollectorServer) -> None:
    if not server.ready_file:
        return

    payload = build_ready_payload(server)
    temp_path = server.ready_file.with_suffix(f'{server.ready_file.suffix}.tmp')
    temp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding='utf-8')
    os.replace(temp_path, server.ready_file)


def main() -> int:
    args = parse_args()
    log_file = Path(args.log_file).expanduser().resolve()
    ready_file = Path(args.ready_file).expanduser().resolve() if args.ready_file else None

    ensure_parent_dirs(log_file, ready_file)
    server = CollectorServer((args.host, args.port), log_file, ready_file, args.session_id)
    hydrate_log_cache(server)
    install_signal_handlers(server)

    if not args.no_open_dashboard:
        open_result = open_dashboard_in_browser(server.dashboard_url)
        server.dashboard_open_attempted = bool(open_result['attempted'])
        server.dashboard_open_succeeded = bool(open_result['succeeded'])
        server.dashboard_open_error = str(open_result['error'])

    write_ready_file(server)

    print(
        json.dumps(
            {
                'endpoint': server.endpoint_url,
                'dashboardUrl': server.dashboard_url,
                'dashboardOpenAttempted': server.dashboard_open_attempted,
                'dashboardOpenSucceeded': server.dashboard_open_succeeded,
                'dashboardOpenError': server.dashboard_open_error,
                'logFile': str(log_file),
                'readyFile': str(ready_file) if ready_file else None,
                'sessionId': args.session_id,
            },
            ensure_ascii=True,
        ),
        flush=True,
    )

    try:
        server.serve_forever()
    finally:
        server.server_close()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
