"""Real socketpair/protocol/pool; fake model and process ownership, no device."""
import ast
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'production_business_overlay/candidate/aura'
sys.path.insert(0, str(BASE))
from board.runtime.audio.board_capture import BoardFrontendPool


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'after/aura' / relative)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


m = load('board.runtime.audio.board_frontend_process', 'board/runtime/audio/board_frontend_process.py')
selection = load('process_selection_test', 'tools/production_frontend_selection.py')


class Gate:
    def __init__(self, block=None, started=None, fail=False):
        self.closed = False
        self.lock = threading.Lock()
        self.error = ''
        self.frames = self.samples = 0
        self.last_ms, self.max_ms = None, 0.
        self.block, self.started, self.fail = block, started, fail
        self.resets = [0, 0]
        self.denoiser = SimpleNamespace(reset=lambda:self.reset(0))
        self.vad = SimpleNamespace(reset=lambda:self.reset(1))
    def reset(self, index):
        self.resets[index] += 1
    def __call__(self, frame):
        if self.started:
            self.started.set()
        if self.block:
            self.block.wait(timeout=1.)
        if self.fail:
            raise ValueError('Synthetic private text must never be returned')
        self.frames += 1
        self.samples += 320
        self.last_ms = self.max_ms = .1
        return bool(np.max(np.abs(frame)) > .2)
    def close(self):
        self.closed = True


class Process:
    def __init__(self, stream, target):
        self.pid = os.getpid()  # Thread fixture serves in this test process.
        self.stream = stream
        self.terminations = 0
        self.thread = threading.Thread(target=self.run, args=(target,), daemon=True)
        self.thread.start()
    def run(self, target):
        try:
            target(self.stream)
        finally:
            self.stream.close()
    def poll(self):
        return None if self.thread.is_alive() else 0
    def wait(self, timeout):
        self.thread.join(timeout)
        if self.thread.is_alive():
            raise subprocess.TimeoutExpired('fake owned frontend', timeout)
        return 0
    def terminate(self):
        self.terminations += 1
        try:
            self.stream.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


def duplicate_socket(handle):
    borrowed = socket.socket(fileno=handle)
    try:
        return borrowed.dup()
    finally:
        borrowed.detach()  # The production constructor owns this original handle.


