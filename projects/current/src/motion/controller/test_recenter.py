"""Real ContinuousSession/Ruckig with fake register owner; no camera or board."""
import copy
import hashlib
import platform
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from continuous_face_control import EdgeConfig
from continuous_session import ContinuousSession
from trajectory import Trajectory
from common.motion_observation import PROTOCOL
from test_continuous_session import Device


def profile():
    return EdgeConfig(left_ratio=.1,maximum_correction_us=None,confirm_frames=2,
        maximum_speed_us_s=30.,maximum_acceleration_us_s2=120.,gain_us_s=200.,
        minimum_edge_speed_us_s=6.,velocity_gain_us=24.,prearm_confirmed_face=True,
        recenter_on_edge=True,target_center_ratio=.5,center_tolerance_ratio=.03)


class Scene:
    def __init__(self,reference=1469):
        self.now=10.;self.fid=0;self.last=None
        self.device=Device(lambda:self.now)
        self.device.pulse=self.device.accepted_target_us=reference
        library=(HERE/'libaura_trajectory.so' if platform.machine()=='aarch64'
                 else HERE.parent/'ps_trajectory_v1/libaura_trajectory_compat_host.so')
        solver=Trajectory(library,hashlib.sha256(library.read_bytes()).hexdigest())
        self.session=ContinuousSession(self.device,'fixture-boot',profile(),
            lambda p:SimpleNamespace(reference_us=p),trajectory=solver,
            clock=lambda:self.now,allow_fixture=True)
    def packet(self,center=.5,**extra):
        self.fid+=1;stamp=round(self.now*1000)-60
        value=dict(protocol_version=PROTOCOL,source_kind='fixture',target_kind='face',
            board_boot_id='fixture-boot',service_epoch='service',camera_epoch='camera',
            state='READY',source_frame_id=self.fid,source_mono_ms=stamp,deadline_mono_ms=stamp+250,
            face_detection_mono_ms=stamp,frame_width=640,frame_height=480,mirror_horizontal=True,
            target=dict(track_id=1,track_generation=1,box=[center*640-40,100.,80.,80.],score=.95))
        value.update(extra)
        if value['state']!='READY':
            value.update(target=None,source_frame_id=None,source_mono_ms=None,deadline_mono_ms=None)
        self.last=copy.deepcopy(value)
        return value
    def tick(self,count=4):
        for _ in range(count):self.now+=.02;self.session.tick()
    def feed(self,centers,**extra):
        for center in centers:self.session.step(self.packet(center,**extra));self.tick()
    def trigger(self):
        self.feed([.78]*4+[.86]*12)
        assert self.session.controller.recenter_active and self.session.motion_updates>0
    def loss(self):
        self.session.step(self.packet(state='UNCONFIRMED'))
        assert not self.session.active and self.device.status()['flags']==0


