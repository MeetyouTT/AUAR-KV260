import copy
import json
import unittest

import unattended_observer as observer


def health():
    job = dict(calls=100, native_completed=98, overruns=1, native_failures=0,
        not_submitted=2, disabled=False,
        recovery=dict(phase='RUNNING', faults=1, attempts=1, recoveries=1),
        last_native_report=dict(abi_version=2, task=1, hardcap=1, guard=0,
            submitted=1, completed=1, native_status=0, start_ns=1,
            native_return_ns=31_000_001, release_decision_ns=31_000_002,
            after_unlock_ns=31_000_003, business_ready=0, result_fresh=1,
            recovery_phase=1, private_vector=[1., 2.]))
    return dict(pid=1291, detected_frames=1000, camera_error='', detector_error='',
        identity=dict(display_name='PRIVATE_NAME', feature_inference=dict(ready=True),
            face_targets=dict(worker_alive=True, inference=dict(fallback_calls=3),
                freshness_metrics=dict(counters=dict(observed_gap_intervals=0)), image='PRIVATE_IMAGE')),
        dpu_schedule=dict(native_critical=True, native_abi=2, primary_calls=1000,
            primary_period_overruns=1, owner_fenced=False,
            optional=dict(yunet=copy.deepcopy(job), sface=copy.deepcopy(job))))


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.raw = health()
        self.before = observer.extract(self.raw, 1_000_000_000)
        self.after = copy.deepcopy(self.before)
        self.after['mono_ns'] += 10_000_000_000
        self.after['frames'] += 100

    def test_private_fields_are_not_serialized(self):
        raw = json.dumps(self.before)
        for text in ('PRIVATE_NAME', 'PRIVATE_IMAGE', 'private_vector'):
            self.assertNotIn(text, raw)

    def test_real_rate_and_counter_deltas(self):
        result = observer.compare(self.before, self.after)
        self.assertEqual(result['yolo_hz'], 10.)
        self.assertEqual(result['primary_overruns'], 0)
        self.assertEqual(result['optional']['yunet']['faults'], 0)

    def test_no_sface_requests_do_not_prove_three_model_load(self):
        self.assertFalse(observer.compare(self.before, self.after)['three_model_load_observed'])

    def test_sface_completion_is_required(self):
        self.after['optional']['sface']['completed'] += 2
        self.assertTrue(observer.compare(self.before, self.after)['three_model_load_observed'])

    def test_new_process_counters_are_not_merged(self):
        self.after['pid'] += 1
        with self.assertRaises(ValueError):observer.compare(self.before, self.after)

    def test_reset_of_any_basic_counter_is_rejected(self):
        for key in ('frames', 'primary_calls', 'primary_overruns', 'gaps', 'fallback_calls'):
            with self.subTest(key=key):
                bad = copy.deepcopy(self.after);bad[key] = self.before[key] - 1
                with self.assertRaises(ValueError):observer.compare(self.before, bad)

    def test_reset_of_any_optional_counter_is_rejected(self):
        for key in ('calls', 'completed', 'overruns', 'native_failures', 'not_submitted',
                    'faults', 'attempts', 'recoveries'):
            with self.subTest(key=key):
                bad = copy.deepcopy(self.after)
                bad['optional']['yunet'][key] = self.before['optional']['yunet'][key] - 1
                with self.assertRaises(ValueError):observer.compare(self.before, bad)

    def test_clock_must_advance(self):
        self.after['mono_ns'] = self.before['mono_ns']
        with self.assertRaises(ValueError):observer.compare(self.before, self.after)

    def test_unknown_backend_is_rejected(self):
        self.raw['dpu_schedule']['native_abi'] = 1
        with self.assertRaises(ValueError):observer.extract(self.raw, 1)

    def test_unknown_policy_is_rejected(self):
        self.raw['dpu_schedule']['optional']['yunet']['recovery']['phase'] = 'PRIVATE_NAME'
        with self.assertRaises(ValueError):observer.extract(self.raw, 1)

    def test_negative_counters_are_rejected(self):
        self.raw['detected_frames'] = -1
        with self.assertRaises(ValueError):observer.extract(self.raw, 1)

    def test_negative_native_status_is_retained(self):
        self.raw['dpu_schedule']['optional']['yunet']['last_native_report']['native_status'] = -5
        self.assertEqual(observer.extract(self.raw, 1)['optional']['yunet']['report']['native_status'], -5)

    def test_per_cpu_percent_has_own_denominator(self):
        result = observer.cpu_delta({'cpu':(100, 50), 'cpu0':(100, 50)},
                                    {'cpu':(500, 150), 'cpu0':(200, 75)})
        self.assertEqual(result, dict(cpu=75., cpu0=75.))


if __name__ == '__main__':
    unittest.main()
