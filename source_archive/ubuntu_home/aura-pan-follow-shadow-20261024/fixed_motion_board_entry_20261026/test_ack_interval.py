from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.append(str(Path(__file__).resolve().parent.parent / 'fixed_motion_isolation_20261026'))
from test_run_fixed_motion import Clock, FakeDriver
from plan_fixed import make_plan
from run_fixed_motion import BenchFailure, BenchPermit, plan_digest, run_fixed_motion


class IntervalDriver(FakeDriver):
    def submit_bench(self, *args, **kwargs):
        result = super().submit_bench(*args, **kwargs)
        result['lease_expiry_lower_bound_mono_s'] = self.expires - .001
        if self.mode == 'post_batch_pause':
            # Lease was sampled at the start of a 25ms batch; the caller then
            # resumes 90ms later. End+cached lease is NOT proof of validity.
            result['observed_mono_s'] += .025
            self.clock.now += .115
        if self.mode == 'invalid_bound':
            result['lease_expiry_lower_bound_mono_s'] = self.expires + 1.
        return result


class AckIntervalTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.driver = IntervalDriver(self.clock)
        self.rows = make_plan(1420, -1)
        self.reference = SimpleNamespace(boot_id=self.driver.boot_id, reference_us=1420, confirmed=True)
        self.permit = BenchPermit(self.driver.boot_id, 'fixture', 'fixture', 1420, 1415, 1420,
                                  1234, 9., 14., plan_digest(self.rows))

    def run_core(self):
        return run_fixed_motion(self.driver, self.reference, self.permit, self.rows,
                                clock=self.clock, sleep=self.clock.sleep)

    def test_live_lower_bounds_allow_complete_fake_run(self):
        result = self.run_core()
        self.assertEqual(len(result['commands']), 98)
        self.assertTrue(result['stop_confirmed'])
        self.assertIsNotNone(result['commands'][0]['acknowledgement']['lease_expiry_lower_bound_mono_s'])

    def test_later_batch_end_does_not_extend_old_lease(self):
        self.driver.mode = 'post_batch_pause'
        with self.assertRaises(BenchFailure) as error:
            self.run_core()
        self.assertIn('ACK_LEASE_LOWER_BOUND_EXPIRED', str(error.exception))
        self.assertEqual(self.driver.commits, 1)
        self.assertTrue(error.exception.report['stop_confirmed'])

    def test_impossible_lower_bound_is_rejected(self):
        self.driver.mode = 'invalid_bound'
        with self.assertRaisesRegex(BenchFailure, 'ACK_LEASE_LOWER_BOUND_EXPIRED'):
            self.run_core()
        self.assertEqual(self.driver.commits, 1)


if __name__ == '__main__':
    unittest.main()
