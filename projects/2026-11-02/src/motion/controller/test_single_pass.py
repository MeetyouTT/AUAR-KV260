"""Actual session and trajectory with a latched visual-center episode."""
import copy
from dataclasses import replace
import unittest
from test_recenter import Scene,profile


def single_scene(reference=1469):
    f=Scene(reference)
    f.session.config=replace(profile(),single_pass_recenter=True,smooth_recenter_stop=True,
                             maximum_speed_us_s=40.,velocity_gain_us=0.)
    f.session.controller=f.session.fresh()
    return f


class SinglePassTests(unittest.TestCase):
    def test_position_and_velocity_jitter_do_not_recompute_cruise_speed(self):
        f=single_scene();f.trigger();s=f.session
        for x in [.84,.87,.85,.88,.84,.86]*5:
            f.feed([x])
            self.assertEqual(s.controller.requested_speed,40.)
            self.assertEqual(s.controller.recenter_direction,1)
            self.assertEqual(s.controller.recenter_phase,'CRUISE')
        self.assertFalse(s.fatal)

    def test_three_motion_phases_only_slow_down_until_center_completion(self):
        f=single_scene();f.trigger();s=f.session
        f.feed([.72]*3);self.assertEqual(s.controller.requested_speed,40.)
        f.feed([.64]*3);self.assertEqual(s.controller.requested_speed,18.)
        f.feed([.70]*3);self.assertEqual(s.controller.requested_speed,18.)
        f.feed([.56]*3);self.assertEqual(s.controller.requested_speed,8.)
        f.feed([.63]*3);self.assertEqual(s.controller.requested_speed,8.)
        f.feed([.52]*3);self.assertEqual(s.controller.requested_speed,0.)
        self.assertEqual(s.controller.recenter_phase,'COMPLETE')
        self.assertFalse(s.controller.recenter_active)
        f.feed([.5]*12);held=f.device.pulse
        f.feed([.42,.60,.70,.55,.50]*4)
        self.assertEqual(f.device.pulse,held)

    def test_confirmed_overshoot_completes_without_reversing(self):
        f=single_scene();f.trigger();f.feed([.70]*3+[.60]*3+[.55]*3)
        before=len(f.device.commands);f.feed([.45]*4)
        self.assertFalse(f.session.controller.recenter_active)
        self.assertEqual(f.session.controller.requested_speed,0.)
        self.assertTrue(all(c['target']>=f.device.commands[before-1]['target']
                            for c in f.device.commands[before:]))

    def test_left_box_triggers_one_negative_direction_episode(self):
        f=single_scene(reference=1530);f.feed([.30]*5+[.16]*12)
        self.assertEqual(f.session.controller.recenter_direction,-1)
        self.assertEqual(f.session.controller.requested_speed,-40.)
        f.feed([.30]*3+[.37]*3)
        self.assertEqual(f.session.controller.requested_speed,-18.)
        f.feed([.45]*3)
        self.assertEqual(f.session.controller.requested_speed,-8.)
        f.feed([.49]*10)
        self.assertFalse(f.session.controller.recenter_active)
        self.assertEqual(f.session.controller.requested_speed,0.)

    def test_inside_faces_do_not_trigger_any_centering_move(self):
        f=single_scene();f.feed([.3,.4,.5,.6,.7]*8)
        self.assertEqual(f.device.arms,0);self.assertFalse(f.device.commands)

    def test_actual_loss_stops_and_same_face_restores_only_goal_direction_phase(self):
        f=single_scene();f.trigger();f.feed([.70]*3+[.64]*3)
        f.loss();s=f.session;before=len(f.device.commands)
        self.assertEqual(s.recenter_intent['original_side'],1)
        self.assertEqual(s.recenter_intent['phase'],'BRAKING')
        self.assertEqual(s.pva[1:], [0.,0.])
        f.tick(4);f.feed([.70]*12)
        self.assertGreater(len(f.device.commands),before)
        self.assertEqual(s.controller.recenter_direction,1)
        self.assertEqual(s.controller.requested_speed,18.)

    def test_no_reverse_after_loss_when_person_has_already_crossed_center(self):
        f=single_scene();f.trigger();f.loss();before=len(f.device.commands)
        f.feed([.4]*10)
        self.assertFalse(f.session.controller.recenter_active)
        self.assertEqual(len(f.device.commands),before)

    def test_changed_face_cannot_inherit_direction(self):
        f=single_scene();f.trigger();f.loss();before=len(f.device.commands)
        for _ in range(8):
            p=f.packet(.65);p['target']['track_generation']=2
            f.session.step(p);f.tick(4)
        self.assertFalse(f.session.controller.recenter_active)
        self.assertEqual(len(f.device.commands),before)

    def test_source_and_anchor_expiry_still_win_over_single_pass_goal(self):
        f=single_scene();f.trigger();source=copy.deepcopy(f.last)
        f.tick(15);before=len(f.device.commands)
        self.assertFalse(f.session.active)
        f.session.step(source);f.tick(10)
        self.assertEqual(len(f.device.commands),before)
        self.assertEqual(f.device.status()['flags'],0)

    def test_soft_limit_never_claims_visual_center_completion(self):
        f=single_scene(reference=1590);f.feed([.86]*50)
        self.assertFalse(f.session.fatal)
        self.assertTrue(f.session.controller.recenter_active)
        self.assertFalse(f.session.controller.recenter_completed)
        self.assertTrue(all(1400<=c['target']<=1600 for c in f.device.commands))

    def test_cruise_steps_remain_bounded_under_original_four_us_source_budget(self):
        f=single_scene();f.trigger()
        s=f.session;before=len(f.device.commands);origin=s.source_origin
        f.tick(12)
        self.assertTrue(all(abs(c['target']-origin)<=4 for c in f.device.commands[before:]))
        self.assertTrue(all(c['deadline']<=c['stamp']+c['freshness_s'] for c in f.device.commands))
        self.assertFalse(s.fatal)


if __name__=='__main__':unittest.main()