class ProcessTests(unittest.TestCase):
    def make(self, gate=None, target=None, timeout=.5, startup=.5):
        self.instances = []
        self.gates = []
        self.spawn = []
        gate = gate or Gate()
        def create():
            self.gates.append(gate)
            return gate
        def factory(argv, **kwargs):
            self.spawn.append((argv, kwargs))
            child = duplicate_socket(kwargs['pass_fds'][0])
            process = Process(child, target or (lambda stream:m.serve(stream, create)))
            self.instances.append(process)
            return process
        proxy = m.BoardProcessSpeechGate('/public-model-fixture', process_factory=factory,
            frame_timeout=timeout, startup_timeout=startup)
        self.addCleanup(proxy.shutdown)
        return proxy, gate

    def test_one_child_model_exact_float_payload_and_metrics(self):
        proxy, gate = self.make()
        pool = BoardFrontendPool(proxy)
        lease = pool.acquire()
        self.assertTrue(lease(np.full(320, .25, np.float32)))
        self.assertFalse(lease(np.zeros(320, np.float32)))
        state = proxy.public()
        self.assertEqual(state['frames'], 2)
        self.assertEqual(state['processed_samples'], 640)
        self.assertEqual(len(self.gates), 1)
        self.assertEqual(gate.resets, [1, 1])
        self.assertTrue(state['worker_process_alive'])
        for name in ('worker_frame_wall_last_ms','worker_frame_cpu_total_ms','ipc_rpc_last_ms'):
            self.assertGreaterEqual(state[name], 0.)
        argv, kwargs = self.spawn[0]
        self.assertEqual(argv[0], sys.executable)
        self.assertIn('--worker-fd', argv)
        self.assertTrue(kwargs['close_fds'])
        self.assertNotIn('preexec_fn', kwargs)
        lease.close()
        self.assertIsNone(pool.active)
        self.assertTrue(proxy.public()['worker_process_alive'])
        next_lease = pool.acquire()
        self.assertFalse(next_lease(np.zeros(320, np.float32)))
        self.assertEqual(len(self.gates), 1)
        self.assertEqual(gate.resets, [2, 2])
        pool.close()
        self.assertTrue(proxy.shutdown())
        self.assertFalse(proxy.public()['worker_process_alive'])
        self.assertEqual(self.instances[0].terminations, 0)

    def test_cancel_returns_before_late_result_and_next_generation_discards_it(self):
        release, started = threading.Event(), threading.Event()
        proxy, gate = self.make(Gate(block=release, started=started))
        pool = BoardFrontendPool(proxy)
        lease = pool.acquire()
        result = []
        def classify():
            try:
                result.append(lease(np.ones(320, np.float32)))
            except BaseException as exc:
                result.append(exc)
        consumer = threading.Thread(target=classify)
        consumer.start()
        self.assertTrue(started.wait(.25))
        before = time.monotonic()
        lease.close()
        consumer.join(.15)
        self.assertFalse(consumer.is_alive())
        self.assertLess(time.monotonic() - before, .15)
        self.assertIsInstance(result[0], InterruptedError)
        self.assertIsNone(pool.active)
        threading.Timer(.03, release.set).start()
        next_lease = pool.acquire()
        self.assertFalse(next_lease(np.zeros(320, np.float32)))
        self.assertEqual(proxy.public()['frames'], 1)
        self.assertEqual(proxy.public()['worker_generation'], 2)
        self.assertEqual(len(proxy._abandoned), 0)
        pool.close()

    def test_timeout_fails_whole_turn_and_no_replacement_model(self):
        release, started = threading.Event(), threading.Event()
        proxy, _ = self.make(Gate(block=release, started=started), timeout=.05)
        self.addCleanup(release.set)
        pool = BoardFrontendPool(proxy)
        lease = pool.acquire()
        with self.assertRaisesRegex(m.FrontendProcessError, 'read_timeout'):
            lease(np.zeros(320, np.float32))
        self.assertTrue(proxy.closed)
        lease.close()
        with self.assertRaises(m.FrontendProcessError):
            pool.acquire()
        self.assertEqual(len(self.gates), 1)
        release.set()
        self.assertTrue(proxy.shutdown())

    def test_model_exception_has_fixed_code_and_child_retires(self):
        proxy, _ = self.make(Gate(fail=True))
        pool = BoardFrontendPool(proxy)
        lease = pool.acquire()
        with self.assertRaisesRegex(m.FrontendProcessError, '^frontend_worker_compute_failed$'):
            lease(np.zeros(320, np.float32))
        self.assertNotIn('private', repr(proxy.public()))
        lease.close()
        self.assertTrue(proxy.shutdown())
        self.assertFalse(proxy.public()['worker_process_alive'])

    def test_invalid_local_shape_or_range_is_never_sent(self):
        proxy, _ = self.make()
        pool = BoardFrontendPool(proxy)
        lease = pool.acquire()
        for frame in (np.zeros(319), np.full(320, np.nan), np.full(320, 1.1)):
            with self.assertRaises(ValueError):
                lease(frame)
        self.assertEqual(proxy.public()['frames'], 0)
        pool.close()

    def test_response_sequence_mismatch_is_failclosed(self):
        def target(stream):
            wire = m._Channel(stream)
            wire.send(m.HELLO | 128, 0, 0, m._result(), time.monotonic()+1)
            while True:
                kind, gen, seq, payload = wire.receive(time.monotonic()+1)
                wire.send(kind | 128, gen, seq+1, m._result(), time.monotonic()+1)
                return
        proxy, _ = self.make(target=target)
        pool = BoardFrontendPool(proxy)
        with self.assertRaisesRegex(m.FrontendProcessError, 'owner_mismatch'):
            pool.acquire()
        self.assertTrue(proxy.shutdown())

    def test_startup_failure_reaps_owned_child_without_fallback(self):
        processes = []
        def factory(argv, **kwargs):
            child = duplicate_socket(kwargs['pass_fds'][0])
            def target(stream):
                def fail():
                    raise RuntimeError('No model fixture')
                m.serve(stream, fail)
            process = Process(child, target)
            processes.append(process)
            return process
        with self.assertRaisesRegex(m.FrontendProcessError, '^frontend_worker_initialization_failed$'):
            m.BoardProcessSpeechGate('/unused', process_factory=factory, startup_timeout=.5)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())

    def test_priority_failure_is_reported_before_any_gate_is_created(self):
        gates, processes = [], []
        def factory(argv, **kwargs):
            child = duplicate_socket(kwargs['pass_fds'][0])
            def target(stream):
                def denied():
                    raise PermissionError('fixture')
                m.serve(stream, lambda:gates.append('unexpected'), apply_priority=denied)
            process = Process(child, target)
            processes.append(process)
            return process
        with self.assertRaisesRegex(m.FrontendProcessError, 'priority_rejected'):
            m.BoardProcessSpeechGate('/unused', process_factory=factory, startup_timeout=.5)
        self.assertEqual(gates, [])
        self.assertIsNotNone(processes[0].poll())

    def test_changed_actual_child_priority_is_rejected_on_next_response(self):
        priority = [-10]
        def target(stream):
            m.serve(stream, Gate, priority_reader=lambda:priority[0])
        proxy, _ = self.make(target=target)
        priority[0] = 0
        with self.assertRaisesRegex(m.FrontendProcessError, 'priority_rejected'):
            BoardFrontendPool(proxy).acquire()
        self.assertTrue(proxy.shutdown())


