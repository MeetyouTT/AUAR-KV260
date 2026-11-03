import bootstrap
from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from board.vision.dpu_vision_schedule import DpuVisionSchedule
from board.vision.dpu_sface import DpuSFace


class NotificationTests(unittest.TestCase):
    def test_separate_sface_wait_leaves_yunet_wait_statistics_independent(self):
        now=[1000.];s=DpuVisionSchedule(clock=lambda:now[0],yunet_slot_wait_ms=100,sface_slot_wait_ms=100)
        s.next_primary=1001.
        self.assertTrue(s.wait_for_optional('sface',1000.1))
        self.assertEqual(s.health()['sface_slot_wait']['calls'],1)
        self.assertEqual(s.health()['yunet_slot_wait']['calls'],0)
        self.assertIsNone(s.active)

    def test_sface_notification_preserves_waiting_primary_and_hard_cap(self):
        now=[1000.];s=DpuVisionSchedule(clock=lambda:now[0],sface_slot_wait_ms=100)
        s.next_primary=1001.;s.waiting_primary=1
        s.condition.wait=lambda duration:now.__setitem__(0,now[0]+duration)
        self.assertFalse(s.wait_for_optional('sface',1000.1))
        s.waiting_primary=0
        with s.optional('sface') as acquired:
            self.assertTrue(acquired);now[0]+=.031
        self.assertTrue(s.disabled('sface'));self.assertEqual(s.health()['optional']['sface']['overruns'],1)

    def test_sface_wait_configuration_requires_bounded_explicit_integer(self):
        for value in (True,-1,101,None,1.5):
            with self.assertRaises(ValueError):DpuVisionSchedule(sface_slot_wait_ms=value)

    def engine(self):
        e=DpuSFace.__new__(DpuSFace);e.clock=lambda:1000;e.source_ttl=1000
        e.slot_denials=e.expired_after_admission=e.execution_attempts=0
        e.schedule=SimpleNamespace(sface_slot_wait_ms=100,disabled=lambda k:False)
        return e

    def test_denial_releases_context_before_wait_then_rechecks_freshness(self):
        e=self.engine();calls=[];inside=[False];cost=[0.]
        @contextmanager
        def optional(kind):
            inside[0]=True;calls.append(kind)
            try:yield len(calls)>1
            finally:inside[0]=False
        def wait(kind,deadline):
            self.assertFalse(inside[0]);cost[0]+=.020;return True
        e.schedule.optional=optional;e.schedule.wait_for_optional=wait
        with patch('board.vision.dpu_sface.time.monotonic',lambda:cost[0]):
            with e._slot(1000) as acquired:self.assertTrue(acquired)
        self.assertEqual(e.execution_attempts,1);self.assertEqual(e.slot_denials,1)

    def test_expired_frame_after_notification_never_executes(self):
        e=self.engine();now=[1000];e.clock=lambda:now[0];n=[0]
        @contextmanager
        def optional(kind):n[0]+=1;yield n[0]>1
        e.schedule.optional=optional
        def wait(kind,deadline):now[0]=2000;return True
        e.schedule.wait_for_optional=wait
        with e._slot(1000) as acquired:self.assertFalse(acquired)
        self.assertEqual(e.execution_attempts,0);self.assertEqual(e.expired_after_admission,1)


if __name__=='__main__':unittest.main()
