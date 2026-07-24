#!/usr/bin/env python3
"""Focused tests for collector config, security, and location resolution."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import http.client
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
import main as collector_main
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
                    with mock.patch.object(
                        collector_browser.webbrowser,
                        'open_new_tab',
                        return_value=False,
                    ):
                        result = collector_browser.open_dashboard_in_browser('http://127.0.0.1:43125/')

        self.assertTrue(result['attempted'])
        self.assertFalse(result['succeeded'])
        self.assertIn('macos_open_exit_1', str(result['error']))
        self.assertIn('No application knows how to open URL', str(result['error']))
        self.assertIn('browser_open_returned_false', str(result['error']))

    def test_failed_platform_open_falls_back_to_python_webbrowser(self) -> None:
        completed = subprocess.CompletedProcess(
            args=['/usr/bin/xdg-open', 'http://127.0.0.1:43125/'],
            returncode=3,
            stderr='no method available',
        )

        with mock.patch.object(collector_browser.platform, 'system', return_value='Linux'):
            with mock.patch.object(collector_browser.shutil, 'which', return_value='/usr/bin/xdg-open'):
                with mock.patch.object(collector_browser.subprocess, 'run', return_value=completed):
                    with mock.patch.object(
                        collector_browser.webbrowser,
                        'open_new_tab',
                        return_value=True,
                    ) as browser_mock:
                        result = collector_browser.open_dashboard_in_browser('http://127.0.0.1:43125/')

        self.assertTrue(result['succeeded'])
        self.assertEqual(result['method'], 'python_webbrowser')
        self.assertEqual(len(result['attempts']), 2)
        browser_mock.assert_called_once_with('http://127.0.0.1:43125/')

    def test_webbrowser_fallback_when_no_platform_opener_exists(self) -> None:
        with mock.patch.object(collector_browser.platform, 'system', return_value='Linux'):
            with mock.patch.object(collector_browser.shutil, 'which', return_value=None):
                with mock.patch.object(collector_browser.webbrowser, 'open_new_tab', return_value=True) as browser_mock:
                    result = collector_browser.open_dashboard_in_browser('http://127.0.0.1:43125/')

        self.assertTrue(result['attempted'])
        self.assertTrue(result['succeeded'])
        self.assertEqual(result['error'], '')
        browser_mock.assert_called_once_with('http://127.0.0.1:43125/')


class CollectorDashboardStartupTests(unittest.TestCase):
    def test_auto_open_waits_for_http_readiness_before_browser_launch(self) -> None:
        events: list[str] = []

        class FakeServer:
            def __init__(self) -> None:
                self.write_lock = threading.Lock()
                self.health_url = 'http://127.0.0.1:43125/health'
                self.dashboard_url = 'http://127.0.0.1:43125/'
                self.dashboard_open_started_at = None
                self.dashboard_open_pending = True
                self.result = None

            def write_ready_file(self) -> None:
                events.append('ready')

            def record_dashboard_open_result(self, result: dict[str, object]) -> None:
                events.append('record')
                self.result = result

        server = FakeServer()

        def ready(_url: str) -> bool:
            events.append('health')
            return True

        def open_browser(_url: str) -> dict[str, object]:
            events.append('open')
            return {
                'method': 'test',
                'attempted': True,
                'succeeded': True,
                'error': '',
                'attempts': [],
            }

        with mock.patch.object(collector_main, 'wait_for_dashboard_ready', side_effect=ready):
            with mock.patch.object(collector_main, 'open_dashboard_in_browser', side_effect=open_browser):
                collector_main.auto_open_dashboard(server)  # type: ignore[arg-type]

        self.assertLess(events.index('health'), events.index('open'))
        self.assertLess(events.index('open'), events.index('record'))
        self.assertTrue(server.result['succeeded'])

    def test_auto_open_records_readiness_timeout_without_opening_browser(self) -> None:
        class FakeServer:
            def __init__(self) -> None:
                self.write_lock = threading.Lock()
                self.health_url = 'http://127.0.0.1:43125/health'
                self.dashboard_url = 'http://127.0.0.1:43125/'
                self.dashboard_open_started_at = None
                self.dashboard_open_pending = True
                self.result = None

            def write_ready_file(self) -> None:
                pass

            def record_dashboard_open_result(self, result: dict[str, object]) -> None:
                self.result = result

        server = FakeServer()
        with mock.patch.object(collector_main, 'wait_for_dashboard_ready', return_value=False):
            with mock.patch.object(collector_main, 'open_dashboard_in_browser') as open_mock:
                collector_main.auto_open_dashboard(server)  # type: ignore[arg-type]

        open_mock.assert_not_called()
        self.assertFalse(server.result['succeeded'])
        self.assertIn('not_ready', server.result['error'])


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
        payload: object | None = None,
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

    def _request_json_on_connection(
        self,
        connection: http.client.HTTPConnection,
        method: str,
        path: str,
        *,
        payload: object | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[http.client.HTTPResponse, dict[str, object]]:
        request_headers = {'Content-Type': 'application/json'}
        if headers:
            request_headers.update(headers)
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        connection.request(method, path, body=data, headers=request_headers)
        response = connection.getresponse()
        body = response.read()
        return response, json.loads(body.decode('utf-8') or '{}')

    def _assert_transport_batch_conflict(
        self,
        status: int,
        payload: dict[str, object],
        *,
        batch_id: str,
        expected_events: int | None,
        received_events: int,
    ) -> None:
        self.assertEqual(status, 409)
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['error'], 'transport_batch_id_conflict')
        self.assertEqual(payload['batchId'], batch_id)
        self.assertEqual(payload['expectedEventCount'], expected_events)
        self.assertEqual(payload['receivedEventCount'], received_events)
        self.assertNotIn('accepted', payload)
        self.assertNotIn('duplicateBatch', payload)
        self.assertNotIn('persistedEvents', payload)

    def test_clear_body_does_not_corrupt_next_request_on_persistent_connection(self) -> None:
        connection = http.client.HTTPConnection(
            '127.0.0.1',
            self.server.server_port,
            timeout=5,
        )
        try:
            clear_response, clear_payload = self._request_json_on_connection(
                connection,
                'POST',
                '/api/clear',
                payload={},
                headers={
                    collector_server.DASHBOARD_TOKEN_HEADER: self.server.dashboard_token,
                },
            )
            self.assertEqual(clear_response.status, 200)
            self.assertEqual(clear_response.version, 11)
            self.assertFalse(clear_response.will_close)
            self.assertEqual(clear_payload['summary']['totalEntries'], 0)
            original_socket = connection.sock
            self.assertIsNotNone(original_socket)

            state_response, state_payload = self._request_json_on_connection(
                connection,
                'GET',
                '/api/state',
            )

            self.assertEqual(state_response.status, 200)
            self.assertTrue(state_payload['ok'])
            self.assertIs(connection.sock, original_socket)
        finally:
            connection.close()

    def test_freeze_body_preserves_persistent_connection(self) -> None:
        connection = http.client.HTTPConnection(
            '127.0.0.1',
            self.server.server_port,
            timeout=5,
        )
        try:
            freeze_response, freeze_payload = self._request_json_on_connection(
                connection,
                'POST',
                '/api/recording/freeze',
                payload={},
                headers={
                    collector_server.DASHBOARD_TOKEN_HEADER: self.server.dashboard_token,
                },
            )
            self.assertEqual(freeze_response.status, 200)
            self.assertFalse(freeze_response.will_close)
            self.assertEqual(freeze_payload['status'], 'frozen')
            original_socket = connection.sock
            self.assertIsNotNone(original_socket)

            state_response, state_payload = self._request_json_on_connection(
                connection,
                'GET',
                '/api/state',
            )

            self.assertEqual(state_response.status, 200)
            self.assertEqual(state_payload['status'], 'frozen')
            self.assertIs(connection.sock, original_socket)
        finally:
            connection.close()

    def test_freeze_discards_events_clear_stays_available_and_resume_accepts_new_events(self) -> None:
        dashboard_headers = {
            collector_server.DASHBOARD_TOKEN_HEADER: self.server.dashboard_token,
        }
        initial_status, initial_payload = self._request_json(
            'POST',
            '/ingest',
            payload={'probeId': 'before-freeze', 'event': 'before_freeze'},
        )
        self.assertEqual(initial_status, 202)
        self.assertEqual(initial_payload['persistedEvents'], 1)

        freeze_status, freeze_payload = self._request_json(
            'POST',
            '/api/recording/freeze',
            payload={},
            headers=dashboard_headers,
        )
        self.assertEqual(freeze_status, 200)
        self.assertEqual(freeze_payload['status'], 'frozen')
        self.assertTrue(freeze_payload['service']['recordingFrozen'])
        self.assertTrue(freeze_payload['service']['recordingFrozenAt'])

        single_status, single_payload = self._request_json(
            'POST',
            '/ingest',
            payload={'probeId': 'frozen-single', 'event': 'must_not_persist'},
        )
        self.assertEqual(single_status, 202)
        self.assertEqual(single_payload['accepted'], 1)
        self.assertEqual(single_payload['persistedEvents'], 0)
        self.assertEqual(single_payload['discardedEvents'], 1)
        self.assertTrue(single_payload['discardedByFreeze'])

        frozen_batch = {
            'batchId': 'freeze-client:1:2',
            'events': [
                {'probeId': 'frozen-batch', 'event': 'must_not_persist', 'sequence': 1},
                {'probeId': 'frozen-batch', 'event': 'must_not_persist', 'sequence': 2},
            ],
        }
        batch_status, batch_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload=frozen_batch,
        )
        self.assertEqual(batch_status, 202)
        self.assertEqual(batch_payload['accepted'], 2)
        self.assertEqual(batch_payload['persistedEvents'], 0)
        self.assertEqual(batch_payload['discardedEvents'], 2)
        self.assertTrue(batch_payload['discardedByFreeze'])
        self.assertFalse(batch_payload['duplicateBatch'])
        self.assertEqual(len(self.log_file.read_text(encoding='utf-8').splitlines()), 1)

        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        self.assertEqual(state_payload['status'], 'frozen')
        self.assertEqual(state_payload['summary']['totalEntries'], 1)
        self.assertEqual(state_payload['service']['ingestFrozenDiscardedRequestCount'], 2)
        self.assertEqual(state_payload['service']['ingestFrozenDiscardedEventCount'], 3)

        health_status, health_payload = self._request_json('GET', '/health')
        self.assertEqual(health_status, 200)
        self.assertEqual(health_payload['status'], 'running')
        self.assertTrue(health_payload['recordingFrozen'])

        clear_status, clear_payload = self._request_json(
            'POST',
            '/api/clear',
            payload={},
            headers=dashboard_headers,
        )
        self.assertEqual(clear_status, 200)
        self.assertEqual(clear_payload['status'], 'frozen')
        self.assertTrue(clear_payload['service']['recordingFrozen'])
        self.assertEqual(clear_payload['summary']['totalEntries'], 0)
        self.assertEqual(clear_payload['service']['ingestFrozenDiscardedEventCount'], 0)
        self.assertEqual(self.log_file.read_text(encoding='utf-8'), '')

        resume_status, resume_payload = self._request_json(
            'POST',
            '/api/recording/resume',
            payload={},
            headers=dashboard_headers,
        )
        self.assertEqual(resume_status, 200)
        self.assertEqual(resume_payload['status'], 'running')
        self.assertFalse(resume_payload['service']['recordingFrozen'])
        self.assertTrue(resume_payload['service']['recordingResumedAt'])

        retry_status, retry_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload=frozen_batch,
        )
        self.assertEqual(retry_status, 202)
        self.assertTrue(retry_payload['duplicateBatch'])
        self.assertTrue(retry_payload['discardedByFreeze'])
        self.assertEqual(retry_payload['persistedEvents'], 0)
        self.assertEqual(self.log_file.read_text(encoding='utf-8'), '')

        resumed_status, resumed_payload = self._request_json(
            'POST',
            '/ingest',
            payload={'probeId': 'after-resume', 'event': 'after_resume'},
        )
        self.assertEqual(resumed_status, 202)
        self.assertEqual(resumed_payload['persistedEvents'], 1)
        self.assertEqual(resumed_payload['discardedEvents'], 0)
        self.assertEqual(len(self.log_file.read_text(encoding='utf-8').splitlines()), 1)

    def test_recording_controls_require_dashboard_access(self) -> None:
        for path in ('/api/recording/freeze', '/api/recording/resume'):
            with self.subTest(path=path):
                status, payload = self._request_json('POST', path, payload={})
                self.assertEqual(status, 403)
                self.assertEqual(payload['error'], 'dashboard_token_required')

    def test_stale_recording_generation_is_discarded_after_resume(self) -> None:
        dashboard_headers = {
            collector_server.DASHBOARD_TOKEN_HEADER: self.server.dashboard_token,
        }
        freeze_status, freeze_payload = self._request_json(
            'POST',
            '/api/recording/freeze',
            payload={},
            headers=dashboard_headers,
        )
        self.assertEqual(freeze_status, 200)
        self.assertEqual(freeze_payload['service']['recordingGeneration'], 1)

        repeated_status, repeated_payload = self._request_json(
            'POST',
            '/api/recording/freeze',
            payload={},
            headers=dashboard_headers,
        )
        self.assertEqual(repeated_status, 200)
        self.assertEqual(repeated_payload['service']['recordingGeneration'], 1)

        resume_status, resume_payload = self._request_json(
            'POST',
            '/api/recording/resume',
            payload={},
            headers=dashboard_headers,
        )
        self.assertEqual(resume_status, 200)
        current_generation = resume_payload['service']['recordingGeneration']
        self.assertEqual(current_generation, 2)

        stale_batch = {
            'batchId': 'offline-client:1:1',
            'events': [
                {
                    'probeId': 'offline-during-freeze',
                    'event': 'must_not_replay',
                    'recordingGeneration': 0,
                },
            ],
        }
        stale_status, stale_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload=stale_batch,
        )
        self.assertEqual(stale_status, 202)
        self.assertEqual(stale_payload['disposition'], 'discarded_stale_generation')
        self.assertEqual(stale_payload['discardedEvents'], 1)
        self.assertFalse(stale_payload['discardedByFreeze'])
        self.assertTrue(stale_payload['discardedByStaleGeneration'])
        self.assertEqual(stale_payload['recordingGeneration'], current_generation)
        self.assertEqual(self.log_file.read_text(encoding='utf-8'), '')

        retry_status, retry_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload=stale_batch,
        )
        self.assertEqual(retry_status, 202)
        self.assertTrue(retry_payload['duplicateBatch'])
        self.assertEqual(retry_payload['disposition'], 'discarded_stale_generation')
        self.assertEqual(self.log_file.read_text(encoding='utf-8'), '')

        current_status, current_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload={
                'batchId': 'online-client:2:2',
                'events': [
                    {
                        'probeId': 'online-after-resume',
                        'event': 'persist_now',
                        'recordingGeneration': current_generation,
                    },
                ],
            },
        )
        self.assertEqual(current_status, 202)
        self.assertEqual(current_payload['disposition'], 'persisted')
        self.assertEqual(current_payload['persistedEvents'], 1)
        self.assertEqual(len(self.log_file.read_text(encoding='utf-8').splitlines()), 1)

        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        self.assertEqual(
            state_payload['service']['ingestStaleGenerationDiscardedEventCount'],
            1,
        )

    def test_concurrent_recording_toggles_keep_ready_file_valid_and_current(self) -> None:
        ready_file = self.workspace_root / 'collector.ready.json'
        self.server.ready_file = ready_file
        self.server.write_ready_file()
        dashboard_headers = {
            collector_server.DASHBOARD_TOKEN_HEADER: self.server.dashboard_token,
        }

        def toggle_recording(index: int) -> tuple[int, dict[str, object]]:
            action = 'freeze' if index % 2 == 0 else 'resume'
            return self._request_json(
                'POST',
                f'/api/recording/{action}',
                payload={},
                headers=dashboard_headers,
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(toggle_recording, range(32)))

        self.assertTrue(all(status == 200 for status, _ in results))
        ready_payload = json.loads(ready_file.read_text(encoding='utf-8'))
        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        self.assertEqual(
            ready_payload['recordingGeneration'],
            state_payload['service']['recordingGeneration'],
        )
        self.assertEqual(
            ready_payload['recordingFrozen'],
            state_payload['service']['recordingFrozen'],
        )

    def test_freeze_linearizes_with_concurrent_batches_without_partial_writes(self) -> None:
        dashboard_headers = {
            collector_server.DASHBOARD_TOKEN_HEADER: self.server.dashboard_token,
        }
        batch_count = 24
        events_per_batch = 3
        start_gate = threading.Barrier(batch_count + 1)

        def send_batch(index: int) -> tuple[int, dict[str, object]]:
            start_gate.wait(timeout=5)
            return self._request_json(
                'POST',
                '/ingest/batch',
                payload={
                    'batchId': f'concurrent-freeze:{index}',
                    'events': [
                        {
                            'probeId': f'concurrent.{index}',
                            'event': 'race_with_freeze',
                            'sequence': sequence,
                        }
                        for sequence in range(events_per_batch)
                    ],
                },
            )

        def freeze() -> tuple[int, dict[str, object]]:
            start_gate.wait(timeout=5)
            return self._request_json(
                'POST',
                '/api/recording/freeze',
                payload={},
                headers=dashboard_headers,
            )

        with ThreadPoolExecutor(max_workers=batch_count + 1) as pool:
            batch_futures = [pool.submit(send_batch, index) for index in range(batch_count)]
            freeze_future = pool.submit(freeze)
            batch_results = [future.result(timeout=10) for future in batch_futures]
            freeze_status, freeze_payload = freeze_future.result(timeout=10)

        self.assertEqual(freeze_status, 200)
        self.assertEqual(freeze_payload['status'], 'frozen')
        persisted_events = 0
        for response_status, payload in batch_results:
            self.assertEqual(response_status, 202)
            self.assertIn(payload['persistedEvents'], (0, events_per_batch))
            self.assertIn(payload['discardedEvents'], (0, events_per_batch))
            self.assertEqual(
                payload['persistedEvents'] + payload['discardedEvents'],
                events_per_batch,
            )
            persisted_events += payload['persistedEvents']

        persisted_lines = self.log_file.read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(persisted_lines), persisted_events)

        post_freeze_status, post_freeze_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload={
                'batchId': 'concurrent-freeze:after',
                'events': [
                    {'probeId': 'after-freeze', 'event': 'must_not_persist'},
                ],
            },
        )
        self.assertEqual(post_freeze_status, 202)
        self.assertEqual(post_freeze_payload['persistedEvents'], 0)
        self.assertEqual(post_freeze_payload['discardedEvents'], 1)
        self.assertEqual(
            len(self.log_file.read_text(encoding='utf-8').splitlines()),
            persisted_events,
        )

    def test_dashboard_opened_body_preserves_persistent_connection(self) -> None:
        connection = http.client.HTTPConnection(
            '127.0.0.1',
            self.server.server_port,
            timeout=5,
        )
        try:
            opened_response, opened_payload = self._request_json_on_connection(
                connection,
                'POST',
                '/api/dashboard-opened',
                payload={},
                headers={
                    collector_server.DASHBOARD_TOKEN_HEADER: self.server.dashboard_token,
                },
            )
            self.assertEqual(opened_response.status, 200)
            self.assertTrue(opened_payload['ok'])
            original_socket = connection.sock
            self.assertIsNotNone(original_socket)

            state_response, state_payload = self._request_json_on_connection(
                connection,
                'GET',
                '/api/state',
            )

            self.assertEqual(state_response.status, 200)
            self.assertTrue(state_payload['ok'])
            self.assertIs(connection.sock, original_socket)
        finally:
            connection.close()

    def test_rejected_sensitive_post_closes_connection_with_unread_body(self) -> None:
        cases = [
            ('missing token', {}),
            (
                'untrusted origin',
                {
                    collector_server.DASHBOARD_TOKEN_HEADER: self.server.dashboard_token,
                    'Origin': 'https://evil.example',
                },
            ),
        ]

        for label, headers in cases:
            with self.subTest(label=label):
                connection = http.client.HTTPConnection(
                    '127.0.0.1',
                    self.server.server_port,
                    timeout=5,
                )
                try:
                    connection.connect()
                    original_socket = connection.sock
                    rejected_response, rejected_payload = self._request_json_on_connection(
                        connection,
                        'POST',
                        '/api/config',
                        payload={'selectedIde': 'zed'},
                        headers=headers,
                    )
                    self.assertEqual(rejected_response.status, 403)
                    self.assertEqual(rejected_response.getheader('Connection'), 'close')
                    self.assertTrue(rejected_response.will_close)
                    self.assertIn(
                        rejected_payload['error'],
                        {'dashboard_token_required', 'dashboard_origin_forbidden'},
                    )

                    state_response, state_payload = self._request_json_on_connection(
                        connection,
                        'GET',
                        '/api/state',
                    )

                    self.assertEqual(state_response.status, 200)
                    self.assertTrue(state_payload['ok'])
                    self.assertIsNot(connection.sock, original_socket)
                finally:
                    connection.close()

    def test_non_ascii_content_length_is_rejected_and_closes_connection(self) -> None:
        connection = http.client.HTTPConnection(
            '127.0.0.1',
            self.server.server_port,
            timeout=5,
        )
        try:
            connection.putrequest('POST', '/api/clear')
            connection.putheader('Content-Type', 'application/json')
            connection.putheader(
                collector_server.DASHBOARD_TOKEN_HEADER,
                self.server.dashboard_token,
            )
            connection.putheader('Content-Length', '²')
            connection.endheaders()

            response = connection.getresponse()
            payload = json.loads(response.read().decode('utf-8'))

            self.assertEqual(response.status, 400)
            self.assertEqual(response.getheader('Connection'), 'close')
            self.assertTrue(response.will_close)
            self.assertEqual(payload['error'], 'invalid_request_body')
        finally:
            connection.close()

    def test_any_transfer_encoding_is_rejected_and_closes_connection(self) -> None:
        connection = http.client.HTTPConnection(
            '127.0.0.1',
            self.server.server_port,
            timeout=5,
        )
        try:
            connection.putrequest('POST', '/api/clear')
            connection.putheader('Content-Type', 'application/json')
            connection.putheader(
                collector_server.DASHBOARD_TOKEN_HEADER,
                self.server.dashboard_token,
            )
            connection.putheader('Transfer-Encoding', '')
            connection.putheader('Transfer-Encoding', 'chunked')
            connection.endheaders()

            response = connection.getresponse()
            payload = json.loads(response.read().decode('utf-8'))

            self.assertEqual(response.status, 400)
            self.assertEqual(response.getheader('Connection'), 'close')
            self.assertTrue(response.will_close)
            self.assertEqual(payload['error'], 'invalid_request_body')
        finally:
            connection.close()

    def test_batch_ingest_appends_structured_events(self) -> None:
        events = [
            {
                'runId': 'run-1',
                'correlationId': 'corr-1',
                'sequence': 1,
                'probeId': 'flow.start',
                'hypothesisIds': ['H1', 'H2'],
                'location': 'src/app.ts:1',
                'event': 'start',
            },
            {
                'runId': 'run-1',
                'correlationId': 'corr-1',
                'sequence': 2,
                'probeId': 'flow.end',
                'hypothesisIds': ['H2'],
                'location': 'src/app.ts:2',
                'event': 'finish',
            },
        ]

        status, payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload={'events': events},
            headers={'X-Debug-Session-Id': 'test-session'},
        )
        self.assertEqual(status, 202)
        self.assertEqual(payload['accepted'], 2)

        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        self.assertEqual(state_payload['service']['batchEndpoint'], self.server.batch_endpoint_url)
        summary = state_payload['summary']
        self.assertEqual(summary['totalEntries'], 2)
        self.assertEqual(summary['correlationCounts'], [{'name': 'corr-1', 'count': 2}])
        self.assertEqual(
            {item['name']: item['count'] for item in summary['hypothesisCounts']},
            {'H2': 2, 'H1': 1},
        )
        self.assertEqual(len(self.log_file.read_text(encoding='utf-8').splitlines()), 2)

    def test_message_less_event_remains_valid_for_dashboard_summary_fallback(self) -> None:
        event = {
            'runId': 'post-repair',
            'probeId': 'flow.terminal',
            'location': 'src/app.ts:12',
            'event': 'flow_terminal',
            'timestamp': 1_783_933_652_000,
        }

        status, payload = self._request_json('POST', '/ingest', payload=event)
        self.assertEqual(status, 202)
        self.assertTrue(payload['ok'])

        logs_status, logs_payload = self._request_json('GET', '/api/logs')
        self.assertEqual(logs_status, 200)
        entry = logs_payload['entries'][0]
        self.assertEqual(entry['message'], '')
        self.assertEqual(entry['event'], 'flow_terminal')
        self.assertEqual(entry['probeId'], 'flow.terminal')

        detail_status, detail_payload = self._request_json(
            'GET',
            f"/api/logs/detail?entryIndex={entry['entryIndex']}",
        )
        self.assertEqual(detail_status, 200)
        raw_payload = detail_payload['entry']['payload']
        self.assertNotIn('message', raw_payload)
        self.assertEqual(raw_payload['event'], event['event'])
        self.assertEqual(raw_payload['probeId'], event['probeId'])

    def test_batch_ingest_has_no_event_count_cap(self) -> None:
        events = [
            {
                'probeId': f'p{i}',
                'event': 'fetch_start',
                'sequence': i + 1,
            }
            for i in range(1_000)
        ]
        status, payload = self._request_json('POST', '/ingest/batch', payload=events)
        self.assertEqual(status, 202)
        self.assertEqual(payload['accepted'], len(events))
        self.assertEqual(len(self.log_file.read_text(encoding='utf-8').splitlines()), len(events))

        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        self.assertFalse(state_payload['service']['ingestEventCountLimited'])
        self.assertEqual(state_payload['summary']['totalEntries'], len(events))

    def test_state_count_lists_are_bounded_without_limiting_capture(self) -> None:
        events = [
            {
                'probeId': 'fetch.lifecycle',
                'event': 'fetch_start',
                'correlationId': f'fetch-{index}',
            }
            for index in range(500)
        ]
        status, payload = self._request_json('POST', '/ingest/batch', payload={'events': events})
        self.assertEqual(status, 202)
        self.assertEqual(payload['accepted'], len(events))

        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        summary = state_payload['summary']
        self.assertEqual(summary['totalEntries'], len(events))
        self.assertEqual(summary['countCardinality']['correlationCounts'], len(events))
        self.assertIn('correlationCounts', summary['countListsTruncated'])
        self.assertEqual(len(summary['correlationCounts']), summary['countListLimit'])

    def test_retrying_same_transport_batch_is_idempotent(self) -> None:
        events = [
            {'probeId': 'fetch.lifecycle', 'event': 'fetch_start', 'transportId': f'e-{i}'}
            for i in range(25)
        ]
        body = {'batchId': 'client-a:1:25', 'events': events}
        reordered_body = {
            'batchId': body['batchId'],
            'events': [
                {
                    'transportId': event['transportId'],
                    'event': event['event'],
                    'probeId': event['probeId'],
                }
                for event in events
            ],
        }

        first_status, first_payload = self._request_json('POST', '/ingest/batch', payload=body)
        second_status, second_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload=reordered_body,
        )

        self.assertEqual(first_status, 202)
        self.assertEqual(first_payload['persistedEvents'], len(events))
        self.assertFalse(first_payload['duplicateBatch'])
        self.assertEqual(second_status, 202)
        self.assertEqual(second_payload['accepted'], len(events))
        self.assertEqual(second_payload['persistedEvents'], 0)
        self.assertTrue(second_payload['duplicateBatch'])
        self.assertEqual(len(self.log_file.read_text(encoding='utf-8').splitlines()), len(events))

    def test_outer_batch_id_survives_spoofed_inner_id_and_restart(self) -> None:
        outer_batch_id = 'client-restart:1:1'
        original_events = [
            {
                'probeId': 'restart.identity',
                'event': 'persist_once',
                'transportBatchId': 'spoofed-inner-original',
            },
        ]
        body = {'batchId': outer_batch_id, 'events': original_events}
        first_status, first_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload=body,
        )
        self.assertEqual(first_status, 202)
        self.assertEqual(first_payload['persistedEvents'], 1)

        changed_inner_events = [dict(original_events[0])]
        changed_inner_events[0]['transportBatchId'] = 'spoofed-inner-retry'
        duplicate_status, duplicate_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload={'batchId': outer_batch_id, 'events': changed_inner_events},
        )
        self.assertEqual(duplicate_status, 202)
        self.assertTrue(duplicate_payload['duplicateBatch'])
        self.assertEqual(duplicate_payload['persistedEvents'], 0)

        persisted_before_restart = [
            json.loads(line)
            for line in self.log_file.read_text(encoding='utf-8').splitlines()
        ]
        self.assertEqual(len(persisted_before_restart), 1)
        self.assertEqual(
            persisted_before_restart[0]['transportBatchId'],
            outer_batch_id,
        )

        previous_server = self.server
        previous_thread = self._thread
        previous_server.shutdown()
        previous_server.server_close()
        previous_thread.join(timeout=5)

        restarted_server = collector_server.CollectorServer(
            ('127.0.0.1', 0),
            self.log_file,
            self.workspace_root,
            '',
            self.location_state_file,
            None,
            'test-session',
            None,
        )
        collector_state.hydrate_log_cache(restarted_server)
        restarted_thread = threading.Thread(
            target=restarted_server.serve_forever,
            daemon=True,
        )
        restarted_thread.start()
        self.server = restarted_server
        self._thread = restarted_thread

        self.assertIn(outer_batch_id, restarted_server.seen_transport_batch_ids)
        self.assertNotIn('spoofed-inner-original', restarted_server.seen_transport_batch_ids)
        self.assertNotIn(outer_batch_id, restarted_server.transport_batch_identities)

        retry_status, retry_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload=body,
        )
        self._assert_transport_batch_conflict(
            retry_status,
            retry_payload,
            batch_id=outer_batch_id,
            expected_events=None,
            received_events=1,
        )
        self.assertEqual(
            len(self.log_file.read_text(encoding='utf-8').splitlines()),
            1,
        )

    def test_persisted_batch_id_rejects_every_different_frame(self) -> None:
        batch_id = 'client-persisted-conflict:1:2'
        events = [
            {'probeId': 'persisted.conflict', 'event': 'original', 'sequence': 1},
            {'probeId': 'persisted.conflict', 'event': 'original', 'sequence': 2},
        ]
        first_status, first_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload={'batchId': batch_id, 'events': events},
        )
        self.assertEqual(first_status, 202)
        self.assertEqual(first_payload['persistedEvents'], len(events))

        different_count_status, different_count_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload={'batchId': batch_id, 'events': events[:1]},
        )
        self._assert_transport_batch_conflict(
            different_count_status,
            different_count_payload,
            batch_id=batch_id,
            expected_events=len(events),
            received_events=1,
        )

        different_body = [dict(event) for event in events]
        different_body[1]['event'] = 'changed-with-same-count'
        different_body_status, different_body_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload={'batchId': batch_id, 'events': different_body},
        )
        self._assert_transport_batch_conflict(
            different_body_status,
            different_body_payload,
            batch_id=batch_id,
            expected_events=len(events),
            received_events=len(different_body),
        )

        persisted = [
            json.loads(line)
            for line in self.log_file.read_text(encoding='utf-8').splitlines()
        ]
        self.assertEqual([event['event'] for event in persisted], ['original', 'original'])

    def test_discarded_batch_id_rejects_a_different_frame(self) -> None:
        dashboard_headers = {
            collector_server.DASHBOARD_TOKEN_HEADER: self.server.dashboard_token,
        }
        freeze_status, _ = self._request_json(
            'POST',
            '/api/recording/freeze',
            payload={},
            headers=dashboard_headers,
        )
        self.assertEqual(freeze_status, 200)

        batch_id = 'client-discarded-conflict:1:2'
        events = [
            {'probeId': 'discarded.conflict', 'event': 'original', 'sequence': 1},
            {'probeId': 'discarded.conflict', 'event': 'original', 'sequence': 2},
        ]
        first_status, first_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload={'batchId': batch_id, 'events': events},
        )
        self.assertEqual(first_status, 202)
        self.assertEqual(first_payload['disposition'], 'discarded_frozen')
        self.assertEqual(first_payload['discardedEvents'], len(events))

        changed_events = [dict(event) for event in events]
        changed_events[0]['event'] = 'changed-with-same-count'
        conflict_status, conflict_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload={'batchId': batch_id, 'events': changed_events},
        )
        self._assert_transport_batch_conflict(
            conflict_status,
            conflict_payload,
            batch_id=batch_id,
            expected_events=len(events),
            received_events=len(changed_events),
        )

        retry_status, retry_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload={'batchId': batch_id, 'events': events},
        )
        self.assertEqual(retry_status, 202)
        self.assertTrue(retry_payload['duplicateBatch'])
        self.assertEqual(retry_payload['disposition'], 'discarded_frozen')
        self.assertEqual(retry_payload['discardedEvents'], len(events))
        self.assertEqual(self.log_file.read_text(encoding='utf-8'), '')

    def test_clear_marks_preclear_persisted_batch_as_terminally_discarded(self) -> None:
        events = [
            {'probeId': 'before.clear', 'event': 'persist_then_clear'},
            {'probeId': 'before.clear', 'event': 'persist_then_clear'},
        ]
        body = {'batchId': 'client-clear:1:2', 'events': events}
        first_status, first_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload=body,
        )
        self.assertEqual(first_status, 202)
        self.assertEqual(first_payload['persistedEvents'], len(events))

        clear_status, clear_payload = self._request_json(
            'POST',
            '/api/clear',
            payload={},
            headers={
                collector_server.DASHBOARD_TOKEN_HEADER: self.server.dashboard_token,
            },
        )
        self.assertEqual(clear_status, 200)
        self.assertEqual(clear_payload['summary']['totalEntries'], 0)

        retry_status, retry_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload=body,
        )
        self.assertEqual(retry_status, 202)
        self.assertTrue(retry_payload['duplicateBatch'])
        self.assertEqual(retry_payload['disposition'], 'discarded_cleared')
        self.assertEqual(retry_payload['persistedEvents'], 0)
        self.assertEqual(retry_payload['discardedEvents'], len(events))
        self.assertTrue(retry_payload['discardedByClear'])
        self.assertFalse(retry_payload['discardedByFreeze'])
        self.assertEqual(self.log_file.read_text(encoding='utf-8'), '')

        changed_events = [dict(event) for event in events]
        changed_events[0]['event'] = 'changed_after_clear'
        conflict_status, conflict_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload={'batchId': body['batchId'], 'events': changed_events},
        )
        self._assert_transport_batch_conflict(
            conflict_status,
            conflict_payload,
            batch_id=str(body['batchId']),
            expected_events=len(events),
            received_events=len(changed_events),
        )
        self.assertEqual(self.log_file.read_text(encoding='utf-8'), '')

    def test_clear_waits_for_persisted_batch_ack_before_truncating(self) -> None:
        class ContentionLock:
            def __init__(self) -> None:
                self._lock = threading.Lock()
                self.contended = threading.Event()

            def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
                if self._lock.locked():
                    self.contended.set()
                return self._lock.acquire(blocking, timeout)

            def release(self) -> None:
                self._lock.release()

            def __enter__(self) -> ContentionLock:
                self.acquire()
                return self

            def __exit__(self, *_args: object) -> None:
                self.release()

        ingest_lock = ContentionLock()
        self.server.ingest_lock = ingest_lock
        events = [
            {'probeId': 'ack.clear', 'event': 'persist_before_ack', 'sequence': 1},
            {'probeId': 'ack.clear', 'event': 'persist_before_ack', 'sequence': 2},
        ]
        batch_id = 'client-ack-clear:1:2'
        body = {'batchId': batch_id, 'events': events}
        append_completed = threading.Event()
        allow_ack = threading.Event()
        ack_flushed = threading.Event()
        original_json_response = collector_server.CollectorRequestHandler._json_response

        def hold_persisted_ack(
            handler: collector_server.CollectorRequestHandler,
            status: collector_server.HTTPStatus,
            payload: dict[str, object],
            *,
            cors_mode: str = 'none',
        ) -> None:
            if payload.get('batchId') == batch_id and payload.get('persistedEvents') == len(events):
                append_completed.set()
                if not allow_ack.wait(timeout=5):
                    raise AssertionError('timed out waiting to release the persisted ACK')
            original_json_response(handler, status, payload, cors_mode=cors_mode)
            if payload.get('batchId') == batch_id and payload.get('persistedEvents') == len(events):
                ack_flushed.set()

        dashboard_headers = {
            collector_server.DASHBOARD_TOKEN_HEADER: self.server.dashboard_token,
        }
        with mock.patch.object(
            collector_server.CollectorRequestHandler,
            '_json_response',
            new=hold_persisted_ack,
        ):
            with ThreadPoolExecutor(max_workers=2) as pool:
                try:
                    ingest_future = pool.submit(
                        self._request_json,
                        'POST',
                        '/ingest/batch',
                        payload=body,
                    )
                    self.assertTrue(append_completed.wait(timeout=5))
                    self.assertEqual(
                        len(self.log_file.read_text(encoding='utf-8').splitlines()),
                        len(events),
                    )

                    clear_future = pool.submit(
                        self._request_json,
                        'POST',
                        '/api/clear',
                        payload={},
                        headers=dashboard_headers,
                    )
                    self.assertTrue(ingest_lock.contended.wait(timeout=5))
                    self.assertFalse(clear_future.done())

                    allow_ack.set()
                    ingest_status, ingest_payload = ingest_future.result(timeout=5)
                    clear_status, clear_payload = clear_future.result(timeout=5)
                finally:
                    allow_ack.set()

        self.assertTrue(ack_flushed.is_set())
        self.assertEqual(ingest_status, 202)
        self.assertEqual(ingest_payload['persistedEvents'], len(events))
        self.assertEqual(clear_status, 200)
        self.assertEqual(clear_payload['summary']['totalEntries'], 0)

        retry_status, retry_payload = self._request_json(
            'POST',
            '/ingest/batch',
            payload=body,
        )
        self.assertEqual(retry_status, 202)
        self.assertTrue(retry_payload['duplicateBatch'])
        self.assertEqual(retry_payload['disposition'], 'discarded_cleared')
        self.assertEqual(retry_payload['persistedEvents'], 0)
        self.assertEqual(retry_payload['discardedEvents'], len(events))
        self.assertEqual(self.log_file.read_text(encoding='utf-8'), '')

    def test_ingest_ack_is_not_blocked_by_dashboard_index_lock(self) -> None:
        self.server.write_lock.acquire()
        try:
            status, payload = self._request_json(
                'POST',
                '/ingest/batch',
                payload={'events': [{'probeId': 'fetch.start'} for _ in range(500)]},
            )
        finally:
            self.server.write_lock.release()

        self.assertEqual(status, 202)
        self.assertEqual(payload['accepted'], 500)

    def test_concurrent_batches_all_complete_and_persist(self) -> None:
        batch_count = 32
        events_per_batch = 64

        def send_batch(batch_index: int) -> tuple[int, dict[str, object]]:
            events = [
                {
                    'probeId': 'fetch.lifecycle',
                    'event': 'fetch_start',
                    'correlationId': f'{batch_index}-{event_index}',
                }
                for event_index in range(events_per_batch)
            ]
            return self._request_json('POST', '/ingest/batch', payload={'events': events})

        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(send_batch, range(batch_count)))

        self.assertTrue(all(status == 202 for status, _ in results))
        self.assertEqual(
            sum(int(payload['accepted']) for _, payload in results),
            batch_count * events_per_batch,
        )
        self.assertEqual(
            len(self.log_file.read_text(encoding='utf-8').splitlines()),
            batch_count * events_per_batch,
        )

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

    def test_sync_locations_accepts_more_than_ten_active_sources(self) -> None:
        source_file = self.workspace_root / 'src' / 'app.ts'
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text(
            '\n'.join(f'console.log({index});' for index in range(1, 12)),
            encoding='utf-8',
        )

        state_status, state_payload = self._request_json('GET', '/api/state')
        self.assertEqual(state_status, 200)
        dashboard_token = state_payload['service']['dashboardToken']

        locations = [
            {'location': f'src/app.ts:{index}', 'hypothesisIds': [f'H{index}']}
            for index in range(1, 12)
        ]
        status, payload = self._request_json(
            'POST',
            '/api/locations/sync',
            payload={'locations': locations},
            headers={collector_server.DASHBOARD_TOKEN_HEADER: dashboard_token},
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload['trackedLocationCount'], 11)
        self.assertEqual(len(payload['locations']), 11)

        persisted = json.loads(self.location_state_file.read_text(encoding='utf-8'))
        self.assertEqual(persisted['trackedLocationCount'], 11)

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
