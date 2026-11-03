from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'candidate/aura'))
if (ROOT/'tests/bootstrap.py').exists(): import bootstrap
from board.vision.dpu_vision_schedule import DpuVisionSchedule
import test_bounded_recovery as bounded


class Clock:
    def __init__(self): self.now = 1000.
    def __call__(self): return self.now
    def advance(self, seconds): self.now += seconds


class Harness:
    def setUp(self):
        self.clock = Clock()
        self.schedule = DpuVisionSchedule(clock=self.clock, yunet_slot_wait_ms=100)
        self.schedule.next_primary = self.clock()+1

    def timeout(self, seconds): self.clock.advance(seconds)

    def release_primary(self, seconds):
        self.assertNotEqual(self.schedule.active, 'yunet')
        self.clock.advance(min(.020, seconds))
        self.schedule.active = None
        self.schedule.next_primary = self.clock()+.1

    def stats(self): return self.schedule.health()['yunet_slot_wait']


class WaitTests(Harness, unittest.TestCase):
    def test_config_is_bounded_explicit_integer(self):
        for value in (-1,101,True,None,1.5):
            with self.assertRaises(ValueError): DpuVisionSchedule(yunet_slot_wait_ms=value)
        self.assertNotIn('yunet_slot_wait', DpuVisionSchedule().health())

    def test_ready_predicate_returns_without_wait_or_ownership(self):
        self.schedule.condition.wait = lambda timeout:self.fail('unexpected wait')
        self.assertTrue(self.schedule.wait_for_optional('yunet', self.clock()+.1))
        self.assertIsNone(self.schedule.active)
        self.assertEqual(self.stats()['condition_waits'], 0)

    def test_missed_completion_notification_is_not_lost(self):
        self.schedule.active = 'yolo'
        with self.schedule.optional('yunet') as acquired: self.assertFalse(acquired)
        self.schedule.active = None
        self.schedule.condition.wait = lambda timeout:self.fail('lost completion notification')
        self.assertTrue(self.schedule.wait_for_optional('yunet', self.clock()+.1))

    def test_configured_hundred_ms_caps_long_caller_deadline(self):
        self.schedule.active = 'yolo'; self.schedule.condition.wait = self.timeout
        self.assertFalse(self.schedule.wait_for_optional('yunet', self.clock()+10))
        self.assertAlmostEqual(self.clock.now, 1000.1)
        self.assertEqual(self.stats()['timeouts'], 1)

    def test_outer_deadline_shortens_wait(self):
        self.schedule.active = 'yolo'; self.schedule.condition.wait = self.timeout
        self.assertFalse(self.schedule.wait_for_optional('yunet', self.clock()+.025))
        self.assertAlmostEqual(self.clock.now, 1000.025)

    def test_expired_deadline_cannot_return_ready(self):
        self.assertFalse(self.schedule.wait_for_optional('yunet', self.clock()))
        self.assertEqual(self.stats()['ready'], 0)

    def test_disabled_job_returns_without_wait(self):
        self.schedule.jobs['yunet'] = {'disabled':True}
        self.schedule.condition.wait = lambda timeout:self.fail('disabled job waited')
        self.assertFalse(self.schedule.wait_for_optional('yunet', self.clock()+.1))
        self.assertEqual(self.stats()['disabled'],1)

    def test_waiting_primary_retains_priority(self):
        self.schedule.waiting_primary = 1; self.schedule.condition.wait = self.timeout
        self.assertFalse(self.schedule.wait_for_optional('yunet', self.clock()+.1))
        self.assertEqual(self.stats()['ready'],0)

    def test_nonfinite_deadline_and_unknown_model_are_rejected(self):
        for value in (float('nan'),float('inf'),True,'later'):
            with self.assertRaises(ValueError): self.schedule.wait_for_optional('yunet',value)
        with self.assertRaises(ValueError): self.schedule.wait_for_optional('unknown-model',self.clock()+.1)

    def test_primary_completion_wakes_prepared_input_without_owning_slot(self):
        self.schedule.active='yolo';self.schedule.condition.wait=self.release_primary
        self.assertTrue(self.schedule.wait_for_optional('yunet',self.clock()+.1))
        self.assertIsNone(self.schedule.active)
        with self.schedule.optional('yunet') as acquired:
            self.assertTrue(acquired);self.clock.advance(.004)
        self.assertAlmostEqual(self.schedule.health()['optional']['yunet']['maximum_ms'],4.)
        self.assertAlmostEqual(self.stats()['maximum_wall_ms'],20.)

    def test_native_hardcap_remains_thirty_ms_after_waiting(self):
        self.schedule.active='yolo';self.schedule.condition.wait=self.release_primary
        self.assertTrue(self.schedule.wait_for_optional('yunet',self.clock()+.1))
        with self.schedule.optional('yunet') as acquired:
            self.assertTrue(acquired);self.clock.advance(.031)
        self.assertTrue(self.schedule.disabled('yunet'))
        self.assertEqual(self.schedule.health()['optional']['yunet']['overruns'],1)

    def test_primary_can_reacquire_between_notification_and_admission(self):
        self.assertTrue(self.schedule.wait_for_optional('yunet',self.clock()+.1))
        self.schedule.waiting_primary=1
        with self.schedule.optional('yunet') as acquired:self.assertFalse(acquired)
        self.assertIsNone(self.schedule.active)

    def test_wait_releases_actual_condition_for_primary_completion(self):
        schedule=DpuVisionSchedule(yunet_slot_wait_ms=100)
        entered=threading.Event();release=threading.Event();waiting=threading.Event();answer=[]
        def primary():
            with schedule.primary(time.monotonic()+1):
                entered.set();release.wait(.5)
        original=schedule.condition.wait
        def wait(timeout):waiting.set();return original(timeout)
        schedule.condition.wait=wait
        p=threading.Thread(target=primary);p.start();self.assertTrue(entered.wait(.5))
        w=threading.Thread(target=lambda:answer.append(schedule.wait_for_optional('yunet',time.monotonic()+.1)))
        w.start();self.assertTrue(waiting.wait(.5));release.set();p.join(.5);w.join(.5)
        self.assertFalse(p.is_alive() or w.is_alive());self.assertEqual(answer,[True])
        self.assertIsNone(schedule.active)


