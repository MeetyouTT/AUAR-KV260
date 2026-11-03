"""Unknown native completion must stop admission for every model in the owner."""
import bootstrap
import unittest
from board.vision.dpu_vision_runtime import NativeExecutionError
from board.vision.dpu_vision_schedule import DpuVisionSchedule


class OwnerFenceTests(unittest.TestCase):
    def test_native_unknown_stops_both_optional_models_and_primary(self):
        now=[1000.]
        scheduler=DpuVisionSchedule(clock=lambda:now[0],yunet_recovery=True,
                                    yunet_slot_wait_ms=100,sface_slot_wait_ms=100)
        scheduler.next_primary=1001.
        with self.assertRaises(NativeExecutionError):
            with scheduler.optional('yunet') as acquired:
                self.assertTrue(acquired)
                raise NativeExecutionError('synthetic unknown completion')
        self.assertIsNone(scheduler.active)
        health=scheduler.health()
        self.assertTrue(health['owner_fenced'])
        self.assertEqual(health['owner_fault_reason'],'NATIVE_COMPLETION_UNCONFIRMED')
        for kind in ('yunet','sface'):
            self.assertTrue(scheduler.disabled(kind))
            self.assertFalse(scheduler.recovery_ready(kind))
            with scheduler.optional(kind) as acquired:self.assertFalse(acquired)
            self.assertFalse(scheduler.wait_for_optional(kind,1000.1))
        with self.assertRaisesRegex(RuntimeError,'native completion unconfirmed'):
            with scheduler.primary(1001.):self.fail('A fenced owner admitted YOLO')
        self.assertEqual(scheduler.waiting_primary,0)

    def test_successfully_completed_hardcap_does_not_fence_owner(self):
        now=[1000.]
        scheduler=DpuVisionSchedule(clock=lambda:now[0],yunet_recovery=True)
        scheduler.next_primary=1001.
        with scheduler.optional('yunet') as acquired:
            self.assertTrue(acquired);now[0]+=.031;scheduler.native_completed('yunet')
        self.assertFalse(scheduler.owner_fenced)
        self.assertEqual(scheduler.health()['yunet_recovery']['phase'],'COOLDOWN')
        with scheduler.primary(1001.):pass

    def test_pre_submission_withdrawal_does_not_fence(self):
        class Withdrawn(RuntimeError):native_not_submitted=True
        scheduler=DpuVisionSchedule();scheduler.next_primary=scheduler.clock()+1.
        with self.assertRaises(Withdrawn):
            with scheduler.optional('sface') as acquired:
                self.assertTrue(acquired);raise Withdrawn()
        self.assertFalse(scheduler.owner_fenced)
        self.assertFalse(scheduler.disabled('sface'))


if __name__=='__main__':unittest.main()
