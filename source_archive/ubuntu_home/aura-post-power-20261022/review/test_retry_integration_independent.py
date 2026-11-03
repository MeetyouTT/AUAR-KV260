"""Independent counter/backoff regressions on root's read-only integration."""
import unittest
from test_yunet_retry import Harness
from board.vision.pipeline_metrics import OptionalDiagnostics


class IndependentIntegrationTests(unittest.TestCase):
    def diagnostics(self, harness):
        observer = OptionalDiagnostics(enabled=True, clock_ns=harness.clock.monotonic_ns,
            thread_clock_ns=lambda: 1)
        harness.schedule.diagnostics = observer
        harness.runner.metrics.optional_diagnostics = observer
        return observer

    def test_real_execute_failure_is_not_masked_as_withdrawal(self):
        h = Harness(); diagnostics = self.diagnostics(h)
        h.native.failure = RuntimeError('independent synthetic native failure')
        with self.assertRaises(RuntimeError): h.run()
        row = diagnostics.snapshot()['counters']['yunet']
        self.assertEqual(row['native_failed'], 1)
        self.assertEqual(h.service.retry_health()['withdrawn_after_slot'], 0)
        self.assertEqual(row['native_completed'], 0)
        self.assertEqual(h.native.submitted, 1)

    def test_nonzero_wait_status_is_not_masked_as_withdrawal(self):
        h = Harness(); diagnostics = self.diagnostics(h); h.native.status = -7
        with self.assertRaises(RuntimeError): h.run()
        row = diagnostics.snapshot()['counters']['yunet']
        self.assertEqual(row['native_failed'], 1)
        self.assertEqual(h.service.retry_health()['withdrawn_after_slot'], 0)
        self.assertEqual(row['native_completed'], 0)
        self.assertEqual(h.native.submitted, 1)

    def test_guard_after_slot_has_explicit_no_submit_evidence(self):
        h = Harness(); diagnostics = self.diagnostics(h); h.deny()
        original = h.runner._diagnostic_mark
        def delayed(phase, status=None):
            original(phase, status)
            if phase == 'execute_start': h.clock.advance(.180)
        h.runner._diagnostic_mark = delayed
        h.event(.025, lambda: (h.allow(), h.offer(2))); h.run()
        row = diagnostics.snapshot()['counters']['yunet']
        self.assertEqual(row['native_failed'], 1)
        self.assertEqual(h.service.retry_health()['withdrawn_after_slot'], 1)
        self.assertEqual(row['native_completed'], 0)
        self.assertEqual(h.native.submitted, 0)

    def test_slow_denial_preserves_real_25ms_delay_before_second_preparation(self):
        h = Harness(); h.deny(); began = h.clock.now; starts = []
        h.preparer.before = lambda _: starts.append(h.clock.now)
        class Diagnostics:
            enabled = True
            def begin(self, kind, acquired, *args):
                if not acquired: h.clock.advance(.030)
                return None
            def error(self): raise AssertionError('unexpected diagnostic failure')
        h.schedule.diagnostics = Diagnostics(); h.offer(2)
        h.event(.054, h.allow); h.run()
        self.assertEqual(h.preparer.fids, [1, 2])
        self.assertGreaterEqual(starts[1]-(began+.030), .025-1e-10)
        self.assertEqual(h.native_fids, [2])

    def test_backoff_cannot_move_absolute_200ms_deadline_later(self):
        h = Harness(); h.deny(); began = h.clock.now
        class Diagnostics:
            enabled = True
            def begin(self, *args): h.clock.advance(.190)
            def error(self): raise AssertionError('unexpected diagnostic failure')
        h.schedule.diagnostics = Diagnostics(); h.offer(2); h.run()
        self.assertEqual(h.preparer.fids, [1])
        self.assertAlmostEqual(h.clock.now-began, .200)
        self.assertEqual(h.service.retry_health()['deadline'], 1)
        self.assertEqual(h.native.submitted, 0)


if __name__ == '__main__': unittest.main(verbosity=2)
