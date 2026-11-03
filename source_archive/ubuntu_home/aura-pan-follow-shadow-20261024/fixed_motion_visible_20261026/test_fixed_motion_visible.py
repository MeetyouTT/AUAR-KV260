from dataclasses import replace
import copy
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(Path(__file__).resolve().parent),
               str(ROOT / 'continuous_v10r15_candidate'), str(ROOT / 'offline_host_driver')]
from fixed_bench_adapter import FixedBenchDriver
from register_model import Clock, Registers
from vsrv_driver import PhysicalReference, BUILD_ID
from run_fixed_motion import BenchFailure, BenchPermit, plan_digest, run_fixed_motion
from plan_fixed import make_plan


def rig(initial_us=1420):
    clock = Clock()
    io = Registers(clock, initial_us)
    device = FixedBenchDriver(io, BUILD_ID, 'fixture-current-boot', minimum_us=1402, maximum_us=1420,
                              clock=clock, sleep=clock.sleep)
    ref = PhysicalReference('fixture-current-boot', 1420, 'fixture-setup', 'fixture-observation', 1, True, True)
    return device, io, clock, ref


def armed():
    device, io, clock, ref = rig()
    device.confirm_and_arm(ref, 1234, 41, authorized=True)
    return device, io, clock, ref


def submit(device, target=1420, deadline=15., maximum=100):
    return device.submit_bench(target, absolute_deadline_s=deadline, maximum_lease_ms=maximum, margin_ms=20)


def integrated_run(device, clock, ref):
    rows = make_plan(1420, -1)
    permit = BenchPermit(device.boot_id, 'fixture-authorization', 'fixture-observation', 1420,
                         1402, 1420, 1234, 9., 17., plan_digest(rows))
    return run_fixed_motion(device, ref, permit, rows, clock=clock, sleep=clock.sleep)