class AdapterTests(Harness, unittest.TestCase):
    def adapter(self): return bounded.AdapterTests.adapter(self)

    def clocks(self, adapter):
        return patch.dict(adapter._guarded_slot.__wrapped__.__globals__,
                          {'time':SimpleNamespace(monotonic=self.clock)})

    def test_prepared_input_waits_once_then_executes_without_cpu_fallback(self):
        adapter=self.adapter();self.schedule.active='yolo';self.schedule.condition.wait=self.release_primary
        with self.clocks(adapter):adapter.detect_with_admission_guard('encoded-frame',lambda:None)
        self.assertEqual(self.native_calls,1);self.assertEqual(self.cpu_calls,0)
        self.assertEqual(adapter.kind,'DPU_YUNET_INT8')
        self.assertEqual(self.stats()['ready'],1)

    def test_timeout_retains_original_rejection_timestamp(self):
        adapter=self.adapter();self.schedule.active='yolo';self.schedule.condition.wait=self.timeout
        with self.clocks(adapter),self.assertRaises(RuntimeError) as error:
            adapter.detect_with_admission_guard('frame',lambda:None)
        self.assertEqual(error.exception.args[0],1000.)
        self.assertAlmostEqual(self.clock.now,1000.1)
        self.assertEqual(self.native_calls,0)

    def test_outer_deadline_prevents_another_full_wait(self):
        adapter=self.adapter();self.schedule.active='yolo';self.schedule.condition.wait=self.timeout
        check=lambda:None;check.deadline_monotonic=self.clock()+.025
        with self.clocks(adapter),self.assertRaises(RuntimeError):adapter.detect_with_admission_guard('frame',check)
        self.assertAlmostEqual(self.clock.now,1000.025)
        self.assertEqual(self.native_calls,0)

    def test_native_disabled_during_wait_does_not_submit(self):
        adapter=self.adapter();self.schedule.active='yolo'
        def disable(timeout):
            self.clock.advance(.005);self.schedule.active=None
            self.schedule.jobs['yunet']['disabled']=True
        self.schedule.condition.wait=disable
        with self.clocks(adapter),self.assertRaises(RuntimeError):adapter.detect_with_admission_guard('frame',lambda:None)
        self.assertEqual(self.native_calls,0)


if __name__=='__main__':unittest.main()
