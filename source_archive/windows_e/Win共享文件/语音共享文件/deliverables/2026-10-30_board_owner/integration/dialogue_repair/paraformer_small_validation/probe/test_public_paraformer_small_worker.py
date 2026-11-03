"""Fake runtime and temporary public fixture tests; no installed models needed."""
import ast
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('public_paraformer_small_worker', ROOT/'public_paraformer_small_worker.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class FakeClock:
    def __init__(self):
        self.wall, self.cpu = 0.0, 0.0
    def advance(self, wall, cpu):
        self.wall += wall
        self.cpu += cpu


class FakeArray:
    def __init__(self, pcm): self.pcm = pcm
    def astype(self, dtype): return self
    def __truediv__(self, divisor):
        assert divisor == 32768.0
        return self


class FakeNumpy:
    float32 = object()
    @staticmethod
    def frombuffer(pcm, dtype):
        assert dtype == '<i2'
        return FakeArray(pcm)


class FakeRecognizer:
    def __init__(self, clock, text='你好'):
        self.clock, self.text, self.decodes, self.accepted = clock, text, 0, []
    def create_stream(self):
        def accept(rate, samples):
            self.accepted.append((rate, samples.pcm))
        return types.SimpleNamespace(result=types.SimpleNamespace(text=self.text), accept_waveform=accept)
    def decode_stream(self, stream):
        self.decodes += 1
        self.clock.advance(0.5, 0.7)
    def transcribe(self, pcm, *, sample_rate, deadline, cancelled):
        assert sample_rate == 16000 and not cancelled()
        self.decodes += 1
        self.clock.advance(0.5, 0.7)
        return self.text


def namespace(engine='paraformer_small', **kwargs):
    args = dict(engine=engine, threads=3, rounds=2, max_seconds=170,
                manifest_sha256=w.MANIFEST_SHA, paraformer_source=None)
    args.update(kwargs)
    return types.SimpleNamespace(**args)


@contextmanager
def fixtures():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        helper = w.load_helper(ROOT/'public_quality_helper.py')
        helper.WAV_ROOT = root
        cases = []
        for case_id, text, _ in helper.CASES:
            path = root/(case_id+'.wav')
            with wave.open(str(path), 'wb') as f:
                f.setparams((1, 2, 16000, 0, 'NONE', ''))
                f.writeframes(b'\x01\x00' * 160)
            cases.append(dict(id=case_id, reference_text=text, samples=160, rate=16000,
                              wav_path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        manifest = dict(source_texts_sha256=helper.TEXT_SET_SHA, public_synthetic=True,
                        intended_not_human_verified=True, cases=cases)
        yield root, helper, manifest


class Tests(unittest.TestCase):
    def test_python39_and_original_helper_frozen(self):
        ast.parse((ROOT/'public_paraformer_small_worker.py').read_text('utf-8'), feature_version=(3, 9))
        self.assertEqual(hashlib.sha256((ROOT/'public_quality_helper.py').read_bytes()).hexdigest(), w.HELPER_SHA)

    def test_helper_pin_is_checked_before_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'helper.py'
            p.write_text('raise RuntimeError("should not execute")', encoding='utf-8')
            with self.assertRaisesRegex(w.Refused, '^HELPER_PIN_MISMATCH$'): w.load_helper(p)

    def test_cli_constraints_and_manifest_pin(self):
        base = ['--engine', 'paraformer_small', '--manifest', '/public/manifest.json',
                '--manifest-sha256', w.MANIFEST_SHA, '--model-dir', '/model', '--external-deadline-managed']
        self.assertEqual(w.parse_args(base).threads, 3)
        for extra in (['--threads', '4'], ['--rounds', '1'], ['--max-seconds', '171'], ['--threads', '2'],
                      ['--paraformer-source', '/adapter.py'], ['--manifest-sha256', '0'*64]):
            with self.subTest(extra=extra), self.assertRaises(w.Refused): w.parse_args(base+extra)
        with self.assertRaises(w.Refused): w.parse_args(base[:-1])

    def test_strict_public_manifest_and_sample_limit(self):
        with fixtures() as (_, helper, manifest):
            self.assertEqual(len(helper.validate_manifest(manifest)), 8)
            original = json.dumps(manifest)
            edits = [('public_synthetic', False), ('source_texts_sha256', '0'*64)]
            for key, value in edits:
                broken = json.loads(original); broken[key] = value
                with self.subTest(key=key), self.assertRaises(helper.Refused): helper.validate_manifest(broken)
            for key, value in [('samples', 320001), ('rate', 24000), ('reference_text', '私人句子'),
                               ('sha256', '0'*64)]:
                broken = json.loads(original); broken['cases'][0][key] = value
                with self.subTest(key=key), self.assertRaises(helper.Refused): helper.validate_manifest(broken)
            broken = json.loads(original); broken['cases'][1]['wav_path'] = broken['cases'][0]['wav_path']
            with self.assertRaisesRegex(helper.Refused, 'WAV_PATH_REUSED'): helper.validate_manifest(broken)

    def test_prepare_pins_model_and_manifests_before_runtime(self):
        with fixtures() as (root, helper, manifest):
            m = root/'manifest.json'; m.write_text(json.dumps(manifest), encoding='utf-8')
            model = root/'model'; model.mkdir()
            (model/'model.int8.onnx').write_bytes(b'public fake model')
            (model/'tokens.txt').write_bytes(b'public fake token')
            pins = tuple(hashlib.sha256((model/name).read_bytes()).hexdigest() for name in ('model.int8.onnx', 'tokens.txt'))
            args = namespace(manifest=str(m), model_dir=str(model))
            with patch.object(w, 'MANIFEST_SHA', hashlib.sha256(m.read_bytes()).hexdigest()), patch.dict(w.PINS, paraformer_small=pins):
                p = w.prepare(args, helper)
                self.assertEqual(len(p['audio']), 8)
                (model/'tokens.txt').write_bytes(b'changed')
                with self.assertRaisesRegex(helper.Refused, 'MODEL_PIN_MISMATCH'): w.prepare(args, helper)
                m.write_text('{}', encoding='utf-8')
                with self.assertRaisesRegex(helper.Refused, 'PIN_MISMATCH'): w.prepare(args, helper)

    def test_paraformer_small_factory_args_and_load_separated(self):
        clock, calls = FakeClock(), []
        def factory(**kwargs):
            calls.append(kwargs); clock.advance(2.0, 3.0)
            return FakeRecognizer(clock)
        sherpa = types.SimpleNamespace(__version__='1.13.8', OfflineRecognizer=types.SimpleNamespace(from_paraformer=factory))
        rec, stats = w.construct(namespace(), dict(directory=Path('/model')), sherpa,
                                 wall=lambda: clock.wall, cpu=lambda: clock.cpu)
        self.assertEqual(calls, [dict(paraformer=str(Path('/model/model.int8.onnx')), tokens=str(Path('/model/tokens.txt')),
            num_threads=3, sample_rate=16000, feature_dim=80,
            decoding_method='greedy_search', provider='cpu')])
        self.assertEqual(stats['load_wall_ms'], 2000)
        self.assertEqual(stats['load_cpu_ms'], 3000)
        _, _, wall_ms, cpu_ms = w.decode_case('paraformer_small', rec, FakeNumpy, b'\x01\x00', 10,
            clock=lambda: clock.wall, wall=lambda: clock.wall, cpu=lambda: clock.cpu)
        self.assertEqual((wall_ms, cpu_ms), (500, 700))
        self.assertEqual(rec.accepted, [(16000, b'\x01\x00')])

    def test_baseline_original_adapter_contract_and_duplicate_hash_overhead(self):
        clock, calls = FakeClock(), []
        def factory(**kwargs):
            calls.append(kwargs); clock.advance(2, 3)
            return FakeRecognizer(clock)
        def adapter(directory, *, model_sha256, tokens_sha256, num_threads, recognizer_factory):
            self.assertEqual((model_sha256, tokens_sha256), w.PINS['paraformer'])
            clock.advance(0.4, 0.3)  # simulated original adapter's repeated pin verification
            return recognizer_factory(paraformer=str(Path(directory)/'model.int8.onnx'),
                tokens=str(Path(directory)/'tokens.txt'), num_threads=num_threads,
                sample_rate=16000, feature_dim=80, decoding_method='greedy_search', provider='cpu')
        sherpa = types.SimpleNamespace(__version__='1.13.8', OfflineRecognizer=types.SimpleNamespace(from_paraformer=factory))
        _, stats = w.construct(namespace('paraformer'), dict(directory=Path('/model'), adapter=adapter), sherpa,
                               wall=lambda: clock.wall, cpu=lambda: clock.cpu)
        self.assertEqual(stats['load_wall_ms'], 2000)
        self.assertEqual(stats['constructor_nonfactory_wall_ms'], 400)
        self.assertEqual(stats['constructor_nonfactory_cpu_ms'], 300)
        self.assertEqual(stats['recognizer_constructions'], 1)
        self.assertEqual(calls[0]['num_threads'], 3)

    def test_sherpa_version_rejected_before_factory(self):
        with self.assertRaisesRegex(w.Refused, 'SHERPA_VERSION_MISMATCH'):
            w.construct(namespace(), {}, types.SimpleNamespace(__version__='wrong'))

    def test_rounds_have_no_hidden_warmup_and_cpu_sums(self):
        with fixtures() as (_, helper, manifest):
            prepared = dict(audio=helper.validate_manifest(manifest))
            clock = FakeClock(); rec = FakeRecognizer(clock, ' 你好 ')
            rows = w.evaluate(namespace(rounds=2), prepared, helper, rec, FakeNumpy, 20,
                clock=lambda: clock.wall, wall=lambda: clock.wall, cpu=lambda: clock.cpu)
            self.assertEqual(rec.decodes, 16)
            self.assertEqual(sum(r['first_model_decode'] for r in rows), 1)
            self.assertEqual(sum(r['repeated_input_round'] for r in rows), 8)
            self.assertEqual(sum(r['offline_decode_wall_ms'] for r in rows), 8000)
            self.assertEqual(sum(r['offline_decode_cpu_ms'] for r in rows), 11200)
            self.assertNotEqual(rows[0]['raw_hypothesis'], rows[0]['hypothesis'])

    def test_cancellation_and_deadline_before_and_after_decode(self):
        clock = FakeClock(); rec = FakeRecognizer(clock)
        for cancel, deadline, code in [(lambda: True, 10, 'CANCELLED'), (lambda: False, 0, 'SOFT_DEADLINE_EXCEEDED')]:
            with self.subTest(code=code), self.assertRaisesRegex(w.Refused, code):
                w.decode_case('paraformer_small', rec, FakeNumpy, b'\x01\x00', deadline, cancelled=cancel,
                              clock=lambda: clock.wall, wall=lambda: clock.wall, cpu=lambda: clock.cpu)
        self.assertEqual(rec.decodes, 0)
        with self.assertRaisesRegex(w.Refused, 'SOFT_DEADLINE_EXCEEDED'):
            w.decode_case('paraformer_small', rec, FakeNumpy, b'\x01\x00', 0.1,
                          clock=lambda: clock.wall, wall=lambda: clock.wall, cpu=lambda: clock.cpu)
        self.assertEqual(rec.decodes, 1)
        with self.assertRaisesRegex(w.Refused, 'CANCELLED'):
            w.decode_case('paraformer_small', rec, FakeNumpy, b'\x01\x00', 10, cancelled=lambda: rec.decodes > 1,
                          clock=lambda: clock.wall, wall=lambda: clock.wall, cpu=lambda: clock.cpu)

    def test_pcm_limit_and_hypothesis_type(self):
        clock = FakeClock(); rec = FakeRecognizer(clock)
        for pcm in (b'', b'a', b'\0'*640002, bytearray(b'\1\0')):
            with self.subTest(length=len(pcm)), self.assertRaisesRegex(w.Refused, 'PCM_INVALID'):
                w.decode_case('paraformer_small', rec, FakeNumpy, pcm, 10, clock=lambda: clock.wall)
        self.assertEqual(rec.decodes, 0)
        rec.text = None
        with self.assertRaisesRegex(w.Refused, 'HYPOTHESIS_INVALID'):
            w.decode_case('paraformer_small', rec, FakeNumpy, b'\1\0', 10, clock=lambda: clock.wall)


if __name__ == '__main__':
    unittest.main(verbosity=2)
