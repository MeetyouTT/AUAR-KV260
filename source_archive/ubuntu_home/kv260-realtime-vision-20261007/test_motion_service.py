"""Command acceptance, frozen evidence, bounded motion and recovery contracts."""
from dataclasses import replace
import unittest
from motion_service import MotionConfig, MotionService, SimMotionPort


def observation(fid, t, center=480., epoch='cam', tid=1, generation=1, visible=True):
    return {'epoch': epoch, 'frame_id': fid, 'observed_time': t, 'target_id': tid,
            'tracks': [{'epoch': epoch, 'frame_id': fid, 'observed_time': t,
                        'track_id': tid, 'generation': generation, 'visible': visible,
                        'confirmed': True, 'box': [center-40, 100., 80., 80.]}]}


class RejectOncePort(SimMotionPort):
    def __init__(self, config):
        super().__init__(config)
        self.reject_next = True

    def submit(self, command, now):
        if self.reject_next:
            self.reject_next = False
            return {'outcome': 'REJECTED', 'reason': 'INJECTED_REJECT',
                    'scope': self.kind, 'ack_seq': self.accepted_seq,
                    'accepted_mdeg': self.accepted_mdeg}
        return super().submit(command, now)


class UnknownPort(SimMotionPort):
    def submit(self, command, now):
        super().submit(command, now)
        return {'outcome': 'UNKNOWN', 'reason': 'INJECTED_LOST_ACK'}


class WrongAckPort(SimMotionPort):
    def submit(self, command, now):
        r = super().submit(command, now)
        r['session'] = 'different-session'
        return r


