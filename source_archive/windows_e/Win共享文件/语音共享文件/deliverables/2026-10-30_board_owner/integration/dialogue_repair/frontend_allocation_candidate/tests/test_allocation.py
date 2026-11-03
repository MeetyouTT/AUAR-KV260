"""Public synthetic PCM only; real Python/VAD/FFT paths, fake model/device IO.

No model constructors, microphone, socket, Store or live service is used.
Run with Python -B -X utf8; numpy is the only external dependency.
"""
import ast
import ctypes
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / 'reference'


def package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    sys.modules[name] = module
    if '.' in name:
        parent, attr = name.rsplit('.', 1)
        setattr(sys.modules[parent], attr, module)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    parent, attr = name.rsplit('.', 1)
    setattr(sys.modules[parent], attr, module)
    return module


for name in ('board', 'board.runtime', 'board.runtime.audio', 'host', 'host.model_service'):
    package(name)
protocol = load('host.model_service.protocol', REF / 'host/model_service/protocol.py')
capture = load('board.runtime.audio.capture', REF / 'board/runtime/audio/capture.py')
vad = load('board.runtime.audio.vad', REF / 'board/runtime/audio/vad.py')
front = load('board.runtime.audio.board_asr_frontend', REF / 'board/runtime/audio/board_asr_frontend.py')
base = load('board.runtime.audio.board_gtcrn_fft', REF / 'board/runtime/audio/board_gtcrn_fft.py')
before = load('board.runtime.audio.automatic_before', ROOT / 'before/board/runtime/audio/automatic_capture.py')
after = load('board.runtime.audio.automatic_after', ROOT / 'after/board/runtime/audio/automatic_capture.py')
reuse_before = load('board.runtime.audio.reuse_before', ROOT / 'before/board/runtime/audio/board_gtcrn_reuse.py')
reuse_after = load('board.runtime.audio.reuse_after', ROOT / 'after/board/runtime/audio/board_gtcrn_reuse.py')


def pcm_frames(count):
    # Includes both PCM16 extremes; the classifier decisions are a separate fixture.
    values = ((np.arange(count * 320, dtype=np.int64) * 787 + 32768) % 65536 - 32768).astype('<i2')
    return [values[i:i + 320].tobytes() for i in range(0, len(values), 320)]


def fragmented(data, widths):
    result, offset, index = [], 0, 0
    while offset < len(data):
        size = widths[index % len(widths)]
        result.append(data[offset:offset + size])
        offset += size
        index += 1
    return result


class Decisions:
    def __init__(self, choices):
        self.choices = iter(choices)
        self.frames = []
        self.closed = False

    def __call__(self, frame):
        if self.closed:
            raise InterruptedError('synthetic cancellation')
        self.frames.append(frame.tobytes())
        return next(self.choices)

    def close(self):
        self.closed = True


def endpoint_trace(module, chunks, choices, max_seconds=20, pre_roll_ms=500):
    classifier = Decisions(choices) if choices is not None else None
    endpoint = module.SpeechEndpoint(max_seconds, frame_classifier=classifier, pre_roll_ms=pre_roll_ms)
    events, states, result = [], [], None
    accept = endpoint.vad.accept

    def observed(samples):
        emitted = accept(samples)
        events.extend((event.kind, event.duration_ms,
                       event.audio.tobytes() if event.audio is not None else None) for event in emitted)
        return emitted

    endpoint.vad.accept = observed
    for chunk in chunks:
        result = endpoint.feed(chunk)
        states.append((endpoint.active, endpoint.done, endpoint.total_samples,
                       endpoint.speech_samples, endpoint.start_sample, bytes(endpoint.pending),
                       endpoint.prefix, tuple(endpoint.ring)))
        if result is not None:
            break
    return endpoint, result, events, states, classifier.frames if classifier else None


class ManualTimer:
    def __init__(self, *args, **kwargs):
        self.started = self.cancelled = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True


