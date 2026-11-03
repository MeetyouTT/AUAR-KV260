from dataclasses import replace
import unittest
from test_left_episode import configured
from hardware_slew_session import HardwareSlewSession

def stable_scene(reference=1600):
    f=configured(reference=reference)
    cfg=replace(f.session.config,rearm_stability_ms=150)
    f.session=HardwareSlewSession(f.device,'fixture-boot',cfg,f.session.factory,
        trajectory=f.session.trajectory,clock=lambda:f.now,allow_fixture=True)
    return f

def interrupted(reference=1600):
    f=stable_scene(reference)
    points=[.1]*4+[.16,.22,.28] if reference==1600 else [.86]*4+[.80,.74,.68]
    f.feed(points)
    assert f.device.commands and f.session.active
    f.session.step(f.packet(state='UNCONFIRMED'))
    assert not f.session.active and f.device.status()['flags']==0
    return f

class RearmStabilityTests(unittest.TestCase):
    def test_config_validation_and_default_compatibility(self):
        from continuous_face_control import EdgeConfig
        for bad in (-1,501,True,150.,'150'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):replace(EdgeConfig(),rearm_stability_ms=bad)
        self.assertEqual(EdgeConfig().rearm_stability_ms,0)
        self.assertEqual(replace(EdgeConfig(),rearm_stability_ms=150).rearm_stability_ms,150)

    def test_protective_loss_still_stops_immediately_without_pwm_renewal(self):
        f=interrupted();before=len(f.device.commands)
        self.assertEqual(f.device.status()['flags'],0)
        self.assertEqual(f.device.status()['lease_left_ms'],0)
        self.assertIsNotNone(f.session.rearm_stability_gate)
        f.tick(4)
        self.assertEqual(len(f.device.commands),before)
        self.assertFalse(f.session.active)

    def test_no_short_restart_and_post_arm_rule_and_left_target_kept(self):
        f=interrupted();arms=f.device.arms;commands=len(f.device.commands)
        f.feed([.28]*3)
        self.assertFalse(f.session.active);self.assertEqual(f.device.arms,arms)
        self.assertEqual(len(f.device.commands),commands)
        self.assertEqual(f.session.status()['reason'],'WAITING_FOR_STABLE_REARM')
        f.session.step(f.packet(.28))
        self.assertTrue(f.session.active);self.assertEqual(f.device.arms,arms+1)
        self.assertIsNone(f.session.controller.source)
        self.assertEqual(len(f.device.commands),commands)
        self.assertEqual(f.session.status()['target_center_ratio'],.4)
        f.tick(4);f.feed([.28])
        self.assertGreater(len(f.device.commands),commands)
        self.assertEqual({c['target'] for c in f.device.commands},{1400})
        self.assertTrue(all(c['deadline']<=c['stamp']+c['freshness_s'] for c in f.device.commands))

    def test_right_target_and_direction_kept_after_stability_gate(self):
        f=interrupted(reference=1400);commands=len(f.device.commands)
        f.feed([.68]*5)
        self.assertTrue(f.session.active)
        self.assertGreater(len(f.device.commands),commands)
        self.assertEqual(f.session.status()['target_center_ratio'],.45)
        self.assertEqual(f.session.controller.recenter_trigger_side,1)
        self.assertEqual({c['target'] for c in f.device.commands},{1600})

    def test_duplicate_frames_do_not_advance_stability(self):
        f=interrupted();f.feed([.28]*2)
        before=f.session.rearm_stability_gate['distinct_sources'];commands=len(f.device.commands)
        p=f.last
        for _ in range(5):f.session.step(p)
        self.assertEqual(f.session.rearm_stability_gate['distinct_sources'],before)
        self.assertFalse(f.session.active);self.assertEqual(len(f.device.commands),commands)

    def test_queued_images_cannot_supply_elapsed_wall_stability(self):
        f=interrupted();f.now+=.18;now=round(f.now*1000)
        for age in (230,220,120,20):
            p=f.packet(.28);p['source_mono_ms']=now-age;p['deadline_mono_ms']=now-age+250;p['face_detection_mono_ms']=now-age
            f.session.step(p)
        gate=f.session.rearm_stability_gate
        self.assertGreaterEqual(gate['stable_source_ms'],150)
        self.assertEqual(gate['stable_wall_ms'],0)
        self.assertFalse(f.session.active)

    def test_same_old_detection_anchor_cannot_rearm(self):
        f=interrupted();anchor=f.session.rearm_stability_gate['interrupted_anchor_ms']
        for _ in range(4):
            p=f.packet(.28);p['face_detection_mono_ms']=anchor;f.session.step(p);f.tick(4)
        gate=f.session.rearm_stability_gate
        self.assertIsNotNone(gate);self.assertFalse(gate['new_detection_seen'])
        self.assertGreaterEqual(gate['stable_wall_ms'],150)
        self.assertFalse(f.session.active)
        f.session.step(f.packet(.28));self.assertTrue(f.session.active)

    def test_new_gap_resets_stability_progress_without_motion(self):
        f=interrupted();f.feed([.28]*3)
        self.assertGreater(f.session.rearm_stability_gate['distinct_sources'],0)
        f.session.step(f.packet(state='UNCONFIRMED'))
        self.assertEqual(f.session.rearm_stability_gate['distinct_sources'],0)
        f.feed([.28]*2)
        self.assertFalse(f.session.active)
        self.assertEqual(f.device.status()['flags'],0)
        self.assertLess(f.session.rearm_stability_gate['stable_wall_ms'],150)

    def test_expired_goal_does_not_resume_inside_face(self):
        f=interrupted();commands=len(f.device.commands);f.now+=2.01;f.feed([.28]*8)
        self.assertFalse(f.session.active);self.assertIsNone(f.session.recenter_intent)
        self.assertEqual(len(f.device.commands),commands)
        self.assertEqual(f.session.controller.recenter_trigger_side,0)

    def test_late_tick_anchor_and_stream_loss_keep_original_stops(self):
        for kind in ('late_tick','old_anchor','disconnect'):
            f=stable_scene();f.feed([.1]*4+[.16,.22,.28]);commands=len(f.device.commands)
            if kind=='late_tick':f.now+=.11;f.session.tick()
            elif kind=='old_anchor':
                p=f.packet(.28);p['face_detection_mono_ms']=round(f.now*1000)-501;f.session.step(p)
            else:f.session.disconnected()
            self.assertFalse(f.session.active,kind);self.assertEqual(f.device.status()['flags'],0,kind)
            self.assertEqual(f.device.status()['lease_left_ms'],0,kind)
            self.assertEqual(len(f.device.commands),commands,kind)

    def test_normal_completion_and_next_first_start_have_no_gate_delay(self):
        f=stable_scene();f.feed([.1]*4+[.16,.22,.28,.34,.38])
        self.assertEqual(f.session.visual_center_completions,1)
        self.assertIsNone(f.session.rearm_stability_gate)

if __name__=='__main__':unittest.main(verbosity=2)
