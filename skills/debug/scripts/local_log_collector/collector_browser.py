#!/usr/bin/env python3
"""Browser helpers for the local log collector."""

from __future__ import annotations

from typing import Any
import os
import platform
import shutil
import subprocess
import webbrowser


def _result(
    *,
    method: str,
    attempted: bool,
    succeeded: bool,
    error: str = '',
) -> dict[str, Any]:
    return {
        'method': method,
        'attempted': attempted,
        'succeeded': succeeded,
        'error': error,
    }


def _command_failure(command_name: str, exc: Exception) -> dict[str, Any]:
    return _result(
        method=command_name,
        attempted=True,
        succeeded=False,
        error=f'{command_name}: {type(exc).__name__}: {exc}',
    )


def _run_open_command(command: list[str], command_name: str) -> dict[str, Any]:
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
        return _result(method=command_name, attempted=True, succeeded=True)

    stderr = (completed.stderr or '').strip()
    error = f'{command_name}_exit_{completed.returncode}'
    if stderr:
        error = f'{error}: {stderr}'
    return _result(
        method=command_name,
        attempted=True,
        succeeded=False,
        error=error,
    )


def _open_with_platform_command(dashboard_url: str) -> dict[str, Any] | None:
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
        return _result(method='windows_startfile', attempted=True, succeeded=True)

    opener = shutil.which('xdg-open')
    if opener:
        return _run_open_command([opener, dashboard_url], 'xdg_open')

    opener = shutil.which('gio')
    if opener:
        return _run_open_command([opener, 'open', dashboard_url], 'gio_open')

    return None


def _open_with_webbrowser(dashboard_url: str) -> dict[str, Any]:
    try:
        opened = bool(webbrowser.open_new_tab(dashboard_url))
    except Exception as exc:
        return _result(
            method='python_webbrowser',
            attempted=True,
            succeeded=False,
            error=f'python_webbrowser: {type(exc).__name__}: {exc}',
        )

    return _result(
        method='python_webbrowser',
        attempted=True,
        succeeded=opened,
        error='' if opened else 'browser_open_returned_false',
    )


def open_dashboard_in_browser(dashboard_url: str) -> dict[str, Any]:
    """Open the dashboard, falling back when an installed platform opener fails.

    A zero exit status only confirms that the operating system accepted the request.
    The dashboard frontend separately records an HTTP callback when the page actually loads.
    """

    attempts: list[dict[str, Any]] = []
    platform_result = _open_with_platform_command(dashboard_url)
    if platform_result is not None:
        attempts.append(platform_result)
        if platform_result['succeeded']:
            return {
                **platform_result,
                'attempts': attempts,
            }

    browser_result = _open_with_webbrowser(dashboard_url)
    attempts.append(browser_result)
    if browser_result['succeeded']:
        return {
            **browser_result,
            'attempts': attempts,
        }

    errors = [str(item.get('error') or '') for item in attempts if item.get('error')]
    return {
        **browser_result,
        'attempted': any(bool(item.get('attempted')) for item in attempts),
        'succeeded': False,
        'error': '; '.join(errors) or 'dashboard_open_failed',
        'attempts': attempts,
    }
