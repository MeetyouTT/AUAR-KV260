import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import live_checks


def fixture(fault=False, phase='RUNNING'):
    policy = {'enabled': True, 'phase': phase, 'faults': int(fault),
        'attempts': int(fault and phase != 'COOLDOWN'),
        'recoveries': int(fault and phase == 'RUNNING'),
        'probe_successes': 3 if fault and phase == 'RUNNING' else 0, 'required_successes': 3}
    event = {'hardcap_exceeded': 1, 'guard_exceeded': 0, 'native_completed': 1,
             'native_status': 0, 'body_failed': 0}
    return {'camera_error': '', 'detector_error': '', 'observation_age_ms': 50,
        'identity_backend': 'WINDOWS_CPU_SFACE_ORT', 'shadow': None,
        'face_targets': {'ready': True, 'error': '', 'source_age_ms': 100,
            'backend': 'CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN' if phase == 'COOLDOWN' else 'DPU_YUNET_INT8'},
        'dpu_schedule': {'optional': {'yunet': {'overruns': int(fault), 'disabled': phase == 'COOLDOWN'}},
            'yunet_recovery': policy, 'optional_diagnostics': {'fault_events': [event] if fault else []}}}


class Checks(unittest.TestCase):
    def test_clean_state_is_accepted(self): live_checks.validate_state(fixture())

    def test_normal_acceptance_rejects_even_recovered_fault(self):
        with self.assertRaises(AssertionError): live_checks.validate_state(fixture(True))

    def test_declared_injected_cooldown_and_recovered_states(self):
        for phase in ('COOLDOWN', 'PROBATION', 'RUNNING'):
            live_checks.validate_state(fixture(True, phase), injected=True)

    def test_baseline_degraded_state_needs_exact_completed_fault(self):
        value = fixture(True, 'COOLDOWN')
        live_checks.validate_state(value, allow_parent_fallback=True)
        value['dpu_schedule']['optional_diagnostics']['fault_events'][0]['native_status'] = -1
        with self.assertRaises(AssertionError): live_checks.validate_state(value, allow_parent_fallback=True)

    def test_guard_or_unknown_completion_is_rejected(self):
        for key, value in (('guard_exceeded', 1), ('native_completed', 0), ('body_failed', 1)):
            state = fixture(True)
            state['dpu_schedule']['optional_diagnostics']['fault_events'][0][key] = value
            with self.assertRaises(AssertionError): live_checks.validate_state(state, injected=True)

    def test_extra_fault_or_latched_probe_is_rejected(self):
        state = fixture(True)
        state['dpu_schedule']['optional']['yunet']['overruns'] = 2
        with self.assertRaises(AssertionError): live_checks.validate_state(state, injected=True)
        state = fixture(True, 'LATCHED')
        with self.assertRaises(AssertionError): live_checks.validate_state(state, injected=True)

    def test_final_recovery_requires_three_successes_and_real_backend(self):
        state = fixture(True); live_checks.completed_recovery(state)
        state['dpu_schedule']['yunet_recovery']['probe_successes'] = 2
        with self.assertRaises(AssertionError): live_checks.completed_recovery(state)

    def test_camera_stale_identity_or_sface_failure_is_rejected(self):
        for key, value in (('observation_age_ms', 1000), ('identity_backend', 'OTHER')):
            state = fixture(); state[key] = value
            with self.assertRaises(AssertionError): live_checks.validate_state(state)
        state = fixture(); state['dpu_schedule']['optional']['sface'] = {'disabled': True}
        with self.assertRaises(AssertionError): live_checks.validate_state(state)

    def test_units_keep_gil_and_use_exact_new_config(self):
        original = ('[Service]\nEnvironment="AURA_EXPERIMENT_GIL_MS=1"\nWorkingDirectory=/old/aura\n'
            'ExecStart=/usr/bin/python3 /old/runtime_entry.py /old/aura/tools/board_camera_motion.py --config '
            '/home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e-live-134783/board_camera_ui.json\n').encode()
        clean = live_checks.rewrite_unit(original, '/old', '/new')
        injected = live_checks.rewrite_unit(original, '/old', '/new', injected=True)
        self.assertIn(b'/new/runtime_entry.py', clean)
        self.assertNotIn(b'injection_entry', clean)
        self.assertIn(b'/new/injection_entry.py', injected)
        self.assertIn(b'--config /new/board_camera_ui.json', clean)
        self.assertNotIn(b'/old', clean)


class InjectionTests(unittest.TestCase):
    def test_one_time_delay_occurs_only_after_native_completion_and_with_slack(self):
        root = Path(__file__).resolve().parent
        sys.path.insert(0, str(root/'candidate/aura'))
        from board.vision.dpu_vision_schedule import DpuVisionSchedule
        spec = importlib.util.spec_from_file_location('_test_single_injection', root/'injection_entry.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        now = [1000.]
        clock = lambda: now[0]
        def advance(seconds): now[0] += seconds
        schedule = DpuVisionSchedule(clock=clock, yunet_recovery=True)
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(module, 'ROOT', Path(directory)), \
                patch.object(module, 'time', SimpleNamespace(monotonic=clock, sleep=advance)):
            for _ in range(4):
                schedule.next_primary = now[0]+1
                with module.one_delay(schedule, 'yunet') as acquired:
                    self.assertTrue(acquired); advance(.004); schedule.native_completed('yunet')
            self.assertTrue(module.injected)
            state = schedule.health()
            self.assertEqual(state['optional']['yunet']['overruns'], 1)
            self.assertEqual(state['yunet_recovery']['phase'], 'COOLDOWN')
            self.assertTrue(json.loads((Path(directory)/'injected-once.json').read_text())['one_time'])
            advance(10)
            with schedule.primary(now[0]+1): advance(.001)
            for _ in range(3):
                with module.one_delay(schedule, 'yunet') as acquired:
                    self.assertTrue(acquired); advance(.004); schedule.native_completed('yunet')
            self.assertEqual(schedule.health()['yunet_recovery']['recoveries'], 1)
            self.assertEqual(schedule.health()['optional']['yunet']['overruns'], 1)


if __name__ == '__main__': unittest.main()
