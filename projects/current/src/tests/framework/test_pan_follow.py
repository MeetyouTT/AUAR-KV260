"""Pan commands and failures are software tests, with no physical output."""
from http.server import BaseHTTPRequestHandler
import math
from types import SimpleNamespace
import unittest

from board.motion.camera_feed import install, observation
from board.motion.follow import FixedCameraAnchors, FollowConfig, PanFollowController, ShadowDriver
from board.vision.ui_camera_service import CameraState
from common.motion_observation import MAX_AGE_MS, ObservationError, PROTOCOL, validate


def packet(fid=1, stamp=1000, x=200., score=.9, generation=1, **changes):
    value = {'protocol_version': PROTOCOL, 'source_kind': 'actual', 'board_boot_id': 'boot',
             'service_epoch': 'service', 'camera_epoch': 'camera', 'state': 'READY',
             'source_frame_id': fid, 'source_mono_ms': stamp, 'deadline_mono_ms': stamp+MAX_AGE_MS,
             'frame_width': 640, 'frame_height': 480, 'mirror_horizontal': True,
             'target': {'track_id': 1, 'track_generation': generation,
                        'box': [x, 0., 80., 480.], 'score': score}}
    value.update(changes)
    return value


class PanFollowTests(unittest.TestCase):
    def setUp(self):
        self.driver = ShadowDriver()
        self.controller = PanFollowController(self.driver, 'boot')

    def feed(self, count=6, x=200., start=1, t=1000):
        for i in range(count):
            self.controller.observe(packet(start+i, t+i*100, x=x), t+i*100+50)
        return self.controller.status()

    def test_wait_for_five_distinct_confirmed_sources(self):
        self.feed(4);self.assertEqual(self.driver.submissions, [])
        self.controller.observe(packet(5, 1400), 1450)
        self.assertEqual(len(self.driver.submissions), 1)

    def test_left_in_mirrored_view_increases_pulse_for_confirmed_polarity(self):
        self.feed(15, x=40.)
        self.assertGreater(self.controller.pulse_us, 1500)

    def test_right_decreases_pulse(self):
        self.feed(15, x=520.)
        self.assertLess(self.controller.pulse_us, 1500)

    def test_center_stays_at_reference(self):
        self.feed(30, x=280.)
        self.assertEqual({p for p, _ in self.driver.submissions}, {1500})

    def test_step_rate_and_total_offset_are_bounded(self):
        self.feed(80, x=40.)
        pulses = [1500]+[p for p, _ in self.driver.submissions]
        self.assertTrue(all(1460 <= p <= 1540 for p in pulses))
        self.assertTrue(all(abs(a-b) <= 4 for a, b in zip(pulses, pulses[1:])))
        self.assertEqual(max(pulses), 1540)

    def test_duplicate_does_not_resubmit_or_integrate(self):
        self.feed();before = (len(self.driver.submissions), self.controller.position)
        self.controller.observe(packet(6, 1500), 1600)
        self.assertEqual((len(self.driver.submissions), self.controller.position), before)

    def test_duplicate_cannot_renew_deadline(self):
        self.feed()
        result = self.controller.observe(packet(6, 1500), 1750)
        self.assertEqual(result['reason'], 'SOURCE_EXPIRED')
        self.assertEqual(self.driver.stops, 1)

    def test_source_mutation_latches_stop(self):
        self.feed()
        result = self.controller.observe(packet(6, 1500, x=210.), 1580)
        self.assertEqual(result['reason'], 'SOURCE_MUTATED')

    def test_clock_reversal_stops(self):
        self.feed()
        self.assertEqual(self.controller.poll(1500)['reason'], 'INVALID_CLOCK')

    def test_poll_without_new_frames_expires(self):
        self.feed()
        self.assertEqual(self.controller.poll(1750)['state'], 'DISARMED')

    def test_stop_is_latched_and_does_not_auto_recover(self):
        self.feed()
        self.controller.observe(packet(7, 1600, state='NO_TARGET', target=None), 1650)
        count = len(self.driver.submissions)
        self.feed(6, start=8, t=1700)
        self.assertTrue(self.controller.stopped)
        self.assertEqual(len(self.driver.submissions), count)

    def test_camera_restart_and_service_restart_stop(self):
        for field in ('camera_epoch', 'service_epoch'):
            with self.subTest(field=field):
                self.setUp();self.feed()
                result = self.controller.observe(packet(7, 1600, **{field: 'new'}), 1650)
                self.assertEqual(result['reason'], 'CAMERA_CONTEXT_CHANGED')

    def test_target_or_track_generation_change_stops(self):
        self.feed()
        result = self.controller.observe(packet(7, 1600, generation=2), 1650)
        self.assertEqual(result['reason'], 'TARGET_CHANGED')

    def test_boot_change_never_accepted(self):
        result = self.controller.observe(packet(board_boot_id='new'), 1050)
        self.assertEqual(result['reason'], 'BOOT_CHANGED')
        self.assertEqual(self.driver.submissions, [])

    def test_frame_reordering_stops(self):
        self.feed()
        result = self.controller.observe(packet(5, 1520), 1570)
        self.assertEqual(result['reason'], 'SOURCE_REORDERED')

    def test_low_confidence_and_horizontal_clipping_stop(self):
        for values in ({'score': .2}, {'x': 0.}):
            with self.subTest(values=values):
                self.setUp();result = self.controller.observe(packet(**values), 1050)
                self.assertEqual(result['state'], 'DISARMED')

    def test_future_or_extended_deadline_is_rejected(self):
        for value in (packet(stamp=1100), packet(deadline_mono_ms=1500)):
            with self.subTest(value=value):
                with self.assertRaises(ObservationError):validate(value, 'boot', 1050)

    def test_nonfinite_box_and_bool_timestamp_are_rejected(self):
        value = packet();value['target']['box'][0] = math.nan
        with self.assertRaises(ObservationError):validate(value, 'boot', 1050)
        with self.assertRaises(ObservationError):validate(packet(source_mono_ms=True), 'boot', 1050)

    def test_fixture_needs_explicit_replay_permission(self):
        value = packet(source_kind='fixture')
        with self.assertRaises(ObservationError):validate(value, 'boot', 1050)
        self.assertEqual(validate(value, 'boot', 1050, allow_fixture=True)['source_kind'], 'fixture')

    def test_cannot_use_shadow_driver_for_physical_control(self):
        with self.assertRaises(ValueError):PanFollowController(self.driver, 'boot', physical=True)

    def test_stationary_camera_requires_measured_mapping(self):
        with self.assertRaises(ValueError):PanFollowController(self.driver, 'boot', camera_moves_with_axis=False)

    def test_stationary_target_does_not_accumulate_to_limit(self):
        anchors = FixedCameraAnchors('boot', 'camera', 'setup', 1500, -1, -.5, 1520, .5, 1480, 'test fixture', True)
        self.controller = PanFollowController(self.driver, 'boot', camera_moves_with_axis=False, anchors=anchors)
        self.feed(80, x=120.)  # normalized centre -0.5 -> fixed pulse 1520
        self.assertEqual(self.controller.pulse_us, 1520)
        self.assertTrue(all(p <= 1520 for p, _ in self.driver.submissions))

    def test_changed_anchor_camera_is_rejected(self):
        anchors = FixedCameraAnchors('boot', 'old-camera', 'setup', 1500, -1, -.5, 1520, .5, 1480, 'fixture', True)
        self.controller = PanFollowController(self.driver, 'boot', camera_moves_with_axis=False, anchors=anchors)
        self.assertEqual(self.controller.observe(packet(), 1050)['reason'], 'ANCHOR_CAMERA_CHANGED')

    def test_rejected_ack_does_not_advance_position(self):
        self.driver.submit = lambda *a: {'outcome': 'UNKNOWN'}
        self.feed(5)
        self.assertEqual(self.controller.position, 1500.)
        self.assertTrue(self.controller.stopped)

    def test_transport_error_stops_and_propagates(self):
        def fail(*args):raise OSError('fixture IO fault')
        self.driver.submit = fail
        with self.assertRaises(OSError):self.feed(5)
        self.assertTrue(self.controller.stopped)
        self.assertTrue(self.controller.stop_confirmed)

    def test_failed_stop_is_never_reported_confirmed(self):
        def fail():raise OSError('fixture stop fault')
        self.driver.stop = fail
        with self.assertRaises(OSError):self.controller.stop()
        self.assertTrue(self.controller.stopped)
        self.assertFalse(self.controller.stop_confirmed)

    def test_deadband_hysteresis_avoids_chatter(self):
        self.feed(5, x=280.)
        self.assertFalse(self.controller.engaged)
        # Error .0375 is inside the engage threshold; remain centred.
        self.feed(8, x=292., start=6, t=1500)
        self.assertFalse(self.controller.engaged)
        self.assertEqual(self.controller.pulse_us, 1500)

    def test_invalid_config_rejected(self):
        for values in ({'rate_us_s': 500}, {'step_us': 5}, {'deadband_enter': .01}, {'confirm_frames': 1}):
            with self.subTest(values=values), self.assertRaises(ValueError):FollowConfig(**values)


class CameraFeedTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.state = CameraState('boot', 'service', clock=lambda: self.now)
        self.state.camera_epoch = 'camera'
        self.state.captured(1000)
        self.state.observed(1, 1000, {'target_id': 1, 'tracks': [
            {'track_id': 1, 'generation': 1, 'visible': True, 'confirmed': True,
             'frame_id': 1, 'captured_at': 1., 'box': [100., 0., 100., 480.], 'score': .9}]}, 10.)

    def test_export_is_source_bound_and_contains_no_identity_or_images(self):
        value = observation(self.state)
        self.assertEqual(validate(value, 'boot', 1000)['target']['track_id'], 1)
        self.assertNotIn('identity', value);self.assertNotIn('image', value)
        self.assertEqual(value['source_mono_ms'], 1000)

    def test_refresh_does_not_change_capture_timestamp(self):
        first = observation(self.state);self.now += 100
        self.assertEqual(observation(self.state), first)

    def test_fresh_preview_cannot_refresh_old_detection(self):
        self.now += 251;self.state.captured(self.now)
        self.assertEqual(observation(self.state)['state'], 'EXPIRED')

    def test_pending_selection_hides_old_target(self):
        self.state.requested_target = 2
        self.assertEqual(observation(self.state)['state'], 'TARGET_PENDING')

    def test_only_the_selected_measured_track_is_exported(self):
        self.state.observation['tracks'][0]['frame_id'] = 2
        self.assertEqual(observation(self.state)['state'], 'INCONSISTENT_SOURCE')

    def test_camera_or_detector_error_hides_target(self):
        for field in ('camera_error', 'detector_error'):
            with self.subTest(field=field):
                self.setUp();setattr(self.state, field, 'fixture')
                self.assertIsNone(observation(self.state)['target'])

    def test_handler_registration_is_idempotent_and_preserves_original_route(self):
        seen = []
        class Original(BaseHTTPRequestHandler):
            def do_GET(self):seen.append(self.path)
            def respond(self, status, body):self.captured_response = status, body
        module = SimpleNamespace(handler_for=lambda state: Original)
        install(module);factory = module.handler_for;install(module)
        self.assertIs(module.handler_for, factory)
        handler = object.__new__(factory(self.state))
        handler.path = '/health';handler.do_GET();self.assertEqual(seen, ['/health'])
        handler.path = '/v1/motion/observation';handler.do_GET()
        self.assertEqual(handler.captured_response[1]['state'], 'READY')


if __name__ == '__main__':
    unittest.main()
