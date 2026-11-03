import copy
from dataclasses import replace
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

from plan_fixed import make_plan
from run_fixed_motion import BenchFailure, BenchPermit, plan_digest, run_fixed_motion


class Clock:
    def __init__(self):
        self.now = 10.
        self.sleeps = 0
        self.late_sleep = None
        self.late_extra_s = .031

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps += 1
        self.now += seconds + (self.late_extra_s if self.sleeps == self.late_sleep else 0.)


class FakeDriver:
    """Independent lease/PWM clock. No real devices or production source packets."""
    boot_id = 'fixture-current-boot'

    def __init__(self, clock, initial=1420):
        self.clock = clock
        self.flags, self.reason, self.seq, self.session, self.epoch = 0, 0, 0, 0, 40
        self.target = self.width = initial
        self.expires = self.latch_at = None
        self.arms = self.stops = self.finishes = self.attempts = self.commits = 0
        self.mode = None
        self.stop_raises = self.stop_unconfirmed = False
        self.deadlines = []
        self.stop_delay_s = 0.
        self.shared_ack = {'readback': {}}

    def status(self):
        if self.flags == 15 and self.clock() >= self.expires:
            self.flags, self.reason = 64, 4
        if self.latch_at is not None and self.clock() >= self.latch_at:
            self.width = self.target
            self.latch_at = None
        if self.mode == 'expired_status' and self.seq == 3 and self.flags == 15:
            self.flags, self.reason = 64, 4
        return dict(flags=self.flags, reason=self.reason, ack_seq=self.seq, session=self.session,
                    epoch=self.epoch, target_us=self.target, width_us=self.width,
                    lease_left_ms=max(1, math.floor((self.expires - self.clock()) * 1000 + 1e-8)) if self.flags == 15 else 0)

    def confirm_and_arm(self, reference, session, epoch, *, authorized):
        assert authorized and self.flags == 0 and self.width == reference.reference_us
        self.arms += 1
        self.session, self.epoch, self.seq, self.flags = session, epoch, 0, 14

    def submit_bench(self, target, *, absolute_deadline_s, maximum_lease_ms, margin_ms):
        self.attempts += 1
        self.deadlines.append(absolute_deadline_s)
        if self.mode == 'raise_submit':
            raise OSError('injected submit IO error')
        if self.mode == 'native_pause':
            self.clock.now += 3.
        # Independent adapter rejects lateness at COMMIT, not merely in caller.
        budget = min(maximum_lease_ms, math.floor((absolute_deadline_s - self.clock()) * 1000 - margin_ms + 1e-8))
        if budget < 3 or self.flags not in (14, 15):
            return dict(outcome='REJECTED', reason='EXPIRED_BENCH_WINDOW')
        self.seq += 1
        self.commits += 1
        self.target, self.flags = target, 15
        self.expires = self.clock() + budget / 1000.
        self.latch_at = self.clock() + .02
        observed = self.clock()
        rb = self.status()
        if self.mode == 'bad_seq': rb['ack_seq'] += 1
        if self.mode == 'bad_session': rb['session'] += 1
        if self.mode == 'bad_epoch': rb['epoch'] += 1
        if self.mode == 'bad_width': rb['width_us'] = 1500
        if self.mode == 'bad_lease': rb['lease_left_ms'] = 101
        if self.mode == 'bad_target': rb['target_us'] += 1
        if self.mode == 'bad_sample_time': observed -= .01
        if self.mode == 'cached_ack_pause': self.clock.now += .15
        if self.mode == 'reuse_ack':
            self.shared_ack.update(outcome='ACCEPTED', observed_mono_s=observed)
            self.shared_ack['readback'].clear()
            self.shared_ack['readback'].update(rb)
            return self.shared_ack
        return dict(outcome='ACCEPTED', observed_mono_s=observed, readback=rb)

    def finish(self, *, absolute_deadline_s):
        self.finishes += 1
        if self.mode == 'raise_finish':
            raise OSError('injected QUIESCE IO error')
        assert self.clock() < absolute_deadline_s
        self.status()
        self.flags = self.reason = 0
        return self.status()

    def stop(self):
        self.stops += 1
        if self.stop_raises:
            raise OSError('injected STOP IO error')
        self.status()
        if self.stop_unconfirmed:
            self.flags, self.expires = 15, self.clock() + .1
        else:
            self.flags = self.reason = 0
        self.clock.now += self.stop_delay_s
        return self.status()


class FixedCoreTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.driver = FakeDriver(self.clock)
        self.reference = SimpleNamespace(boot_id=self.driver.boot_id, reference_us=1420, confirmed=True)
        self.rows = make_plan(1420, -1)
        self.permit = BenchPermit(self.driver.boot_id, 'fixture-permission', 'fixture-observation',
                                  1420, 1415, 1420, 1234, 9., 14., plan_digest(self.rows))

    def run_core(self):
        return run_fixed_motion(self.driver, self.reference, self.permit, self.rows,
                                 clock=self.clock, sleep=self.clock.sleep)

    def failed_report(self):
        with self.assertRaises(BenchFailure) as cm:
            self.run_core()
        return cm.exception.report

    def test_complete_roundtrip_records_every_submission_and_stops_before_deadline(self):
        r = self.run_core()
        self.assertEqual(len(r['commands']), 98)
        self.assertEqual(self.driver.commits, 98)
        self.assertEqual((self.driver.arms, self.driver.finishes, self.driver.stops), (1, 1, 1))
        self.assertEqual(set(self.driver.deadlines), {12.})
        self.assertAlmostEqual(r['commands'][-1]['scheduled_mono_s'], 11.94)
        self.assertAlmostEqual(r['completed_mono_s'], 11.96)
        self.assertEqual(r['stopped_readback']['width_us'], 1420)
        self.assertTrue(r['stop_confirmed'])
        self.assertFalse(r['hardware_absolute_deadline_guaranteed'])
        self.assertEqual(min(x['target_us'] for x in r['commands']), 1415)

    def test_current_default_width_cannot_be_used_as_old_physical_reference(self):
        self.driver.width = self.driver.target = 1500
        r = self.failed_report()
        self.assertIn('OBSERVED_REFERENCE', r['error']['message'])
        self.assertEqual((self.driver.arms, self.driver.commits, self.driver.stops), (0, 0, 1))

    def test_wrong_boot_and_expired_permit_do_not_arm(self):
        original = self.permit
        for permit in (replace(original, boot_id='old-boot'), replace(original, valid_until_mono_s=11.9)):
            with self.subTest(permit=permit):
                self.permit = permit
                with self.assertRaises(RuntimeError): self.run_core()
        self.assertEqual((self.driver.arms, self.driver.commits), (0, 0))

    def test_outside_window_and_modified_plan_are_rejected_before_any_motion(self):
        original = self.permit
        for permit in (replace(original, minimum_us=1416), replace(original, plan_sha256='wrong')):
            self.permit = permit
            with self.assertRaises(RuntimeError): self.run_core()
        self.assertEqual((self.driver.arms, self.driver.commits), (0, 0))

    def test_late_tick_stops_without_catchup_submissions(self):
        self.clock.late_sleep = 4
        r = self.failed_report()
        self.assertIn('LATE_TICK', r['error']['message'])
        self.assertEqual(self.driver.commits, 4)
        self.assertTrue(r['stop_confirmed'])

    def test_19ms_late_slot_cannot_burst_the_next_submission_1ms_later(self):
        self.clock.late_sleep, self.clock.late_extra_s = 4, .019
        r = self.failed_report()
        self.assertIn('SPACING_NO_CATCHUP', r['error']['message'])
        self.assertEqual(self.driver.commits, 5)
        times = [x['submitted_mono_s'] for x in r['commands']]
        self.assertTrue(all(b - a >= .01 - 1e-9 for a, b in zip(times, times[1:])))
        self.assertTrue(r['stop_confirmed'])

    def test_expired_actual_lease_stops_before_next_submission(self):
        self.driver.mode = 'expired_status'
        r = self.failed_report()
        self.assertIn('CONTEXT_LOST', r['error']['message'])
        self.assertEqual(self.driver.commits, 3)
        self.assertTrue(r['stop_confirmed'])

    def test_wrong_ack_context_width_lease_or_sample_time_never_retries(self):
        for mode in ('bad_seq', 'bad_session', 'bad_epoch', 'bad_width', 'bad_lease', 'bad_target', 'bad_sample_time'):
            with self.subTest(mode=mode):
                self.setUp()
                self.driver.mode = mode
                r = self.failed_report()
                self.assertEqual(self.driver.attempts, 1)
                self.assertTrue(r['stop_confirmed'])
                self.assertFalse(r['status'].startswith('FIXED_BENCH_ACK_AND_STOP_PASS'))

    def test_independent_native_delay_guard_prevents_commit_after_deadline(self):
        self.driver.mode = 'native_pause'
        r = self.failed_report()
        self.assertEqual(self.driver.commits, 0)
        self.assertIn('AFTER_ABSOLUTE_DEADLINE', r['error']['message'])
        self.assertEqual(self.driver.stops, 1)

    def test_cached_ack_that_expired_during_pause_is_rejected(self):
        self.driver.mode = 'cached_ack_pause'
        r = self.failed_report()
        self.assertIn('ACK_LEASE_OUTSIDE', r['error']['message'])
        self.assertEqual(self.driver.commits, 1)
        self.assertTrue(r['stop_confirmed'])

    def test_submit_exception_still_stops(self):
        self.driver.mode = 'raise_submit'
        r = self.failed_report()
        self.assertEqual(r['error']['type'], 'OSError')
        self.assertEqual(self.driver.stops, 1)
        self.assertEqual(len(r['commands']), 1)

    def test_stop_error_is_secondary_to_ack_error_and_no_pass_proof(self):
        self.driver.mode, self.driver.stop_raises = 'bad_seq', True
        r = self.failed_report()
        self.assertIn('CONTEXT_LOST', r['error']['message'])
        self.assertEqual(r['stop_error']['type'], 'OSError')
        self.assertFalse(r['stop_confirmed'])
        self.assertIsNone(r['stopped_readback'])

    def test_unconfirmed_stop_is_never_success(self):
        self.driver.stop_unconfirmed = True
        r = self.failed_report()
        self.assertIn('STOP_NOT_CONFIRMED', r['error']['message'])
        self.assertFalse(r['stop_confirmed'])

    def test_stop_returning_after_deadline_is_not_a_passing_timed_run(self):
        self.driver.stop_delay_s = .1
        r = self.failed_report()
        self.assertIn('FINAL_STOP_RETURNED_AFTER_DEADLINE', r['error']['message'])
        self.assertFalse(r['stop_confirmed'])
        self.assertEqual(r['stopped_readback']['flags'], 0)
        self.assertGreater(r['completed_mono_s'], r['absolute_deadline_mono_s'])

    def test_reused_adapter_ack_dictionary_does_not_mutate_earlier_evidence(self):
        self.driver.mode = 'reuse_ack'
        r = self.run_core()
        snapshots = [x['acknowledgement']['readback'] for x in r['commands']]
        self.assertEqual([x['ack_seq'] for x in snapshots], list(range(1, 99)))
        self.driver.shared_ack['readback']['ack_seq'] = 999
        self.assertEqual(snapshots[-1]['ack_seq'], 98)

    def test_finish_exception_still_uses_final_stop(self):
        self.driver.mode = 'raise_finish'
        r = self.failed_report()
        self.assertEqual(r['error']['type'], 'OSError')
        self.assertTrue(r['stop_confirmed'])
        self.assertEqual(self.driver.stops, 1)

    def test_cli_defaults_to_plan_and_explicit_execution_is_refused(self):
        script = Path(__file__).with_name('run_fixed_motion.py')
        plan = subprocess.run([sys.executable, '-B', str(script)], capture_output=True, text=True, timeout=3)
        refusal = subprocess.run([sys.executable, '-B', str(script), '--execute'], capture_output=True, text=True, timeout=3)
        self.assertEqual(plan.returncode, 0)
        self.assertIn('PLAN_ONLY', plan.stdout)
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn('EXECUTION_REFUSED', refusal.stderr)


if __name__ == '__main__':
    unittest.main()
