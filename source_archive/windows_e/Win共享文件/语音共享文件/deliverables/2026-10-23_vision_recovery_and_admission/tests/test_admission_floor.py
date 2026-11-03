"""Conservative admission candidate; not loaded in the live camera."""
import bootstrap
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('floor_candidate',ROOT/'admission_candidate/aura/board/vision/dpu_vision_schedule.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class AdmissionFloorTests(unittest.TestCase):
    def schedule(self,floor=30):
        self.now=1000.
        return module.DpuVisionSchedule(clock=lambda:self.now,admission_floor_ms=floor)

    def test_recorded_twenty_one_ms_guard_slot_is_declined_without_disabling(self):
        s=self.schedule();s.next_primary=self.now+.025909669
        with s.optional('yunet') as acquired:self.assertFalse(acquired)
        self.assertEqual(s.jobs['yunet']['skipped'],1);self.assertEqual(s.jobs['yunet']['calls'],0)
        self.assertFalse(s.disabled('yunet'));self.assertIsNone(s.active)

    def test_default_keeps_existing_admission(self):
        s=self.schedule(0);s.next_primary=self.now+.025909669
        with s.optional('yunet') as acquired:self.assertTrue(acquired)

    def test_original_thirty_ms_cap_and_five_ms_guard_still_apply(self):
        s=self.schedule();s.next_primary=self.now+1
        with s.optional('yunet') as acquired:
            self.assertTrue(acquired);self.now+=.031
        self.assertTrue(s.disabled('yunet'));self.assertEqual(s.jobs['yunet']['overruns'],1)
        self.assertEqual(s.guard,.005);self.assertEqual(s.budget,.020)

    def test_wait_and_acquire_use_identical_floor(self):
        s=self.schedule();s.yunet_slot_wait_ms=1;s.next_primary=self.now+.026
        # Real condition wait with a frozen clock would not advance: test the
        # shared predicate via expired deadline and positive wide window only.
        self.assertFalse(s.wait_for_optional('yunet',self.now))
        s.next_primary=self.now+.1
        self.assertTrue(s.wait_for_optional('yunet',self.now+.001))
        with s.optional('yunet') as acquired:self.assertTrue(acquired)

    def test_waiting_primary_keeps_priority(self):
        s=self.schedule();s.next_primary=self.now+1;s.waiting_primary=1
        with s.optional('yunet') as acquired:self.assertFalse(acquired)

    def test_configuration_rejects_bool_nonfinite_and_out_of_range(self):
        for value in (True,None,'30',31,-1,30.,float('inf')):
            with self.subTest(value=value),self.assertRaises(ValueError):module.DpuVisionSchedule(admission_floor_ms=value)

if __name__=='__main__':unittest.main(verbosity=2)
