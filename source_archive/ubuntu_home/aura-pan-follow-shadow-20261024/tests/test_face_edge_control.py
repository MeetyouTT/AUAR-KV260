"""Verify wide safe-zone hold, hysteresis and bounded smooth face proposals."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'motion_v2'))
sys.path.insert(0, str(ROOT))
from common.motion_observation import PROTOCOL
from face_edge_control import EdgeConfig, FaceEdgeController


def packet(fid, stamp, x, width=80., **changes):
    p = {'protocol_version': PROTOCOL, 'source_kind': 'fixture', 'target_kind': 'face',
         'board_boot_id': 'boot', 'service_epoch': 'service', 'camera_epoch': 'camera',
         'state': 'READY', 'source_frame_id': fid, 'source_mono_ms': stamp,
         'deadline_mono_ms': stamp+250, 'frame_width': 640, 'frame_height': 480,
         'mirror_horizontal': True, 'target': {'track_id': 1, 'track_generation': 1,
                                              'box': [x, 100., width, 80.], 'score': .95}}
    p.update(changes)
    return p


class EdgeTests(unittest.TestCase):
    def setUp(self):
        self.c = FaceEdgeController('boot', 1435)
        self.fid = 0

    def feed(self, xs):
        rows = []
        for x in xs:
            self.fid += 1
            stamp = 1000+self.fid*100
            rows.append(self.c.observe(packet(self.fid, stamp, x), stamp+25, allow_fixture=True))
        return rows

    def test_faces_anywhere_inside_safe_zone_hold_current_framing(self):
        self.feed([100., 150., 280., 400., 450.]*4)
        self.assertEqual(self.c.pulse_us, 1435)
        self.assertEqual(self.c.velocity, 0.)
        self.assertEqual(self.c.reason, 'SAFE_ZONE_HOLD')

    def test_right_edge_increases_pulse_with_observed_mirrored_polarity(self):
        self.feed([550.]*8)
        self.assertGreater(self.c.pulse_us, 1435)
        self.assertEqual(self.c.edge, 1)

    def test_left_edge_decreases_pulse(self):
        self.feed([10.]*8)
        self.assertLess(self.c.pulse_us, 1435)
        self.assertEqual(self.c.edge, -1)

    def test_hysteresis_keeps_following_until_safe_margin_is_recovered(self):
        self.feed([550.]*7)
        self.feed([500.]*5)  # right margin .09375: outside entry, inside exit.
        self.assertEqual(self.c.edge, 1)
        self.feed([350.]*8)
        self.assertEqual(self.c.edge, 0)
        self.assertEqual(self.c.velocity, 0.)
        self.assertEqual(self.c.reason, 'SAFE_ZONE_HOLD')

    def test_speed_acceleration_step_and_position_are_bounded(self):
        previous = self.c.position
        velocity = 0.
        for r in self.feed([550.]*15):
            self.assertLessEqual(abs(self.c.config.maximum_speed_us_s), 20)
            self.assertLessEqual(abs(r['velocity_us_s']), 12)
            self.assertTrue(1425 <= r['pulse_us'] <= 1445)
        self.c = FaceEdgeController('boot', 1435)
        self.fid = 0
        for _ in range(8):
            self.feed([550.])
            self.assertLessEqual(abs(self.c.position-previous), 2.000001)
            if self.c.reason != 'AT_LIMIT':
                self.assertLessEqual(abs(self.c.velocity-velocity), 4.000001)
            previous, velocity = self.c.position, self.c.velocity

    def test_duplicate_does_not_integrate_or_refresh_source(self):
        self.feed([550.]*5)
        before = self.c.position, self.c.velocity, self.c.proposals
        stamp = 1000+self.fid*100
        self.c.observe(packet(self.fid, stamp, 550.), stamp+100, allow_fixture=True)
        self.assertEqual(before, (self.c.position, self.c.velocity, self.c.proposals))
        self.c.observe(packet(self.fid, stamp, 550.), stamp+250, allow_fixture=True)
        self.assertEqual(self.c.reason, 'SOURCE_EXPIRED')
        self.feed([550.]*3)
        self.assertTrue(self.c.stopped)

    def test_multiple_faces_or_track_change_latches(self):
        self.feed([300.]*3)
        stamp = 1000+(self.fid+1)*100
        self.c.observe(packet(self.fid+1, stamp, 300., state='MULTIPLE_FACES', target=None), stamp+20, allow_fixture=True)
        self.assertEqual(self.c.reason, 'SOURCE_MULTIPLE_FACES')
        self.c = FaceEdgeController('boot', 1435)
        self.fid = 0
        self.feed([300.]*3)
        p = packet(4, 1400, 300.)
        p['target']['track_generation'] = 2
        self.c.observe(p, 1420, allow_fixture=True)
        self.assertEqual(self.c.reason, 'FACE_CONTEXT_CHANGED')

    def test_body_source_is_never_used_as_fallback(self):
        self.c.observe(packet(1, 1000, 300., target_kind='person'), 1020, allow_fixture=True)
        self.assertEqual(self.c.reason, 'FACE_SOURCE_REQUIRED')

    def test_unconfirmed_frame_waits_without_proposal_or_source_deadline_renewal(self):
        self.feed([550.]*5)
        before=(self.c.pulse_us,self.c.proposals,self.c.source)
        p=packet(6,1600,550.,state='UNCONFIRMED',target=None)
        value=self.c.observe(p,1580,allow_fixture=True)
        self.assertFalse(self.c.stopped);self.assertFalse(value['new_source'])
        self.assertEqual(before,(self.c.pulse_us,self.c.proposals,self.c.source))
        self.c.observe(p,1750,allow_fixture=True)
        self.assertEqual(self.c.reason,'SOURCE_EXPIRED')

    def test_invalid_face_and_bounds_rejected(self):
        p = packet(1, 1000, 300.)
        p['target']['score'] = .5
        self.c.observe(p, 1020, allow_fixture=True)
        self.assertEqual(self.c.reason, 'FACE_QUALITY')
        for cfg in ({'enter_margin': .2, 'exit_margin': .1}, {'maximum_us': 1450}, {'maximum_acceleration_us_s2': 1000}):
            with self.assertRaises(ValueError):
                EdgeConfig(**cfg)


if __name__ == '__main__':
    unittest.main()
