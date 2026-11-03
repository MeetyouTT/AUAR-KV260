"""Independent public-only review of the frozen actual-camera JPEG candidate.

No camera, model, microphone, display, service or private database is opened.
Only synthetic in-memory HTTP handler calls are used. OpenCV is a test fixture.
"""
import ast
import copy
import gc
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import threading
import time
import types
import unittest
import weakref
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parents[1]
CANDIDATE = REPAIR / 'jpeg_demand_actual_camera_candidate_v20'
ACTUAL = REPAIR / 'jpeg_demand_review_v20/actual_camera_source_9d714'
BEFORE_SHA = '9d714b9bd00ea1da12088fa1e22100d7bdb689d0cac10332c3933b31e4f4d2df'
AFTER_SHA = '44b02084cb5e80b12349892183b08e02563c4447e75c5e05276d52786b8a55c4'
PINS = {
    'SOURCE_MANIFEST.json': 'b598afff1976c898bdb9839e0cbecb0eb65aaf0ffe28793432724c233da99a13',
    'HANDOFF.json': 'c8e962ffa199be28f73638505a17261e11666e4c05d4018113aa67a1ce212490',
    'CALL_CHAIN_REVIEW.json': '609ef2873995812b93d82913f51407e4f63a396333f7dc708475eaca5128930c',
    'run_local_tests.py': 'f65a6db648e681bb2c15e57a5cfeb6bc611da8d2c76791a757fecf881a78cbf5',
    'test_jpeg_demand.py': 'be81bc629ce15de1de5c068fc5a138fdc963163496b3b7e166023420fb64225f',
    'before/board/vision/ui_camera_service.py': BEFORE_SHA,
    'after/board/vision/ui_camera_service.py': AFTER_SHA,
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


for relative, expected in PINS.items():
    assert sha(CANDIDATE / relative) == expected, relative
runner = load('independent_pinned_imports', CANDIDATE / 'run_local_tests.py')
runner.prepare_imports()
from board.vision import ui_camera_service as camera
from board.interaction.ui_contract import validate_snapshot
from board.vision.local_preview import TRANSPORT

before = load('independent_camera_before', CANDIDATE / 'before/board/vision/ui_camera_service.py')
author_tests = load('independent_author_tests', CANDIDATE / 'test_jpeg_demand.py')
PIXELS = 640 * 480 * 3
JPEG = b'\xff\xd8' + b'independent-public-jpeg-fixture' * 4 + b'\xff\xd9'


class CountingLock:
    """Observe entry into the real lock without retaining image payloads."""
    def __init__(self):
        self.lock = threading.Lock()
        self.condition = threading.Condition()
        self.arrived = 0
        self.timeouts = []

    def acquire(self, *, timeout):
        with self.condition:
            self.arrived += 1
            self.timeouts.append(timeout)
            self.condition.notify_all()
        return self.lock.acquire(timeout=timeout)

    def release(self):
        self.lock.release()

    def wait_for(self, count):
        with self.condition:
            return self.condition.wait_for(lambda: self.arrived >= count, timeout=2)


class IndependentTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.state = camera.CameraState('public-boot', 'public-service', clock=lambda: self.now)
        self.state.raw_preview = True
        self.threads = []
        self.release = threading.Event()
        self.addCleanup(self.join_threads)

    def join_threads(self):
        self.release.set()
        for thread in self.threads:
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive(), 'public test left a running thread')

    def start(self, function):
        thread = threading.Thread(target=function, name='public-jpeg-review')
        self.threads.append(thread)
        thread.start()
        return thread

    def publish(self, fid, value=30):
        self.state.captured(self.now)
        self.state.publish_preview(fid, self.now, pixels=bytes([value]) * PIXELS)

    def get(self, fid, epoch=None):
        return self.state.preview(epoch or self.state.camera_epoch, fid)

    @staticmethod
    def http(module, state, fid):
        kind = module.handler_for(state)
        handler = kind.__new__(kind)
        handler.path = f'/v1/ui/preview.jpg?camera_epoch={state.camera_epoch}&frame_id={fid}'
        handler.wfile = io.BytesIO()
        reply = {'headers': {}}
        handler.send_response = lambda code: reply.update(status=code)
        handler.send_header = lambda key, value: reply['headers'].update({key: value})
        handler.end_headers = lambda: None
        handler.do_GET()
        reply['body'] = handler.wfile.getvalue()
        return reply

    def test_32_waiters_and_64_retirements_retain_only_eight_plus_active(self):
        lock = CountingLock()
        self.state.preview_encoding_lock = lock
        started = threading.Event()
        results = []
        references = []
        calls = []

        def encode(pixels):
            calls.append(hashlib.sha256(pixels).hexdigest())
            started.set()
            if not self.release.wait(3):
                raise AssertionError('synthetic encoder release missing')
            return JPEG

        self.publish(1)
        references.append(weakref.ref(self.state.frames[1]))
        with patch.object(camera, 'encode_preview', encode):
            self.start(lambda: results.append(self.get(1)))
            self.assertTrue(started.wait(2))
            for fid in range(2, 34):
                self.publish(fid, fid)
                references.append(weakref.ref(self.state.frames[fid]))
                self.start(lambda requested=fid: results.append(self.get(requested)))
                self.assertTrue(lock.wait_for(fid))
            for fid in range(34, 66):
                self.publish(fid, fid)
                references.append(weakref.ref(self.state.frames[fid]))
            gc.collect()
            live_ids = [index + 1 for index, reference in enumerate(references) if reference() is not None]
            self.assertEqual(live_ids, [1] + list(range(58, 66)))
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(self.state.frames), 8)
            self.assertEqual(sum(len(frame.pixels) for frame in self.state.frames.values()), 8 * PIXELS)
            self.assertEqual(validate_snapshot(self.state.snapshot(), self.state.boot, self.now)['preview']['frame_id'], 65)
            self.release.set()
            self.join_threads()
            self.assertEqual(results, [None] * 33)
            self.assertEqual(len(calls), 1)
        gc.collect()
        self.assertIsNone(references[0]())
        self.assertEqual(sum(reference() is not None for reference in references), 8)

    def test_24_same_frame_callers_share_exact_success_and_release_bgr(self):
        self.publish(1)
        lock = CountingLock()
        self.state.preview_encoding_lock = lock
        started = threading.Event()
        results = []
        calls = []

        def encode(pixels):
            calls.append(hashlib.sha256(pixels).hexdigest())
            started.set()
            self.release.wait(3)
            return JPEG

        with patch.object(camera, 'encode_preview', encode):
            for _ in range(24):
                self.start(lambda: results.append(self.get(1)))
            self.assertTrue(started.wait(2))
            self.assertTrue(lock.wait_for(24))
            self.release.set()
            self.join_threads()
        self.assertEqual(len(calls), 1)
        self.assertEqual(results, [JPEG] * 24)
        self.assertIsNone(self.state.frames[1].pixels)
        self.assertEqual({hashlib.sha256(value).hexdigest() for value in results}, {hashlib.sha256(JPEG).hexdigest()})

    def test_queued_replaced_frame_cannot_encode_or_return_replacement(self):
        self.publish(1)
        lock = CountingLock()
        lock.lock.acquire()
        self.state.preview_encoding_lock = lock
        result = []
        with patch.object(camera, 'encode_preview', return_value=JPEG) as encode:
            self.start(lambda: result.append(self.get(1)))
            self.assertTrue(lock.wait_for(1))
            self.publish(1, 80)
            lock.release()
            self.join_threads()
            self.assertEqual(result, [None])
            encode.assert_not_called()
            self.assertEqual(self.get(1), JPEG)
            encode.assert_called_once()

    def test_active_completion_revalidates_epoch_ttl_error_and_retirement(self):
        for invalidation in ('epoch', 'ttl', 'error', 'retired', 'replacement'):
            with self.subTest(invalidation=invalidation):
                self.now = 1000
                self.state = camera.CameraState('public-boot', clock=lambda: self.now)
                self.publish(1)
                old_epoch = self.state.camera_epoch

                def encode(_pixels):
                    if invalidation == 'epoch':
                        self.state.camera_epoch = 'public-next-epoch'
                    elif invalidation == 'ttl':
                        self.now = 2000
                    elif invalidation == 'error':
                        self.state.camera_error = 'public capture error'
                    elif invalidation == 'retired':
                        for fid in range(2, 10):
                            self.publish(fid)
                    else:
                        self.publish(1, 80)
                    return JPEG

                with patch.object(camera, 'encode_preview', encode):
                    self.assertIsNone(self.get(1, old_epoch))
                self.assertFalse(self.state.preview_encoding_lock.locked())
                self.assertTrue(all(frame.jpeg is None for frame in self.state.frames.values()))

    def test_shared_failure_is_cached_until_next_publication_and_unlocks(self):
        self.publish(1)
        with patch.object(camera, 'encode_preview', side_effect=ValueError('public encode failure')) as encode:
            self.assertIsNone(self.get(1))
            self.assertIsNone(self.get(1))
            encode.assert_called_once()
            self.assertEqual(self.state.preview_error, 'public encode failure')
        self.publish(2)
        with patch.object(camera, 'encode_preview', return_value=JPEG):
            self.assertEqual(self.get(2), JPEG)
        self.assertEqual(self.state.preview_error, '')
        self.assertFalse(self.state.preview_encoding_lock.locked())

    def test_old_failure_never_sets_error_on_new_frame(self):
        self.publish(1)

        def fail(_pixels):
            self.publish(2)
            raise ValueError('public old-frame failure')

        with patch.object(camera, 'encode_preview', fail):
            self.assertIsNone(self.get(1))
        self.assertEqual(self.state.preview_error, '')
        self.assertTrue(self.state.frames[1].failed)
        self.assertFalse(self.state.frames[2].failed)

    def test_http_hash_headers_and_metadata_match_old_contract(self):
        old = before.CameraState(self.state.boot, self.state.epoch, clock=lambda: self.now)
        old.camera_epoch = self.state.camera_epoch
        old.captured(self.now)
        old.publish_preview(1, self.now, JPEG)
        self.publish(1)
        snapshot = validate_snapshot(self.state.snapshot(), self.state.boot, self.now)
        self.assertEqual(snapshot['preview'], old.snapshot()['preview'])
        self.assertEqual(snapshot['modules']['camera']['preview_transport'], TRANSPORT)
        self.assertEqual(set(snapshot['preview']), {'camera_epoch', 'frame_id', 'captured_mono_ms'})
        with patch.object(camera, 'encode_preview', return_value=JPEG) as encode:
            new = self.http(camera, self.state, 1)
            self.assertEqual(new, self.http(before, old, 1))
            self.assertEqual(new, self.http(camera, self.state, 1))
            encode.assert_called_once()
        self.assertEqual(new['headers']['Content-Length'], str(len(JPEG)))
        self.assertEqual(new['headers']['Cache-Control'], 'no-store')
        self.assertEqual(new['headers']['Content-Type'], 'image/jpeg')
        self.now += 1000
        self.assertEqual(self.http(camera, self.state, 1)['status'], 404)
        self.assertNotIn('preview', self.state.snapshot())

    def test_lock_budget_is_original_source_lifetime_and_no_expiry_renewal(self):
        self.publish(1)
        self.now = 1999
        lock = CountingLock()
        lock.lock.acquire()
        self.state.preview_encoding_lock = lock
        try:
            with patch.object(camera, 'encode_preview') as encode:
                self.assertIsNone(self.get(1))
                encode.assert_not_called()
            self.assertEqual(lock.timeouts, [0.001])
        finally:
            lock.release()
        self.now = 2000
        self.assertIsNone(self.get(1))


