"""Regression cases for real session/Ruckig; fake PWM, no board access."""
import copy
from dataclasses import replace
import unittest

from test_recenter import Scene,profile


def pending(scene,reason='UNCONFIRMED_DETECTION',**fields):
    packet=scene.packet(state='UNCONFIRMED')
    packet['face_tracking']=dict(version=11,error='',reason=reason)
    packet.update(fields)
    return packet


def enable_smooth_stop(scene):
    scene.session.config=replace(profile(),smooth_recenter_stop=True)
    scene.session.controller=scene.session.fresh()


class ContinuityTests(unittest.TestCase):
    def test_single_pending_measurement_brakes_without_restart_or_new_authority(self):
        f=Scene();f.trigger();s=f.session
        before=(s.authority,s.source_origin,s.controller.authority_deadline_ms,
                s.controller.warmup,s.controller.center_filter.timestamp_s,
                f.device.arms,len(f.device.commands),copy.deepcopy(s.pva))
        s.step(pending(f))
        self.assertTrue(s.active);self.assertTrue(s.brief_face_gap)
        self.assertEqual((s.authority,s.source_origin,s.controller.authority_deadline_ms,
                          s.controller.warmup,s.controller.center_filter.timestamp_s,
                          f.device.arms,len(f.device.commands),s.pva),before)
        self.assertEqual(s.controller.requested_speed,0.)
        f.tick(2)
        self.assertTrue(s.active)
        old_deadline=before[2]
        self.assertTrue(all(c['deadline']<=old_deadline/1000. for c in f.device.commands[before[6]:]))
        f.feed([.76]*4)
        self.assertEqual(f.device.arms,before[5]);self.assertEqual(s.brief_face_recoveries,1)
        self.assertFalse(s.brief_face_gap);self.assertFalse(s.fatal)

    def test_repeated_pending_packets_never_extend_original_deadline_or_budget(self):
        f=Scene();f.trigger();s=f.session
        source=s.authority;origin=s.source_origin;deadline=s.controller.authority_deadline_ms
        before=len(f.device.commands)
        for _ in range(20):
            s.step(pending(f));f.tick(1)
        self.assertFalse(s.active);self.assertEqual(f.device.status()['flags'],0)
        for c in f.device.commands[before:]:
            self.assertEqual(c['stamp'],source[1]/1000.)
            self.assertLessEqual(c['deadline'],deadline/1000.)
            self.assertLessEqual(abs(c['target']-origin),4)
        count=len(f.device.commands);f.tick(20)
        self.assertEqual(len(f.device.commands),count)
        self.assertEqual(s.brief_face_gaps,1)

    def test_explicit_loss_and_unknown_reason_still_stop_immediately(self):
        for reason in ('FACE_CONTINUITY_LOST','FACE_ANCHOR_EXPIRED','NO_FACE_ANCHOR',
                       'MULTIPLE_FACES','UNKNOWN'):
            f=Scene();f.trigger();before=len(f.device.commands)
            f.session.step(pending(f,reason))
            self.assertFalse(f.session.active,reason)
            self.assertEqual(f.device.status()['flags'],0)
            self.assertEqual(len(f.device.commands),before)

    def test_changed_camera_geometry_body_and_malformed_pending_cannot_bridge(self):
        changes=[dict(camera_epoch='other'),dict(frame_width=800),dict(mirror_horizontal=False),
                 dict(target_kind='body'),dict(protocol_version='other'),dict(board_boot_id='other'),
                 dict(source_kind='synthetic'),dict(target={'track_id':2}),
                 dict(face_tracking={'version':11,'error':'failure','reason':'UNCONFIRMED_DETECTION'}),
                 dict(face_tracking=['not a tracking object'])]
        for fields in changes:
            f=Scene();f.trigger();before=len(f.device.commands)
            f.session.step(pending(f,**fields))
            self.assertFalse(f.session.active,fields)
            self.assertEqual(len(f.device.commands),before)

    def test_expired_and_no_target_packets_have_no_missing_frame_grace(self):
        for state in ('EXPIRED','NO_TARGET','MULTIPLE_FACES'):
            f=Scene();f.trigger();f.session.step(f.packet(state=state))
            self.assertFalse(f.session.active)

    def test_pending_before_output_never_bypasses_post_arm_confirmation(self):
        f=Scene();f.feed([.78]*3);self.assertTrue(f.session.active)
        self.assertFalse(f.session.epoch_output_started)
        f.session.step(pending(f))
        self.assertFalse(f.session.active);self.assertFalse(f.device.commands)

    def test_wrong_person_cannot_resume_brief_gap(self):
        f=Scene();f.trigger();f.session.step(pending(f));before=len(f.device.commands)
        p=f.packet(.7);p['target']['track_generation']=2;f.session.step(p)
        self.assertFalse(f.session.active);self.assertFalse(f.session.brief_face_gap)
        self.assertEqual(len(f.device.commands),before)

    def test_stream_disconnect_and_operator_stop_still_stop_during_gap(self):
        for action in ('disconnected','close'):
            f=Scene();f.trigger();f.session.step(pending(f));before=len(f.device.commands)
            getattr(f.session,action)()
            self.assertFalse(f.session.active);self.assertFalse(f.session.brief_face_gap)
            self.assertEqual(f.device.status()['flags'],0)
            self.assertEqual(len(f.device.commands),before)

    def test_center_arrival_keeps_pva_then_brakes_on_fresh_sources(self):
        f=Scene();enable_smooth_stop(f);f.trigger()
        f.feed([.76]*3+[.65]*3+[.55]*3)
        previous=list(f.session.pva);self.assertGreater(abs(previous[1]),.1)
        f.session.step(f.packet(.52))
        self.assertTrue(f.session.center_settling)
        self.assertEqual(f.session.pva,previous)
        self.assertEqual(f.session.controller.requested_speed,0.)
        commands=len(f.device.commands);arms=f.device.arms
        samples=[]
        f.tick(4)
        for _ in range(15):
            f.session.step(f.packet(.50))
            for _ in range(4):
                f.tick(1);samples.append((f.now,list(f.session.pva)))
        self.assertFalse(f.session.center_settling)
        self.assertTrue(f.session.zone_holding)
        self.assertEqual(f.session.reason,'SAFE_ZONE_HOLD')
        self.assertEqual(f.device.arms,arms)
        self.assertTrue(all(c['target']>=previous[0]-.5 for c in f.device.commands[commands:]))
        for (ta,a),(tb,b) in zip(samples,samples[1:]):
            self.assertLessEqual(abs(b[2]-a[2]),800*(tb-ta)+.01)
            self.assertLessEqual(abs(b[1]),30.001)
        held=f.device.pulse;f.feed([.49,.55,.60,.68,.72,.58,.50]*3)
        self.assertEqual(f.device.pulse,held)

    def test_center_settling_still_stops_on_expiry(self):
        f=Scene();enable_smooth_stop(f);f.trigger()
        f.feed([.76]*3+[.65]*3+[.55]*3)
        f.session.step(f.packet(.52));f.tick(15)
        self.assertFalse(f.session.active);self.assertFalse(f.session.center_settling)
        self.assertEqual(f.device.status()['flags'],0)

    def test_initial_inside_faces_never_start_pwm_even_with_smooth_stop(self):
        f=Scene();enable_smooth_stop(f);f.feed([.4,.5,.6,.7]*12)
        self.assertEqual(f.device.arms,0);self.assertFalse(f.device.commands)

    def test_center_hold_never_withdraws_accepted_target_when_pwm_latches_later(self):
        f=Scene();enable_smooth_stop(f);f.trigger()
        f.feed([.76]*3+[.65]*3+[.55]*3)
        status=f.device.status
        def lagging_width():
            value=status()
            if f.device.active:value['width_us']-=1
            return value
        f.device.status=lagging_width
        target=f.device.accepted_target_us
        f.session.pva=[float(target),0.,0.]
        f.session.step(f.packet(.52));f.tick(1)
        self.assertEqual(f.session.pva[0],target)
        self.assertEqual(f.device.accepted_target_us,target)
        self.assertTrue(f.session.zone_holding)

    def test_four_us_budget_and_limits_hold_while_braking(self):
        for reference in (1402,1590):
            f=Scene(reference=reference);enable_smooth_stop(f);f.trigger()
            f.session.step(pending(f));origin=f.session.source_origin
            before=len(f.device.commands);f.tick(15)
            self.assertTrue(all(1400<=c['target']<=1600 and abs(c['target']-origin)<=4
                                for c in f.device.commands[before:]))
            self.assertFalse(f.session.fatal)


if __name__=='__main__':unittest.main()
