from pathlib import Path
import sys
import unittest

sys.path.insert(0,'/home/ghmd/aura-pan-joint-20261023')
from test_finite_step import FakeClock,FakeHardware
from bench_observed_20us import run_roundtrip


class Observed20usTests(unittest.TestCase):
    def setUp(self):
        self.clock=FakeClock();self.hardware=FakeHardware(self.clock)
        self.hardware.width=self.hardware.target=self.hardware.reference=1425
        self.expected=self.hardware.status();self.events=[]

    def run_trial(self,sleep=None):
        return run_roundtrip(self.hardware,self.hardware,1425,self.expected,self.events,
            clock=self.clock,sleep=sleep or self.clock.sleep)

    def test_two_seconds_20us_excursion_returns_and_stops(self):
        result=self.run_trial()
        self.assertAlmostEqual(self.clock.now,102.)
        self.assertEqual(result['commanded_sequence_us'],[1425,1445,1425])
        self.assertEqual(result['stopped']['width_us'],1425)
        self.assertEqual(self.hardware.flags,0)
        self.assertEqual(self.hardware.finishes,1)
        self.assertEqual(self.hardware.stops,2)

    def test_current_context_change_refused_before_setup(self):
        self.hardware.epoch=9
        with self.assertRaisesRegex(RuntimeError,'context changed'):
            self.run_trial()
        self.assertEqual(self.hardware.shadow,{})

    def test_out_of_range_excursion_refused(self):
        with self.assertRaisesRegex(RuntimeError,'outside the existing range'):
            run_roundtrip(self.hardware,self.hardware,1590,self.expected,[],clock=self.clock,sleep=self.clock.sleep)
        self.assertEqual(self.hardware.shadow,{})

    def test_delayed_shadow_write_refuses_commit_and_stops(self):
        self.hardware.delay_shadow=True
        with self.assertRaisesRegex(RuntimeError,'Late COMMIT refused'):
            self.run_trial()
        self.assertEqual(self.hardware.commits,0)
        self.assertEqual(self.hardware.flags,0)

    def test_expired_permit_not_rearmed_or_retried(self):
        with self.assertRaisesRegex(RuntimeError,'Lease/context lost'):
            self.run_trial(sleep=lambda _:self.clock.sleep(.11))
        self.assertEqual(self.hardware.commits,1)
        self.assertEqual(self.hardware.flags,0)


if __name__=='__main__':unittest.main()
