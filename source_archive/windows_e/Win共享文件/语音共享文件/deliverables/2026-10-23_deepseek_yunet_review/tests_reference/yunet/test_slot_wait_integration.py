from pathlib import Path
import threading
import unittest

ROOT=Path(__file__).resolve().parents[1]
if (ROOT/'tests/bootstrap.py').exists():
    import bootstrap
    from test_yunet_retry import Harness
    from board.vision.dpu_vision_schedule import DpuVisionSchedule
else:Harness=None


@unittest.skipIf(Harness is None,'Frozen retry/real-wrapper harness runs in offline image')
class IntegrationTests(unittest.TestCase):
    def make(self):
        h=Harness();h.schedule=DpuVisionSchedule(clock=h.clock.monotonic,yunet_recovery=True,yunet_slot_wait_ms=100)
        h.schedule.next_primary=h.clock.now+10;h.adapter.schedule=h.schedule
        h.service.independent_admission=True;h.service._admission_cancelled=threading.Event()
        return h

    def test_prepare_one_frame_and_wait_for_primary_instead_of_repreparing(self):
        h=self.make();h.deny()
        def released(timeout):
            h.clock.advance(.040);h.offer(2);h.allow()
        h.schedule.condition.wait=released
        h.run(1)
        self.assertEqual(h.preparer.fids,[1]);self.assertEqual(h.native_fids,[1])
        self.assertEqual(h.native.completed,1);self.assertEqual(h.service.processed,1)
        self.assertEqual(h.service.pending[1],2)
        self.assertEqual(h.service.retry_health()['retries'],0)
        self.assertEqual(h.schedule.health()['yunet_slot_wait']['ready'],1)
        self.assertEqual(h.schedule.health()['optional']['yunet']['overruns'],0)

    def test_existing_two_hundred_ms_round_deadline_is_not_extended(self):
        h=self.make();h.deny()
        h.schedule.condition.wait=lambda timeout:h.clock.advance(timeout)
        h.event(.125,lambda:h.offer(2))
        began=h.clock.now;h.run(1)
        self.assertEqual(h.native.submitted,0)
        self.assertLessEqual(h.clock.now-began,.201)
        self.assertEqual(h.preparer.fids,[1,2])
        self.assertEqual(h.service.retry_health()['deadline'],1)

    def test_close_during_wait_is_checked_again_before_native_submission(self):
        h=self.make();h.deny()
        def closed(timeout):h.clock.advance(.020);h.service.close();h.allow()
        h.schedule.condition.wait=closed
        h.run(1)
        self.assertEqual(h.native.submitted,0)
        self.assertFalse(h.schedule.disabled('yunet'))
        self.assertEqual(h.service.retry_health()['withdrawn_after_slot'],1)

    def test_wait_completion_does_not_hide_nonzero_native_status(self):
        h=self.make();h.deny();h.native.status=-1
        h.schedule.condition.wait=lambda timeout:(h.clock.advance(.020),h.allow())
        with self.assertRaisesRegex(RuntimeError,'VART execution failed'):h.run(1)
        self.assertEqual(h.native.submitted,1);self.assertEqual(h.native.completed,0)
        self.assertTrue(h.schedule.disabled('yunet'))
        self.assertEqual(h.schedule.health()['yunet_recovery']['phase'],'LATCHED')

    def test_source_expiring_while_waiting_never_reaches_native(self):
        h=self.make();h.deny()
        h.schedule.condition.wait=lambda timeout:(h.clock.advance(.020),h.allow())
        h.run(1,packet=h.packet(1,h.clock.millis()-990))
        self.assertEqual(h.native.submitted,0)
        self.assertEqual(h.service.retry_health()['expired'],1)
        self.assertEqual(h.publications,[])

    def test_state_lock_contention_after_notification_does_not_cancel_fresh_native(self):
        h=self.make();h.deny();locked=threading.Event();release=threading.Event()
        def hold_state():
            with h.service.lock:locked.set();release.wait(1.)
        thread=threading.Thread(target=hold_state)
        original=h.runner._diagnostic_mark
        def marker(phase,status=None):
            original(phase,status)
            if phase=='execute_start':thread.start();self.assertTrue(locked.wait(.5))
            elif phase=='wait_end':release.set()
        h.runner._diagnostic_mark=marker
        h.schedule.condition.wait=lambda timeout:(h.clock.advance(.020),h.allow())
        try:h.run(1)
        finally:
            release.set()
            if thread.ident is not None:thread.join(.5)
        self.assertEqual(h.native.completed,1)
        self.assertEqual(h.service.retry_health()['busy'],0)
        self.assertEqual(h.service.retry_health()['withdrawn_after_slot'],0)

    def test_close_token_is_visible_even_while_other_thread_holds_state_lock(self):
        h=self.make();locked=threading.Event();release=threading.Event();closed=threading.Event()
        def hold_state():
            with h.service.lock:locked.set();release.wait(1.)
        holder=threading.Thread(target=hold_state)
        closer=threading.Thread(target=lambda:(h.service.close(),closed.set()))
        original=h.runner._diagnostic_mark
        def marker(phase,status=None):
            original(phase,status)
            if phase=='execute_start':
                holder.start();self.assertTrue(locked.wait(.5));closer.start()
                self.assertTrue(h.service._admission_cancelled.wait(.5))
            elif phase=='exception':release.set()
        h.runner._diagnostic_mark=marker
        try:h.run(1)
        finally:
            release.set()
            for thread in (holder,closer):
                if thread.ident is not None:thread.join(.5)
        self.assertTrue(closed.is_set())
        self.assertEqual(h.native.submitted,0)
        self.assertEqual(h.service.retry_health()['closed'],1)
        self.assertFalse(h.schedule.disabled('yunet'))

    def test_independent_mode_is_explicit_and_requires_retry(self):
        from board.identity.face_targets import FaceTargetService
        for value in (1,None,'yes'):
            with self.assertRaises(ValueError):FaceTargetService(None,None,'x',slot_retry=True,independent_admission=value)
        with self.assertRaises(ValueError):FaceTargetService(None,None,'x',independent_admission=True)
        service=FaceTargetService(None,None,'x',slot_retry=True)
        self.assertFalse(service.independent_admission)


if __name__=='__main__':unittest.main()
