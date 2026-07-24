#!/usr/bin/env python3
"""Tests for browser debug instrumentation validation."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from validate_browser_instrumentation import validate


SAFE_TRANSPORT = """
import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'

const transport = getOrCreateBrowserDebugTransport({
  endpoint: ready.endpoint,
  batchEndpoint: ready.batchEndpoint,
  sessionId: ready.sessionId,
  recordingGeneration: ready.recordingGeneration,
})

export function emit(event) {
  void transport.recordSafe(event)
}
"""


class BrowserInstrumentationValidationTests(unittest.TestCase):
    def _validate_source(self, source: str) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "probe.ts"
            path.write_text(source, encoding="utf-8")
            return validate([path])

    def test_shared_transport_passes(self) -> None:
        report = self._validate_source(SAFE_TRANSPORT)
        self.assertTrue(report["ok"], msg=report)

    def test_global_fetch_only_instrumentation_counts_as_transport_usage(self) -> None:
        report = self._validate_source(
            """
import {
  getOrCreateBrowserDebugTransport,
  instrumentGlobalFetch,
} from './browser-debug-transport.mjs'

const transport = getOrCreateBrowserDebugTransport({
  endpoint: ready.endpoint,
  batchEndpoint: ready.batchEndpoint,
  sessionId: ready.sessionId,
  recordingGeneration: ready.recordingGeneration,
})

export const restoreFetch = instrumentGlobalFetch({ transport })
"""
        )
        self.assertTrue(report["ok"], msg=report)
        self.assertEqual(report["recordSafeCallSites"], 0)
        self.assertEqual(report["sharedProducerCallSites"], 1)

    def test_local_fake_producer_does_not_satisfy_transport_usage(self) -> None:
        report = self._validate_source(
            """
import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'

