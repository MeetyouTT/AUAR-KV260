"""Public loader and source-closure counterexamples without device access."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
import types
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('jpeg_entry_fixture', HERE / 'candidate/entry.py')
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
MANIFEST_RAW = (HERE / 'candidate/candidate-manifest.json').read_bytes()
MANIFEST = json.loads(MANIFEST_RAW)
CAMERA_RAW = (HERE / 'candidate/ui_camera_service.py').read_bytes()


class EntryTests(unittest.TestCase):
    def verification_fixture(self):
        root = (HERE / 'candidate').resolve()
        manifest = copy.deepcopy(MANIFEST)
        files = {name: ('public source fixture ' + name).encode() for name in manifest['inherited_pins']}
        saved = json.loads((HERE.parent / 'progress_followup_20261031/v21_camera_metadata_1793506766766332400.json').read_bytes())['result']
        for name, row in saved['metadata'].items():
            fields = dict(row['fields'])
            if name == entry.OPS + '/meta.json':
                fields['root'] = entry.OPS
            files[name] = json.dumps(fields, sort_keys=True).encode()
        files[entry.PAN_ENTRY] = (HERE.parent / 'jpeg_demand_review_v20/actual_camera_source_9d714/3_native_entry_pan_face_v5.py').read_bytes()
        fixtures = {raw: manifest['inherited_pins'][name] for name, raw in files.items()}
        files[str(root / 'entry.py')] = (root / 'entry.py').read_bytes()
        files[str(root / 'ui_camera_service.py')] = CAMERA_RAW
        files[str(root / 'candidate-manifest.json')] = MANIFEST_RAW

        def fixture_digest(raw):
            return fixtures.get(raw, hashlib.sha256(raw).hexdigest())

        return root, manifest, files, fixture_digest

    def test_exact_camera_and_old_executor_bytes_and_python38_syntax(self):
        self.assertEqual(entry.CAMERA_AFTER, hashlib.sha256(CAMERA_RAW).hexdigest())
        self.assertEqual('1e8aeee2a94b4fce674f2468ce48c77fbb88ef99bd9cb1ab66dd3bf20a0327f6',
                         hashlib.sha256((HERE / 'serial_trial.py').read_bytes()).hexdigest())
        for path in (HERE / 'candidate/entry.py', HERE / 'serial_trial.py'):
            ast.parse(path.read_bytes(), feature_version=(3, 8))

    def test_all_current_readback_and_actual_entry_pins_are_carried(self):
        saved = json.loads((HERE.parent / 'progress_followup_20261031/v21_camera_metadata_1793506766766332400.json').read_bytes())['result']
        self.assertEqual(62, len(MANIFEST['inherited_pins']))
        for name, expected in saved['readback']['source_sha256'].items():
            self.assertEqual(expected, MANIFEST['inherited_pins'][name])
        self.assertEqual(entry.CAMERA_BEFORE, MANIFEST['inherited_pins'][entry.ORIGINAL_CAMERA])
        self.assertEqual(entry.CAMERA_AFTER, MANIFEST['candidate_sources']['ui_camera_service.py'])

    def test_original_meta_app_shadow_and_operator_closure_are_required(self):
        root, manifest, files, fixture_digest = self.verification_fixture()
        with patch.object(entry, 'digest', side_effect=fixture_digest):
            checked = entry.verify(root, hashlib.sha256(MANIFEST_RAW).hexdigest(), reader=files.__getitem__)
            self.assertEqual(manifest, checked)
        for missing in (entry.SOURCE_ROOT + '/board/motion/camera_feed.py',
                        entry.OPS + '/pan-face-edge-v5/motion_stream.py',
                        entry.OPS + '/pan-face-edge-v5/face-source-v17/face_lock.py'):
            changed = copy.deepcopy(manifest)
            changed['inherited_pins'].pop(missing)
            raw = json.dumps(changed).encode()
            files[str(root / 'candidate-manifest.json')] = raw
            with self.subTest(missing=missing), patch.object(entry, 'digest', side_effect=fixture_digest):
                with self.assertRaisesRegex(ValueError, 'closure incomplete'):
                    entry.verify(root, hashlib.sha256(raw).hexdigest(), reader=files.__getitem__)

    def test_policy_manifest_hash_and_camera_hash_cannot_drift(self):
        root, manifest, files, fixture_digest = self.verification_fixture()
        with patch.object(entry, 'digest', side_effect=fixture_digest):
            with self.assertRaisesRegex(ValueError, 'manifest SHA'):
                entry.verify(root, '0' * 64, reader=files.__getitem__)
            changed = copy.deepcopy(manifest)
            changed['policy']['face_period_ms'] = 200
            raw = json.dumps(changed).encode()
            files[str(root / 'candidate-manifest.json')] = raw
            with self.assertRaisesRegex(ValueError, 'exact policy'):
                entry.verify(root, hashlib.sha256(raw).hexdigest(), reader=files.__getitem__)
            files[str(root / 'candidate-manifest.json')] = MANIFEST_RAW
            files[str(root / 'ui_camera_service.py')] = b'public wrong candidate'
            with self.assertRaisesRegex(ValueError, 'source SHA'):
                entry.verify(root, hashlib.sha256(MANIFEST_RAW).hexdigest(), reader=files.__getitem__)

    def dependencies(self):
        board = types.ModuleType('board')
        board.__path__ = []
        vision = types.ModuleType('board.vision')
        vision.__path__ = []
        vision.__file__ = entry.SOURCE_ROOT + '/board/vision/__init__.py'
        board.vision = vision
        interaction = types.ModuleType('board.interaction')
        interaction.__path__ = []
        board.interaction = interaction
        modules = {'board': board, 'board.vision': vision, 'board.interaction': interaction,
                   'fcntl': types.ModuleType('fcntl')}
        values = {
            'board.vision.native_errors': {'PrimaryAdmissionDeferred': type('PrimaryAdmissionDeferred', (Exception,), {})},
            'board.interaction.ui_contract': {'ACTIONS': (), 'PROTOCOL': 1, 'integer': lambda x: x,
                                             'millis': lambda: 0, 'validate_action': lambda x: x},
            'board.vision.local_preview': {'RawFrameStore': object, 'TRANSPORT': 'fixture'},
            'board.vision.camera_device': {'CAMERA_IDENTITY': {}, 'PINNED_CAMERA': '/fixture',
                                          'CameraUnavailable': type('CameraUnavailable', (Exception,), {}),
                                          'resolve_camera_device': lambda: '/fixture'},
        }
        for name, attrs in values.items():
            module = types.ModuleType(name)
            module.__dict__.update(attrs)
            modules[name] = module
        return modules, vision

    def test_real_frozen_module_uses_original_root_and_restores_search_path(self):
        modules, parent = self.dependencies()
        before = list(sys.path)
        with patch.dict(sys.modules, modules):
            sys.modules.pop(entry.MODULE_NAME, None)
            module = entry.install_camera(HERE / 'candidate', reader=lambda _: CAMERA_RAW)
            self.assertIs(module, sys.modules[entry.MODULE_NAME])
            self.assertIs(module, parent.ui_camera_service)
            self.assertEqual(str(HERE / 'candidate/ui_camera_service.py'), module.__file__)
            self.assertEqual(Path(entry.SOURCE_ROOT), module.AURA)
            self.assertEqual(before, sys.path)
            self.assertTrue(hasattr(module, 'PreviewFrame'))
            self.assertTrue(callable(module.main))

    def test_install_failure_removes_only_its_partial_module_and_restores_path(self):
        modules, parent = self.dependencies()
        before = list(sys.path)
        failure = compile("raise RuntimeError('public initialization failure')", '<fixture>', 'exec')
        with patch.dict(sys.modules, modules), patch.object(entry, 'compile', return_value=failure, create=True):
            sys.modules.pop(entry.MODULE_NAME, None)
            with self.assertRaisesRegex(RuntimeError, 'public initialization failure'):
                entry.install_camera(HERE / 'candidate', reader=lambda _: CAMERA_RAW)
            self.assertNotIn(entry.MODULE_NAME, sys.modules)
            self.assertFalse(hasattr(parent, 'ui_camera_service'))
            self.assertEqual(before, sys.path)

    def test_existing_module_or_package_attribute_is_never_replaced(self):
        modules, parent = self.dependencies()
        sentinel = object()
        with patch.dict(sys.modules, dict(modules, **{entry.MODULE_NAME: sentinel})):
            with self.assertRaisesRegex(RuntimeError, 'already loaded'):
                entry.install_camera(HERE / 'candidate', reader=lambda _: CAMERA_RAW)
            self.assertIs(sentinel, sys.modules[entry.MODULE_NAME])
        with patch.dict(sys.modules, modules):
            sys.modules.pop(entry.MODULE_NAME, None)
            parent.ui_camera_service = sentinel
            with self.assertRaisesRegex(RuntimeError, 'already selected'):
                entry.install_camera(HERE / 'candidate', reader=lambda _: CAMERA_RAW)
            self.assertIs(sentinel, parent.ui_camera_service)

    def test_dispatch_calls_original_native_operator_once_after_selection(self):
        calls = []
        run = types.SimpleNamespace()

        def original(name, **kwargs):
            calls.append(('original', name, kwargs))
            if name == entry.BASE_ENTRY:
                return run.run_path(entry.DISPATCH_ENTRY, run_name='__main__')
            return 'finished_original_chain'

        run.run_path = original
        selected = lambda root: calls.append(('install', str(root)))
        result = entry.launch(MANIFEST, HERE / 'candidate', run_module=run, installer=selected)
        self.assertEqual('finished_original_chain', result)
        self.assertEqual(['original', 'install', 'original'], [row[0] for row in calls])
        self.assertIs(original, run.run_path)

    def test_missing_repeated_or_altered_dispatch_is_rejected_and_hook_restored(self):
        for mode in ('missing', 'repeated', 'altered'):
            run = types.SimpleNamespace()

            def original(name, **kwargs):
                if name == entry.BASE_ENTRY:
                    if mode == 'missing':
                        return None
                    run.run_path(entry.DISPATCH_ENTRY, run_name='other' if mode == 'altered' else '__main__')
                    if mode == 'repeated':
                        run.run_path(entry.DISPATCH_ENTRY, run_name='__main__')

            run.run_path = original
            with self.subTest(mode=mode), self.assertRaises(RuntimeError):
                entry.launch(MANIFEST, HERE / 'candidate', run_module=run, installer=lambda _: object())
            self.assertIs(original, run.run_path)


if __name__ == '__main__':
    unittest.main()
