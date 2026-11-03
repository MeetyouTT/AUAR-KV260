from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
if (ROOT/'tests/bootstrap.py').exists():
    import bootstrap
    from test_yunet_retry import Harness
    from board.vision.dpu_recovery_policy import YuNetRecoveryPolicy
else:
    Harness = None


@unittest.skipIf(Harness is None, 'Full frozen retry harness runs in the offline regression image')
class RealWrapperTests(unittest.TestCase):
    def make(self):
        h = Harness()
        h.schedule.yunet_recovery = YuNetRecoveryPolicy()
        return h

    def cool(self, h):
        h.clock.advance(10)
        with h.schedule.primary(h.clock.now+1): h.clock.advance(.001)

    def test_pinned_runner_wait_success_proves_recovery_and_backend(self):
        h = self.make(); h.native.cost = .031; h.run(1)
        self.assertEqual(h.schedule.health()['yunet_recovery']['phase'], 'COOLDOWN')
        self.assertEqual(h.native.completed, 1)
        h.clock.advance(.2); h.run(2)
        self.assertEqual(h.fallback_fids, [2])
        self.cool(h); h.native.cost = .004
        for fid in (3, 4, 5):
            h.run(fid); h.clock.advance(.2)
        health = h.schedule.health()
        self.assertEqual(health['yunet_recovery']['recoveries'], 1)
        self.assertEqual(health['optional']['yunet']['overruns'], 1)
        self.assertEqual(h.native.completed, 4)
        self.assertEqual(h.service.backend, 'DPU_YUNET_INT8')

    def test_nonzero_status_during_probe_cannot_reuse_old_success_proof(self):
        h = self.make(); h.native.cost = .031; h.run(1); self.cool(h)
        h.native.cost = .004; h.native.status = -1
        with self.assertRaisesRegex(RuntimeError, 'VART execution failed'): h.run(2)
        self.assertTrue(h.schedule.disabled('yunet'))
        self.assertEqual(h.schedule.health()['yunet_recovery']['phase'], 'LATCHED')
        self.assertEqual(h.schedule.health()['yunet_recovery']['recoveries'], 0)

    def test_expired_source_during_cooldown_cannot_spend_probe(self):
        h = self.make(); h.native.cost = .031; h.run(1); self.cool(h)
        h.run(2, packet=h.packet(2, h.clock.millis()-1001))
        self.assertEqual(h.native.submitted, 1)
        self.assertEqual(h.schedule.health()['yunet_recovery']['attempts'], 0)

    def test_preexecute_close_withdrawal_does_not_become_native_failure(self):
        h = self.make()
        h.runner._diagnostic_mark = lambda phase, status=None: h.service.close() if phase == 'execute_start' else None
        h.run(1)
        self.assertEqual(h.native.submitted, 0)
        self.assertFalse(h.schedule.disabled('yunet'))
        self.assertEqual(h.schedule.health()['yunet_recovery']['faults'], 0)


if __name__ == '__main__': unittest.main()
