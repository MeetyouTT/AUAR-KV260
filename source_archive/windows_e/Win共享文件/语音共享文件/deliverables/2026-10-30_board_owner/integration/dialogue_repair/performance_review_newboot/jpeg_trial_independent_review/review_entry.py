"""Public-only loader and inherited-chain audit. No actual entry is started."""
import ast
import builtins
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parents[1]
CANDIDATE = REPAIR / 'jpeg_demand_camera_trial_v21'
ENTRY_SHA = '4f708aca4b3dd876664b302f8f978ef96e5226b1000cdbc3cd045e3567d2675f'
MANIFEST_SHA = '6a7c6a56a5ceda2259ddf0ee7e00fbc932d1a34d56a396202e2f4cd045fce6e1'
EXECUTOR_SHA = '1e8aeee2a94b4fce674f2468ce48c77fbb88ef99bd9cb1ab66dd3bf20a0327f6'
SNAPSHOT = REPAIR / 'progress_followup_20261031/v21_camera_metadata_1793506766766332400.json'
SNAPSHOT_SHA = '3ccef2829ef9fbbece73c7408855ab2a461c9eaa78692cd19a23676c0ef13964'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


assert digest(CANDIDATE / 'candidate/entry.py') == ENTRY_SHA
assert digest(CANDIDATE / 'candidate/candidate-manifest.json') == MANIFEST_SHA
assert digest(CANDIDATE / 'serial_trial.py') == EXECUTOR_SHA
assert digest(SNAPSHOT) == SNAPSHOT_SHA
entry = load('independent_trial_entry', CANDIDATE / 'candidate/entry.py')
manifest = json.loads((CANDIDATE / 'candidate/candidate-manifest.json').read_bytes())
runner_path = REPAIR / 'jpeg_demand_actual_camera_candidate_v20/run_local_tests.py'
assert digest(runner_path) == 'f65a6db648e681bb2c15e57a5cfeb6bc611da8d2c76791a757fecf881a78cbf5'
load('independent_actual_pinned_imports', runner_path).prepare_imports()
import board.vision as vision


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.original_path = list(sys.path)
        self.assertNotIn(entry.MODULE_NAME, sys.modules)
        self.assertFalse(hasattr(vision, 'ui_camera_service'))
        self.addCleanup(self.cleanup)

    def cleanup(self):
        sys.modules.pop(entry.MODULE_NAME, None)
        if hasattr(vision, 'ui_camera_service'):
            del vision.ui_camera_service
        self.assertEqual(sys.path, self.original_path)

    def install(self):
        expected = str(Path(entry.SOURCE_ROOT) / 'board/vision/__init__.py')
        with patch.object(vision, '__file__', expected):
            return entry.install_camera(CANDIDATE / 'candidate')

    def test_exact_candidate_registers_canonical_module_and_original_aura(self):
        module = self.install()
        path = str(CANDIDATE / 'candidate/ui_camera_service.py')
        self.assertIs(module, sys.modules[entry.MODULE_NAME])
        self.assertIs(module, vision.ui_camera_service)
        self.assertEqual(module.__file__, path)
        self.assertEqual(module.run.__code__.co_filename, path)
        self.assertEqual(module.AURA, Path(entry.SOURCE_ROOT))
        self.assertEqual(sys.path, self.original_path)
        self.assertEqual(module.PreviewFrame.__module__, entry.MODULE_NAME)
        # Exact loaded code is exercised without a device or encoder dependency.
        state = module.CameraState('public-loader-boot', clock=lambda: 1000)
        state.captured(1000)
        state.publish_preview(1, 1000, pixels=bytes(640 * 480 * 3))
        with patch.object(module, 'encode_preview', return_value=b'public-jpeg') as encode:
            self.assertEqual(state.preview(state.camera_epoch, 1), b'public-jpeg')
            self.assertEqual(state.preview(state.camera_epoch, 1), b'public-jpeg')
            encode.assert_called_once()

    def test_already_loaded_module_is_preserved_and_refused(self):
        foreign = object()
        sys.modules[entry.MODULE_NAME] = foreign
        with self.assertRaisesRegex(RuntimeError, 'already loaded'):
            self.install()
        self.assertIs(sys.modules[entry.MODULE_NAME], foreign)

    def test_foreign_parent_attribute_is_preserved_and_refused(self):
        foreign = object()
        vision.ui_camera_service = foreign
        with self.assertRaisesRegex(RuntimeError, 'attribute already'):
            self.install()
        self.assertIs(vision.ui_camera_service, foreign)
        self.assertNotIn(entry.MODULE_NAME, sys.modules)

    def test_dependency_root_mismatch_is_refused_before_candidate_execution(self):
        with self.assertRaisesRegex(RuntimeError, 'package path changed'):
            entry.install_camera(CANDIDATE / 'candidate')
        self.assertNotIn(entry.MODULE_NAME, sys.modules)

    def test_source_change_is_refused_without_registration(self):
        with self.assertRaisesRegex(ValueError, 'source changed'):
            entry.install_camera(CANDIDATE / 'candidate', reader=lambda name: b'public tampered source')
        self.assertNotIn(entry.MODULE_NAME, sys.modules)

    def test_execution_failure_cleans_owned_registration_and_search_path(self):
        def execute_then_fail(code, namespace):
            builtins.exec(code, namespace)
            raise RuntimeError('public synthetic execution failure')
        with patch.object(entry, 'exec', execute_then_fail, create=True):
            with self.assertRaisesRegex(RuntimeError, 'synthetic execution'):
                self.install()
        self.assertNotIn(entry.MODULE_NAME, sys.modules)
        self.assertFalse(hasattr(vision, 'ui_camera_service'))

    def test_one_selection_delegates_original_operator_and_restores_dispatch(self):
        calls = []
        selected = []
        run_module = types.SimpleNamespace()
        def original(name, **options):
            calls.append((name, options))
            if name == entry.BASE_ENTRY:
                return run_module.run_path(entry.DISPATCH_ENTRY, run_name='__main__')
            self.assertEqual(len(selected), 1)
            return 'public-original-operator-result'
        run_module.run_path = original
        def install(root):
            selected.append(str(root))
            return object()
        result = entry.launch(manifest, CANDIDATE / 'candidate', run_module=run_module, installer=install)
        self.assertEqual(result, 'public-original-operator-result')
        self.assertEqual([row[0] for row in calls], [entry.BASE_ENTRY, entry.DISPATCH_ENTRY])
        self.assertIs(run_module.run_path, original)

    def test_repeated_altered_or_absent_boundary_refuses_and_restores(self):
        for mode in ('repeat', 'alter', 'absent', 'error'):
            with self.subTest(mode=mode):
                selected = []
                run_module = types.SimpleNamespace()
                def original(name, **options):
                    if name != entry.BASE_ENTRY:
                        if mode == 'error':
                            raise RuntimeError('public original entry failure')
                        return None
                    if mode == 'absent':
                        return None
                    run_module.run_path(entry.DISPATCH_ENTRY,
                        run_name='other' if mode == 'alter' else '__main__')
                    if mode == 'repeat':
                        run_module.run_path(entry.DISPATCH_ENTRY, run_name='__main__')
                run_module.run_path = original
                with self.assertRaises(RuntimeError):
                    entry.launch(manifest, CANDIDATE / 'candidate', run_module=run_module,
                        installer=lambda root: selected.append(root))
                self.assertLessEqual(len(selected), 1)
                self.assertIs(run_module.run_path, original)