class RecenterTests(unittest.TestCase):
    def test_right_trigger_keeps_moving_after_return_to_original_region_then_holds_at_center(self):
        f=Scene();f.trigger();before=f.device.pulse
        f.feed([.76]*8)
        self.assertTrue(f.session.controller.recenter_active)
        self.assertGreater(f.device.pulse,before)
        f.feed([.68]*3+[.60]*3+[.55]*3+[.52]*2)
        held=f.device.pulse
        self.assertEqual(f.session.reason,'SAFE_ZONE_HOLD')
        self.assertEqual(f.session.status()['recenter_state'],'AT_CENTER')
        f.feed([.49,.55,.60,.68,.72,.58,.50]*3)
        self.assertEqual(f.device.pulse,held)
        self.assertFalse(f.session.controller.recenter_active)

    def test_left_box_trigger_and_inside_region_recenter(self):
        f=Scene();f.feed([.30]*5+[.16]*12)
        self.assertGreater(f.session.controller.raw_center,.1)
        self.assertLessEqual(f.session.controller.raw_left_ratio,.1)
        self.assertTrue(f.session.controller.recenter_active)
        before=f.device.pulse;f.feed([.26]*6)
        self.assertLess(f.device.pulse,before)
        self.assertTrue(f.session.controller.recenter_active)

    def test_inside_center_area_never_prearms_or_moves(self):
        f=Scene();f.feed([.45,.50,.55,.6,.65,.7,.4]*4)
        self.assertEqual(f.device.arms,0)
        self.assertEqual(f.device.commands,[])

    def test_near_original_line_prearms_without_pwm_and_trigger_uses_same_arm(self):
        f=Scene();f.feed([.78]*8)
        self.assertEqual(f.device.arms,1);self.assertEqual(f.device.commands,[])
        f.feed([.86]*8)
        self.assertEqual(f.device.arms,1);self.assertTrue(f.device.commands)

    def test_confirmed_crossing_center_completes_instead_of_reversing(self):
        f=Scene();f.trigger();f.feed([.76]*3+[.65]*3+[.55]*3)
        f.session.step(f.packet(.45));held=f.device.pulse;f.tick()
        self.assertEqual(f.session.reason,'SAFE_ZONE_HOLD')
        self.assertFalse(f.session.controller.recenter_active)
        f.feed([.43,.48,.55,.60]*3)
        self.assertEqual(f.device.pulse,held)

    def test_short_loss_physically_stops_and_intent_resumes_only_with_new_confirmed_face(self):
        f=Scene();f.trigger();f.feed([.76]*4);f.loss()
        stopped_count=len(f.device.commands);arms=f.device.arms
        f.tick(25)
        self.assertEqual(len(f.device.commands),stopped_count)
        self.assertTrue(f.session.status()['recenter_intent_pending'])
        first=f.packet(.70);f.session.step(first)
        self.assertEqual(f.session.controller.warmup,1)
        self.assertEqual(f.session.controller.center_filter.timestamp_s,first['source_mono_ms']/1000.)
        self.assertEqual(f.device.arms,arms)
        f.tick();f.session.step(f.packet(.70))
        self.assertEqual(f.device.arms,arms+1)
        self.assertEqual(len(f.device.commands),stopped_count)  # ARM did not revive old PWM.
        f.feed([.70]*10)
        self.assertGreater(len(f.device.commands),stopped_count)
        self.assertTrue(f.session.controller.recenter_active)

    def test_duplicate_old_ready_frame_after_loss_does_not_reconfirm_or_erase_intent(self):
        f=Scene();f.trigger();old=copy.deepcopy(f.last);f.loss()
        count=len(f.device.commands);intent=copy.deepcopy(f.session.recenter_intent)
        f.session.step(old)
        self.assertEqual(f.session.controller.warmup,0)
        self.assertEqual(f.session.recenter_intent,intent)
        self.assertEqual(len(f.device.commands),count)

    def test_two_second_expired_intent_does_not_restart_inside_original_region(self):
        f=Scene();f.trigger();f.loss();count=len(f.device.commands)
        f.tick(110);f.feed([.70]*8)
        self.assertFalse(f.session.controller.recenter_active)
        self.assertFalse(f.session.status()['recenter_intent_pending'])
        self.assertEqual(len(f.device.commands),count)

    def test_different_person_or_camera_epoch_cannot_inherit_pending_intent(self):
        for mode in ('person','camera','service'):
            f=Scene();f.trigger();f.loss();count=len(f.device.commands)
            for _ in range(8):
                p=f.packet(.70)
                if mode=='person':p['target']['track_generation']=2
                elif mode=='camera':p['camera_epoch']='camera-new'
                else:p['service_epoch']='service-new'
                f.session.step(p);f.tick()
            self.assertFalse(f.session.controller.recenter_active)
            self.assertEqual(len(f.device.commands),count)

    def test_target_change_multiple_faces_and_body_stop_and_clear_intent(self):
        for mode in ('person','multiple','body'):
            f=Scene();f.trigger();p=f.packet(.76)
            if mode=='person':p['target']['track_generation']=2
            elif mode=='multiple':p=f.packet(state='MULTIPLE_FACES')
            else:p['target_kind']='body'
            f.session.step(p)
            self.assertFalse(f.session.active);self.assertEqual(f.device.status()['flags'],0)
            self.assertFalse(f.session.status()['recenter_intent_pending'])

    def test_expired_anchor_cannot_refresh_pending_intent_or_arm(self):
        f=Scene();f.trigger();f.loss();intent=copy.deepcopy(f.session.recenter_intent);arms=f.device.arms
        p=f.packet(.70);p['face_detection_mono_ms']=p['source_mono_ms']-501
        f.session.step(p)
        self.assertEqual(f.session.recenter_intent,intent)
        self.assertEqual(f.device.arms,arms);self.assertEqual(f.device.status()['flags'],0)

    def test_segment_time_limit_stops_then_new_frames_resume_semantic_goal(self):
        f=Scene();f.trigger();f.feed([.76]*4)
        f.session.segment_start=f.now-10.;f.tick(1)
        self.assertFalse(f.session.active);self.assertEqual(f.device.status()['flags'],0)
        self.assertEqual(f.session.reason,'MOTION_SEGMENT_TIME_LIMIT')
        self.assertTrue(f.session.status()['recenter_intent_pending'])
        before=len(f.device.commands);f.feed([.70]*10)
        self.assertGreater(len(f.device.commands),before)
        self.assertTrue(f.session.controller.recenter_active)

    def test_operator_close_clears_pending_goal_after_source_loss(self):
        f=Scene();f.trigger();f.loss()
        self.assertTrue(f.session.status()['recenter_intent_pending'])
        f.session.close()
        self.assertFalse(f.session.status()['recenter_intent_pending'])

    def test_limit_brakes_and_holds_without_crossing_hardware_range(self):
        f=Scene(reference=1590);f.feed([.86]*90)
        self.assertFalse(f.session.fatal)
        self.assertTrue(all(1400<=c['target']<=1600 for c in f.device.commands))
        self.assertEqual(len({c['target'] for c in f.device.commands[-15:]}),1)
        self.assertEqual(f.session.state,'HOLD_AT_LIMIT')

    def test_actual_source_deadlines_and_four_us_source_budget_remain(self):
        f=Scene();f.trigger()
        for command in f.device.commands:
            self.assertLessEqual(command['deadline'],command['stamp']+.25+1e-9)
        rows=list(f.session.command_trace)
        self.assertTrue(all(abs(r['delta_us'])<=4 and abs(r['velocity_us_s'])<=30.001
                            and abs(r['acceleration_us_s2'])<=120.001 for r in rows))
        before=len(f.device.commands);f.tick(15)
        self.assertFalse(f.session.active);after=len(f.device.commands);f.tick(15)
        self.assertEqual(len(f.device.commands),after)
        self.assertEqual(f.device.status()['flags'],0)

    def test_new_center_band_checks_do_not_break_legacy_configs(self):
        EdgeConfig(right_ratio=.4)
        with self.assertRaises(ValueError):EdgeConfig(right_ratio=.4,recenter_on_edge=True)


if __name__=='__main__':unittest.main()