class RegisterAdapterTests(unittest.TestCase):
    def test_five_second_frozen_geometry_and_unchanged_kinematic_limits(self):
        rows = make_plan(1420, -1)
        self.assertEqual(len(rows), 251)
        self.assertEqual([r['time_ms'] for r in rows], list(range(0, 5001, 20)))
        self.assertEqual([min(r['target_us'] for r in rows), max(r['target_us'] for r in rows)], [1405, 1420])
        for index, target in ((0, 1420), (125, 1405), (248, 1420), (250, 1420)):
            self.assertAlmostEqual(rows[index]['position_us'], target, places=7)
            self.assertAlmostEqual(rows[index]['velocity_us_s'], 0., places=7)
            self.assertAlmostEqual(rows[index]['acceleration_us_s2'], 0., places=7)
        for row in rows:
            self.assertLessEqual(abs(row['velocity_us_s']), 10. + 1e-7)
            self.assertLessEqual(abs(row['acceleration_us_s2']), 100. + 1e-7)
        for a, b in zip(rows, rows[1:]):
            self.assertLessEqual(abs(b['target_us'] - a['target_us']), 1)
            self.assertLessEqual(abs(b['acceleration_us_s2'] - a['acceleration_us_s2']) / .02, 800. + 1e-7)

    def test_adapter_accepts_fifteen_us_but_rejects_sixteenth_us_inside_window(self):
        d, io, clock, ref = armed()
        for target in range(1419, 1404, -1):
            submit(d, target)
            clock.sleep(.02)
        self.assertEqual(len(io.commits), 15)
        with self.assertRaisesRegex(RuntimeError, 'TARGET_OR_STEP'):
            submit(d, 1404)
        self.assertEqual(len(io.commits), 15)
        self.assertEqual(io.values[0x0c], 0)

    def test_core_rejects_sixteen_us_plan_even_if_approved_window_contains_it(self):
        d, io, clock, ref = rig()
        rows = make_plan(1420, -1)
        rows[125].update(position_us=1404., target_us=1404)
        permit = BenchPermit(d.boot_id, 'fixture-authorization', 'fixture-observation', 1420,
                             1402, 1420, 1234, 9., 17., plan_digest(rows))
        with self.assertRaisesRegex(RuntimeError, 'FIFTEEN_US'):
            run_fixed_motion(d, ref, permit, rows, clock=clock, sleep=clock.sleep)
        self.assertEqual(io.writes, [])

    def test_initial_deadline_cannot_exceed_five_seconds(self):
        d, io, clock, ref = armed()
        with self.assertRaisesRegex(RuntimeError, 'FIVE_SECONDS'):
            submit(d, deadline=15.001)
        self.assertEqual(io.commits, [])

    def test_cli_reports_visible_plan_and_still_refuses_unauthorized_execution(self):
        script = Path(__file__).with_name('run_fixed_motion.py')
        planned = subprocess.run([sys.executable, '-B', str(script)], capture_output=True, text=True, timeout=3)
        refused = subprocess.run([sys.executable, '-B', str(script), '--execute'], capture_output=True, text=True, timeout=3)
        self.assertEqual(planned.returncode, 0)
        self.assertIn('"maximum_duration_s": 5', planned.stdout)
        self.assertIn('"planned_submissions": 248', planned.stdout)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn('EXECUTION_REFUSED', refused.stderr)

    def test_real_driver_core_248_command_roundtrip_and_final_stop(self):
        d, io, clock, ref = rig()
        report = integrated_run(d, clock, ref)
        self.assertEqual(len(io.commits), 248)
        self.assertEqual(len(report['commands']), 248)
        self.assertEqual(min(x['target_us'] for x in io.commits), 1405)
        self.assertEqual(io.values[0x2c], 1420)
        self.assertEqual(io.values[0x0c], 0)
        self.assertEqual(io.quiesces, 1)
        self.assertLess(clock(), 15.)
        self.assertTrue(all(x['lease_ms'] <= 100 and x['expiry_s'] <= 14.98 + 1e-9 for x in io.commits))
        self.assertFalse(report['hardware_absolute_deadline_guaranteed'])

    def test_pwm_phase_and_delayed_target_change_allow_one_hold_of_known_old_width(self):
        d, io, clock, ref = rig()
        # First COMMIT shifts PWM edges to 5+20n ms. The 580ms target change
        # commits at 589ms, after the 585ms boundary. At 600ms the next hold
        # legitimately still reads the previous width until the 605ms edge.
        io.commit_pauses_s = {1: .005, 30: .009}
        report = integrated_run(d, clock, ref)
        a, b = [x['acknowledgement']['readback'] for x in report['commands'][29:31]]
        self.assertEqual((a['target_us'], a['width_us'], a['ack_seq']), (1415, 1416, 30))
        self.assertEqual((b['target_us'], b['width_us'], b['ack_seq']), (1415, 1416, 31))
        self.assertEqual(len(io.commits), 248)
        self.assertEqual(report['stopped_readback']['width_us'], 1420)
        self.assertEqual(report['stopped_readback']['target_us'], 1420)
        self.assertTrue(report['stop_confirmed'])

    def test_new_core_transition_set_still_rejects_unknown_in_window_width(self):
        d, io, clock, ref = rig()
        io.commit_pauses_s = {1: .005, 30: .009}
        original = d.submit_bench
        def corrupt_ack(*args, **kwargs):
            ack = original(*args, **kwargs)
            if ack['readback']['ack_seq'] == 31:
                ack['readback']['width_us'] = 1418  # In approved range but not a known transition.
            return ack
        d.submit_bench = corrupt_ack
        with self.assertRaises(BenchFailure) as failure:
            integrated_run(d, clock, ref)
        self.assertEqual(failure.exception.report['error']['message'], 'UNEXPECTED_PWM_WIDTH')
        self.assertEqual(len(io.commits), 31)
        self.assertTrue(failure.exception.report['stop_confirmed'])

    def test_default_1500_is_not_adopted_as_observed_1420(self):
        d, io, clock, ref = rig(1500)
        with self.assertRaisesRegex(RuntimeError, 'POSITION'):
            d.confirm_and_arm(ref, 1234, 41, authorized=True)
        self.assertEqual(io.commits, [])
        self.assertFalse(any(v in (0x42494e44, 0x52454621, 0x41524d21) for _, n, v in io.writes if n == 0x24))

    def test_first_commit_requires_at_least_23ms_and_no_late_arm_permission(self):
        for maximum, deadline in ((22, 15.), (100, 10.045)):
            d, io, clock, ref = armed()
            with self.assertRaisesRegex(RuntimeError, 'TOO_SHORT'):
                submit(d, maximum=maximum, deadline=deadline)
            self.assertEqual(io.commits, [])
            self.assertEqual(io.values[0x0c], 0)

    def test_exact_23ms_initial_lease_and_next_frame_target_latch(self):
        d, io, clock, ref = armed()
        ack = submit(d, 1419, maximum=23)
        self.assertEqual(ack['lease_ms'], 23)
        self.assertEqual(ack['readback']['target_us'], 1419)
        self.assertEqual(ack['readback']['width_us'], 1420)
        clock.sleep(.020)
        self.assertEqual(d.status()['width_us'], 1419)

    def test_deadline_cannot_change_after_first_submission(self):
        for changed in (14.999, 15.001):
            d, io, clock, ref = armed()
            submit(d)
            with self.assertRaisesRegex(RuntimeError, 'DEADLINE_CHANGED'):
                submit(d, deadline=changed)
            self.assertEqual(len(io.commits), 1)
            self.assertEqual(io.values[0x0c], 0)

    def test_target_window_and_one_us_step_are_enforced(self):
        for target in (1421, 1418, 1414):
            d, io, clock, ref = armed()
            with self.assertRaisesRegex(RuntimeError, 'TARGET_OR_STEP'):
                submit(d, target)
            self.assertEqual(io.commits, [])

    def test_known_shadow_delay_is_rejected_before_commit(self):
        d, io, clock, ref = armed()
        io.shadow_pause_s = 5.1
        with self.assertRaisesRegex(RuntimeError, 'TOO_SHORT'):
            submit(d)
        self.assertEqual(io.commits, [])
        self.assertEqual(io.values[0x0c], 0)

    def test_native_q09_delay_can_commit_late_but_is_detected_and_stopped(self):
        d, io, clock, ref = armed()
        io.native_pause_s = 5.1
        with self.assertRaisesRegex(RuntimeError, 'NATIVE_WRITE_OR_READBACK_LATE'):
            submit(d)
        self.assertEqual(len(io.commits), 1)
        self.assertGreater(io.commits[0]['time_s'], 15.)
        self.assertEqual(io.values[0x0c], 0)
        self.assertFalse(d.hardware_absolute_deadline_guaranteed)

    def test_wrong_session_epoch_seq_target_width_or_lease_stops(self):
        for offset, value in ((0x34, 55), (0x38, 77), (0x28, 20), (0x44, 1418), (0x2c, 1500), (0x40, 1500), (0x0c, 64)):
            with self.subTest(offset=offset):
                d, io, clock, ref = armed()
                io.after_commit_mutation = {offset: value}
                with self.assertRaises(RuntimeError): submit(d)
                self.assertEqual(io.values[0x0c], 0)
                self.assertEqual(len(io.commits), 1)

    def test_real_lease_expiry_before_next_submit_never_restarts(self):
        d, io, clock, ref = armed()
        submit(d)
        clock.sleep(.101)
        with self.assertRaisesRegex(RuntimeError, 'CONTEXT_OR_LEASE_LOST'):
            submit(d)
        self.assertEqual(len(io.commits), 1)
        self.assertEqual(io.values[0x0c], 0)

    def test_batch_snapshot_pause_keeps_expiry_lower_and_upper_bounds(self):
        d, io, clock, ref = armed()
        io.ack_read_pause_s = .025
        ack = submit(d)
        self.assertAlmostEqual(ack['snapshot_started_mono_s'], 10.)
        self.assertAlmostEqual(ack['observed_mono_s'], 10.025)
        self.assertLess(ack['lease_expiry_lower_bound_mono_s'], io.expiry)
        self.assertGreater(ack['lease_expiry_upper_bound_mono_s'], io.expiry)
        self.assertEqual(len(io.commits), 1)

    def test_fractional_millisecond_renewal_uses_existing_rtl_tick_phase(self):
        d, io, clock, ref = armed()
        submit(d)
        clock.sleep(.0205)
        ack = submit(d)
        self.assertAlmostEqual(io.expiry, 10.120)
        self.assertLess(ack['lease_expiry_lower_bound_mono_s'], io.expiry)
        self.assertGreater(ack['lease_expiry_upper_bound_mono_s'], io.expiry)

    def test_core_rejects_cached_ack_when_pause_crosses_expiry_lower_bound(self):
        d, io, clock, ref = rig()
        io.ack_read_pause_s = .025
        original = d.submit_bench
        def delayed_return(*args, **kwargs):
            ack = original(*args, **kwargs)
            clock.sleep(.090)
            return ack
        d.submit_bench = delayed_return
        with self.assertRaises(BenchFailure) as failure:
            integrated_run(d, clock, ref)
        self.assertIn('ACK', failure.exception.report['error']['message'])
        self.assertEqual(len(io.commits), 1)
        self.assertTrue(failure.exception.report['stop_confirmed'])

    def test_primary_io_error_survives_stop_error_with_cleanup_evidence(self):
        d, io, clock, ref = armed()
        first, second = OSError('injected COMMIT failure'), OSError('injected STOP failure')
        io.commit_error, io.stop_error = first, second
        with self.assertRaises(OSError) as caught:
            submit(d)
        self.assertIs(caught.exception, first)
        self.assertEqual(d.last_failure['stop_error']['message'], str(second))
        self.assertFalse(d.last_failure['stop_confirmed'])

    def test_finish_wait_is_clipped_to_remaining_absolute_deadline(self):
        d, io, clock, ref = armed()
        submit(d)
        clock.now = 14.98
        io.expiry = 15.05  # Keep model active to isolate QUIESCE deadline handling.
        io.quiesce_delay_s = .03
        with self.assertRaisesRegex(RuntimeError, 'QUIESCE_.*DEADLINE'):
            d.finish(absolute_deadline_s=15.)
        self.assertLessEqual(clock(), 15. + 1e-9)
        self.assertEqual(io.values[0x0c], 0)

    def test_face_submit_api_is_disabled(self):
        d, io, clock, ref = armed()
        with self.assertRaisesRegex(RuntimeError, 'FACE_SOURCE_SUBMIT_DISABLED'):
            d.submit(1419, clock())
        self.assertEqual(io.commits, [])
        self.assertEqual(io.values[0x0c], 0)


if __name__ == '__main__': unittest.main()