class FakeProcess:
    def __init__(self, data):
        self.stdout = io.BytesIO(data)

    def wait(self, timeout=None):
        return 0

    def poll(self):
        return 0


def fake_capture(module, classifier):
    value = module.AutomaticMcp01Capture.__new__(module.AutomaticMcp01Capture)
    capture.Mcp01Capture.__init__(value, lambda: False, clock=lambda: 123.456,
                                 process_factory=lambda *a, **kw: (_ for _ in ()).throw(AssertionError('No devices')))
    value._reset_endpoint_diagnostics()
    value.endpoint = module.SpeechEndpoint(20, frame_classifier=classifier, pre_roll_ms=500)
    value.input_ready = False
    return value


class EndpointTests(unittest.TestCase):
    def test_aligned_fragmented_batched_pcm_and_endpoint_sequence_equal(self):
        choices = [False] * 30 + [True] * 20 + [False] * 40
        frames = pcm_frames(len(choices))
        data = b''.join(frames) + b'\x01'
        for widths in ((640,), (1, 639, 321, 1279, 3, 257), (len(data),)):
            with self.subTest(widths=widths):
                chunks = fragmented(data, widths)
                a = endpoint_trace(before, chunks, choices)
                b = endpoint_trace(after, chunks, choices)
                self.assertEqual(a[1:], b[1:])
                self.assertEqual(b[1], b''.join(frames[5:85]))
                self.assertEqual([e[0] for e in b[2]], ['speech_start', 'speech_end'])
                self.assertEqual(b[0].start_sample, 5 * 320)
                with self.assertRaises(ValueError):
                    b[0].feed(b'')

    def test_false_onset_silence_and_max_duration_equal(self):
        cases = [([False] * 120, 20),
                 ([False] * 10 + [True] * 8 + [False] * 8 + [True] * 12 + [False] * 40, 20),
                 ([True] * 100, 1)]
        for choices, limit in cases:
            for pre_roll in (200, 500):
                with self.subTest(limit=limit, pre_roll=pre_roll, length=len(choices)):
                    chunks = [b''] + pcm_frames(len(choices))
                    a = endpoint_trace(before, chunks, choices, limit, pre_roll)
                    b = endpoint_trace(after, chunks, choices, limit, pre_roll)
                    self.assertEqual(a[1:], b[1:])
                    self.assertEqual(vars(a[0].config), vars(b[0].config))
                    if b[1] is not None:
                        self.assertLessEqual(len(b[1]), limit * 32000)

    def test_energy_classifier_path_equal(self):
        data = [bytes(640)] * 15 + [b'\xe8\x03' * 320] * 20 + [bytes(640)] * 40
        a = endpoint_trace(before, data, None)
        b = endpoint_trace(after, data, None)
        self.assertEqual(a[1:], b[1:])
        self.assertIsNotNone(b[1])

    def test_only_empty_pending_exact_immutable_640_bytes_is_reused(self):
        raw = pcm_frames(1)[0]
        endpoint = after.SpeechEndpoint(frame_classifier=lambda _: False)
        endpoint.feed(raw)
        self.assertIs(endpoint.ring[-1], raw)
        for maker in (bytearray, memoryview, lambda b: type('BytesSubclass', (bytes,), {})(b)):
            with self.subTest(maker=maker):
                mutable = bytearray(raw)
                value = memoryview(mutable) if maker is memoryview else maker(raw)
                e = after.SpeechEndpoint(frame_classifier=lambda _: False)
                e.feed(value)
                self.assertIs(type(e.ring[-1]), bytes)
                self.assertIsNot(e.ring[-1], value)
                mutable[:] = bytes(640)
                if isinstance(value, bytearray):
                    value[:] = bytes(640)
                self.assertEqual(e.ring[-1], raw)
        e = after.SpeechEndpoint(frame_classifier=lambda _: False)
        e.feed(raw[:1]); e.feed(raw)
        self.assertEqual(e.ring[-1], raw[:1] + raw[:-1])
        self.assertEqual(bytes(e.pending), raw[-1:])
        self.assertIsNot(e.ring[-1], raw)

    def test_full_capture_ready_audio_ref_and_offset_equal(self):
        choices = [False] * 30 + [True] * 20 + [False] * 40
        data = b''.join(pcm_frames(len(choices)))
        results = []
        for module in (before, after):
            classifier = Decisions(choices)
            value = fake_capture(module, classifier)
            with mock.patch.object(module.threading, 'Timer', ManualTimer):
                value._read(FakeProcess(data), io.BytesIO(), 'public-capture', 7, 10000)
            self.assertEqual(value.state, 'READY')
            self.assertTrue(classifier.closed)
            self.assertTrue(value._timer.cancelled)
            result = value.take()
            self.assertEqual(value.state, 'IDLE')
            self.assertEqual(result.started_mono_ms, 10100)
            self.assertEqual(result.audio.first_sample_index, 0)
            self.assertEqual(result.audio.sample_count, 80 * 320)
            results.append((result.pcm, result.metadata(), result.audio))
        self.assertEqual(results[0], results[1])

    def test_cancel_during_classifier_cannot_publish_ready_or_late_audio(self):
        for module in (before, after):
            classifier = Decisions([True] * 100)
            value = fake_capture(module, classifier)

            def cancel_in_frame(frame):
                value.cancel()
                return classifier(frame)

            value.endpoint.vad.frame_classifier = cancel_in_frame
            value._read(FakeProcess(pcm_frames(1)[0]), io.BytesIO(), 'public-cancel', 8, 10000)
            self.assertTrue(classifier.closed)
            self.assertEqual(value.state, 'CANCELLED')
            self.assertIsNone(value._result)
            with self.assertRaises(RuntimeError):
                value.take()
            fresh = module.SpeechEndpoint(frame_classifier=lambda _: False)
            self.assertIsNone(fresh.feed(pcm_frames(1)[0]))
            self.assertFalse(fresh.active)