const transport = getOrCreateBrowserDebugTransport(ready)
function instrumentGlobalFetch() { return transport }
instrumentGlobalFetch()
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("transport_unused", codes)

    def test_commented_out_wiring_cannot_satisfy_the_gate(self) -> None:
        report = self._validate_source(
            """
// import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'
// const transport = getOrCreateBrowserDebugTransport(ready)
// transport.recordSafe({ event: 'comment-only' })
export const noInstrumentation = true
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("transport_import_count", codes)
        self.assertIn("transport_instance_count", codes)
        self.assertIn("transport_binding_count", codes)
        self.assertIn("transport_unused", codes)

    def test_string_and_template_text_cannot_satisfy_the_gate(self) -> None:
        fake_wiring = (
            "import { getOrCreateBrowserDebugTransport } from "
            "'./browser-debug-transport.mjs'; "
            "const transport = getOrCreateBrowserDebugTransport(ready); "
            "transport.recordSafe(event)"
        )
        for literal in (repr(fake_wiring), f"`{fake_wiring}`"):
            with self.subTest(literal=literal[0]):
                report = self._validate_source(
                    f"export const fakeWiring = {literal}\n"
                )
                self.assertFalse(report["ok"])
                self.assertEqual(report["transportImports"], 0)
                self.assertEqual(report["transportInstances"], 0)
                self.assertEqual(report["recordSafeCallSites"], 0)

    def test_comments_cannot_invent_forbidden_instrumentation(self) -> None:
        report = self._validate_source(
            SAFE_TRANSPORT
            + """
/*
void fetch('http://127.0.0.1:59060/ingest', { keepalive: true })
const reduced = throttle((event) => transport.recordSafe(event))
*/
// navigator.sendBeacon('/ingest', '{}')
"""
        )
        self.assertTrue(report["ok"], msg=report)

    def test_fake_record_sink_does_not_activate_unused_shared_transport(self) -> None:
        report = self._validate_source(
            """
import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'

const sharedTransport = getOrCreateBrowserDebugTransport(ready)
const fake = { recordSafe() {} }
fake.recordSafe({ event: 'not-shared' })
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertEqual(report["recordSafeCallSites"], 0)
        self.assertIn("transport_unused", codes)

    def test_producer_must_receive_the_factory_transport_binding(self) -> None:
        report = self._validate_source(
            """
import {
  getOrCreateBrowserDebugTransport,
  instrumentGlobalFetch,
} from './browser-debug-transport.mjs'

const sharedTransport = getOrCreateBrowserDebugTransport(ready)
const fake = { recordSafe() {} }
instrumentGlobalFetch({ transport: fake })
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertEqual(report["sharedProducerCallSites"], 0)
        self.assertIn("producer_transport_binding", codes)
        self.assertIn("transport_unused", codes)

    def test_generic_producer_with_factory_transport_counts_as_usage(self) -> None:
        report = self._validate_source(
            """
import {
  getOrCreateBrowserDebugTransport,
  installRealmDebugProducer,
} from './browser-debug-transport.mjs'

const debugTransport = getOrCreateBrowserDebugTransport(ready)
installRealmDebugProducer({
  producerKey: 'scroll',
  transport: debugTransport,
  install() { return () => {} },
})
"""
        )
        self.assertTrue(report["ok"], msg=report)
        self.assertEqual(report["sharedProducerCallSites"], 1)

    def test_transport_parameter_cannot_shadow_the_factory_binding(self) -> None:
        report = self._validate_source(
            """
import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'

const sharedTransport = getOrCreateBrowserDebugTransport(ready)
export function emit(sharedTransport, event) {
  void sharedTransport.recordSafe(event)
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("transport_binding_shadow", codes)

    def test_producer_transport_parameter_cannot_shadow_the_factory_binding(self) -> None:
        report = self._validate_source(
            """
import {
  getOrCreateBrowserDebugTransport,
  instrumentGlobalFetch,
} from './browser-debug-transport.mjs'

const sharedTransport = getOrCreateBrowserDebugTransport(ready)
export function install(sharedTransport) {
  return instrumentGlobalFetch({ transport: sharedTransport })
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("transport_binding_shadow", codes)

    def test_factory_call_inside_a_shadowing_scope_is_not_canonical(self) -> None:
        report = self._validate_source(
            """
import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'

export function install(getOrCreateBrowserDebugTransport, ready) {
  const sharedTransport = getOrCreateBrowserDebugTransport(ready)
  return (event) => sharedTransport.recordSafe(event)
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("transport_binding_scope", codes)
        self.assertIn("transport_binding_count", codes)

    def test_regex_braces_cannot_fake_a_top_level_factory_binding(self) -> None:
        regex_literals = (
            "/}/",
            r"/[{}\\/]+\\}/dg",
            "/[{]nested[}]/u",
        )
        for regex_literal in regex_literals:
            with self.subTest(regex_literal=regex_literal):
                report = self._validate_source(
                    f"""
import {{ getOrCreateBrowserDebugTransport }} from './browser-debug-transport.mjs'

export function install(getOrCreateBrowserDebugTransport, ready) {{
  const braces = {regex_literal}
  const sharedTransport = getOrCreateBrowserDebugTransport(ready)
  return (event) => sharedTransport.recordSafe(event)
}}
"""
                )
                codes = {issue["code"] for issue in report["issues"]}
                self.assertFalse(report["ok"])
                self.assertIn("transport_binding_scope", codes)
                self.assertIn("transport_binding_count", codes)

    def test_regex_after_control_condition_cannot_change_binding_depth(self) -> None:
        report = self._validate_source(
            """
import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'

export function install(ready) {
  if (ready) /}/.test('}')
  const sharedTransport = getOrCreateBrowserDebugTransport(ready)
  return (event) => sharedTransport.recordSafe(event)
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("transport_binding_scope", codes)
        self.assertIn("transport_binding_count", codes)

    def test_regex_after_block_fails_closed_instead_of_faking_top_level(self) -> None:
        report = self._validate_source(
            """
import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'

export function install(ready) {
  if (ready) {}
  /}/.test('}')
  const sharedTransport = getOrCreateBrowserDebugTransport(ready)
  return (event) => sharedTransport.recordSafe(event)
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("ambiguous_regex_brace", codes)

    def test_division_does_not_mask_following_canonical_wiring(self) -> None:
        report = self._validate_source(
            """
const ratio = total / count
import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'
const sharedTransport = getOrCreateBrowserDebugTransport(ready)
export function emit(event) { void sharedTransport.recordSafe(event) }
"""
        )
        self.assertTrue(report["ok"], msg=report)

    def test_cross_file_import_cannot_shadow_the_canonical_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "transport.ts").write_text(
                """
import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'
export const sharedTransport = getOrCreateBrowserDebugTransport(ready)
""",
                encoding="utf-8",
            )
            (root / "probe.ts").write_text(
                """
import { fakeTransport as sharedTransport } from './fake'
export function emit(event) { void sharedTransport.recordSafe(event) }
""",
                encoding="utf-8",
            )
            report = validate([root])
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("transport_binding_shadow", codes)

    def test_cross_file_declarations_cannot_shadow_the_canonical_binding(self) -> None:
        declarations = (
            "function sharedTransport() {}",
            "class sharedTransport { static recordSafe() {} }",
            "enum sharedTransport { recordSafe }",
            "namespace sharedTransport { export function recordSafe() {} }",
            "module sharedTransport { export function recordSafe() {} }",
        )
        for declaration in declarations:
            with self.subTest(declaration=declaration.split()[0]):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    (root / "transport.ts").write_text(
                        """
import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'
export const sharedTransport = getOrCreateBrowserDebugTransport(ready)
""",
                        encoding="utf-8",
                    )
                    (root / "probe.ts").write_text(
                        f"""
{declaration}
sharedTransport.recordSafe({{ event: 'not-shared' }})
""",
                        encoding="utf-8",
                    )
                    report = validate([root])
                codes = {issue["code"] for issue in report["issues"]}
                self.assertFalse(report["ok"])
                self.assertIn("transport_binding_shadow", codes)

    def test_default_value_call_cannot_hide_a_transport_parameter_shadow(self) -> None:
        report = self._validate_source(
            """
import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'

const sharedTransport = getOrCreateBrowserDebugTransport(ready)
export function emit(sharedTransport = makeFake()) {
  void sharedTransport.recordSafe({ event: 'fake' })
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("transport_binding_shadow", codes)

    def test_direct_keepalive_ingest_and_silent_catch_fail(self) -> None:
        report = self._validate_source(
            """
const DEBUG_ENDPOINT = 'http://127.0.0.1:59060/ingest'
void fetch(DEBUG_ENDPOINT, {
  method: 'POST',
  keepalive: true,
}).catch(() => {})
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("direct_ingest_fetch", codes)
        self.assertIn("steady_keepalive", codes)
        self.assertIn("silent_transport_error", codes)
        self.assertIn("transport_unused", codes)

    def test_window_fetch_and_expressionless_catch_fail(self) -> None:
        report = self._validate_source(
            """
const DEBUG_ENDPOINT = 'http://127.0.0.1:59060/ingest'
void window.fetch(DEBUG_ENDPOINT).catch(() => undefined)
window.navigator.sendBeacon(DEBUG_ENDPOINT, '{}')
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("direct_ingest_fetch", codes)
        self.assertIn("silent_transport_error", codes)
        self.assertIn("send_beacon", codes)

    def test_variable_batch_ingest_fetch_variants_fail(self) -> None:
        for fetch_expression in (
            "fetch(BATCH_ENDPOINT)",
            "window.fetch(BATCH_ENDPOINT)",
            "globalThis.fetch(BATCH_ENDPOINT)",
            "self.fetch(BATCH_ENDPOINT)",
        ):
            with self.subTest(fetch_expression=fetch_expression):
                report = self._validate_source(
                    f"""
const BATCH_ENDPOINT = 'http://127.0.0.1:59060/ingest/batch'
void {fetch_expression}
"""
                )
                codes = {issue["code"] for issue in report["issues"]}
                self.assertFalse(report["ok"])
                self.assertIn("direct_ingest_fetch", codes)

    def test_aliased_batch_ingest_endpoint_fetch_fails(self) -> None:
        report = self._validate_source(
            """
const INGEST = 'http://127.0.0.1:59060/ingest/batch'
const target = INGEST
void fetch(target)
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("direct_ingest_fetch", codes)

    def test_copied_asset_without_runtime_import_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "browser-debug-transport.mjs").write_text(
                "export function createBrowserDebugTransport() {}",
                encoding="utf-8",
            )
            (root / "probe.ts").write_text(
                "export function emit() {}",
                encoding="utf-8",
            )
            report = validate([root])
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("transport_import_count", codes)
        self.assertIn("transport_instance_count", codes)
        self.assertIn("transport_unused", codes)

    def test_multiple_transport_instances_fail(self) -> None:
        report = self._validate_source(
            SAFE_TRANSPORT
            + "\nconst duplicate = getOrCreateBrowserDebugTransport({ batchEndpoint: ready.batchEndpoint, sessionId: ready.sessionId })\n"
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("transport_instance_count", codes)

    def test_exported_installer_uses_top_level_registry_acquisition(self) -> None:
        report = self._validate_source(
            """
import { getOrCreateBrowserDebugTransport } from './browser-debug-transport.mjs'

const transport = getOrCreateBrowserDebugTransport({
  batchEndpoint: ready.batchEndpoint,
  sessionId: ready.sessionId,
  recordingGeneration: ready.recordingGeneration,
})

export function installDebugProbe(ready) {
  return (event) => void transport.recordSafe(event)
}
"""
        )
        self.assertTrue(report["ok"], msg=report)

    def test_compatibility_factory_import_is_registry_backed(self) -> None:
        report = self._validate_source(
            """
import { createBrowserDebugTransport } from './browser-debug-transport.mjs'

const transport = createBrowserDebugTransport({
  batchEndpoint: ready.batchEndpoint,
  sessionId: ready.sessionId,
  recordingGeneration: ready.recordingGeneration,
})

export function installDebugProbe(ready) {
  return (event) => void transport.recordSafe(event)
}
"""
        )
        self.assertTrue(report["ok"], msg=report)

    def test_local_factory_cannot_claim_registry_singleton(self) -> None:
        report = self._validate_source(
            """
function createBrowserDebugTransport(options) {
  return { recordSafe() {} }
}

export function installDebugProbe(ready) {
  const transport = createBrowserDebugTransport(ready)
  return (event) => void transport.recordSafe(event)
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("local_transport_factory", codes)
        self.assertIn("transport_import_count", codes)

    def test_aliased_factory_import_cannot_evade_registry_gate(self) -> None:
        report = self._validate_source(
            """
import { getOrCreateBrowserDebugTransport as makeTransport } from './browser-debug-transport.mjs'
const transport = makeTransport(ready)
export function emit(event) { void transport.recordSafe(event) }
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("transport_import_count", codes)
        self.assertIn("transport_instance_count", codes)

    def test_occurrence_gate_marker_fails(self) -> None:
        report = self._validate_source(
            SAFE_TRANSPORT
            + "\nlet lastSpinnerProbeKey = ''\n"
            + "\nexport function maybeEmit(key, event) { if (key !== lastSpinnerProbeKey) emit(event) }\n"
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("occurrence_reduction", codes)

    def test_set_membership_early_return_gate_fails(self) -> None:
        report = self._validate_source(
            SAFE_TRANSPORT
            + """
const seen = new Set()
export function maybeEmit(key, event) {
  if (seen.has(key)) return
  seen.add(key)
  void transport.recordSafe(event)
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("occurrence_reduction", codes)

    def test_map_membership_early_return_gate_fails(self) -> None:
        report = self._validate_source(
            SAFE_TRANSPORT
            + """
const emitted = new Map()
export function maybeEmit(key, event) {
  if (emitted.get(key)) {
    return
  }
  emitted.set(key, true)
  void transport.recordSafe(event)
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("occurrence_reduction", codes)

    def test_boolean_early_return_gate_fails(self) -> None:
        report = self._validate_source(
            SAFE_TRANSPORT
            + """
let gate = false
export function maybeEmit(event) {
  if (gate) return
  gate = true
  void transport.recordSafe(event)
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("occurrence_reduction", codes)

    def test_ref_early_return_gate_fails(self) -> None:
        report = self._validate_source(
            SAFE_TRANSPORT
            + """
const sentRef = useRef(false)
export function maybeEmit(event) {
  if (sentRef.current) return
  sentRef.current = true
  void transport.recordSafe(event)
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("occurrence_reduction", codes)

    def test_previous_key_change_gate_fails(self) -> None:
        report = self._validate_source(
            SAFE_TRANSPORT
            + """
let previousKey = ''
export function maybeEmit(key, event) {
  if (previousKey === key) return
  previousKey = key
  void transport.recordSafe(event)
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("occurrence_reduction", codes)

    def test_change_only_conditional_emit_fails(self) -> None:
        report = self._validate_source(
            SAFE_TRANSPORT
            + """
let lastKey = ''
export function maybeEmit(key, event) {
  if (key !== lastKey) {
    lastKey = key
    void transport.recordSafe(event)
  }
}
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("occurrence_reduction", codes)

    def test_checkpoint_and_flow_started_gates_fail(self) -> None:
        gate_sources = (
            """
let checkpointDone = false
export function maybeEmit(event) {
  if (checkpointDone) return
  checkpointDone = true
  void transport.recordSafe(event)
}
""",
            """
const flowStartedKeys = new Set()
export function maybeEmit(key, event) {
  if (flowStartedKeys.has(key)) return
  flowStartedKeys.add(key)
  void transport.recordSafe(event)
}
""",
        )
        for gate_source in gate_sources:
            with self.subTest(gate_source=gate_source):
                report = self._validate_source(SAFE_TRANSPORT + gate_source)
                codes = {issue["code"] for issue in report["issues"]}
                self.assertFalse(report["ok"])
                self.assertIn("occurrence_reduction", codes)

    def test_once_wrapper_gate_fails(self) -> None:
        report = self._validate_source(
            SAFE_TRANSPORT
            + """
export const emitOnce = once((event) => {
  void transport.recordSafe(event)
})
"""
        )
        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("occurrence_reduction", codes)

    def test_throttle_and_debounce_wrappers_fail(self) -> None:
        for wrapper in ("throttle", "debounce", "useThrottleFn", "useDebounceFn"):
            with self.subTest(wrapper=wrapper):
                report = self._validate_source(
                    SAFE_TRANSPORT
                    + f"""
export const reducedEmitter = {wrapper}((event) => {{
  void transport.recordSafe(event)
}})
"""
                )
                codes = {issue["code"] for issue in report["issues"]}
                self.assertFalse(report["ok"])
                self.assertIn("occurrence_reduction", codes)

    def test_sequence_modulo_and_first_n_gates_fail(self) -> None:
        gate_sources = (
            """
let counter = 0
export function maybeEmit(event) {
  counter += 1
  if (counter % 2 !== 0) return
  void transport.recordSafe(event)
}
""",
            """
let occurrenceCount = 0
export function maybeEmit(event) {
  occurrenceCount += 1
  if (occurrenceCount < 10) {
    void transport.recordSafe(event)
  }
}
""",
        )
        for gate_source in gate_sources:
            with self.subTest(gate_source=gate_source):
                report = self._validate_source(SAFE_TRANSPORT + gate_source)
                codes = {issue["code"] for issue in report["issues"]}
                self.assertFalse(report["ok"])
                self.assertIn("occurrence_reduction", codes)

    def test_transport_asset_internal_queue_and_fetch_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "browser-debug-transport.mjs").write_text(
                """
const seenBatchIds = new Set()
export function getOrCreateBrowserDebugTransport(options) {
  if (seenBatchIds.has(options.batchId)) return existing
  return window.fetch(options.batchEndpoint)
}
""",
                encoding="utf-8",
            )
            (root / "probe.ts").write_text(SAFE_TRANSPORT, encoding="utf-8")
            report = validate([root])
        self.assertTrue(report["ok"], msg=report)

    def test_missing_declared_source_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "probe.ts"
            source.write_text(SAFE_TRANSPORT, encoding="utf-8")
            report = validate([source, root / "missing-emitter.ts"])

        codes = {issue["code"] for issue in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertIn("missing_source_path", codes)


if __name__ == "__main__":
    unittest.main()
