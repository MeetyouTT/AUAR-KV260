"""Portable synthetic observer checks. No transport, device or service operations."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.abc
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time
import types
import unittest
import unittest.mock  # Python 3.9 imports asyncio/socket; loading the test framework opens no socket.

from prepare_sources import PINS
from evaluate_preflight import ITERATIONS, evaluate

ROOT = Path(__file__).resolve().parent
FORBIDDEN = frozenset(('vart', 'xir', 'cv2', 'gi', 'numpy', 'serial', 'socket', 'requests'))


class DeviceImportBlocker(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in FORBIDDEN:
            raise ImportError('Synthetic check refused device/network dependency: ' + fullname)
        return None


def refuse_device_operation(event, args):
    if event.startswith('socket.') or event in ('ctypes.dlopen', 'subprocess.Popen', 'os.system'):
        raise RuntimeError('Synthetic worker refused device/network/process operation: ' + event)
    if event == 'open' and args and isinstance(args[0], (str, bytes)):
        name = os.fsdecode(args[0])
        if name == '/dev' or name.startswith('/dev/'):
            raise RuntimeError('Synthetic worker refused device open')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_sources():
    for relative, digest in PINS.items():
        p = ROOT / relative
        if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen source differs: ' + relative)


def suite():
    # Override path data only. Frozen test/source bytes remain unchanged.
    module = load('_frozen_freshness_tests', ROOT / 'tests/test_freshness_metrics.py')
    module.BASELINE = ROOT / 'reference/face_targets.py'
    tests = unittest.defaultTestLoader.loadTestsFromModule(module)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(tests)
    return {'pid': os.getpid(), 'run': result.testsRun, 'failures': len(result.failures),
            'errors': len(result.errors), 'skipped': len(result.skipped),
            'successful': result.wasSuccessful(), 'output': stream.getvalue()}


class FakeTracks:
    def __init__(self, *args, **kwargs):
        self.tracks = {}

    def update(self, *args):
        return {'tracks': []}


class SlotUnavailable(RuntimeError):
    pass


class FakeDetector:
    kind = 'SYNTHETIC_NO_DEVICE'

    def __init__(self, denied):
        self.denied, self.calls = denied, 0

    def detect(self, image):
        self.calls += 1
        if self.denied:
            raise SlotUnavailable('synthetic admission rejection')
        return ()


@contextmanager
def fakes(metrics):
    # Inject exact leaf dependencies before loading pinned service definitions.
    values = {
        'board.interaction.ui_contract': types.SimpleNamespace(millis=lambda: time.monotonic_ns() // 1000000),
        'board.vision.reference_core': types.SimpleNamespace(FaceTracks=FakeTracks, valid_box=lambda *a: None),
        'board.vision.dpu_vision_runtime': types.SimpleNamespace(SlotUnavailable=SlotUnavailable),
        'board.identity.face_freshness_metrics': metrics,
    }
    old = {key: sys.modules.get(key) for key in values}
    sys.modules.update(values)
    try:
        yield
    finally:
        for key, previous in old.items():
            if previous is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = previous


def distribution(values):
    return {'count': len(values), 'mean_ms': sum(values) / len(values),
            'min_ms': min(values), 'max_ms': max(values)}


def measure(mode, case, old, new):
    callbacks = [0]
    def on_face(*args):
        callbacks[0] += 1
    module = old if mode == 'original' else new
    kwargs = {} if mode == 'original' else {'freshness_metrics': mode == 'on'}
    service = module.FaceTargetService(lambda: None, on_face, 'SYNTHETIC',
        clock=lambda: time.monotonic_ns() // 1000000, **kwargs)
    service.ready = True
    recorder = getattr(service, '_freshness', None)
    if mode == 'on':
        assert recorder is not None
        assert recorder.wall_clock is time.monotonic_ns
        assert recorder.thread_clock is time.thread_time_ns
    assert module.time is time
    wall, cpu = [], []
    detector = FakeDetector(case != 'normal_empty_face')
    event_count = None
    image = object()
    try:
        if case == 'full_event_health_outer_lock':
            for index in range(16):
                service.process((image, index, time.monotonic_ns() // 1000000), detector)
            event_count = len(service.health()['freshness_metrics']['events']) if mode == 'on' else 0
            if mode == 'on':
                assert event_count == 16
        for index in range(ITERATIONS):
            packet = (image, index, time.monotonic_ns() // 1000000)
            c0, w0 = time.thread_time_ns(), time.monotonic_ns()
            if case == 'full_event_health_outer_lock':
                with service.lock:
                    health = service.health()
                assert health['discarded'] == 16
            else:
                # Include capture offer hooks plus process/observer work.
                service.offer(*packet)
                with service.condition:
                    packet, service.pending = service.pending, None
                service.process(packet, detector)
            w1, c1 = time.monotonic_ns(), time.thread_time_ns()
            wall.append((w1 - w0) / 1000000.)
            cpu.append((c1 - c0) / 1000000.)
        expected = 16 if case == 'full_event_health_outer_lock' else ITERATIONS
        assert detector.calls == expected
        if case == 'normal_empty_face':
            assert service.processed == ITERATIONS and service.discarded == 0 and callbacks[0] == ITERATIONS
        else:
            assert service.discarded == expected and service.processed == 0 and callbacks[0] == 0
        health = service.health()
        complete, failures = None, 0
        if mode == 'on':
            observed = health['freshness_metrics'];counters = observed['counters']
            failures = observed['observer_failures']
            expected_counter = 'published' if case == 'normal_empty_face' else 'slot_unavailable'
            complete = (failures == 0 and counters['attempts'] == expected
                and counters['attempts_finished'] == expected and counters['active_attempts'] == 0
                and counters[expected_counter] == expected
                and all(counters[key] == 0 for key in ('clock_read_failures', 'invalid_clock_values',
                    'invalid_source_ages', 'wall_pairs_rejected', 'cpu_pairs_rejected',
                    'source_clock_pairs_rejected', 'numeric_summary_rejections')))
            if case != 'full_event_health_outer_lock':
                complete = complete and counters['offers_accepted'] == ITERATIONS and counters['latest_replaced'] == 0
        row = {'iterations_completed': ITERATIONS, 'wall': distribution(wall),
               'thread_cpu': distribution(cpu), 'behavior_verified': True,
               'observer_complete': complete, 'observer_failures': failures,
               'events_before_measurement': event_count,
               'scope': 'offer+single-slot dequeue+process with empty fake detector' if case != 'full_event_health_outer_lock'
                        else 'health under an outer shared RLock, full 16-event recorder'}
    finally:
        service.close()
    row['closed_cleanly'] = service.closed and (recorder is None or recorder.closed)
    return row


def benchmark():
    metrics = load('_real_clock_metrics', ROOT / 'candidate/aura/board/identity/face_freshness_metrics.py')
    assert metrics.time is time
    assert callable(getattr(time, 'thread_time_ns', None))
    with fakes(metrics):
        old = load('_original_service', ROOT / 'reference/face_targets.py')
        new = load('_candidate_service', ROOT / 'candidate/aura/board/identity/face_targets.py')
        cases = {case: {mode: measure(mode, case, old, new) for mode in ('original', 'off', 'on')}
                 for case in ('normal_empty_face', 'slot_unavailable', 'full_event_health_outer_lock')}
    return {'pid': os.getpid(), 'iterations': ITERATIONS, 'real_clocks_verified': True,
            'cases': cases, 'schedule': 'one fixed sequential original/off/on block per case',
            'scope': 'synthetic observer hooks, no actual model/runner/worker/camera/audio; not a performance A/B'}


def main():
    if sys.flags.optimize:
        raise RuntimeError('Synthetic verification requires assertions enabled; remove -O/PYTHONOPTIMIZE')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--worker', choices=('tests', 'benchmark'))
    args = parser.parse_args()
    check_sources()
    if args.worker:
        sys.meta_path.insert(0, DeviceImportBlocker())
        sys.addaudithook(refuse_device_operation)
        value = suite() if args.worker == 'tests' else benchmark()
        print(json.dumps(value, ensure_ascii=False, allow_nan=False))
        return
    if args.output is None:
        parser.error('--output NEW_DIRECTORY is required')
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 'aura-synthetic-freshness-preflight-1', 'complete': False,
              'execution_scope': 'synthetic_no_devices', 'board_connected': False, 'new_dpu_jobs': 0,
              'source_sha256': PINS, 'started_utc': datetime.now(timezone.utc).isoformat(),
              'host': {'machine': platform.machine(), 'python': platform.python_version()}}
    for worker, key in (('tests', 'tests'), ('benchmark', 'benchmark')):
        try:
            result = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--worker', worker],
                cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, text=True)
            (args.output / (worker + '.stderr.txt')).write_text(result.stderr)
            if result.returncode:
                raise RuntimeError(worker + ' worker returned ' + str(result.returncode))
            report[key] = json.loads(result.stdout)
            if key == 'tests':
                (args.output / 'frozen-tests.txt').write_text(report[key].pop('output'))
                if not report[key]['successful']:
                    raise RuntimeError('Frozen tests failed')
        except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            report['error'] = type(exc).__name__ + ': ' + str(exc)
            break
    else:
        report['complete'] = True
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    assessment = evaluate(report)
    (args.output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    (args.output / 'assessment.json').write_text(json.dumps(assessment, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'output': str(args.output), 'complete': report['complete'],
        'synthetic_gate_passed': assessment['passed'], 'failures': assessment['failures'],
        'board_validation': False, 'host_machine': report['host']['machine']}))
    raise SystemExit(0 if assessment['passed'] else 1)


if __name__ == '__main__':
    main()