class FakeBinding:
    def __init__(self):
        self.inputs = {}
        self.outputs = {}

    def bind_cpu_input(self, name, value):
        self.inputs[name] = value

    def bind_output(self, name, *, device_type, device_id, element_type, shape, buffer_ptr):
        assert device_type == 'cpu' and device_id == 0 and element_type is np.float32
        backing = (ctypes.c_float * math.prod(shape)).from_address(buffer_ptr)
        self.outputs[name] = np.ctypeslib.as_array(backing).reshape(shape)


class FakeSession:
    input_names = ['mix', 'conv_cache', 'tra_cache', 'inter_cache']
    output_names = ['enh', 'conv_cache_out', 'tra_cache_out', 'inter_cache_out']
    shapes = [(1, 2), (1, 3), (1, 4)]

    def __init__(self):
        self.trace = []
        self.bindings = []
        self.binding_order = []

    def get_outputs(self):
        return [types.SimpleNamespace(shape=s, type='tensor(float)')
                for s in [(1, 257, 1, 2)] + self.shapes]

    def io_binding(self):
        value = FakeBinding(); self.bindings.append(value)
        return value

    def run(self, names, inputs):
        self.trace.append(tuple(inputs[n].tobytes() for n in self.input_names))
        # Deterministic fake recurrence exercises real FFT/OLA and ping-pong;
        # this is not GTCRN model execution or model-output acceptance.
        enhanced = inputs['mix'] * np.float32(.75) + inputs['conv_cache'].flat[0] * np.float32(.001)
        return [enhanced] + [inputs[n] + np.float32(.03125) for n in self.input_names[1:]]

    def run_with_iobinding(self, binding):
        self.binding_order.append(self.bindings.index(binding) % 2)
        results = self.run(self.output_names, binding.inputs)
        for name, value in zip(self.output_names, results):
            binding.outputs[name][:] = value


