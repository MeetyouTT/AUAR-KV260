"""Preview-only behavior, expiry and paired worker regression; no GTK/device IO."""
import ast
from collections import deque
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
BASE = HERE / 'baseline'
CANDIDATE = HERE / 'preview_candidate'


def package(name, paths):
    module = types.ModuleType(name)
    module.__path__ = [str(p) for p in paths]
    sys.modules[name] = module


package('board', [BASE / 'board'])
package('board.interaction', [CANDIDATE / 'board/interaction', BASE / 'board/interaction'])
package('board.vision', [BASE / 'board/vision'])
package('tools', [CANDIDATE / 'tools', BASE / 'tools'])

from board.interaction.ui_contract import ACTIONS, PROTOCOL, SnapshotGate
from board.interaction.ui_services import UiServiceClient
from tools.board_camera_preview import CameraPreviewWorker
import tools.board_camera_preview as preview_module


def fixture(now=10000, *, sequence=1, epoch='public-service', frame_id=1):
    return dict(protocol_version=PROTOCOL, board_boot_id='public-boot', service_epoch=epoch,
        sequence=sequence, observed_mono_ms=now, ttl_ms=2500, source_kind='actual',
        context=dict(session_id='public-session', request_id='public-request', generation=1),
        capabilities={name: True for name in ACTIONS},
        modules=dict(camera=dict(state='READY', detail='public camera', preview_transport='aura-local-bgr-1'),
                     interaction=dict(state='IDLE', transcript='public question', reply='public answer'),
                     identity=dict(state='UNKNOWN', db_version=0, people=[]),
                     vision=dict(state='READY', people_count=1)),
        preview=dict(camera_epoch='a' * 32, frame_id=frame_id, captured_mono_ms=now))


def client():
    value = UiServiceClient.__new__(UiServiceClient)
    value.test_clock = types.SimpleNamespace(now=10000)
    value.clock = lambda: value.test_clock.now
    value.condition = threading.Condition()
    value.gate = SnapshotGate('public-boot', value.clock)
    value.gate.ingest(fixture())
    value.link = 'READY'
    value.connection = dict(enabled=True, host='127.0.0.1', port=8790)
    value.local_raw = True
    value.preview = b'public-jpeg-bytes'
    value.preview_key = copy.deepcopy(value.gate.value['preview'])
    value.error = value.preview_error = value.identity_face_error = ''
    value.identity_preview_enabled = False
    value.identity_face = value.identity_face_key = None
    value.waiting, value.results = deque(), deque(maxlen=16)
    value.inflight = None
    value.ui_epoch = 'public-ui'
    value.ui_generation = value.config_generation = 0
    return value


def normalized(value):
    if value['snapshot'] is None:
        return dict(snapshot=None, preview=None, raw_preview=False)
    snapshot = value['snapshot']
    camera = snapshot['modules'].get('camera', {})
    return dict(snapshot=dict(board_boot_id=snapshot['board_boot_id'],
        service_epoch=snapshot['service_epoch'], source_kind=snapshot['source_kind'],
        modules=dict(camera={k: camera[k] for k in ('state', 'preview_transport') if k in camera}),
        preview=copy.deepcopy(snapshot.get('preview'))),
        preview=value['preview'], raw_preview=value['raw_preview'])


class ProjectionTests(unittest.TestCase):
    def test_display_projection_matches_original_fresh_read(self):
        value = client()
        self.assertEqual(value.read_preview(), normalized(value.read()))

    def test_no_dialogue_identity_command_results_or_full_gate_copy(self):
        value = client()
        value.results.append(dict(detail='public intent result'))
        with patch.object(value.gate, 'read', side_effect=AssertionError('full copy forbidden')):
            projected = value.read_preview()
        payload = json.dumps(projected, default=lambda raw: '<public bytes>')
        for token in ('public question', 'public answer', 'identity', 'capabilities', 'public intent result'):
            self.assertNotIn(token, payload)
        self.assertEqual(set(projected), {'snapshot', 'preview', 'raw_preview'})

    def test_mutation_does_not_change_gate_or_reuse_a_previous_projection(self):
        value = client()
        first = value.read_preview()
        first['snapshot']['modules']['camera']['state'] = 'ERROR'
        first['snapshot']['preview']['frame_id'] = 999
        self.assertEqual(value.read_preview(), normalized(value.read()))

    def test_source_ttl_boundary_and_repeated_read_do_not_extend_validity(self):
        value = client()
        for stamp in (10000, 11000, 12499):
            value.test_clock.now = stamp
            self.assertIsNotNone(value.read_preview()['snapshot'])
        value.test_clock.now = 12500
        self.assertEqual(value.read_preview(), normalized(value.read()))
        self.assertIsNone(value.read_preview()['snapshot'])

    def test_jpeg_source_age_and_exact_key_unchanged(self):
        value = client()
        for stamp in (11500, 11501):
            value.test_clock.now = stamp
            self.assertEqual(value.read_preview(), normalized(value.read()))
        value.test_clock.now = 10000
        value.preview_key['frame_id'] = 0
        self.assertIsNone(value.read_preview()['preview'])

    def test_link_transitions_and_empty_gate_hide_frames(self):
        for link in ('CONNECTING', 'DISABLED', 'OFFLINE', 'STALE'):
            value = client()
            value.link = link
            self.assertIsNone(value.read_preview()['snapshot'])
        value = client()
        value.gate.value = None
        self.assertIsNone(value.read_preview()['snapshot'])

    def test_raw_opt_in_actual_source_and_loopback_rules_unchanged(self):
        for local, source, host, expected in (
            (True, 'actual', '127.0.0.1', True),
            (False, 'actual', '127.0.0.1', False),
            (True, 'fixture', '127.0.0.1', False),
            (True, 'actual', '192.0.2.1', False),
        ):
            value = client()
            value.local_raw = local
            value.connection['host'] = host
            value.gate.value['source_kind'] = source
            self.assertIs(value.read_preview()['raw_preview'], expected)
            self.assertEqual(value.read_preview(), normalized(value.read()))

    def test_cancel_masks_full_read_but_does_not_expose_interaction_in_preview(self):
        value = client()
        value.gate.cancel()
        self.assertTrue(value.read()['snapshot']['interaction_suppressed'])
        self.assertEqual(value.read_preview(), normalized(value.read()))
        self.assertNotIn('interaction', value.read_preview()['snapshot']['modules'])

    def test_service_camera_replacement_is_immediate_and_old_jpeg_not_reused(self):
        value = client()
        newer = fixture(sequence=2, epoch='public-service-2', frame_id=2)
        newer['preview']['camera_epoch'] = 'b' * 32
        value.gate.ingest(newer)
        projected = value.read_preview()
        self.assertEqual(projected['snapshot']['service_epoch'], 'public-service-2')
        self.assertEqual(projected['snapshot']['preview']['camera_epoch'], 'b' * 32)
        self.assertIsNone(projected['preview'])

    def test_empty_camera_or_missing_preview_still_matches_original(self):
        value = client()
        newer = fixture(sequence=2)
        newer['modules'].pop('camera')
        newer.pop('preview')
        value.gate.ingest(newer)
        value.preview = value.preview_key = None
        self.assertEqual(value.read_preview(), normalized(value.read()))

    def test_all_existing_client_methods_are_ast_identical(self):
        baseline = ast.parse((BASE / 'board/interaction/ui_services.py').read_text(encoding='utf-8'))
        candidate = ast.parse((CANDIDATE / 'board/interaction/ui_services.py').read_text(encoding='utf-8'))
        cls = next(n for n in candidate.body if isinstance(n, ast.ClassDef) and n.name == 'UiServiceClient')
        cls.body = [n for n in cls.body if not isinstance(n, ast.FunctionDef) or n.name != 'read_preview']
        self.assertEqual(ast.dump(baseline), ast.dump(candidate))


