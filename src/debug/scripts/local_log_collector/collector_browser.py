#!/usr/bin/env python3
"""Browser helpers for the local log collector."""

from __future__ import annotations

import webbrowser


def open_dashboard_in_browser(dashboard_url: str) -> dict[str, str | bool]:
    try:
        opened = bool(webbrowser.open_new_tab(dashboard_url))
    except Exception as exc:
        return {
            'attempted': True,
            'succeeded': False,
            'error': f'{type(exc).__name__}: {exc}',
        }

    return {
        'attempted': True,
        'succeeded': opened,
        'error': '' if opened else 'browser_open_returned_false',
    }