def denoiser(module, *, reuse=True, binding=True):
    cls = module.ReuseFftGtcrnDenoiser
    value = cls.__new__(cls)
    value.np, value.profile = np, True
    value.buffer_reuse, value.use_io_binding = reuse, binding
    value.session = FakeSession()
    value.input_names, value.output_names = FakeSession.input_names, FakeSession.output_names
    value.state_shapes = FakeSession.shapes
    hann = np.asarray([.5 - .5 * math.cos(2 * math.pi * i / 512) for i in range(512)], dtype=np.float32)
    value.window = np.sqrt(hann)
    value.reset()
    return value


def pcm16(values):
    return np.rint(values * 32768).clip(-32768, 32767).astype('<i2').tobytes()


class DenoiserTests(unittest.TestCase):
    def test_real_fft_hop_sequences_pcm_and_flush_equal_all_modes(self):
        rng = np.random.default_rng(93017)
        source = rng.uniform(-1, 1, 7133).astype(np.float32)
        for reuse in (False, True):
            for binding in (False, True):
                for widths in ((320,), (1, 255, 0, 256, 17, 1024, 63)):
                    with self.subTest(reuse=reuse, binding=binding, widths=widths):
                        a, b = [denoiser(m, reuse=reuse, binding=binding) for m in (reuse_before, reuse_after)]
                        position = index = 0
                        total = 0
                        while position < len(source):
                            size = widths[index % len(widths)]; index += 1
                            chunk = source[position:position + size]; position += len(chunk)
                            x, y = a(chunk).samples, b(chunk).samples
                            self.assertEqual(x.tobytes(), y.tobytes())
                            self.assertEqual(pcm16(x), pcm16(y))
                            self.assertEqual(a.last_timing['hops'], b.last_timing['hops'])
                            self.assertEqual(a.pending.tobytes(), b.pending.tobytes())
                            total += len(y)
                        x, y = a.flush().samples, b.flush().samples
                        self.assertEqual(x.tobytes(), y.tobytes())
                        self.assertEqual(pcm16(x), pcm16(y))
                        self.assertEqual(total + len(y), len(source))
                        self.assertEqual(a.session.trace, b.session.trace)
                        self.assertEqual(a.session.binding_order, b.session.binding_order)
                        self.assertEqual((b.total_input, b.total_output, b.started), (0, 0, False))
                        self.assertEqual(len(b.flush().samples), 0)

    def test_single_double_and_empty_consume_order_and_identity(self):
        for hops in (0, 1, 2, 4):
            with self.subTest(hops=hops):
                value = denoiser(reuse_after)
                pending = np.arange(hops * 256 + 7, dtype=np.float32)
                value.pending = pending
                returned = []

                def hop(samples):
                    result = samples.copy(); returned.append(result); return result

                value._hop = hop
                output = value._consume()
                self.assertEqual(output.tobytes(), pending[:hops * 256].tobytes())
                self.assertEqual(value.pending.tobytes(), pending[hops * 256:].tobytes())
                if hops == 1:
                    self.assertIs(output, returned[0])
                elif hops > 1:
                    self.assertTrue(all(output is not r and not np.shares_memory(output, r) for r in returned))
                if hops:
                    self.assertFalse(np.shares_memory(value.pending, pending))
        value = denoiser(reuse_after)
        value.pending = np.zeros(512, dtype=np.float32)
        results = [np.empty(0, dtype=np.float32), np.arange(256, dtype=np.float32)]
        value._hop = mock.Mock(side_effect=results)
        output = value._consume()
        self.assertEqual(output.tobytes(), results[1].tobytes())
        self.assertIsNot(output, results[1])  # first-hop empty output still counts as one hop

    def test_real_outputs_do_not_alias_state_later_calls_or_reset(self):
        for binding in (False, True):
            with self.subTest(binding=binding):
                value = denoiser(reuse_after, binding=binding)
                preserved = []
                hop_counts = []
                for number in range(12):
                    output = value(np.full(320, (number - 6) / 10, dtype=np.float32)).samples
                    hop_counts.append(value.last_timing['hops'])
                    state_arrays = [value.ola, value.analysis, value.pending, value._spectrum] + value.states
                    if binding:
                        state_arrays += [value._enhanced] + [s for group in value._state_sets for s in group]
                    self.assertTrue(all(not np.shares_memory(output, state) for state in state_arrays))
                    self.assertTrue(all(not np.shares_memory(output, old) for old, _ in preserved))
                    preserved.append((output, output.tobytes()))
                    self.assertTrue(all(old.tobytes() == snapshot for old, snapshot in preserved))
                self.assertEqual(hop_counts, [1, 1, 1, 2] * 3)
                if binding:
                    self.assertEqual(value.session.binding_order, [0, 1] * 7 + [0])
                value.flush(); value.reset()
                self.assertTrue(all(old.tobytes() == snapshot for old, snapshot in preserved))

    def test_reset_repeats_output_and_external_mutation_cannot_change_state(self):
        signal = np.linspace(-.8, .8, 960, dtype=np.float32)
        a, b = denoiser(reuse_after), denoiser(reuse_after)
        a(signal[:320]); b(signal[:320])
        owned = a(signal[320:640]).samples
        control = b(signal[320:640]).samples
        self.assertEqual(owned.tobytes(), control.tobytes())
        owned[:] = 123
        self.assertEqual(a(signal[640:]).samples.tobytes(), b(signal[640:]).samples.tobytes())
        a.reset(); b.reset()
        self.assertEqual(a(signal).samples.tobytes(), b(signal).samples.tobytes())


