"""Exact endpoint/proxy with synthetic clocks/transport; no devices or models."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT.parents[1]
PROJECT = ROOT.parents[4]
sys.path.insert(0, str(PROJECT / 'aura'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


import board.runtime.audio as audio_package
audio_package.__path__.insert(0, str(ROOT.parent / 'capture_sources/board/runtime/audio'))
audio_package.__path__.insert(0, str(ROOT / 'after/board/runtime/audio'))
automatic = load('board.runtime.audio.automatic_capture', ROOT / 'after/board/runtime/audio/automatic_capture.py')
remote = load('board.runtime.audio.capture_diagnostics_remote', ROOT / 'after/board/runtime/audio/board_frontend_auto.py')
recording = load('tools.capture_diagnostics_recording', ROOT.parent /
    'instrumentation_candidate/after/tools/board_recording.py')
presentation = load('tools.capture_diagnostics_presentation', ROOT.parent /
    'before/tools/production_memory_presentation.py')


class Clock:
    def __init__(self): self.now = 10.
    def __call__(self): return self.now


class EndpointMetricsTests(unittest.TestCase):
    def make(self):
        wall, cpu = Clock(), Clock()
        capture = automatic.AutomaticMcp01Capture(lambda: False, clock=wall)
        return capture, wall, cpu

    def test_exact_feed_wall_thread_cpu_and_start_to_start_gaps(self):
        capture, wall, cpu = self.make(); seen = []
        durations = iter([(.006, .002), (.008, .003)])
        def feed(raw):
            seen.append(raw)
            dw, dc = next(durations); wall.now += dw; cpu.now += dc
            return raw
        capture.endpoint = SimpleNamespace(feed=feed, active=False, total_samples=0, frame_classifier=None)
        raw = b'\xe8\x03' * 320
        with mock.patch.object(automatic.time, 'thread_time', side_effect=cpu):
            self.assertIs(capture._feed_endpoint(raw), raw)
            wall.now += .014
            self.assertIs(capture._feed_endpoint(raw), raw)
        self.assertEqual(seen, [raw, raw])
        d = capture.snapshot()['audio_frontend']
        self.assertEqual(d['endpoint_feed_calls'], 2)
        self.assertAlmostEqual(d['endpoint_feed_wall_total_ms'], 14.)
        self.assertAlmostEqual(d['endpoint_feed_wall_max_ms'], 8.)
        self.assertAlmostEqual(d['endpoint_feed_cpu_total_ms'], 5.)
        self.assertAlmostEqual(d['endpoint_feed_cpu_max_ms'], 3.)
        self.assertEqual(d['consumer_gap_count'], 1)
        self.assertAlmostEqual(d['consumer_gap_max_ms'], 20.)
        self.assertTrue(all(type(v) in (int, float, bool) for v in d.values()))

    def test_failed_endpoint_is_counted_but_no_error_body_or_pcm_is_retained(self):
        capture, wall, cpu = self.make()
        def fail(raw):
            wall.now += .009; cpu.now += .004
            raise RuntimeError('private synthetic exception text')
        capture.endpoint = SimpleNamespace(feed=fail, active=False, total_samples=0, frame_classifier=None)
        with mock.patch.object(automatic.time, 'thread_time', side_effect=cpu):
            with self.assertRaises(RuntimeError): capture._feed_endpoint(b'\x01\x00' * 320)
        metrics = capture.snapshot()['audio_frontend']
        self.assertEqual(metrics['endpoint_feed_calls'], 1)
        self.assertAlmostEqual(metrics['endpoint_feed_wall_total_ms'], 9.)
        self.assertAlmostEqual(metrics['endpoint_feed_cpu_total_ms'], 4.)
        self.assertNotIn('private', json.dumps(metrics))

    def test_rearm_resets_metrics_without_changing_original_endpoint_configuration(self):
        capture, _, _ = self.make()
        capture.endpoint = SimpleNamespace(feed=lambda raw: None, active=False,
            total_samples=0, frame_classifier=None)
        capture._feed_endpoint(b'\0' * 640)
        capture._capture_timer()
        self.assertTrue(all(value == 0 for value in capture._endpoint_diagnostics.values()))
        self.assertIsNone(capture._previous_endpoint_started)
        self.assertEqual(capture.endpoint.pre_frames, 10)
        self.assertEqual(capture.endpoint.config.min_silence_ms, 700)
        self.assertEqual(capture.buffer_time_us, 160000)

    def test_original_read_loop_uses_timed_exact_endpoint_and_same_stop_signal(self):
        capture, _, _ = self.make(); original = b'\x01\x00' * 320
        capture.endpoint = SimpleNamespace(frame_bytes=640, active=False, speech_samples=320,
            feed=lambda raw: original, start_sample=0, total_samples=320, frame_classifier=None)
        capture._signal = mock.Mock()
        result = capture._read_automatic_pcm(SimpleNamespace(stdout=io.BytesIO(original)))
        self.assertIs(result, original)
        self.assertEqual(capture.snapshot()['audio_frontend']['endpoint_feed_calls'], 1)
        capture._signal.assert_called_once_with(automatic.signal.SIGINT)
        self.assertTrue(capture._stopping)

    def test_real_speech_endpoint_keeps_bitwise_pcm_and_offset(self):
        decisions = [False] * 25 + [True] * 10 + [False] * 40
        first = automatic.SpeechEndpoint(20, frame_classifier=lambda frame: next(d1), pre_roll_ms=500)
        second = automatic.SpeechEndpoint(20, frame_classifier=lambda frame: next(d2), pre_roll_ms=500)
        d1, d2 = iter(decisions), iter(decisions)
        capture, _, _ = self.make(); capture.endpoint = second
        expected = actual = None
        for n in range(len(decisions)):
            raw = struct.pack('<320h', *[((n * 320 + i) % 61 - 30) * 400 for i in range(320)])
            expected, actual = first.feed(raw), capture._feed_endpoint(raw)
            self.assertEqual(actual, expected)
            if expected is not None: break
        self.assertIsNotNone(actual)
        self.assertEqual(first.start_sample, second.start_sample)
        self.assertEqual(first.speech_samples, second.speech_samples)


class Transport:
    def __init__(self): self.generation = 0; self.status = None; self.lock = threading.Lock()
    def start(self, limit):
        with self.lock:
            self.generation += 1
            self.status = dict(state='RECORDING', capture_id=f'{self.generation:032x}', generation=self.generation,
                speech_started=False, sample_count=0, speech_active=False, input_ready=True,
                listening_seconds=0., has_result=False, error='', input_queue=dict(capacity_frames=8, peak_frames=0),
                audio_frontend=dict(endpoint_feed_calls=0, endpoint_feed_wall_total_ms=0., consumer_gap_max_ms=0.))
            return copy.deepcopy(self.status)
    def poll(self, generation, cid):
        with self.lock: return copy.deepcopy(self.status)
    def fail(self):
        with self.lock:
            self.status.update(state='ERROR', error='pcm_input_queue_overflow',
                input_queue=dict(capacity_frames=8, peak_frames=8, frames_read=11890, frames_delivered=11881,
                    error='pcm_input_queue_overflow', cancelled=False),
                audio_frontend=dict(endpoint_feed_calls=11880, endpoint_feed_wall_total_ms=209001.,
                    endpoint_feed_cpu_total_ms=180001., consumer_gap_max_ms=93., worker_pid=12345))
    def cancel(self, generation, cid):
        with self.lock:
            self.status.update(state='CANCELLED', error='', has_result=False)
            return copy.deepcopy(self.status)
    def close(self, generation, cid):
        with self.lock:
            self.status.update(state='CLOSED', error='', has_result=False)
            return copy.deepcopy(self.status)


def wait_until(predicate):
    deadline = time.monotonic() + 1.
    while not predicate():
        if time.monotonic() > deadline: raise AssertionError('bounded fake status did not arrive')
        threading.Event().wait(.002)


class FaultSnapshotTests(unittest.TestCase):
    def make(self):
        tx = Transport()
        proxy = remote.RemoteAutomaticCapture(lambda: False, transport=tx, poll_interval=.02)
        self.addCleanup(proxy.close)
        proxy.start()
        return proxy, tx

    def test_one_bounded_fault_survives_cancel_rearm_and_public_mapping(self):
        proxy, tx = self.make(); tx.fail()
        wait_until(lambda: proxy.state == 'ERROR')
        first = proxy.snapshot()['audio_frontend']
        self.assertEqual(first['capture_failures'], 1)
        fault = first['last_capture_failure']
        self.assertTrue(fault['from_error_status'])
        self.assertEqual(fault['error_code'], 'pcm_input_queue_overflow')
        self.assertEqual(fault['input_queue']['peak_frames'], 8)
        self.assertEqual(fault['audio_frontend']['endpoint_feed_calls'], 11880)
        self.assertNotIn('capture_id', json.dumps(fault))
        self.assertLess(len(json.dumps(fault)), 2048)
        proxy.cancel(); proxy.start()
        sink = SimpleNamespace(public=lambda: dict(phase='IDLE', playing=False, paused=False,
            pending_job=None, audio_output_state='IDLE_READY'), last_error='')
        owner = recording.RecordingController(sink); owner.capture = proxy
        current = presentation._clean(owner.public())['audio_frontend']['current']
        self.assertEqual(current['capture_failures'], 1)
        self.assertEqual(current['endpoint_feed_calls'], 0)
        self.assertEqual(current['last_capture_failure'], fault)
        current['last_capture_failure']['input_queue']['peak_frames'] = -1
        self.assertEqual(proxy.snapshot()['audio_frontend']['last_capture_failure']['input_queue']['peak_frames'], 8)
        proxy.cancel()
        self.assertEqual(proxy.snapshot()['audio_frontend']['capture_failures'], 1)

    def test_user_pause_cancel_close_never_create_failure(self):
        proxy, tx = self.make()
        proxy.cancel(); proxy.start(); proxy.cancel(); proxy.close()
        frontend = proxy.snapshot()['audio_frontend']
        self.assertEqual(frontend['capture_failures'], 0)
        self.assertNotIn('last_capture_failure', frontend)

    def test_wire_metrics_allow_only_finite_numeric_names_and_original_fixed_errors(self):
        values = dict(endpoint_feed_calls=17, endpoint_feed_cpu_total_ms=12., consumer_gap_max_ms=99.,
            endpoint_feed_wall_total_ms=float('nan'), consumer_gap_last_ms=-1,
            endpoint_feed_wall_max_ms=True, pcm=b'private', text='private', capture_id='private-id')
        metrics = remote._metrics(values)
        self.assertEqual(metrics, dict(endpoint_feed_calls=17, endpoint_feed_cpu_total_ms=12., consumer_gap_max_ms=99.))
        tx = Transport(); status = tx.start(20)
        status['audio_frontend'].update(metrics)
        encoded = remote._json(remote.validate_status(status))
        self.assertLessEqual(len(encoded), 4096)
        self.assertEqual(remote.decode_status(encoded), status)
        status['audio_frontend']['text'] = 'private'
        with self.assertRaises(remote.wire.FrontendProcessError): remote.validate_status(status)


if __name__ == '__main__': unittest.main()
