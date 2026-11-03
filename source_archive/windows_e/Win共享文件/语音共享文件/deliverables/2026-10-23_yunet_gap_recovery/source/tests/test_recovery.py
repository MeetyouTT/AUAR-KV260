"""Failure recovery cadence preserves successful observation cadence and DPU gates."""
import unittest
from test_yunet_retry import Harness
from board.identity.face_targets import FaceTargetService


def make(recovery):
    h=Harness()
    h.service=FaceTargetService(lambda:h.adapter,lambda *args:h.publications.append(args),
        'synthetic',clock=h.clock.millis,slot_retry=True,retry_clock=h.clock.monotonic,
        retry_recovery_ms=recovery)
    h.service.condition.wait=h.wait
    return h


def failed_round(h):
    h.deny();h.service.pending=h.packet(1)
    h.event(.010,lambda:h.offer(2));h.event(.040,lambda:h.offer(3))
    h.preparer.before=lambda fid:h.offer(4) if fid==3 else None


class RecoveryTests(unittest.TestCase):
    def test_recovery_requires_valid_explicit_retry_configuration(self):
        for value in (True,0,24,201,50.0,'50'):
            with self.assertRaises(ValueError):
                FaceTargetService(lambda:None,lambda *a:None,'x',slot_retry=True,retry_recovery_ms=value)
        with self.assertRaises(ValueError):
            FaceTargetService(lambda:None,lambda *a:None,'x',retry_recovery_ms=50)
        self.assertIsNone(FaceTargetService(lambda:None,lambda *a:None,'x').retry_recovery_ms)

    def test_successful_negative_observation_still_waits_200ms(self):
        h=make(50);h.service.pending=h.packet(1)
        h.preparer.after=lambda _:h.offer(2)
        h.event(.010,h.service.close)
        with h.clocks():h.service.work()
        self.assertEqual(h.service.processed,1)
        self.assertAlmostEqual(h.waits[0][1],.200)
        self.assertEqual(h.service.retry_health()['recovery_waits'],0)

    def test_denied_round_recovers_earlier_only_when_enabled(self):
        for recovery,expected in ((None,.200),(50,.050)):
            h=make(recovery);failed_round(h);h.event(.060,h.service.close)
            with h.clocks():h.service.work()
            self.assertEqual(h.preparer.fids,[1,2,3])
            self.assertEqual(h.native.submitted,0)
            self.assertAlmostEqual(h.waits[-1][1],expected)
            self.assertEqual(h.service.retry_health().get('recovery_waits',0),int(recovery is not None))

    def test_recovery_uses_latest_frame_and_returns_to_success_cadence(self):
        h=make(50);failed_round(h)
        h.event(.080,lambda:(h.allow(),h.offer(5)))
        h.preparer.after=lambda fid:h.offer(6) if fid==5 else None
        h.event(.120,h.service.close)
        with h.clocks():h.service.work()
        self.assertEqual(h.preparer.fids,[1,2,3,5])
        self.assertEqual(h.native_fids,[5])
        self.assertEqual(h.service.processed,1)
        self.assertAlmostEqual(h.waits[-1][1],.200)
        self.assertEqual(h.service.retry_health()['recovery_waits'],1)
        self.assertIsNone(h.schedule.active)


if __name__=='__main__':unittest.main()
