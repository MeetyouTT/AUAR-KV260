"""No native models/devices: real isolated capture/pump, synthetic finite sources."""
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock
import warnings

import numpy as np

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('allocation_probe_tested', HERE / 'allocation_public_probe.py')
worker = importlib.util.module_from_spec(spec); spec.loader.exec_module(worker)
parent_spec = importlib.util.spec_from_file_location('unchanged_probe_helpers', HERE / 'reference/board_audio_runtime_probe.py')
parent = importlib.util.module_from_spec(parent_spec); parent_spec.loader.exec_module(parent)
PINS = json.loads((HERE / 'PROBE_SOURCE_PINS.json').read_text('utf-8'))


def selected(arm):
    return {name.replace('/', '.')[:-3]: worker.ROOT / (row[arm] if 'before' in row else row)['relative_path']
            for name, row in PINS['components'].items()}


@contextmanager
def isolated(arm):
    names = ('board', 'board.runtime', 'board.runtime.audio', 'host', 'host.model_service', 'tools', 'common') + worker.MODULE_ORDER
    old = {n: sys.modules.get(n) for n in names}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            yield worker.load_isolated(selected(arm))
    finally:
        for name in reversed(names):
            if old[name] is None: sys.modules.pop(name, None)
            else: sys.modules[name] = old[name]


class FakeDenoiser:
    def __init__(self): self.reset()
    def reset(self):
        self.pending = np.empty(0, dtype=np.float32); self.started = False
    def _hop(self, samples):
        if not self.started:
            self.started = True
            return np.empty(0, dtype=np.float32)
        return samples.copy()
    def __call__(self, samples, sample_rate):
        assert sample_rate == 16000
        self.pending = np.concatenate((self.pending, samples))
        out = []
        while len(self.pending) >= 256:
            out.append(self._hop(self.pending[:256])); self.pending = self.pending[256:]
        return SimpleNamespace(samples=np.concatenate(out) if out else np.empty(0, dtype=np.float32))


class FakeGate:
    def __init__(self, fail=False):
        self.lock = threading.Lock(); self.denoiser = FakeDenoiser()
        self.vad = SimpleNamespace(reset=lambda: None)
        self.closed = False; self.error = ''; self.frames = self.samples = 0
        self.last_ms = None; self.max_ms = 0.; self.fail = fail
    def __call__(self, frame):
        if self.fail: raise RuntimeError('fixed synthetic failure')
        out = self.denoiser(frame, 16000)
        self.samples += len(out.samples); self.frames += 1
        return 4 <= self.frames < 16  # 12 speech frames, then original 700ms tail
    def close(self): self.closed = True
    def public(self): return {'frames': self.frames, 'closed': self.closed}


class BurstSource:
    def __init__(self, pcm):
        self.pcm = pcm; self.frames = 0; self.reader_thread = None
        self.lateness_ms = []; self.stopped = False
    def read(self, size):
        self.reader_thread = threading.current_thread().name
        if self.stopped or self.frames * 640 >= len(self.pcm): return b''
        offset = self.frames * 640; self.frames += 1
        return self.pcm[offset:offset + size]
    def stop(self): self.stopped = True


