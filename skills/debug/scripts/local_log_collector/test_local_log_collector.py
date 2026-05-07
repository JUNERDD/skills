#!/usr/bin/env python3
"""Focused tests for collector config, security, and location resolution."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock
from urllib import error, request

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import collector_config
import collector_browser
import collector_ide
import collector_server
import collector_state


class ConfigPathMixin:
    def setUp(self) -> None:
        super().setUp()
        self._tempdir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self._tempdir.name)
        self.config_dir = self.temp_path / '.junerdd'
        self.config_file = self.config_dir / 'config.json'
        self._original_config_dir = collector_config.CONFIG_DIR
        self._original_config_file = collector_config.CONFIG_FILE
        self._original_server_config_file = collector_server.CONFIG_FILE
        collector_config.CONFIG_DIR = self.config_dir
        collector_config.CONFIG_FILE = self.config_file
        collector_server.CONFIG_FILE = self.config_file

    def tearDown(self) -> None:
        collector_config.CONFIG_DIR = self._original_config_dir
        collector_config.CONFIG_FILE = self._original_config_file
        collector_server.CONFIG_FILE = self._original_server_config_file
        self._tempdir.cleanup()
        super().tearDown()


class CollectorConfigTests(ConfigPathMixin, unittest.TestCase):
    def test_update_selected_ide_preserves_unrelated_config(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(
            json.dumps(
                {
                    'theme': {'name': 'light'},
                    'debug': {'collector': {'mode': 'keep-me'}},
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding='utf-8',
        )

        updated = collector_config.update_collector_selected_ide(' zed ')

        self.assertEqual(updated['theme']['name'], 'light')
        self.assertEqual(updated['debug']['collector']['mode'], 'keep-me')
        self.assertEqual(updated['debug']['collector']['ide']['selected'], 'zed')

        cleared = collector_config.update_collector_selected_ide('')

        self.assertEqual(cleared['theme']['name'], 'light')
        self.assertEqual(cleared['debug']['collector']['mode'], 'keep-me')
        self.assertNotIn('ide', cleared['debug']['collector'])

    def test_invalid_config_is_not_overwritten(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        original = '{"theme":'
        self.config_file.write_text(original, encoding='utf-8')

        with self.assertRaises(collector_config.ConfigError):
            collector_config.update_collector_selected_ide('zed')

        self.assertEqual(self.config_file.read_text(encoding='utf-8'), original)

    def test_non_object_config_ancestor_is_not_overwritten(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        original_payload = {
            'debug': 'keep-me',
            'theme': {'name': 'light'},
        }
        self.config_file.write_text(
            json.dumps(original_payload, ensure_ascii=True, indent=2),
            encoding='utf-8',
        )

        with self.assertRaises(collector_config.ConfigError):
            collector_config.update_collector_selected_ide('zed')

        self.assertEqual(
            json.loads(self.config_file.read_text(encoding='utf-8')),
            original_payload,
        )


class CollectorIdeTests(unittest.TestCase):
    def test_default_ide_falls_back_to_available_option(self) -> None:
        selected_ide, source = collector_ide.resolve_selected_ide(
            stored_selected_ide='',
            default_ide='cursor',
            ide_options=[
                {'id': 'cursor', 'label': 'Cursor', 'available': False, 'launcher': ''},
                {'id': 'zed', 'label': 'Zed', 'available': True, 'launcher': 'cli'},
            ],
        )

        self.assertEqual(selected_ide, 'zed')
        self.assertEqual(source, 'auto')

    def test_resolve_location_blocks_workspace_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / 'workspace'
            root.mkdir(parents=True, exist_ok=True)
            inside_file = root / 'src' / 'app.ts'
            inside_file.parent.mkdir(parents=True, exist_ok=True)
            inside_file.write_text('// ok\n', encoding='utf-8')
            outside_file = Path(tempdir) / 'outside.ts'
            outside_file.write_text('// nope\n', encoding='utf-8')

            inside = collector_ide.resolve_location('src/app.ts:12', root)
            escaped = collector_ide.resolve_location('../outside.ts:9', root)

            self.assertTrue(inside['withinWorkspace'])
            self.assertTrue(inside['openable'])
            self.assertEqual(inside['parseError'], '')

            self.assertFalse(escaped['withinWorkspace'])
            self.assertFalse(escaped['openable'])
            self.assertEqual(escaped['parseError'], 'location_outside_workspace')

    def test_resolve_location_rejects_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / 'workspace'
            root.mkdir(parents=True, exist_ok=True)
            inside_file = root / 'src' / 'app.ts'
            inside_file.parent.mkdir(parents=True, exist_ok=True)
            inside_file.write_text('// ok\n', encoding='utf-8')

            absolute_inside = collector_ide.resolve_location(f'{inside_file}:12', root)

            self.assertTrue(absolute_inside['withinWorkspace'])
            self.assertFalse(absolute_inside['openable'])
            self.assertEqual(absolute_inside['parseError'], 'absolute_path_forbidden')

    def test_open_location_timeout_returns_requested_status(self) -> None:
        resolved_location = {
            'resolvedPath': '/tmp/workspace/src/app.ts',
            'line': 12,
            'column': None,
            'openable': True,
        }
        process = mock.Mock()
        process.communicate.side_effect = subprocess.TimeoutExpired(cmd=['zed'], timeout=1)

        with mock.patch.object(collector_ide, '_build_command', return_value=['zed', 'src/app.ts:12']):
            with mock.patch.object(collector_ide.subprocess, 'Popen', return_value=process):
                result = collector_ide.open_location_in_ide('zed', resolved_location)

        self.assertEqual(result['ide'], 'zed')
        self.assertEqual(result['launchStatus'], 'requested')
        self.assertFalse(result['confirmed'])

    def test_open_location_zero_exit_returns_confirmed_status(self) -> None:
        resolved_location = {
            'resolvedPath': '/tmp/workspace/src/app.ts',
            'line': 12,
            'column': None,
            'openable': True,
        }
        process = mock.Mock()
        process.communicate.return_value = ('', '')
        process.returncode = 0

        with mock.patch.object(collector_ide, '_build_command', return_value=['zed', 'src/app.ts:12']):
            with mock.patch.object(collector_ide.subprocess, 'Popen', return_value=process):
                result = collector_ide.open_location_in_ide('zed', resolved_location)

        self.assertEqual(result['ide'], 'zed')
        self.assertEqual(result['launchStatus'], 'confirmed')
        self.assertTrue(result['confirmed'])


class CollectorBrowserTests(unittest.TestCase):
    def test_macos_uses_system_open_before_webbrowser(self) -> None:
        completed = subprocess.CompletedProcess(
            args=['/usr/bin/open', 'http://127.0.0.1:43125/'],
            returncode=0,
            stderr='',
        )

        with mock.patch.object(collector_browser.platform, 'system', return_value='Darwin'):
            with mock.patch.object(collector_browser.shutil, 'which', return_value='/usr/bin/open'):
                with mock.patch.object(collector_browser.subprocess, 'run', return_value=completed) as run_mock:
                    with mock.patch.object(collector_browser.webbrowser, 'open_new_tab') as browser_mock:
                        result = collector_browser.open_dashboard_in_browser('http://127.0.0.1:43125/')

        self.assertTrue(result['attempted'])
        self.assertTrue(result['succeeded'])
        self.assertEqual(result['error'], '')
        run_mock.assert_called_once()
        browser_mock.assert_not_called()

    def test_system_open_failure_is_reported(self) -> None:
        completed = subprocess.CompletedProcess(
            args=['/usr/bin/open', 'http://127.0.0.1:43125/'],
            returncode=1,
            stderr='No application knows how to open URL',
        )

        with mock.patch.object(collector_browser.platform, 'system', return_value='Darwin'):
            with mock.patch.object(collector_browser.shutil, 'which', return_value='/usr/bin/open'):
                with mock.patch.object(collector_browser.subprocess, 'run', return_value=completed):
                    result = collector_browser.open_dashboard_in_browser('http://127.0.0.1:43125/')

        self.assertTrue(result['attempted'])
        self.assertFalse(result['succeeded'])
        self.assertIn('macos_open_exit_1', str(result['error']))
        self.assertIn('No application knows how to open URL', str(result['error']))

    def test_webbrowser_fallback_when_no_platform_opener_exists(self) -> None:
        with mock.patch.object(collector_browser.platform, 'system', return_value='Linux'):
            with mock.patch.object(collector_browser.shutil, 'which', return_value=None):
                with mock.patch.object(collector_browser.webbrowser, 'open_new_tab', return_value=True) as browser_mock:
                    result = collector_browser.open_dashboard_in_browser('http://127.0.0.1:43125/')

        self.assertTrue(result['attempted'])
        self.assertTrue(result['succeeded'])
        self.assertEqual(result['error'], '')
        browser_mock.assert_called_once_with('http://127.0.0.1:43125/')


class CollectorServerSecurityTests(ConfigPathMixin, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.workspace_root = self.temp_path / 'workspace'
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.log_file = self.workspace_root / 'collector.ndjson'
        self.location_state_file = self.workspace_root / 'collector.locations.json'
        self.log_file.write_text('', encoding='utf-8')
        self.server = collector_server.CollectorServer(
            ('127.0.0.1', 0),
            self.log_file,
            self.workspace_root,
            '',
            self.location_state_file,
            None,
            'test-session',
            None,
        )
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(timeout=5)
        super().tearDown()

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, object]]:
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        req = request.Request(
            f'{self.server.base_url}{path}',
            data=data,
            headers=request_headers,
            method=method,
        )
        try:
            with request.urlopen(req, timeout=5) as response:
                body = response.read()
                return response.status, json.loads(body.decode('utf-8') or '{}')
        except error.HTTPError as exc:
            body = exc.read()
            return exc.code, json.loads(body.decode('utf-8') or '{}')

    def test_config_update_requires_dashboard_token_and_ignores_unrelated_fields(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(
            json.dumps({'theme': {'name': 'light'}}, ensure_ascii=True, indent=2),
            encoding='utf-8',
        )

        status, payload = self._request_json('POST', '/api/config', payload={'selectedIde': 'zed'})
        self.assertEqual(status, 403)
        self.assertEqual(payload['error'], 'dashboard_token_required')

        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        dashboard_token = state_payload['service']['dashboardToken']

        status, payload = self._request_json(
            'POST',
            '/api/config',
            payload={'selectedIde': 'zed', 'theme': {'name': 'dark'}},
            headers={collector_server.DASHBOARD_TOKEN_HEADER: dashboard_token},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload['ide']['selected'], 'zed')

        stored = json.loads(self.config_file.read_text(encoding='utf-8'))
        self.assertEqual(stored['theme']['name'], 'light')
        self.assertEqual(stored['debug']['collector']['ide']['selected'], 'zed')

    def test_config_update_rejects_untrusted_origin(self) -> None:
        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        dashboard_token = state_payload['service']['dashboardToken']

        status, payload = self._request_json(
            'POST',
            '/api/config',
            payload={'selectedIde': 'zed'},
            headers={
                collector_server.DASHBOARD_TOKEN_HEADER: dashboard_token,
                'Origin': 'https://evil.example',
            },
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload['error'], 'dashboard_origin_forbidden')

    def test_open_location_succeeds_for_workspace_file(self) -> None:
        source_file = self.workspace_root / 'src' / 'app.ts'
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text('console.log(\"hi\")\n', encoding='utf-8')
        self.server.default_ide = 'zed'

        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        dashboard_token = state_payload['service']['dashboardToken']

        with mock.patch.object(
            collector_server,
            'open_location_in_ide',
            return_value={
                'ide': 'zed',
                'label': 'Zed',
                'launchStatus': 'confirmed',
                'confirmed': True,
            },
        ) as open_mock:
            status, payload = self._request_json(
                'POST',
                '/api/open-location',
                payload={'location': 'src/app.ts:1', 'ide': 'zed'},
                headers={collector_server.DASHBOARD_TOKEN_HEADER: dashboard_token},
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload['ide'], 'zed')
        self.assertEqual(payload['launchStatus'], 'confirmed')
        self.assertTrue(payload['confirmed'])
        self.assertEqual(payload['location']['displayPath'], 'src/app.ts')
        self.assertTrue(payload['location']['openable'])
        open_mock.assert_called_once()

    def test_open_location_rejects_ide_override(self) -> None:
        source_file = self.workspace_root / 'src' / 'app.ts'
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text('console.log(\"hi\")\n', encoding='utf-8')

        self.server.default_ide = 'zed'
        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        dashboard_token = state_payload['service']['dashboardToken']

        with mock.patch.object(collector_server, 'open_location_in_ide') as open_mock:
            status, payload = self._request_json(
                'POST',
                '/api/open-location',
                payload={'location': 'src/app.ts:1', 'ide': 'vscode'},
                headers={collector_server.DASHBOARD_TOKEN_HEADER: dashboard_token},
            )

        self.assertEqual(status, 400)
        self.assertEqual(payload['error'], 'ide_mismatch')
        self.assertEqual(payload['ide'], 'zed')
        open_mock.assert_not_called()

    def test_sync_locations_requires_dashboard_token(self) -> None:
        status, payload = self._request_json(
            'POST',
            '/api/locations/sync',
            payload={'locations': ['src/app.ts:1']},
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload['error'], 'dashboard_token_required')

    def test_sync_locations_rejects_invalid_tracked_location(self) -> None:
        source_file = self.workspace_root / 'src' / 'app.ts'
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text('console.log(\"hi\")\n', encoding='utf-8')

        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        dashboard_token = state_payload['service']['dashboardToken']

        status, payload = self._request_json(
            'POST',
            '/api/locations/sync',
            payload={'locations': ['../outside.ts:9']},
            headers={collector_server.DASHBOARD_TOKEN_HEADER: dashboard_token},
        )
        self.assertEqual(status, 400)
        self.assertEqual(
            payload['error'],
            'tracked_location_invalid: ../outside.ts:9: location_outside_workspace',
        )

        status, payload = self._request_json('GET', '/api/locations')
        self.assertEqual(status, 200)
        self.assertEqual(payload['locations'], [])

    def test_sync_locations_tracks_active_sources_and_clear_preserves_them(self) -> None:
        source_file = self.workspace_root / 'src' / 'app.ts'
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text('console.log(\"hi\")\n', encoding='utf-8')
        secondary_file = self.workspace_root / 'src' / 'other.ts'
        secondary_file.write_text('console.log(\"other\")\n', encoding='utf-8')

        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        dashboard_token = state_payload['service']['dashboardToken']

        status, payload = self._request_json(
            'POST',
            '/api/locations/sync',
            payload={
                'locations': [
                    {'location': 'src/app.ts:1', 'hypothesisIds': ['H1']},
                    'src/other.ts:1',
                ],
            },
            headers={collector_server.DASHBOARD_TOKEN_HEADER: dashboard_token},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload['trackedLocationCount'], 2)

        locations = {item['location']: item for item in payload['locations']}
        self.assertEqual(set(locations), {'src/app.ts:1', 'src/other.ts:1'})
        self.assertEqual(locations['src/app.ts:1']['count'], 0)
        self.assertTrue(locations['src/app.ts:1']['tracked'])
        self.assertEqual(locations['src/app.ts:1']['displayPath'], 'src/app.ts')
        self.assertEqual(locations['src/app.ts:1']['hypothesisIds'], ['H1'])

        persisted = json.loads(self.location_state_file.read_text(encoding='utf-8'))
        self.assertEqual(persisted['trackedLocationCount'], 2)
        self.assertEqual(
            {item['location'] for item in persisted['trackedLocations']},
            {'src/app.ts:1', 'src/other.ts:1'},
        )

        status, _ = self._request_json(
            'POST',
            '/ingest',
            payload={
                'runId': 'initial',
                'hypothesisId': 'H2',
                'location': 'src/app.ts:1',
                'message': 'before branch',
            },
        )
        self.assertEqual(status, 202)

        status, _ = self._request_json(
            'POST',
            '/ingest',
            payload={
                'runId': 'initial',
                'hypothesisId': 'H3',
                'location': 'src/other.ts:1',
                'message': 'after branch',
            },
        )
        self.assertEqual(status, 202)

        status, payload = self._request_json('GET', '/api/locations')
        self.assertEqual(status, 200)
        locations = {item['location']: item for item in payload['locations']}
        self.assertEqual(locations['src/app.ts:1']['count'], 1)
        self.assertEqual(locations['src/app.ts:1']['runIds'], ['initial'])
        self.assertEqual(locations['src/app.ts:1']['hypothesisIds'], ['H1', 'H2'])
        self.assertTrue(locations['src/app.ts:1']['tracked'])
        self.assertEqual(locations['src/other.ts:1']['count'], 1)
        self.assertEqual(locations['src/other.ts:1']['hypothesisIds'], ['H3'])
        self.assertTrue(locations['src/other.ts:1']['tracked'])

        status, payload = self._request_json(
            'POST',
            '/api/locations/sync',
            payload={
                'locations': [
                    {'location': 'src/app.ts:1', 'hypothesisIds': ['H1']},
                ],
            },
            headers={collector_server.DASHBOARD_TOKEN_HEADER: dashboard_token},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload['trackedLocationCount'], 1)
        self.assertEqual([item['location'] for item in payload['locations']], ['src/app.ts:1'])
        self.assertEqual(payload['locations'][0]['count'], 1)
        self.assertEqual(payload['locations'][0]['hypothesisIds'], ['H1', 'H2'])

        status, payload = self._request_json(
            'POST',
            '/api/clear',
            headers={collector_server.DASHBOARD_TOKEN_HEADER: dashboard_token},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload['summary']['totalEntries'], 0)
        self.assertEqual(payload['summary']['trackedLocationCount'], 1)
        self.assertEqual(payload['summary']['uniqueLocations'], 1)

        status, payload = self._request_json('GET', '/api/locations')
        self.assertEqual(status, 200)
        locations = {item['location']: item for item in payload['locations']}
        self.assertEqual(locations['src/app.ts:1']['count'], 0)
        self.assertEqual(locations['src/app.ts:1']['runIds'], [])
        self.assertEqual(locations['src/app.ts:1']['hypothesisIds'], ['H1'])
        self.assertTrue(locations['src/app.ts:1']['tracked'])
        self.assertNotIn('src/other.ts:1', locations)

    def test_hydrate_log_cache_restores_tracked_locations_from_state_file(self) -> None:
        source_file = self.workspace_root / 'src' / 'app.ts'
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text('console.log(\"hi\")\n', encoding='utf-8')

        collector_state.sync_tracked_locations(
            self.server,
            [{'location': 'src/app.ts:1', 'hypothesisIds': ['H1']}],
        )

        self.server.tracked_location_records = {}
        collector_state.hydrate_log_cache(self.server)

        self.assertIn('src/app.ts:1', self.server.tracked_location_records)
        self.assertEqual(
            self.server.tracked_location_records['src/app.ts:1']['hypothesisIds'],
            {'H1'},
        )

    def test_hydrate_log_cache_ignores_mismatched_location_state_file(self) -> None:
        self.location_state_file.write_text(
            json.dumps(
                {
                    'sessionId': 'different-session',
                    'logFile': str(self.workspace_root / 'other.ndjson'),
                    'trackedLocations': [
                        {'location': 'src/app.ts:1', 'hypothesisIds': ['H1']},
                    ],
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding='utf-8',
        )

        collector_state.hydrate_log_cache(self.server)

        self.assertEqual(self.server.tracked_location_records, {})

    def test_hydrate_log_cache_drops_invalid_tracked_locations(self) -> None:
        source_file = self.workspace_root / 'src' / 'app.ts'
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text('console.log(\"hi\")\n', encoding='utf-8')

        self.location_state_file.write_text(
            json.dumps(
                {
                    'sessionId': 'test-session',
                    'logFile': str(self.log_file),
                    'trackedLocations': [
                        {'location': 'src/app.ts:1', 'hypothesisIds': ['H1']},
                        {'location': '../outside.ts:9', 'hypothesisIds': ['H2']},
                        {'location': 'src/missing.ts:4', 'hypothesisIds': ['H3']},
                    ],
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding='utf-8',
        )

        collector_state.hydrate_log_cache(self.server)

        self.assertEqual(set(self.server.tracked_location_records), {'src/app.ts:1'})
        self.assertEqual(
            self.server.tracked_location_records['src/app.ts:1']['hypothesisIds'],
            {'H1'},
        )


if __name__ == '__main__':
    unittest.main()
