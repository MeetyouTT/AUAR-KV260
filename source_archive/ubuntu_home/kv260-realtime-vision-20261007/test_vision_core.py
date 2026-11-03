"""Behavioral tests: association continuity, expiry and non-actuating control."""
import unittest
from vision_core import FaceTracks, ControlPreview, display_observation


def face(x, y=100, w=80, h=80):
    return [x,y,w,h]+[0.]*10+[.99]


class VisionTests(unittest.TestCase):
    def test_confirm_move_and_hold_target(self):
        t=FaceTracks('a')
        self.assertIsNone(t.update([face(200)],1,1.,640,480)['target_id'])
        s=t.update([face(205)],2,1.1,640,480)
        self.assertEqual(s['target_id'],1)
        s=t.update([face(210),face(420,w=150,h=150)],3,1.2,640,480)
        s=t.update([face(215),face(420,w=150,h=150)],4,1.3,640,480)
        self.assertEqual(s['target_id'],1)
        self.assertEqual(len(s['tracks']),2)

    def test_loss_does_not_refresh_observation(self):
        t=FaceTracks('a')
        t.update([face(200)],1,1.,640,480)
        s=t.update([face(200)],2,1.1,640,480)
        control=ControlPreview()
        self.assertTrue(control.update(s,640,1.11)['valid'])
        missing=t.update([],3,1.2,640,480)
        self.assertEqual(missing['tracks'][0]['observed_time'],1.1)
        self.assertFalse(display_observation(missing,1.21)['target_visible'])
        self.assertFalse(control.update(missing,640,1.21)['valid'])
        returned=t.update([face(200)],4,1.3,640,480)
        self.assertEqual(returned['target_id'],1)
        self.assertTrue(display_observation(returned,1.31)['target_visible'])
        t.update([],5,1.9,640,480)
        t.update([face(200)],6,2.,640,480)
        new=t.update([face(200)],7,2.1,640,480)
        self.assertEqual(new['target_id'],2)

    def test_frozen_frames_and_out_of_order_rejected(self):
        t=FaceTracks('a')
        t.update([face(200)],1,1.,640,480)
        s=t.update([face(200)],2,1.1,640,480)
        self.assertFalse(display_observation(s,1.4)['target_visible'])
        self.assertEqual(display_observation(s,1.4)['state'],'STALE')
        self.assertFalse(ControlPreview().update(s,640,1.4)['valid'])
        self.assertFalse(ControlPreview().update(s,640,.9)['valid'])
        with self.assertRaises(ValueError):t.update([face(200)],2,1.2,640,480)
        with self.assertRaises(ValueError):t.update([face(200)],3,1.,640,480)

    def test_control_uses_dt_and_never_authorizes_actuation(self):
        t=FaceTracks('a')
        t.update([face(440)],1,1.,640,480)
        s=t.update([face(440)],2,1.1,640,480)
        c=ControlPreview()
        self.assertEqual(c.update(s,640,1.11)['virtual_delta_deg'],0.)
        s=t.update([face(440)],3,1.2,640,480)
        v=c.update(s,640,1.21)
        self.assertAlmostEqual(v['raw_error'],.5)
        self.assertAlmostEqual(v['virtual_delta_deg'],1.)
        self.assertEqual(v['direction'],'RIGHT')
        self.assertFalse(v['motion_command_emitted'])
        self.assertFalse(v['actuation_authorized'])
        self.assertFalse(c.update(s,640,1.22)['valid'])
        other=FaceTracks('new-epoch')
        other.update([face(440)],1,1.,640,480)
        s=other.update([face(440)],2,1.1,640,480)
        self.assertEqual(c.update(s,640,1.11)['virtual_delta_deg'],0.)

    def test_clipped_boxes_and_invalid_inputs(self):
        t=FaceTracks('a',confirm_observations=1)
        s=t.update([face(-10),face(100,w=-1),face(float('nan')),face(700)],1,1.,640,480)
        self.assertEqual(len(s['tracks']),1)
        self.assertEqual(s['tracks'][0]['box'],[0.,100.,70.,80.])
        c=ControlPreview()
        centered=FaceTracks('b',confirm_observations=1).update([face(280)],1,1.,640,480)
        v=c.update(centered,640,1.01)
        self.assertEqual(v['direction'],'CENTER')
        self.assertEqual(v['virtual_delta_deg'],0.)


if __name__=='__main__':
    unittest.main()