class ProbeTests(unittest.TestCase):
    def test_bundle_and_current_production_pins_fail_before_import_on_drift(self):
        original = worker.digest
        production = (HERE / 'synthetic-production-code').resolve()
        def fake_digest(path, maximum=1024*1024):
            path = Path(path)
            if production in path.parents:
                return PINS['components'][path.relative_to(production).as_posix()]['production_sha256']
            return original(path, maximum)
        with mock.patch.object(worker, 'digest', side_effect=fake_digest):
            sources, proof, path = worker.validate_sources('after', production)
            self.assertEqual(sources, selected('after'))
            self.assertEqual(len(proof), 12)
            self.assertEqual(original(path), PINS['parent_probe']['sha256'])
        def wrong(path, maximum=1024*1024):
            return '0'*64 if production in Path(path).parents else original(path, maximum)
        with mock.patch.object(worker, 'digest', side_effect=wrong):
            with self.assertRaisesRegex(worker.Refused, 'production_source_drift'):
                worker.validate_sources('before', production)
        target = selected('after')['board.runtime.audio.automatic_capture']
        def candidate_wrong(path, maximum=1024*1024):
            return '0'*64 if Path(path) == target else fake_digest(path, maximum)
        with mock.patch.object(worker, 'digest', side_effect=candidate_wrong):
            with self.assertRaisesRegex(worker.Refused, 'isolated_source_pin'):
                worker.validate_sources('after', production)

    def test_both_arms_bind_actual_endpoint_class_and_mro_before_import(self):
        for arm in ('before', 'after'):
            with isolated(arm) as modules:
                automatic = modules['board.runtime.audio.automatic_capture']
                board = modules['board.runtime.audio.board_capture']
                self.assertIn(automatic.AutomaticMcp01Capture, board.BoardAutomaticCapture.__mro__)
                self.assertIs(board.SpeechEndpoint, automatic.SpeechEndpoint)
                expected = PINS['components']['board/runtime/audio/automatic_capture.py'][arm]['sha256']
                self.assertEqual(worker.digest(Path(automatic.__file__)), expected)
                with self.assertRaisesRegex(worker.Refused, 'fresh_source_process_required'):
                    worker.load_isolated(selected(arm))

    def test_actual_pump_endpoint_hashes_counts_and_cleanup_match_both_arms(self):
        results = []
        samples = ((np.arange(65*320, dtype=np.int64)*71) % 65536 - 32768).astype('<i2')
        framed = samples.tobytes()
        for arm in ('before', 'after'):
            with isolated(arm) as modules:
                gate = FakeGate()
                result = worker.pipeline(parent, modules, gate, np, framed, framed, time.monotonic()+10)
                self.assertEqual(result['status'], 'PASS_PUBLIC_PUMP_ENDPOINT_ONLY')
                self.assertEqual(result['input_queue']['capacity_frames'], 8)
                self.assertFalse(result['input_queue']['reader_alive'])
                self.assertEqual(result['producer_thread'], 'aura-board-raw-pcm')
                self.assertEqual(result['denoised']['calls'], result['consumed_frames'])
                self.assertEqual(result['denoised']['model_hops'], result['consumed_frames']*320//256)
                self.assertTrue(gate.closed)
                results.append((result['endpoint'], result['denoised']['pcm16_sha256'],
                    result['denoised']['float32_sha256'], result['denoised']['samples']))
        self.assertEqual(results[0], results[1])

    def test_raw_eight_frame_overflow_is_failed_not_fake_success(self):
        with isolated('after') as modules, mock.patch.object(parent, 'PacedPublicPcm', BurstSource):
            gate = FakeGate(); framed = bytes(640*80)
            result = worker.pipeline(parent, modules, gate, np, framed, framed, time.monotonic()+10)
            self.assertEqual(result['status'], 'FAILED')
            self.assertEqual(result['error_code'], 'pcm_input_queue_overflow')
            self.assertEqual(result['input_queue']['capacity_frames'], 8)
            self.assertEqual(result['input_queue']['peak_frames'], 8)
            self.assertFalse(result['input_queue']['reader_alive'])
            self.assertTrue(gate.closed)

    def test_deadline_and_classifier_error_stop_owned_source_without_late_success(self):
        for fail, past in ((True, False), (False, True)):
            with isolated('after') as modules:
                gate = FakeGate(fail=fail); framed = bytes(640*80)
                deadline = time.monotonic()-1 if past else time.monotonic()+10
                result = worker.pipeline(parent, modules, gate, np, framed, framed, deadline)
                self.assertEqual(result['status'], 'FAILED')
                self.assertEqual(result['error_code'], 'soft_deadline' if past else 'public_pipeline_failed')
                self.assertFalse(result['input_queue']['reader_alive'])
                self.assertTrue(gate.closed)

    def test_public_wave_requires_exact_sha_format_and_original_padding(self):
        class Wave:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def getnchannels(self): return 1
            def getsampwidth(self): return 2
            def getframerate(self): return 16000
            def getnframes(self): return worker.WAV_SAMPLES
            def getcomptype(self): return 'NONE'
            def readframes(self, n): return b'\x01\0'*n
        with mock.patch.object(worker, 'digest', return_value='bad'), mock.patch.object(worker.wave, 'open') as opened:
            with self.assertRaisesRegex(worker.Refused, 'public_wav_pin'):
                worker.public_pcm(Path('/public/0.wav'))
            opened.assert_not_called()
        with mock.patch.object(worker, 'digest', return_value=worker.WAV_SHA), mock.patch.object(worker.wave, 'open', return_value=Wave()):
            pcm, framed = worker.public_pcm(Path('/public/0.wav'))
            self.assertEqual(len(pcm), 179668)
            self.assertEqual(framed[:len(pcm)], pcm)
            self.assertEqual(framed[len(pcm):], bytes(172+640*70))
            self.assertEqual(len(framed), 640*351)
        bad = Wave(); bad.getframerate = lambda: 48000
        with mock.patch.object(worker, 'digest', return_value=worker.WAV_SHA), mock.patch.object(worker.wave, 'open', return_value=bad):
            with self.assertRaisesRegex(worker.Refused, 'public_wav_format'):
                worker.public_pcm(Path('/public/0.wav'))

    def test_reviewed_priority_restores_existing_and_new_owned_tasks(self):
        class Api:
            PRIO_PROCESS = 0
            def __init__(self): self.values={100:0, 101:5}; self.mutations=[]
            def getpid(self): return 100
            def getpriority(self, _, tid): return self.values[tid]
            def setpriority(self, _, tid, value):
                self.mutations.append((tid,value)); self.values[tid]=value
        api=Api()
        priority=parent.ProbeProcessPriority(-10,api=api,thread_ids=lambda:sorted(api.values))
        with priority:
            self.assertEqual(api.values,{100:-10,101:-10})
            api.values[102]=-10
        self.assertEqual(api.values,{100:0,101:5,102:0})
        self.assertTrue(priority.record['restoration_confirmed'])
        self.assertTrue(all(tid in (100,101,102) for tid,_ in api.mutations))


if __name__ == '__main__': unittest.main(verbosity=2)