class SourceBoundaryTests(unittest.TestCase):
    def test_exact_before_reference_pins_and_external_sources_unchanged(self):
        pins = json.loads((ROOT / 'SOURCE_PINS.json').read_text('utf-8'))
        for component, row in pins['sources'].items():
            branch = 'before' if component in pins['changes'] else 'reference'
            self.assertEqual(hashlib.sha256((ROOT / branch / component).read_bytes()).hexdigest(), row['sha256'])
            self.assertEqual(hashlib.sha256(Path(row['source']).read_bytes()).hexdigest(), row['sha256'])
        reuse_before.verify_baseline(); reuse_after.verify_baseline()

    def test_only_feed_and_consume_change_other_code_including_cancel_unchanged(self):
        component = 'board/runtime/audio/automatic_capture.py'
        trees = [ast.parse((ROOT / branch / component).read_text('utf-8')) for branch in ('before', 'after')]
        for tree in trees:
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'SpeechEndpoint')
            cls.body = [n for n in cls.body if not isinstance(n, ast.FunctionDef) or n.name != 'feed']
        self.assertEqual(ast.dump(trees[0]), ast.dump(trees[1]))
        component = 'board/runtime/audio/board_gtcrn_reuse.py'
        trees = [ast.parse((ROOT / branch / component).read_text('utf-8')) for branch in ('before', 'after')]
        cls = next(n for n in trees[1].body if isinstance(n, ast.ClassDef) and n.name == 'ReuseFftGtcrnDenoiser')
        consume = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_consume')
        cls.body.remove(consume)
        self.assertEqual(ast.dump(trees[0]), ast.dump(trees[1]))
        base_tree = ast.parse((REF / 'board/runtime/audio/board_gtcrn_fft.py').read_text('utf-8'))
        base_class = next(n for n in base_tree.body if isinstance(n, ast.ClassDef) and n.name == 'FftGtcrnDenoiser')
        base_consume = next(n for n in base_class.body if isinstance(n, ast.FunctionDef) and n.name == '_consume')
        consume.body.pop(-2)  # only the single-chunk direct-return branch is new
        self.assertEqual(ast.dump(consume), ast.dump(base_consume))


if __name__ == '__main__':
    unittest.main(verbosity=2)
