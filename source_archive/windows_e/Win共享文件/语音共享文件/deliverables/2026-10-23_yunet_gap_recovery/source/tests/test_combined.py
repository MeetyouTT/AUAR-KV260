"""Four-feature combinations and light2 cancellation accounting; fake only."""
import bootstrap
from contextlib import contextmanager
from types import SimpleNamespace
import unittest

from test_yunet_retry import Harness
from board.identity.face_targets import FaceTargetService
from board.identity.face_freshness_metrics import FaceFreshnessMetrics


def make(retry=True, metrics=True):
    h = Harness(retry)
    h.service = FaceTargetService(lambda: None, lambda *args: h.publications.append(args),
        'synthetic', clock=h.clock.millis, slot_retry=retry, retry_clock=h.clock.monotonic,
        freshness_metrics=metrics)
    h.service.ready = True
    h.service.condition.wait = h.wait
    return h


class CombinedTests(unittest.TestCase):
    def observed(self, h):
        value = h.service.health()['freshness_metrics']
        self.assertEqual(value['schema_version'], 'aura-face-freshness-light-3')
        self.assertEqual(value['observer_failures'], 0)
        self.assertFalse(value['per_attempt_wall_or_thread_cpu_collected'])
        return value

    def test_four_combinations_have_independent_health_and_same_success(self):
        for retry in (False, True):
            for metrics in (False, True):
                h = make(retry, metrics); h.run()
                health = h.service.health()
                self.assertEqual('slot_retry' in health, retry)
                self.assertEqual('freshness_metrics' in health, metrics)
                self.assertEqual(h.native_fids, [1])
                self.assertEqual(len(h.publications), 1)
                self.assertEqual(h.service.processed, 1)
                if metrics:
                    c = self.observed(h)['counters']
                    self.assertEqual((c['attempts'], c['attempts_finished'], c['published']), (1, 1, 1))

    def test_four_combinations_preserve_worker_200ms_success_interval_and_close(self):
        for retry in (False, True):
            for metrics in (False, True):
                h = make(retry, metrics); h.service.factory = lambda: h.adapter
                h.service.pending = h.packet(1)
                h.preparer.after = lambda _: h.offer(2)
                h.event(.010, h.service.close)
                with h.clocks(): h.service.work()
                self.assertEqual(h.preparer.fids, [1])
                self.assertAlmostEqual(h.waits[0][1], .200)
                self.assertIsNone(h.runner.runner)
                if metrics: self.assertTrue(self.observed(h)['closed'])

    def test_three_denials_are_observed_as_three_attempts_not_process_errors(self):
        h = make(); h.deny()
        h.event(.010, lambda: h.offer(2)); h.event(.040, lambda: h.offer(3)); h.run()
        c = self.observed(h)['counters']
        self.assertEqual(h.preparer.fids, [1, 2, 3])
        self.assertEqual((c['attempts'], c['attempts_finished'], c['slot_unavailable']), (3, 3, 3))
        self.assertEqual(c['maximum_consecutive_slot_rejections'], 3)
        self.assertEqual((c['process_errors'], c['cancelled'], c['active_attempts']), (0, 0, 0))

    def test_success_after_denial_resets_streak_and_publishes_latest(self):
        h = make(); h.deny()
        h.event(.005, lambda: h.offer(2)); h.event(.015, lambda: h.offer(3)); h.event(.025, h.allow)
        h.run(); c = self.observed(h)['counters']
        self.assertEqual(h.native_fids, [3])
        self.assertEqual((c['attempts'], c['attempts_finished'], c['slot_unavailable'], c['published']), (2, 2, 1, 1))
        self.assertEqual(c['consecutive_slot_rejections'], 0)
        self.assertEqual(c['maximum_consecutive_slot_rejections'], 1)

    def test_deadline_after_cpu_preparation_is_cancellation_not_slot_or_error(self):
        h = make(); h.deny()
        def slow(): h.allow(); h.offer(2); h.preparer.cost = .190
        h.event(.025, slow); h.run()
        s = self.observed(h); c = s['counters']
        self.assertEqual((c['slot_unavailable'], c['cancelled_deadline'], c['cancelled']), (1, 1, 1))
        self.assertEqual((c['process_errors'], c['active_attempts']), (0, 0))
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(s['events'][-1]['cancel_reason_code'], s['cancel_reason_codes']['deadline'])

    def test_closed_and_expired_cancellations_are_separate(self):
        h = make(); h.service.closed = True; h.run()
        c = self.observed(h)['counters']
        self.assertEqual((c['cancelled_closed'], c['cancelled'], c['process_errors'], c['slot_unavailable']), (1, 1, 0, 0))
        h = make(); h.preparer.cost = 1.001; h.run()
        c = self.observed(h)['counters']
        self.assertEqual((c['cancelled_expired'], c['cancelled'], c['process_errors'], c['slot_unavailable']), (1, 1, 0, 0))

    def test_disabled_race_is_cancelled_and_existing_cpu_fallback_still_works(self):
        h = make()
        h.preparer.before = lambda _: h.schedule.jobs.update(yunet={'disabled':True, 'skipped':0, 'estimated_budget_ms':20.})
        h.run(); c = self.observed(h)['counters']
        self.assertEqual((c['cancelled_disabled'], c['cancelled'], c['slot_unavailable'], c['process_errors']), (1, 1, 0, 0))
        h.clock.advance(.2); h.run(2)
        self.assertEqual(h.fallback_fids, [2])
        self.assertEqual(self.observed(h)['counters']['published'], 1)

    def test_busy_guard_withdrawal_has_no_native_and_numeric_cancel_event(self):
        h = make(); real = h.service.lock
        class Lock:
            fail_try = False
            def __enter__(self): return real.__enter__()
            def __exit__(self, *args): return real.__exit__(*args)
            def acquire(self, blocking=True): return False if not blocking and self.fail_try else real.acquire(blocking)
            def release(self): return real.release()
        proxy = Lock(); h.service.lock = proxy
        h.runner._diagnostic_mark = lambda phase, status=None: setattr(proxy, 'fail_try', True) if phase == 'execute_start' else None
        h.run(); s = self.observed(h); c = s['counters']
        self.assertEqual((c['cancelled_busy'], c['cancelled'], c['process_errors']), (1, 1, 0))
        self.assertEqual(h.service.retry_health()['withdrawn_after_slot'], 1)
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(s['events'][-1]['cancel_reason_code'], 5)

    def test_vart_exception_and_status_failure_propagate_and_remain_process_errors(self):
        for status in (None, -3):
            h = make()
            if status is None: h.native.failure = RuntimeError('synthetic actual native failure')
            else: h.native.status = status
            with self.assertRaises(RuntimeError): h.run()
            c = self.observed(h)['counters']
            self.assertEqual((c['process_errors'], c['cancelled'], c['slot_unavailable'], c['active_attempts']), (1, 0, 0, 0))
            self.assertEqual(h.service.retry_health()['withdrawn_after_slot'], 0)
            self.assertEqual(h.native.submitted, 1)

    def test_observer_failure_does_not_remove_retry_or_replace_business_outcome(self):
        h = make(); h.deny()
        class Broken:
            def __getattr__(self, name): raise RuntimeError('observer unavailable')
        h.service._freshness = Broken()
        h.event(.025, lambda: (h.allow(), h.offer(2))); h.run()
        self.assertEqual(h.native_fids, [2])
        self.assertEqual(h.service.processed, 1)
        self.assertEqual(len(h.publications), 1)
        self.assertTrue(h.service.health()['freshness_metrics']['observer_unavailable'])
        self.assertEqual(h.service.health()['freshness_metrics']['schema_version'], 'aura-face-freshness-light-3')
        self.assertEqual(h.service.retry_health()['denied'], 1)

    def test_cancel_reason_values_are_bounded_enums_and_counters(self):
        recorder = FaceFreshnessMetrics(ttl_ms=1000)
        for reason in (0, 1, 2, 3, 4, 5, -1, 'private string', True):
            token = recorder.begin(0)
            token.update(input_now_ms=0, outcome_code=6, cancel_reason_code=reason)
            recorder.finish(token)
        s = recorder.snapshot(); c = s['counters']
        self.assertEqual((c['cancelled'], c['cancelled_other'], c['process_errors'], c['slot_unavailable']), (9, 4, 0, 0))
        self.assertTrue(all(type(e['cancel_reason_code']) is int and 0 <= e['cancel_reason_code'] <= 5 for e in s['events']))
        self.assertNotIn('private string', repr(s))


if __name__ == '__main__': unittest.main()
