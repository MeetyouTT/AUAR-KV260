"""Synthetic images and independent PL-clock fixture; never opens a device."""
import argparse
import ast
from dataclasses import replace
import importlib.util
import math
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[1]/'src/motion'
sys.path[:0]=[str(SOURCE/'follow'),str(HERE/'fixtures'),str(SOURCE/'controller')]
from continuous_face_control import EdgeConfig,FaceEdgeController
from hardware_slew_session import HardwareSlewSession
from test_hardware_slew import scene

def configured(reference=1600,polarity=1):
    f=scene(reference=reference)
    cfg=replace(f.session.config,left_ratio=.05,target_center_ratio=.45,left_target_center_ratio=.40)
    f.session=HardwareSlewSession(f.device,'fixture-boot',cfg,f.session.factory,
        trajectory=f.session.trajectory,clock=lambda:f.now,allow_fixture=True,polarity=polarity)
    return f

def direct(single=True,polarity=1):
    cfg=replace(configured().session.config,single_pass_recenter=single,hardware_slew_recenter=single)
    c=FaceEdgeController('fixture-boot',1500,config=cfg,polarity=polarity)
    c.filtered_center=.2;c.face_velocity=0.
    return c

class LeftEpisodeTests(unittest.TestCase):
    def test_config_none_and_invalid_left_targets(self):
        self.assertIsNone(EdgeConfig().left_target_center_ratio)
        cfg=configured().session.config
        for bad in (True,'0.4',math.nan,math.inf,-math.inf,0.,1.,.06,.80):
            with self.subTest(bad=bad),self.assertRaises(ValueError):replace(cfg,left_target_center_ratio=bad)

    def test_actual_entry_parser_and_config_wiring(self):
        tree=ast.parse((SOURCE/'follow/run_face_motion.py').read_bytes())
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        setup=[]
        for n in main.body:
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='a' for t in n.targets):break
            setup.append(n)
        ns={'argparse':argparse,'Path':Path,'__doc__':'Pure parser'}
        exec(compile(ast.Module(body=setup,type_ignores=[]),'entry-parser','exec'),ns)
        required=[]
        for name in ('manifest','context','app-root','output','direction-evidence','human-evidence','zone-settings'):
            required+=['--'+name,'unused']
        required+=['--manifest-sha256','unused','--confirmation','FACE_ZONE_CONTINUOUS']
        p=ns['p'];default=p.parse_args(required)
        self.assertIsNone(default.left_target_center_ratio)
        self.assertEqual(default.target_center_ratio,.5)
        self.assertEqual(default.rearm_stability_ms,0)
        args=p.parse_args(required+['--target-center-ratio','.45','--left-target-center-ratio','.40','--rearm-stability-ms','150'])
        call=next(n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='EdgeConfig')
        cfg=eval(compile(ast.Expression(call),'actual-entry-config','eval'),
                 {'EdgeConfig':EdgeConfig,'zone':{'left_ratio':.05,'right_ratio':.8064720153808593},'a':args})
        self.assertEqual((cfg.left_target_center_ratio,cfg.target_center_ratio,cfg.center_tolerance_ratio),(.4,.45,.03))
        self.assertEqual(cfg.rearm_stability_ms,150)

    def test_left_hardware_stops_at_left_band_without_reverse(self):
        f=configured();f.feed([.10]*4+[.16,.22,.28,.34,.36])
        self.assertTrue(f.session.active)
        self.assertEqual(f.session.controller.recenter_trigger_side,-1)
        self.assertEqual(f.session.status()['target_center_ratio'],.40)
        f.feed([.38]*3)
        self.assertEqual(f.session.visual_center_completions,1)
        self.assertEqual(f.device.status()['flags'],0)
        self.assertEqual({c['target'] for c in f.device.commands},{1400})
        self.assertTrue(all(r['width']<=r['before'] for r in f.device.frames))

    def test_right_hardware_keeps_45_and_original_band(self):
        f=configured(reference=1400);f.feed([.86]*4+[.80,.74,.68,.62,.56,.50])
        self.assertTrue(f.session.active)
        self.assertEqual(f.session.controller.recenter_trigger_side,1)
        self.assertEqual(f.session.status()['target_center_ratio'],.45)
        f.feed([.47]*3)
        self.assertEqual(f.session.visual_center_completions,1)
        self.assertEqual(f.device.status()['flags'],0)
        self.assertEqual({c['target'] for c in f.device.commands},{1600})

    def test_target_stays_latched_on_raw_side_or_polarity_changes(self):
        for single in (True,False):
            for polarity in (1,-1):
                c=direct(single,polarity);c.recenter_decision(.1,True,False)
                c.previous_raw_center=.1;c.filtered_center=.34
                c.recenter_decision(.34,False,True)
                self.assertEqual((c.recenter_trigger_side,c.recenter_target_center_ratio),(-1,.4))
                self.assertEqual(c.edge,-1)
                self.assertLess(c.requested_speed*polarity,0)
                c.previous_raw_center=.34;c.recenter_decision(.46,False,True)
                self.assertFalse(c.recenter_active);self.assertEqual(c.edge,0)

    def test_left_non_single_pass_distance_uses_left_target(self):
        c=direct(False);c.recenter_decision(.10,True,False)
        c.filtered_center=.35;c.previous_raw_center=.3;c.recenter_decision(.35,False,True)
        self.assertTrue(c.recenter_active);self.assertEqual(c.recenter_target_center_ratio,.4)
        c.previous_raw_center=.35;c.recenter_decision(.38,False,True)
        self.assertFalse(c.recenter_active);self.assertTrue(c.recenter_completed)

    def test_arm_inherits_goal_but_no_source_authority(self):
        f=configured();f.feed([.10]*2)
        c=f.session.controller
        self.assertTrue(f.session.active)
        self.assertEqual((c.recenter_trigger_side,c.recenter_target_center_ratio),(-1,.4))
        self.assertIsNone(c.source);self.assertIsNone(c.authority_deadline_ms)
        self.assertFalse(f.device.commands)
        f.feed([.10]);self.assertTrue(f.device.commands)

    def test_short_loss_and_source_expiry_restore_left_goal(self):
        for kind in ('NO_TARGET','UNCONFIRMED','SOURCE_HORIZON_ENDED'):
            f=configured();f.feed([.1]*4+[.16,.22,.28])
            before=len(f.device.commands)
            if kind=='SOURCE_HORIZON_ENDED':f.tick(10)
            else:f.session.step(f.packet(state=kind))
            self.assertFalse(f.session.active)
            self.assertEqual(f.device.status()['flags'],0)
            self.assertIsNotNone(f.session.recenter_intent)
            self.assertEqual(f.session.recenter_intent['trigger_side'],-1)
            self.assertEqual(f.session.recenter_intent['target_center_ratio'],.4)
            self.assertEqual(len(f.device.commands),before)
            f.feed([.28]*4)
            self.assertTrue(f.session.active)
            self.assertEqual((f.session.controller.recenter_trigger_side,f.session.status()['target_center_ratio']),(-1,.4))
            self.assertEqual({c['target'] for c in f.device.commands},{1400})

    def test_canonical_brief_gap_stops_and_restores_left_goal(self):
        f=configured();f.feed([.1]*4+[.16,.22,.28])
        p=f.packet(state='UNCONFIRMED');p['face_tracking']=dict(version=11,error='',reason='UNCONFIRMED_DETECTION')
        f.session.step(p)
        self.assertFalse(f.session.active);self.assertEqual(f.device.status()['flags'],0)
        f.feed([.28]*4)
        self.assertTrue(f.session.active)
        self.assertEqual(f.session.controller.recenter_target_center_ratio,.4)

    def test_expired_intent_does_not_resume_inside_face(self):
        f=configured();f.feed([.1]*4+[.16,.22,.28])
        f.session.step(f.packet(state='NO_TARGET'));before=len(f.device.commands)
        f.now+=2.01;f.feed([.28]*4)
        self.assertIsNone(f.session.recenter_intent);self.assertFalse(f.session.active)
        self.assertEqual(f.session.controller.recenter_trigger_side,0)
        self.assertEqual(f.session.controller.recenter_target_center_ratio,.45)
        self.assertEqual(len(f.device.commands),before)

    def test_changed_epoch_track_or_multiple_faces_discard_intent(self):
        for kind in ('service_epoch','camera_epoch','track','generation','MULTIPLE_FACES'):
            f=configured();f.feed([.1]*4+[.16,.22,.28]);f.session.step(f.packet(state='NO_TARGET'))
            p=f.packet(.28)
            if kind in ('service_epoch','camera_epoch'):p[kind]='different'
            elif kind=='track':p['target']['track_id']=2
            elif kind=='generation':p['target']['track_generation']=2
            else:p=f.packet(state=kind)
            f.session.step(p)
            self.assertIsNone(f.session.recenter_intent,kind)
            self.assertEqual(f.session.controller.recenter_trigger_side,0,kind)
            self.assertEqual(f.session.controller.recenter_target_center_ratio,.45,kind)
            self.assertFalse(f.session.active,kind)

    def test_old_source_cannot_restore_or_renew_motion(self):
        f=configured();f.feed([.1]*4+[.16,.22,.28]);old=f.last
        f.session.step(f.packet(state='NO_TARGET'));before=len(f.device.commands)
        f.session.step(old)
        self.assertFalse(f.session.active);self.assertFalse(f.device.active)
        self.assertEqual(len(f.device.commands),before)

    def test_jump_crossing_left_target_stops_without_reverse(self):
        f=configured();f.feed([.1]*4+[.16,.22,.28]);before=len(f.device.commands)
        f.session.step(f.packet(.46))
        self.assertFalse(f.session.active);self.assertEqual(f.device.status()['flags'],0)
        self.assertEqual(len(f.device.commands),before)
        self.assertEqual({c['target'] for c in f.device.commands},{1400})

    def test_new_episode_selects_opposite_target_after_completion(self):
        c=direct();c.recenter_decision(.1,True,False)
        c.previous_raw_center=.34;c.recenter_decision(.4,False,True)
        self.assertFalse(c.recenter_active)
        c.previous_raw_center=.4;c.recenter_decision(.9,False,False)
        self.assertTrue(c.recenter_active)
        self.assertEqual((c.recenter_trigger_side,c.recenter_target_center_ratio),(1,.45))

    def test_none_compatibility_and_right_side_match_before_source(self):
        spec=importlib.util.spec_from_file_location('axis_before_core',HERE/'before/continuous_face_control.py')
        old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
        oldcfg=old.EdgeConfig(**{k:v for k,v in configured().session.config.__dict__.items() if k not in ('left_target_center_ratio','rearm_stability_ms')})
        extras={'recenter_trigger_side','configured_target_center_ratio','configured_left_target_center_ratio'}
        for points,left in (([.10]*4+[.16,.22,.28,.34,.40,.44,.46],None),
                            ([.86]*4+[.8,.74,.68,.62,.56,.5,.47],None),
                            ([.86]*4+[.8,.74,.68,.62,.56,.5,.47],.4)):
            f=configured();cfg=replace(f.session.config,left_target_center_ratio=left)
            a=FaceEdgeController('fixture-boot',1500,config=cfg)
            b=old.FaceEdgeController('fixture-boot',1500,config=oldcfg)
            for x in points:
                p=f.packet(x);now=round(f.now*1000)
                av=a.observe(p,now,allow_fixture=True);bv=b.observe(p,now,allow_fixture=True)
                self.assertEqual({k:v for k,v in av.items() if k not in extras},bv)
                f.now+=.08

if __name__=='__main__':unittest.main(verbosity=2)
