#!/usr/bin/env python3
"""Browser helpers for the local log collector."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import webbrowser


def _command_failure(command_name: str, exc: Exception) -> dict[str, str | bool]:
    return {
        'attempted': True,
        'succeeded': False,
        'error': f'{command_name}: {type(exc).__name__}: {exc}',
    }


def _run_open_command(command: list[str], command_name: str) -> dict[str, str | bool]:
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception as exc:
        return _command_failure(command_name, exc)

    if completed.returncode == 0:
        return {
            'attempted': True,
            'succeeded': True,
            'error': '',
        }

    stderr = (completed.stderr or '').strip()
    error = f'{command_name}_exit_{completed.returncode}'
    if stderr:
        error = f'{error}: {stderr}'
    return {
        'attempted': True,
        'succeeded': False,
        'error': error,
    }


def _open_with_platform_command(dashboard_url: str) -> dict[str, str | bool] | None:
    system_name = platform.system()

    if system_name == 'Darwin':
        opener = shutil.which('open')
        if opener:
            return _run_open_command([opener, dashboard_url], 'macos_open')
        return None

    if system_name == 'Windows':
        try:
            os.startfile(dashboard_url)  # type: ignore[attr-defined]
        except Exception as exc:
            return _command_failure('windows_startfile', exc)
        return {
            'attempted': True,
            'succeeded': True,
            'error': '',
        }

    opener = shutil.which('xdg-open')
    if opener:
        return _run_open_command([opener, dashboard_url], 'xdg_open')

    opener = shutil.which('gio')
    if opener:
        return _run_open_command([opener, 'open', dashboard_url], 'gio_open')

    return None


def open_dashboard_in_browser(dashboard_url: str) -> dict[str, str | bool]:
    platform_result = _open_with_platform_command(dashboard_url)
    if platform_result is not None:
        return platform_result

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