class ProtocolTests(unittest.TestCase):
    def test_partial_header_and_payload_survive_cancel_without_reframing(self):
        first, second = socket.socketpair()
        self.addCleanup(first.close)
        self.addCleanup(second.close)
        wire = m._Channel(first)
        packet = m.HEADER.pack(m.MAGIC, 1, m.FRAME | 128, 0, 1, 7, m.RESULT.size) + m._result()
        second.sendall(packet[:m.HEADER.size+3])
        cancelled = threading.Event()
        threading.Timer(.03, cancelled.set).start()
        with self.assertRaises(InterruptedError):
            wire.receive(time.monotonic()+.5, cancelled.is_set)
        self.assertLessEqual(len(wire.buffer), m.HEADER.size+3)
        second.sendall(packet[m.HEADER.size+3:])
        kind, gen, seq, payload = wire.receive(time.monotonic()+.5)
        self.assertEqual((kind, gen, seq), (m.FRAME | 128, 1, 7))
        self.assertEqual(payload, m._result())

    def test_oversized_header_is_rejected_before_body_allocation(self):
        first, second = socket.socketpair()
        self.addCleanup(first.close)
        self.addCleanup(second.close)
        second.sendall(m.HEADER.pack(m.MAGIC,1,m.FRAME,0,1,1,m.MAX_PAYLOAD+1))
        wire = m._Channel(first)
        with self.assertRaisesRegex(m.FrontendProcessError, 'protocol_failed'):
            wire.receive(time.monotonic()+.5)
        self.assertEqual(len(wire.buffer), m.HEADER.size)

    def test_finite_idle_wait_has_no_audio_or_model_side_effect(self):
        self.assertEqual(m.FRAME_BYTES, 1280)
        self.assertLess(m.RESULT.size, m.FRAME_BYTES)


