"""Meaningful failure cases for the offline evidence gate; no model/device use."""
import copy
import math
import unittest
import subprocess
import sys
from pathlib import Path
from evaluate_preflight import evaluate
from prepare_sources import PINS


def fixture():
    def row(mode):
        return {'iterations_completed': 200, 'closed_cleanly': True, 'behavior_verified': True,
                'observer_complete': True if mode == 'on' else None,
                'observer_failures': 0 if mode == 'on' else None,
                'observer_schema': 'aura-face-freshness-light-1' if mode == 'on' else None,
                'internal_attempt_wall_or_cpu_collected': False if mode == 'on' else None,
                'events_before_measurement': 16 if mode == 'on' else 0,
                'wall': {'count': 200, 'mean_ms': .2, 'min_ms': .1, 'max_ms': .3},
                'thread_cpu': {'count': 200, 'mean_ms': .1, 'min_ms': .05, 'max_ms': .2}}
    return {'schema': 'aura-synthetic-freshness-light-preflight-1', 'complete': True,
            'source_sha256': dict(PINS), 'execution_scope': 'synthetic_no_devices',
            'new_dpu_jobs': 0, 'board_connected': False,
            'tests': {'successful': True, 'run': 32, 'failures': 0, 'errors': 0, 'skipped': 0, 'pid': 100},
            'benchmark': {'iterations': 200, 'real_clocks_verified': True, 'pid': 101,
                          'cases': {case: {mode: row(mode) for mode in ('original', 'off', 'on')}
                                    for case in ('normal_empty_face', 'slot_unavailable', 'full_event_health_outer_lock')}}}


class EvaluationTests(unittest.TestCase):
    def test_complete_synthetic_report_passes_without_board_claim(self):
        result = evaluate(fixture())
        self.assertTrue(result['passed'])
        self.assertFalse(result['physical_board_verified'])
        self.assertFalse(result['allows_automatic_deployment'])

    def test_missing_and_malformed_data_are_rejected(self):
        for value in (None, [], {}, {'complete': True}):
            self.assertFalse(evaluate(value)['passed'])
        report = fixture();report['benchmark']['cases']['slot_unavailable'] = []
        self.assertFalse(evaluate(report)['passed'])

    def test_partial_worker_or_failed_tests_never_pass(self):
        for key, value in (('complete', False), ('tests', {}), ('benchmark', {})):
            report = fixture();report[key] = value
            self.assertFalse(evaluate(report)['passed'])
        for key in ('failures', 'errors', 'skipped'):
            report = fixture();report['tests'][key] = 1
            self.assertFalse(evaluate(report)['passed'])

    def test_different_source_or_device_scope_rejected(self):
        for key, value in (('source_sha256', {}), ('board_connected', True), ('new_dpu_jobs', 1)):
            report = fixture();report[key] = value
            self.assertFalse(evaluate(report)['passed'])

    def test_virtual_clock_contamination_and_same_process_rejected(self):
        report = fixture();report['benchmark']['real_clocks_verified'] = False
        self.assertFalse(evaluate(report)['passed'])
        report = fixture();report['benchmark']['pid'] = report['tests']['pid']
        self.assertFalse(evaluate(report)['passed'])

    def test_truncated_measurement_and_observer_failure_rejected(self):
        for key, value in (('iterations_completed', 199), ('observer_complete', False),
                           ('observer_failures', 1), ('closed_cleanly', False), ('behavior_verified', False)):
            report = fixture();report['benchmark']['cases']['slot_unavailable']['on'][key] = value
            self.assertFalse(evaluate(report)['passed'])

    def test_nan_inf_negative_and_boolean_not_zero(self):
        for value in (math.nan, math.inf, -1, True, '0', None):
            report = fixture();report['benchmark']['cases']['slot_unavailable']['on']['wall']['mean_ms'] = value
            self.assertFalse(evaluate(report)['passed'])
        for key in ('failures', 'errors', 'skipped'):
            report = fixture();report['tests'][key] = False
            self.assertFalse(evaluate(report)['passed'])

    def test_cost_threshold_applies_to_both_clocks_and_all_cases(self):
        for case in fixture()['benchmark']['cases']:
            for clock in ('wall', 'thread_cpu'):
                report = fixture();row = report['benchmark']['cases'][case]['on'][clock]
                row.update(mean_ms=1., max_ms=1.1)
                self.assertFalse(evaluate(report)['passed'])

    def test_default_off_added_cost_is_also_bounded(self):
        report = fixture();report['benchmark']['cases']['normal_empty_face']['off']['wall'].update(mean_ms=1., max_ms=1.)
        self.assertFalse(evaluate(report)['passed'])

    def test_negative_delta_is_kept_without_speedup_claim(self):
        report = fixture();report['benchmark']['cases']['normal_empty_face']['on']['wall'].update(mean_ms=.15)
        result = evaluate(report)
        self.assertTrue(result['passed'])
        self.assertLess(result['signed_mean_differences_ms']['normal_empty_face']['on_minus_original']['wall'], 0)
        self.assertFalse(result['speedup_or_ttl_improvement_proven'])

    def test_full_event_health_required(self):
        report = fixture();report['benchmark']['cases']['full_event_health_outer_lock']['on']['events_before_measurement'] = 15
        self.assertFalse(evaluate(report)['passed'])

    def test_full_observer_schema_and_misclaimed_internal_cpu_rejected(self):
        for key, value in (('observer_schema', 'aura-face-freshness-metrics-1'),
                ('internal_attempt_wall_or_cpu_collected', True), ('internal_attempt_wall_or_cpu_collected', None)):
            report = fixture();report['benchmark']['cases']['normal_empty_face']['on'][key] = value
            self.assertFalse(evaluate(report)['passed'])

    def test_disabled_observer_does_not_fake_zero_samples(self):
        for key in ('observer_complete', 'observer_failures', 'internal_attempt_wall_or_cpu_collected'):
            report = fixture();report['benchmark']['cases']['slot_unavailable']['off'][key] = 0
            self.assertFalse(evaluate(report)['passed'])

    def test_optimized_runner_refuses_validation(self):
        result = subprocess.run([sys.executable, '-O', str(Path(__file__).parent/'run_preflight.py'),
            '--worker', 'benchmark'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('assertions enabled', result.stderr)

    def test_nonpositive_pid_rejected(self):
        for value in (0, -1, True, None):
            report = fixture();report['benchmark']['pid'] = value
            self.assertFalse(evaluate(report)['passed'])

    def audited_child(self, statement):
        code = ('import sys; import socket; import subprocess; '
            'from run_preflight import refuse_device_operation; '
            'sys.addaudithook(refuse_device_operation); '+statement)
        result = subprocess.run([sys.executable, '-B', '-c', code],
            cwd=str(Path(__file__).resolve().parent), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Synthetic worker refused', result.stderr)
        return result

    def test_preloaded_socket_is_blocked_before_socket_creation(self):
        self.audited_child('socket.socket()')

    def test_device_open_is_blocked_before_open(self):
        self.audited_child('open("/dev/null", "rb")')

    def test_nested_process_is_blocked_before_creation(self):
        self.audited_child('subprocess.run([sys.executable, "-c", "print(123)"])')


if __name__ == '__main__':
    unittest.main()
