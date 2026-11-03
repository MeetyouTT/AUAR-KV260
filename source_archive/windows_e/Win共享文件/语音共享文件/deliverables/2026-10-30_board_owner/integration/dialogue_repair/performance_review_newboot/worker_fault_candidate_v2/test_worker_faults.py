"""Local worker fault metadata tests plus the unchanged worker regression suite."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import threading
import types
import unittest


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parents[1]
BASE = REPAIR/'feature_trigger_collaboration/board_integration_v17/local_runtime_v17'
sys.path.insert(0, str(BASE))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# This suite checks worker scheduling, cancellation and metadata. Its tiny
# public images use a deterministic resize double without an OpenCV install.
resize_module = types.ModuleType('tools.board_avatar_affine')
resize_module.resize_rgb = lambda image, size: image.resize(size).convert('RGB').tobytes()
sys.modules['tools.board_avatar_affine'] = resize_module

WORKER = load('tools.board_avatar_worker', HERE/'after/tools/board_avatar_worker.py')
ORIGINAL_TESTS = load('original_worker_regression_tests', BASE/'tests/framework/test_board_avatar_worker.py')


class MemoryBusy(RuntimeError):
    pass


class SyntheticPrivateClass(RuntimeError):
    pass


def until(predicate):
    deadline = time.monotonic()+3
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.005)
    raise AssertionError('Public worker fixture did not settle')


class Controller:
    def __init__(self, fail_in='tick'):
        self.last_error = ''
        self.fail_in = fail_in
        self.failed = False
        self.successful_ticks = 0
        self.public_reads = 0
        self.cancels = 0
        self.events = 0

    def tick(self):
        if self.fail_in == 'tick' and not self.failed:
            self.failed = True
            raise MemoryBusy('PUBLIC_SYNTHETIC_CONTENT_MUST_NOT_ENTER_FAULT_METADATA')
        self.successful_ticks += 1
        return None

    def public(self):
        self.public_reads += 1
        if self.fail_in == 'public' and self.public_reads > 1 and not self.failed:
            self.failed = True
            raise ValueError('PUBLIC_SYNTHETIC_STATE_CONTENT')
        return dict(phase='IDLE', playing=False, error=self.last_error)

    def cancel(self):
        self.cancels += 1

    def event(self, name):
        self.events += 1
        return dict(accepted=True)

    def close(self):
        pass


class FaultMetadataTests(unittest.TestCase):
    def worker(self, fail_in='tick'):
        controller = Controller(fail_in)
        worker = WORKER.AvatarRenderWorker(controller, '#ffffff', (1, 1), interval=.01)
        self.addCleanup(worker.close)
        until(lambda: controller.successful_ticks > 2)
        return worker, controller

    def test_native_tid_matches_real_worker_thread_and_snapshot_is_detached(self):
        worker, _ = self.worker()
        value = worker.read()['state']['avatar_renderer']
        native_tid = value['worker_native_tid']
        self.assertIs(type(native_tid), int)
        self.assertGreater(native_tid, 0)
        self.assertEqual(native_tid, worker.thread.native_id)
        self.assertNotEqual(native_tid, threading.get_native_id())
        value['worker_native_tid'] = -1
        self.assertEqual(worker.read()['state']['avatar_renderer']['worker_native_tid'], native_tid)

    def test_uninitialized_thread_fixture_reports_no_native_tid(self):
        worker, _ = self.worker()
        fixture = copy.copy(worker)
        fixture.thread = None
        self.assertIsNone(fixture.read()['state']['avatar_renderer']['worker_native_tid'])
        del fixture.thread
        self.assertIsNone(fixture.read()['state']['avatar_renderer']['worker_native_tid'])

    def test_fault_survives_successful_ticks_and_commands(self):
        worker, controller = self.worker()
        initial = worker.read()['state']['avatar_renderer']['worker_faults']
        self.assertEqual(initial['count'], 1)
        self.assertEqual(initial['last']['error_class'], 'MemoryBusy')
        self.assertEqual(initial['last']['stage'], 'controller_tick')
        self.assertEqual(controller.cancels, 1)
        command = worker.event('idle')
        until(lambda: any(row['command_id'] == command and row['ok'] for row in
                          worker.read()['state']['avatar_renderer']['command_results']))
        after = worker.read()['state']['avatar_renderer']['worker_faults']
        self.assertEqual(after, initial)
        self.assertEqual(controller.cancels, 1)
        self.assertNotIn('PUBLIC_SYNTHETIC_CONTENT', json.dumps(after))

    def test_fault_snapshot_is_detached(self):
        worker, _ = self.worker()
        value = worker.read()['state']['avatar_renderer']['worker_faults']
        value['last']['error_class'] = 'changed by test'
        value['last']['frames'].clear()
        fresh = worker.read()['state']['avatar_renderer']['worker_faults']
        self.assertEqual(fresh['last']['error_class'], 'MemoryBusy')
        self.assertTrue(fresh['last']['frames'])

    def test_state_snapshot_failure_keeps_original_cancel_behavior(self):
        worker, controller = self.worker('public')
        value = worker.read()['state']['avatar_renderer']['worker_faults']
        self.assertEqual(value['last']['stage'], 'state_snapshot')
        self.assertEqual(value['last']['error_class'], 'ValueError')
        self.assertEqual(controller.cancels, 1)

    def test_unknown_exception_name_and_messages_are_not_exported(self):
        try:
            raise SyntheticPrivateClass('PUBLIC_SYNTHETIC_SECRET')
        except Exception as error:
            value = WORKER._worker_fault_metadata(error, 1)
        text = json.dumps(value)
        self.assertEqual(value['last']['error_class'], 'other')
        self.assertNotIn('SyntheticPrivateClass', text)
        self.assertNotIn('PUBLIC_SYNTHETIC_SECRET', text)
        self.assertNotIn(str(HERE), text)

    def test_trace_is_bounded_and_count_saturates(self):
        def nested(depth):
            if depth:
                return nested(depth-1)
            raise RuntimeError('public test')
        try:
            nested(45)
        except Exception as error:
            value = WORKER._worker_fault_metadata(error, 10**30)
        self.assertEqual(value['count'], 9007199254740991)
        self.assertEqual(len(value['last']['frames']), 6)
        self.assertTrue(value['last']['frames_truncated'])


if __name__ == '__main__':
    suite = unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromModule(ORIGINAL_TESTS),
                               unittest.defaultTestLoader.loadTestsFromTestCase(FaultMetadataTests)))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = dict(status='PASS' if result.wasSuccessful() else 'FAIL', tests_run=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), results=stream.getvalue(),
                  hardware_model_or_private_store_opened=False, image_resize_test_double=True)
    print(json.dumps(report))
    raise SystemExit(0 if result.wasSuccessful() else 1)