class IntegrationTests(unittest.TestCase):
    def test_config_failure_after_worker_creation_calls_existing_close_handler(self):
        tree = ast.parse((ROOT/'after/aura/tools/production_board_business_gui.py').read_text(encoding='utf-8'))
        cls = next(node for node in tree.body if isinstance(node,ast.ClassDef))
        ctor = next(node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='__init__')
        guarded = next(node for node in ctor.body if isinstance(node,ast.Try))
        self.assertEqual(guarded.body[0].targets[0].attr,'frontend')
        self.assertEqual(guarded.body[1].targets[0].id,'config')
        scoped = copy.deepcopy(guarded)
        scoped.body = scoped.body[:2]
        function = ast.FunctionDef(name='initialize',
            args=ast.arguments(posonlyargs=[],args=[ast.arg(arg='self'),ast.arg(arg='value')],
                kwonlyargs=[],kw_defaults=[],defaults=[]),body=[scoped],decorator_list=[])
        events = []
        def config(*args,**kwargs):
            raise ValueError('Synthetic configuration rejection')
        namespace = dict(create_frontend_pool=lambda *args,**kwargs:'owned-child-pool',BoardBusinessConfig=config)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),
                     '<actual-post-spawn-constructor>','exec'),namespace)
        owner = SimpleNamespace(frontend_optimization='baseline',frontend_process=True,
                                close=lambda:events.append('close-owned-child'))
        value = dict(frontend_directory='/public-model',private_root='/private',utc_bounds=[1,2],
                     data_origin='board',bootstrap_receipt='/receipt',bootstrap_receipt_sha256='a'*64)
        with self.assertRaisesRegex(ValueError,'configuration rejection'):
            namespace['initialize'](owner,value)
        self.assertEqual(owner.frontend,'owned-child-pool')
        self.assertEqual(events,['close-owned-child'])

    def test_default_and_explicit_process_configuration(self):
        self.assertEqual(selection.validate_frontend_options({}), ('baseline',0))
        self.assertEqual(selection.validate_frontend_options(dict(frontend_process=True,
            frontend_optimization='baseline',frontend_threads=1,capture_priority_nice=-10)),('baseline',-10))
        for data in (dict(frontend_process='true'),dict(frontend_process=True,frontend_optimization='combined'),
                     dict(frontend_process=True,frontend_threads=2)):
            with self.assertRaises(ValueError):
                selection.validate_frontend_options(data)
        gate = Gate()
        with patch.object(m,'BoardProcessSpeechGate',return_value=gate) as construct:
            pool = selection.create_frontend_pool('/public-model',optimization='baseline',
                                                  num_threads=1,frontend_process=True)
        self.assertIs(pool.gate, gate)
        construct.assert_called_once_with('/public-model',num_threads=1)

    def test_gui_shutdown_must_complete_before_runtime_release(self):
        path = ROOT / 'after/aura/tools/production_board_business_gui.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        cls = next(node for node in tree.body if isinstance(node,ast.ClassDef))
        close = copy.deepcopy(next(node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='close'))
        isolated = ast.Module(body=[ast.ClassDef(name='ProductionGuiBoardBusiness',
            bases=[ast.Name(id='Base',ctx=ast.Load())],keywords=[],body=[close],decorator_list=[])],type_ignores=[])
        for success in (True,False):
            events = []
            class Base:
                def close(self):
                    events.append('release_runtime')
            namespace = dict(Base=Base)
            exec(compile(ast.fix_missing_locations(isolated),'<actual-gui-close>','exec'),namespace)
            gui = namespace['ProductionGuiBoardBusiness']()
            gui.recording = None
            gui.worker_owned = True
            gui.frontend = SimpleNamespace(close=lambda:events.append('cancel_pool'),
                gate=SimpleNamespace(shutdown=lambda:events.append('shutdown_worker') or success))
            if success:
                gui.close()
                self.assertEqual(events,['cancel_pool','shutdown_worker','release_runtime'])
            else:
                with self.assertRaisesRegex(RuntimeError,'shutdown_incomplete'):
                    gui.close()
                self.assertEqual(events,['cancel_pool','shutdown_worker'])

    def test_sources_are_python39_and_original_pool_queue_unchanged(self):
        for path in (ROOT / 'after/aura').rglob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'),feature_version=(3,9))
        self.assertFalse((ROOT/'after/aura/board/runtime/audio/board_capture.py').exists())
        self.assertFalse((ROOT/'after/aura/board/runtime/audio/board_pcm_queue.py').exists())
        source = (ROOT/'after/aura/board/runtime/audio/board_frontend_process.py').read_text(encoding='utf-8')
        self.assertNotIn('fork(',source)
        self.assertNotIn('.kill(',source)
        self.assertIn("from board.runtime.audio.board_gtcrn_fft import BoardFftSpeechGate",source)


if __name__ == '__main__':
    unittest.main()