class OneStep:
    def __init__(self): self.calls = 0
    def wait(self, _):
        self.calls += 1
        return self.calls > 1


class WorkTests(unittest.TestCase):
    def run_work(self, services, *, reader_type=None):
        worker = CameraPreviewWorker.__new__(CameraPreviewWorker)
        worker.stop = OneStep()
        worker.lock = threading.RLock()
        worker.outputs = {'public': object()}
        worker.services = services
        worker.reader = worker.reader_owner = worker.last_key = None
        worker.raw_directory = '/public-not-opened'
        worker.clear_count = 0
        worker.error = ''
        worker.clear = lambda: setattr(worker, 'clear_count', worker.clear_count + 1)
        worker.is_current = lambda *_: False
        with patch.object(preview_module, 'RawFrameReader', reader_type or object):
            worker.work()
        return worker

    def test_worker_uses_new_projection_and_keeps_raw_reader_owner_and_deadline(self):
        value = client()
        owners = []
        class Reader:
            def __init__(self, owner, directory): owners.append(dict(owner))
            def read(self, now_ms): return None
        value.read = lambda: (_ for _ in ()).throw(AssertionError('full read called'))
        worker = self.run_work(value, reader_type=Reader)
        self.assertEqual(worker.error, '')
        self.assertEqual(owners, [dict(board_boot_id='public-boot', service_epoch='public-service', camera_epoch='a'*32)])

    def test_worker_compatibility_fallback_without_new_method(self):
        services = types.SimpleNamespace(read=lambda: dict(snapshot=None, preview=None, raw_preview=False))
        worker = self.run_work(services)
        self.assertEqual(worker.clear_count, 1)
        self.assertEqual(worker.error, '')

    def test_expired_source_clears_without_constructing_a_reader(self):
        value = client()
        value.test_clock.now = 12500
        class ForbiddenReader:
            def __init__(self, *_): raise AssertionError('stale frame read')
        worker = self.run_work(value, reader_type=ForbiddenReader)
        self.assertEqual(worker.clear_count, 1)
        self.assertIsNone(worker.reader_owner)
        self.assertEqual(worker.error, '')


def main():
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    spec = importlib.util.spec_from_file_location('legacy_ui_service_tests', BASE / 'tests/framework/test_board_ui_services.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if os.name != 'posix':
        name = 'test_connections_persist_without_changing_audio_preferences'
        original = getattr(module.StoreTests, name)
        setattr(module.StoreTests, name, unittest.skip('POSIX 0600 permissions require the ARM/Linux run')(original))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    proof = dict(schema='aura-preview-projection-tests-1', tests=result.testsRun,
                 failures=len(result.failures), errors=len(result.errors),
                 passed=result.wasSuccessful(), skipped=len(result.skipped),
                 host_os=os.name, posix_permission_test_requires_arm=os.name != 'posix',
                 device_or_network_or_model=False,
                 files={rel: hashlib.sha256((CANDIDATE / rel).read_bytes()).hexdigest()
                        for rel in ('board/interaction/ui_services.py', 'tools/board_camera_preview.py')})
    target = HERE / 'preview_test_result.json'
    if target.exists():
        old = target.read_bytes()
        archive = HERE / ('preview_test_previous_' + hashlib.sha256(old).hexdigest()[:16] + '.json')
        if not archive.exists():
            with archive.open('xb') as handle:
                handle.write(old)
    target.write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(proof))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