class SourceTests(unittest.TestCase):
    def test_all_16_readback_pins_match_same_camera_owner(self):
        rows = []
        for name in ('READBACK.json', 'ADDITIONAL_READBACK.json', 'DEPENDENCY_READBACK.json'):
            record = json.loads((ACTUAL / name).read_text('utf-8'))
            self.assertEqual(record['boot_id'], 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc')
            self.assertEqual(record['camera_pid'], 1335)
            for row in record['files']:
                self.assertEqual(sha(Path(row['local_path'])), row['sha256'])
                self.assertEqual(Path(row['local_path']).stat().st_size, row['bytes'])
                rows.append(row)
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({row['path'] for row in rows}), 16)
        self.assertEqual(rows[0]['sha256'], BEFORE_SHA)

    def test_native_dispatch_redirects_exact_camera_entry_to_real_wrapper(self):
        tree = ast.parse((ACTUAL / '3_native_entry_pan_face_v5.py').read_text('utf-8'))
        hook = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'hook_camera_run')
        namespace = {'Path': Path, 'sys': types.SimpleNamespace(argv=['public'])}
        exec(compile(ast.Module(body=[hook], type_ignores=[]), '<public-dispatch>', 'exec'), namespace)
        calls = []
        runpy = types.SimpleNamespace(run_path=lambda path, **kwargs: calls.append((path, kwargs)))
        source = ACTUAL / '0_ui_camera_service.py'
        wrapper = ACTUAL / '5_camera_wrapper.py'
        namespace['hook_camera_run'](runpy, source, wrapper)
        runpy.run_path(str(source), run_name='__main__')
        runpy.run_path(str(source), run_name='not-main')
        self.assertEqual(calls[0][0], str(wrapper.resolve()))
        self.assertEqual(calls[1][0], str(source))
        assignments = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
                       if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                       and node.targets[0].id == 'APP_PINS'}
        self.assertEqual(assignments['APP_PINS']['board/vision/ui_camera_service.py'], BEFORE_SHA)

    def test_unrelated_methods_handlers_and_thread_creation_are_unchanged(self):
        old = ast.parse((CANDIDATE / 'before/board/vision/ui_camera_service.py').read_text('utf-8'))
        new = ast.parse((CANDIDATE / 'after/board/vision/ui_camera_service.py').read_text('utf-8'))
        old_top = {node.name: node for node in old.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        new_top = {node.name: node for node in new.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        self.assertEqual(set(new_top) - set(old_top), {'PreviewFrame', 'encode_preview'})
        for name in set(old_top) - {'CameraState', 'run'}:
            self.assertEqual(ast.dump(old_top[name]), ast.dump(new_top[name]), name)
        old_methods = {node.name: node for node in old_top['CameraState'].body if isinstance(node, ast.FunctionDef)}
        new_methods = {node.name: node for node in new_top['CameraState'].body if isinstance(node, ast.FunctionDef)}
        self.assertEqual(set(new_methods) - set(old_methods), {'_preview_frame'})
        for name in set(old_methods) - {'__init__', 'publish_preview', 'snapshot', 'preview'}:
            self.assertEqual(ast.dump(old_methods[name]), ast.dump(new_methods[name]), name)
        def thread_calls(tree):
            return [ast.dump(node) for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute) and node.func.attr == 'Thread']
        self.assertEqual(thread_calls(old), thread_calls(new))
        old_preview = next(node for node in ast.walk(old_top['run'])
                           if isinstance(node, ast.FunctionDef) and node.name == 'preview')
        reverted_run = copy.deepcopy(new_top['run'])
        preview = next(node for node in ast.walk(reverted_run)
                       if isinstance(node, ast.FunctionDef) and node.name == 'preview')
        old_block = next(node.body for node in ast.walk(old_preview) if isinstance(node, ast.Try))
        new_block = next(node.body for node in ast.walk(preview) if isinstance(node, ast.Try))
        old_index = next(index for index, node in enumerate(old_block)
                         if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                         and ast.unparse(node.value.func) == 'raw.publish')
        new_index = next(index for index, node in enumerate(new_block)
                         if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == 'pixels')
        self.assertEqual([ast.unparse(node) for node in new_block[new_index:new_index+3]], [
            'pixels = image.tobytes()',
            'raw.publish(fid, stamp, pixels)',
            'state.publish_preview(fid, stamp, pixels=pixels)',
        ])
        new_block[new_index:new_index+3] = copy.deepcopy(old_block[old_index:old_index+4])
        self.assertEqual(ast.dump(old_top['run']), ast.dump(reverted_run))


def main():
    baseline_threads = {thread.ident for thread in threading.enumerate()}
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(SourceTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(author_tests))
    log = io.StringIO()
    started = time.monotonic()
    with patch.dict(os.environ, {'AURA_PIPELINE_METRICS': '0', 'AURA_DPU_DIAGNOSTICS': '0'}):
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    lingering = [thread.name for thread in threading.enumerate() if thread.ident not in baseline_threads]
    report = {
        'status': 'PASS' if result.wasSuccessful() and not lingering else 'FAIL',
        'tests_run': result.testsRun,
        'independent_tests': 11,
        'author_regressions_rerun': 25,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'seconds': round(time.monotonic() - started, 3),
        'new_threads_remaining': lingering,
        'before_sha256': BEFORE_SHA,
        'after_sha256': AFTER_SHA,
        'review_test_sha256': sha(Path(__file__)),
        'author_pins': PINS,
        'device_accessed': False,
        'author_files_modified': False,
        'opencv_actual_encode_executed': False,
        'network_or_localhost_listener_opened': False,
        'raw_payload_bound_bytes': {'ring': 8 * PIXELS, 'evicted_active': PIXELS, 'total': 9 * PIXELS},
        'scope': 'Frame payload references only. OpenCV/Python scratch, source frame, raw transport, HTTP threads and response bytes are additional.',
        'failed_tests': [{'id': test.id(), 'traceback': error} for test, error in result.failures + result.errors],
    }
    for relative, expected in PINS.items():
        assert sha(CANDIDATE / relative) == expected, relative
    (HERE / 'PUBLIC_REVIEW_RESULT_01.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (HERE / 'PUBLIC_REVIEW_RESULT_01.log').write_text(log.getvalue(), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('status', 'tests_run', 'failures', 'errors', 'seconds', 'new_threads_remaining')}))
    if not result.wasSuccessful():
        print(log.getvalue()[-9000:])
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