class MotionTests(unittest.TestCase):
    def service(self, config=None, port=None):
        s = MotionService('boot', 'cam', config, port)
        s.resume_simulation(0.)
        return s

    def observe(self, s, fid, t, center=480., latency=.05, **kwargs):
        return s.observe(observation(fid, t, center, **kwargs), 640, 480, t+latency, 'boot')

    def start(self, s, center=480.):
        self.assertEqual(self.observe(s, 1, 1., center)['control']['reason'], 'TARGET_INITIALIZED')
        return self.observe(s, 2, 1.1, center)

    def test_startup_requires_explicit_simulation_resume(self):
        s = MotionService('boot', 'cam')
        r = self.observe(s, 1, 1.)
        self.assertEqual(r['state'], 'DISARMED')
        self.assertEqual(r['simulated_submit_attempts'], 0)

    def test_proportional_actual_dt_and_polarity(self):
        for polarity, center, sign in [(1, 480, 1), (1, 160, -1), (-1, 480, -1)]:
            with self.subTest(polarity=polarity, center=center):
                s = self.service(replace(MotionConfig(), polarity=polarity))
                r = self.start(s, center)
                self.assertEqual(r['controller_accepted_mdeg'], sign*1000)
                r = self.observe(s, 3, 1.25, center)
                self.assertEqual(r['controller_accepted_mdeg'], sign*2500)
                self.assertFalse(r['physical_actuation_authorized'])
                self.assertFalse(r['motion_command_emitted'])

    def test_center_renews_only_new_real_observations(self):
        s = self.service()
        r = self.start(s, 320)
        self.assertEqual(r['controller_accepted_mdeg'], 0)
        self.assertEqual(r['control']['direction'], 'CENTER')
        deadline = s.port.deadline
        r = s.observe(observation(2, 1.1, 320), 640, 480, 1.2, 'boot')
        self.assertEqual(r['control']['reason'], 'NO_NEW_OBSERVATION')
        self.assertEqual(s.port.deadline, deadline)
        r = self.observe(s, 3, 1.2, 320)
        self.assertEqual(r['controller_accepted_seq'], 2)
        self.assertGreater(s.port.deadline, deadline)

    def test_new_sequence_cannot_refresh_frozen_source_time(self):
        s = self.service()
        self.start(s)
        deadline = s.port.deadline
        r = s.observe(observation(3, 1.1), 640, 480, 1.2, 'boot')
        self.assertEqual(r['control']['reason'], 'NO_NEW_OBSERVATION')
        self.assertEqual(s.port.deadline, deadline)

    def test_expiry_without_observe_and_no_automatic_rearm(self):
        s = self.service()
        self.start(s)
        deadline = s.port.deadline
        r = s.poll(deadline+.001)
        self.assertEqual(r['state'], 'FAULT')
        self.assertEqual(r['reason'], 'LEASE_EXPIRED')
        self.assertFalse(r['simulated_output_active'])
        r = self.observe(s, 3, deadline+.01)
        self.assertEqual(r['control']['reason'], 'SIM_REQUIRES_EXPLICIT_RESUME')
        self.assertEqual(r['simulated_acceptances'], 1)

    def test_loss_stops_and_reappearance_requires_resume(self):
        s = self.service()
        self.start(s)
        r = self.observe(s, 3, 1.2, visible=False)
        self.assertEqual(r['state'], 'DISARMED')
        self.assertFalse(r['simulated_output_active'])
        r = self.observe(s, 4, 1.3)
        self.assertEqual(r['control']['reason'], 'SIM_REQUIRES_EXPLICIT_RESUME')
        old_session = s.session
        s.resume_simulation(1.36)
        self.assertNotEqual(s.session, old_session)
        self.observe(s, 5, 1.4)
        r = self.observe(s, 6, 1.5)
        self.assertEqual(r['controller_accepted_seq'], 1)
        self.assertEqual(r['controller_accepted_mdeg'], 1000)

    def test_stale_and_future_evidence_disarm(self):
        for latency in [.251, -.001]:
            s = self.service()
            r = self.observe(s, 1, 1., latency=latency)
            self.assertEqual(r['control']['reason'], 'STALE_OBSERVATION')
            self.assertEqual(r['state'], 'DISARMED')

    def test_resume_rejects_pre_reference_frame(self):
        s = self.service()
        s.resume_simulation(1.1)
        r = self.observe(s, 1, 1., latency=.15)
        self.assertEqual(r['control']['reason'], 'PRE_REFERENCE_OBSERVATION')
        self.assertEqual(r['simulated_acceptances'], 0)

    def test_boot_epoch_generation_changes_do_not_continue_old_motion(self):
        for change in ['boot', 'epoch', 'generation', 'track_id']:
            s = self.service()
            self.start(s)
            snap = observation(3, 1.2)
            boot = 'boot'
            if change == 'boot':
                boot = 'another-boot'
            elif change == 'epoch':
                snap['epoch'] = 'another-camera'
            elif change == 'generation':
                snap['tracks'][0]['generation'] = 2
            else:
                snap['target_id'] = snap['tracks'][0]['track_id'] = 2
            r = s.observe(snap, 640, 480, 1.25, boot)
            self.assertFalse(r['simulated_output_active'])
            self.assertEqual(r['simulated_acceptances'], 1)

    def test_rejection_does_not_advance_angle_or_sequence(self):
        c = MotionConfig()
        s = self.service(c, RejectOncePort(c))
        r = self.start(s)
        self.assertEqual(r['controller_accepted_mdeg'], 0)
        self.assertEqual(r['controller_accepted_seq'], 0)
        r = self.observe(s, 3, 1.2)
        self.assertEqual(r['controller_accepted_mdeg'], 1000)
        self.assertEqual(r['controller_accepted_seq'], 1)
        self.assertEqual(r['simulated_rejections'], 1)

    def test_unknown_or_mismatched_ack_faults_without_advancing_controller(self):
        for cls in [UnknownPort, WrongAckPort]:
            c = MotionConfig()
            s = self.service(c, cls(c))
            r = self.start(s)
            self.assertEqual(r['state'], 'FAULT')
            self.assertEqual(r['reason'], 'UNKNOWN_ACCEPTANCE')
            self.assertEqual(r['controller_accepted_mdeg'], 0)
            self.assertFalse(r['simulated_output_active'])

    def test_lease_never_outlives_original_observation_budget(self):
        s = self.service()
        r = self.start(s)
        cmd = r['control']['source']
        self.assertLessEqual(s.port.deadline, cmd['source_observed_time']+.25-.02)
        self.assertGreater(cmd['lease_us'], 0)
        self.assertLessEqual(cmd['lease_us'], 180000)

    def test_late_but_still_fresh_frame_cannot_get_tiny_lease(self):
        s = self.service()
        self.observe(s, 1, 1.)
        r = self.observe(s, 2, 1.1, latency=.241)
        self.assertEqual(r['control']['reason'], 'INSUFFICIENT_FRESHNESS_BUDGET')
        self.assertEqual(r['simulated_submit_attempts'], 0)

    def test_bounded_angle_step_rate_and_effective_pulse(self):
        s = self.service()
        initial = self.start(s, 600)
        prior = initial['controller_accepted_mdeg']
        for fid in range(3, 30):
            r = self.observe(s, fid, 1+(fid-1)*.1, 600)
            angle = r['controller_accepted_mdeg']
            self.assertLessEqual(abs(angle-prior), 2000)
            self.assertLessEqual(angle, 5000)
            prior = angle
        self.assertEqual(r['state'], 'AT_LIMIT')
        self.assertEqual(r['controller_accepted_mdeg'], 5000)
        self.assertLessEqual(r['simulated_effective_pulse_us'], 1550.)

    def test_output_model_changes_only_at_frame_boundaries(self):
        s = self.service()
        self.start(s)
        t = s.port.frame_time
        self.assertEqual(s.poll(t+.019)['simulated_effective_pulse_us'], 1500.)
        self.assertEqual(s.poll(t+.021)['simulated_effective_pulse_us'], 1504.)
        self.assertEqual(s.poll(t+.041)['simulated_effective_pulse_us'], 1508.)

    def test_time_gap_does_not_cause_large_catch_up(self):
        s = self.service()
        self.observe(s, 1, 1.)
        r = self.observe(s, 2, 1.26)
        self.assertEqual(r['control']['reason'], 'CONTROL_TIME_GAP')
        self.assertEqual(r['simulated_submit_attempts'], 0)

    def test_malformed_box_or_predicted_time_fails_closed(self):
        for field, value in [('box', [float('nan'), 100, 80, 80]),
                             ('box', [600, 100, 80, 80]), ('observed_time', .9),
                             ('frame_id', 1), ('generation', True)]:
            s = self.service()
            self.start(s)
            snap = observation(3, 1.2)
            snap['tracks'][0][field] = value
            r = s.observe(snap, 640, 480, 1.25, 'boot')
            self.assertEqual(r['state'], 'DISARMED')
            self.assertFalse(r['simulated_output_active'])

    def test_invalid_clock_faults(self):
        for now in [float('nan'), float('inf'), -.1]:
            s = self.service()
            with self.assertRaises(ValueError):
                s.poll(now)
            self.assertEqual(s.status()['state'], 'FAULT')

    def test_repeated_port_commit_does_not_extend_deadline(self):
        s = self.service()
        r = self.start(s)
        cmd = r['control']['source']
        deadline = s.port.deadline
        response = s.port.submit(cmd, 1.16)
        self.assertEqual(response['reason'], 'SEQUENCE_REJECTED')
        self.assertEqual(s.port.deadline, deadline)

    def test_bounded_history_and_invalid_configuration(self):
        s = self.service()
        for fid in range(1, 160):
            self.observe(s, fid, 1+(fid-1)*.1, 320)
        self.assertEqual(len(s.port.history), 128)
        for kwargs in [{'tau_s': 0}, {'submit_margin_s': 0}, {'polarity': 0},
                       {'us_per_deg': 1000}, {'max_rate_deg_s': float('nan')}]:
            with self.assertRaises(ValueError):
                replace(MotionConfig(), **kwargs)


if __name__ == '__main__':
    unittest.main()
