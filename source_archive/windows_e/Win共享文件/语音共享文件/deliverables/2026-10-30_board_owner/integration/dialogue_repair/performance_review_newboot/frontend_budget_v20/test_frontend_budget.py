"""Fake-session policy and offline screening tests. No ONNX model is loaded."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PROBE = load('public_frontend_budget_under_test', HERE/'public_frontend_budget.py')
COMPARE = load('compare_frontend_abba_under_test', HERE/'compare_frontend_abba.py')


class Options:
    def __init__(self, threads):
        self.intra_op_num_threads = threads
        self.inter_op_num_threads = 1
        self.entries = {}

    def add_session_config_entry(self, key, value):
        self.entries[key] = value

    def get_session_config_entry(self, key):
        return self.entries[key]


class FakeOrt:
    def __init__(self):
        self.calls = []
        self.InferenceSession = self.create

    def create(self, path, *, sess_options, providers):
        self.calls.append(dict(path=path, options=sess_options, providers=providers))
        return SimpleNamespace(get_session_options=lambda:sess_options, get_providers=lambda:providers)


class PolicyTests(unittest.TestCase):
    def test_baseline_keeps_original_one_thread_default(self):
        ort = FakeOrt()
        original = ort.InferenceSession
        options = Options(1)
        with PROBE.selected_session_policy(ort, Path('gtcrn_simple.onnx'), 'baseline_1') as record:
            ort.InferenceSession('gtcrn_simple.onnx', sess_options=options, providers=['CPUExecutionProvider'])
        self.assertIs(ort.InferenceSession, original)
        self.assertEqual(options.entries, {})
        self.assertEqual(record['sessions_created'], 1)

    def test_dual_thread_disables_only_intra_op_spinning(self):
        ort = FakeOrt()
        options = Options(2)
        with PROBE.selected_session_policy(ort, Path('gtcrn_simple.onnx'), 'dual_nospin'):
            ort.InferenceSession('gtcrn_simple.onnx', sess_options=options, providers=['CPUExecutionProvider'])
        self.assertEqual(options.entries, {'session.intra_op.allow_spinning':'0'})
        self.assertEqual(options.inter_op_num_threads, 1)

    def test_other_model_refused_and_constructor_restored(self):
        ort = FakeOrt()
        original = ort.InferenceSession
        with self.assertRaises(ValueError):
            with PROBE.selected_session_policy(ort, Path('gtcrn_simple.onnx'), 'dual_nospin'):
                ort.InferenceSession('other.onnx', sess_options=Options(2), providers=['CPUExecutionProvider'])
        self.assertIs(ort.InferenceSession, original)
        self.assertEqual(ort.calls, [])

    def test_second_session_refused(self):
        ort = FakeOrt()
        with self.assertRaises(ValueError):
            with PROBE.selected_session_policy(ort, Path('gtcrn_simple.onnx'), 'dual_nospin'):
                ort.InferenceSession('gtcrn_simple.onnx', sess_options=Options(2), providers=['CPUExecutionProvider'])
                ort.InferenceSession('gtcrn_simple.onnx', sess_options=Options(2), providers=['CPUExecutionProvider'])
        self.assertEqual(len(ort.calls), 1)

    def test_empty_policy_is_not_a_successful_trial(self):
        ort = FakeOrt()
        original = ort.InferenceSession
        with self.assertRaises(ValueError):
            with PROBE.selected_session_policy(ort, Path('gtcrn_simple.onnx'), 'baseline_1'):
                pass
        self.assertIs(ort.InferenceSession, original)


def records():
    rows = []
    owners = {role: COMPARE.current.baseline()[role] for role in ('supervisor', 'gtk', 'camera')}
    guard = dict(owners=owners, capture_stats=dict(armed=0, speech_starts=0, submitted=0),
                 memory_completed=0, memory_discarded=0)
    for slot, mode in (('A1','baseline_1'),('B1','dual_nospin'),('B2','dual_nospin'),('A2','baseline_1')):
        trial = dict(frames=351, model_hops=438, output_samples=111872,
            output_float32_sha256='float', output_pcm16_sha256='pcm', decision_sha256='vad', decision_bytes_hex='00',
            gate_wall_ms=dict(mean=20. if mode=='baseline_1' else 15.),
            gate_process_cpu_ms=dict(mean=18. if mode=='baseline_1' else 21.),
            frame_windows=dict(windows_50_frames=[dict(count=50,mean=15.)]))
        owner = dict(boot_id='boot', ui_pid=1, camera_pid=2)
        rows.append(dict(status='PASS_PUBLIC_SLOT', slot=slot, mode=mode,
            startup_sha256=COMPARE.current.STARTUP_SHA,source_wav_sha256='public-wav',before=owner,after=dict(owner),
            source_mapping_sha256=COMPARE.current.MAPPING_SHA,source_components_verified=380,
            live_guard_before=copy.deepcopy(guard),live_guard_after=copy.deepcopy(guard),
            priority=dict(restoration_confirmed=True),runtime=dict(versions={'ort':'1.17.3'}),
            throughput=[copy.deepcopy(trial),copy.deepcopy(trial)],
            paced=dict(endpoint=dict(start_sample=0,captured_samples=100,original_pcm_sha256='source',
                decision_sha256='vad',end_total_samples=100),denoised=dict(float32_sha256='float'),
                input_queue=dict(capacity_frames=8,error='',peak_frames=4,queue_max_ms=70.))))
    return rows


class ScreeningTests(unittest.TestCase):
    def test_complete_gain_is_only_eligible_for_live_validation(self):
        result = COMPARE.compare(records())
        self.assertEqual(result['status'], 'ELIGIBLE_FOR_CONTROLLED_LIVE_VALIDATION')
        self.assertFalse(result['production_change_authorized'])
        self.assertFalse(result['physical_dialogue_accepted'])

    def test_incomplete_or_failed_slots_block(self):
        self.assertEqual(COMPARE.compare(records()[:2])['status'], 'INCOMPLETE_DO_NOT_DEPLOY')
        rows = records()
        rows[1]['status'] = 'FAILED'
        self.assertEqual(COMPARE.compare(rows)['status'], 'FAILED_SLOT_DO_NOT_DEPLOY')

    def test_pcm_or_vad_change_blocks(self):
        rows = records()
        rows[1]['throughput'][0]['decision_sha256'] = 'changed'
        self.assertEqual(COMPARE.compare(rows)['status'], 'DO_NOT_DEPLOY')

    def test_total_cpu_increase_blocks_even_with_fast_wall(self):
        rows = records()
        for row in rows[1:3]:
            for trial in row['throughput']:
                trial['gate_process_cpu_ms']['mean'] = 30.
        self.assertFalse(COMPARE.compare(rows)['checks']['total_process_cpu_budget'])

    def test_eight_frame_capacity_has_to_retain_headroom(self):
        rows = records()
        rows[1]['paced']['input_queue']['peak_frames'] = 8
        self.assertFalse(COMPARE.compare(rows)['checks']['paced_raw8_headroom'])


if __name__ == '__main__':
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    print(json.dumps(dict(status='PASS' if result.wasSuccessful() else 'FAIL', tests_run=result.testsRun,
        errors=len(result.errors), failures=len(result.failures), results=stream.getvalue(),
        model_loaded=False, board_contacted=False)))
    raise SystemExit(0 if result.wasSuccessful() else 1)
