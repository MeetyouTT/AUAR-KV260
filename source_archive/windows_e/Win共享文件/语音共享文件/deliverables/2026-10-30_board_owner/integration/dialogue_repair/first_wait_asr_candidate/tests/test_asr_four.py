"""Offline tiny public resource fixtures and bounded probe orchestration fakes."""
import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


asr = load('public_asr_four_thread', ROOT/'after/board/runtime/audio/board_asr.py')
probe = load('public_asr_abba_probe', ROOT/'probe_asr_abba.py')


class ThreadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.calls = []
        for name, value in {'model.int8.onnx': b'public fixture', 'tokens.txt': b'tokens'}.items():
            (self.root/name).write_bytes(value)
        self.pins = {name: hashlib.sha256((self.root/name).read_bytes()).hexdigest()
                     for name in ('model.int8.onnx', 'tokens.txt')}
    def factory(self, **kwargs): self.calls.append(kwargs); return object()
    def make(self, **kwargs):
        return asr.BoardParaformer(self.root, model_sha256=self.pins['model.int8.onnx'],
            tokens_sha256=self.pins['tokens.txt'], recognizer_factory=self.factory, **kwargs)
    def test_default_two_preserves_exact_inference_parameters(self):
        value = self.make()
        self.assertEqual(self.calls, [dict(paraformer=str(self.root/'model.int8.onnx'),
            tokens=str(self.root/'tokens.txt'), num_threads=2, sample_rate=16000, feature_dim=80,
            decoding_method='greedy_search', provider='cpu')])
        self.assertEqual(value.MAX_SAMPLES, 320000)
    def test_three_and_four_are_explicit_without_coercion(self):
        for threads in (1, 2, 3, 4):
            self.make(num_threads=threads)
            self.assertEqual(self.calls[-1]['num_threads'], threads)
    def test_invalid_threads_refused_before_model_factory(self):
        for value in (True, False, 0, -1, 5, 100, 4., '4', None):
            with self.subTest(value=value), self.assertRaises(ValueError): self.make(num_threads=value)
        self.assertEqual(self.calls, [])
    def test_unchanged_model_and_token_hash_gates_at_four(self):
        for name in self.pins:
            original = (self.root/name).read_bytes()
            (self.root/name).write_bytes(b'changed')
            with self.assertRaises(asr.BoardAsrUnavailable): self.make(num_threads=4)
            (self.root/name).write_bytes(original)
        self.assertEqual(self.calls, [])
    def test_all_transcribe_and_factory_ast_other_than_guard_unchanged(self):
        before = ast.parse((ROOT/'before/board/runtime/audio/board_asr.py').read_bytes())
        after = ast.parse((ROOT/'after/board/runtime/audio/board_asr.py').read_bytes(), feature_version=(3, 9))
        original_class = next(node for node in before.body if isinstance(node, ast.ClassDef) and node.name == 'BoardParaformer')
        changed_class = next(node for node in after.body if isinstance(node, ast.ClassDef) and node.name == 'BoardParaformer')
        init_before = next(node for node in original_class.body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
        init_after = next(node for node in changed_class.body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
        self.assertEqual(ast.dump(init_before.args), ast.dump(init_after.args))
        init_before.body = init_before.body[1:]; init_after.body = init_after.body[1:]
        self.assertEqual(ast.dump(before), ast.dump(after))


def state():
    return dict(ui={'pid': 10, 'birth': 20}, camera={'pid': 30, 'birth': 40},
                memory={'completed': 1}, model_idle=True)


def row(threads, ms, changed=False):
    return dict(threads=threads, asr_ms=ms, transcript_sha256='a'*64,
                warmup_same_transcript=True, background_changed=changed)


class ProbeTests(unittest.TestCase):
    def args(self):
        candidate = ROOT/'after/board/runtime/audio/board_asr.py'
        return ['probe_asr_abba.py', '--boot-id', 'public-boot', '--ui-pid', '10', '--ui-birth', '20',
                '--camera-pid', '30', '--camera-birth', '40', '--candidate', str(candidate),
                '--candidate-sha256', hashlib.sha256(candidate.read_bytes()).hexdigest()]
    def main(self, *, run=False, snapshots=None, slots=None):
        output = io.StringIO()
        with patch.object(sys, 'argv', self.args() + (['--run'] if run else [])), \
             patch.object(probe, 'metadata', side_effect=snapshots or [state()]), \
             patch.object(probe, 'run_slot', side_effect=slots or AssertionError('no model operation allowed')) as start, \
             contextlib.redirect_stdout(output):
            code = probe.main()
        return code, json.loads(output.getvalue()), start
    def test_default_inspect_constructs_no_model_or_child(self):
        code, value, start = self.main()
        self.assertEqual(code, 0); start.assert_not_called()
        self.assertEqual(value['status'], 'INSPECT_ONLY_NO_MODEL_CONSTRUCTED')
        self.assertTrue(value['production_model_also_resident'])
    def test_complete_abba_order_and_pair_summary(self):
        rows = [row(3, 4000), row(4, 3500), row(4, 3600), row(3, 4200)]
        code, value, calls = self.main(run=True, snapshots=[state(), state()], slots=rows)
        self.assertEqual(code, 0)
        self.assertEqual([c.args[1] for c in calls.call_args_list], [3, 4, 4, 3])
        self.assertEqual(value['comparison']['improvement_ms'], 550)
        self.assertFalse(value['comparison']['formal_gui_asr_acceptance'])
    def test_background_change_preserves_all_timings_without_gain_claim(self):
        rows = [row(3, 4000), row(4, 3500, True), row(4, 3600), row(3, 4200)]
        code, value, _ = self.main(run=True, snapshots=[state(), state()], slots=rows)
        self.assertEqual(code, 0)
        self.assertEqual(value['status'], 'CONTAMINATED_NO_GAIN_CLAIM')
        self.assertEqual(value['results'], rows)
        self.assertFalse(value['comparison']['gain_claim_allowed'])
        self.assertNotIn('improvement_ms', value['comparison'])
    def test_changed_outer_memory_counters_also_preserve_data(self):
        after = state(); after['memory']['completed'] += 1
        code, value, _ = self.main(run=True, snapshots=[state(), after],
            slots=[row(3, 4000), row(4, 3500), row(4, 3500), row(3, 4000)])
        self.assertEqual(value['status'], 'CONTAMINATED_NO_GAIN_CLAIM')
        self.assertEqual(len(value['results']), 4)
    def test_busy_slot_does_not_start_next_and_keeps_prior_slot(self):
        code, value, calls = self.main(run=True, snapshots=[state(), state()],
            slots=[row(3, 4000), probe.ProbeRefused('model_or_background_summary_active')])
        self.assertEqual(code, 1)
        self.assertEqual(calls.call_count, 2)
        self.assertEqual(len(value['results']), 1)
        self.assertEqual(value['failure_code'], 'model_or_background_summary_active')
    def test_transcript_difference_never_claims_speedup(self):
        rows = [row(3, 4000), row(4, 3500), row(4, 3500), row(3, 4000)]
        rows[1]['transcript_sha256'] = 'b'*64
        code, value, _ = self.main(run=True, snapshots=[state(), state()], slots=rows)
        self.assertEqual(code, 1)
        self.assertEqual(value['failure_code'], 'public_transcript_changed')
        self.assertEqual(len(value['results']), 4)
        self.assertFalse(value['comparison']['gain_claim_allowed'])
    def test_fixed_error_codes_never_include_arbitrary_exception_message(self):
        self.assertEqual(probe.error_code(RuntimeError('SECRET_DIALOGUE_OR_PCM')), 'unexpected_probe_error')
        self.assertEqual(probe.error_code(probe.ProbeRefused('SECRET_DIALOGUE_OR_PCM')), 'probe_refused')
        self.assertEqual(probe.error_code(probe.ProbeRefused('pause_and_idle_required')), 'pause_and_idle_required')
    def test_slot_uses_metadata_pipe_normal_env_and_waits_for_owned_child(self):
        started = []
        class Child:
            def __init__(self, command, **kwargs):
                started.append((command, kwargs))
                os.write(kwargs['pass_fds'][0], json.dumps(dict(status='PASS', result=row(4, 3500))).encode())
            def wait(self, timeout):
                self.timeout = timeout
                return 0
        with patch.object(sys, 'argv', ['probe', '--run', '--boot-id', 'fixture']), \
             patch.object(probe.subprocess, 'Popen', Child):
            result = probe.run_slot(types.SimpleNamespace(), 4)
        self.assertEqual(result['threads'], 4)
        self.assertNotIn('--run', started[0][0])
        self.assertIn('--result-fd', started[0][0])
        self.assertEqual(started[0][1]['env']['OMP_NUM_THREADS'], '1')
        self.assertEqual(started[0][1]['stdout'], subprocess.DEVNULL)
    def test_timed_out_owned_slot_is_terminated_and_reaped(self):
        children = []
        class Child:
            def __init__(self, *args, **kwargs): self.calls = 0; self.terminated = False; children.append(self)
            def wait(self, timeout):
                self.calls += 1
                if self.calls == 1: raise subprocess.TimeoutExpired('owned fixture', timeout)
                return 0
            def terminate(self): self.terminated = True
        with patch.object(sys, 'argv', ['probe']), patch.object(probe.subprocess, 'Popen', Child):
            with self.assertRaises(subprocess.TimeoutExpired): probe.run_slot(types.SimpleNamespace(), 3)
        self.assertTrue(children[0].terminated)
        self.assertEqual(children[0].calls, 2)
    def test_probe_python39_compatible(self):
        ast.parse((ROOT/'probe_asr_abba.py').read_bytes(), feature_version=(3, 9))


if __name__ == '__main__': unittest.main()