class InheritedTests(unittest.TestCase):
    def test_62_pins_preserve_fresh_21_and_actual_16_source_readbacks(self):
        inherited = manifest['inherited_pins']
        self.assertEqual(len(inherited), 62)
        snapshot = json.loads(SNAPSHOT.read_bytes())['result']
        self.assertEqual(snapshot['owners'], snapshot['final_owners'])
        self.assertEqual(len(snapshot['readback']['source_sha256']), 21)
        for name, pin in snapshot['readback']['source_sha256'].items():
            self.assertEqual(inherited[name], pin)
        actual = REPAIR / 'jpeg_demand_review_v20/actual_camera_source_9d714'
        count = 0
        for filename in ('READBACK.json', 'ADDITIONAL_READBACK.json', 'DEPENDENCY_READBACK.json'):
            for row in json.loads((actual / filename).read_bytes())['files']:
                self.assertEqual(digest(Path(row['local_path'])), row['sha256'])
                self.assertEqual(inherited[row['path']], row['sha256'])
                count += 1
        self.assertEqual(count, 16)
        for name, row in snapshot['metadata'].items():
            self.assertEqual(inherited[name], row['sha256'])
            for group in ('pins', 'files'):
                for child, pin in row['fields'].get(group, {}).items():
                    self.assertEqual(inherited[child], pin)

    def test_original_native_app_shadow_and_operator_dispatch_are_inherited(self):
        actual = REPAIR / 'jpeg_demand_review_v20/actual_camera_source_9d714'
        tree = ast.parse((actual / '3_native_entry_pan_face_v5.py').read_bytes())
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                group = node.targets[0].id
                if group in ('APP_PINS', 'SHADOW_PINS'):
                    prefix = entry.SOURCE_ROOT if group == 'APP_PINS' else entry.OPS + '/pan-face-edge-v5'
                    for relative, pin in ast.literal_eval(node.value).items():
                        self.assertEqual(manifest['inherited_pins'][prefix + '/' + relative], pin)
        self.assertEqual(manifest['inherited_pins'][entry.ORIGINAL_CAMERA], entry.CAMERA_BEFORE)
        self.assertEqual(manifest['candidate_sources']['ui_camera_service.py'], entry.CAMERA_AFTER)
        self.assertEqual(digest(CANDIDATE / 'candidate/ui_camera_service.py'), entry.CAMERA_AFTER)
        self.assertEqual((CANDIDATE / 'serial_trial.py').read_bytes(),
                         (REPAIR.parent / 'resume_camera_budget/serial_trial.py').read_bytes())


log = io.StringIO()
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(kind)
                           for kind in (LoaderTests, InheritedTests))
result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
report = {
    'status': 'PASS_LOADER_AND_INHERITED_CHAIN_LOCAL_ONLY' if result.wasSuccessful() else 'FAIL',
    'tests_run': result.testsRun,
    'failures': len(result.failures),
    'errors': len(result.errors),
    'entry_sha256': ENTRY_SHA,
    'manifest_sha256': MANIFEST_SHA,
    'executor_sha256': EXECUTOR_SHA,
    'snapshot_sha256': SNAPSHOT_SHA,
    'test_sha256': digest(Path(__file__)),
    'actual_62_file_verify_pending_root': True,
    'protected_entry_or_native_owner_started': False,
    'device_accessed': False,
    'candidate_modified': False,
    'readback_adapter_and_measurement_review_pending': True,
    'failed_tests': [{'id': test.id(), 'traceback': error} for test, error in result.failures + result.errors],
}
assert digest(CANDIDATE / 'candidate/entry.py') == ENTRY_SHA
assert digest(CANDIDATE / 'candidate/candidate-manifest.json') == MANIFEST_SHA
(HERE / 'LOADER_REVIEW.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
(HERE / 'LOADER_PUBLIC_TESTS.log').write_text(log.getvalue(), encoding='utf-8')
print(json.dumps({key: report[key] for key in ('status', 'tests_run', 'failures', 'errors')}))
if not result.wasSuccessful():
    print(log.getvalue()[-7000:])
raise SystemExit(0 if result.wasSuccessful() else 1)
