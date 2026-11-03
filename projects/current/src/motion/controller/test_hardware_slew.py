"""Independent-clock model of the existing PL 4us/20ms endpoint ramp."""
import math
from dataclasses import replace
from types import SimpleNamespace
import unittest
from continuous_session import ContinuousSession
from hardware_slew_session import HardwareSlewSession
from test_recenter import Scene,profile


class FrameSlewDevice:
    def __init__(self,clock,pulse,minimum_us=1400,maximum_us=1600):
        self.minimum_us=minimum_us;self.maximum_us=maximum_us
        self.clock=clock;self.pulse=pulse;self.accepted_target_us=pulse
        self.armed=self.active=False;self.reason=0
        self.session=1;self.epoch=80;self.ack_seq=0;self.reference_time=None
        self.deadline=None;self.next_frame=None;self.commands=[];self.frames=[]
        self.arms=self.finishes=0
    def advance(self):
        now=self.clock()
        while (self.active and self.next_frame<=now+1e-9
               and self.next_frame<=self.deadline-.003):
            before=self.pulse;delta=self.accepted_target_us-self.pulse
            self.pulse+=max(-4,min(4,delta))
            self.frames.append(dict(now=self.next_frame,before=before,width=self.pulse,
                                    target=self.accepted_target_us,deadline=self.deadline))
            self.next_frame+=.020
        if self.active and now>=self.deadline:
            self.active=self.armed=False;self.reason=4
    def status(self):
        self.advance()
        flags=(15 if self.active else 14 if self.armed else 0)|(self.reason<<4)
        return dict(flags=flags,width_us=self.pulse,target_us=self.accepted_target_us,
            lease_left_ms=max(0,int((self.deadline-self.clock())*1000)) if self.active else 0,
            session=self.session,epoch=self.epoch,ack_seq=self.ack_seq,reference_us=self.reference_us if self.reference_time is not None else self.pulse,
            reason=self.reason,active=self.active,armed=self.armed)
    def confirm_and_arm(self,reference,session,epoch,**kwargs):
        self.advance();assert not self.active
        self.pulse=self.accepted_target_us=reference.reference_us;self.reference_us=reference.reference_us
        self.armed=True;self.reason=0;self.session=session;self.epoch=epoch
        self.ack_seq=0;self.reference_time=self.clock();self.arms+=1
    def submit(self,target,stamp,**kwargs):
        self.advance();assert self.armed and self.reference_time<stamp<=self.clock()
        assert type(target) is int and self.minimum_us<=target<=self.maximum_us
        freshness=kwargs.get('freshness_s',.25);margin=kwargs.get('margin_s',.02)
        budget=math.floor((stamp+freshness-self.clock()-margin)*1000)
        assert budget>=max(4,kwargs.get('minimum_lease_ms',0))
        if not self.active:self.next_frame=self.clock()+.020
        self.accepted_target_us=target;self.ack_seq+=1;self.active=True
        self.deadline=self.clock()+budget/1000.
        self.commands.append(dict(now=self.clock(),stamp=stamp,target=target,deadline=self.deadline,freshness_s=freshness))
        return dict(outcome='ACCEPTED',lease_ms=budget,readback=self.status())
    def stop(self):
        self.advance();self.armed=self.active=False;self.reason=0;return self.status()
    def finish(self):self.finishes+=1;return self.stop()


def scene(hardware=True,reference=1469):
    f=Scene(reference);solver=f.session.trajectory
    f.device=FrameSlewDevice(lambda:f.now,reference)
    config=replace(profile(),single_pass_recenter=True,smooth_recenter_stop=True,
                   hardware_slew_recenter=hardware,maximum_speed_us_s=40.,velocity_gain_us=0.)
    cls=HardwareSlewSession if hardware else ContinuousSession
    f.session=cls(f.device,'fixture-boot',config,lambda p:SimpleNamespace(reference_us=p),
                  trajectory=solver,clock=lambda:f.now,allow_fixture=True)
    return f


class HardwareSlewTests(unittest.TestCase):
    def test_first_endpoint_is_not_an_instantaneous_emitted_pulse_jump(self):
        f=scene(reference=1400);f.feed([.86]*3)
        self.assertTrue(f.device.commands)
        first=f.device.commands[0]
        self.assertEqual(first['target'],1600)
        changed=[r for r in f.device.frames if r['width']!=r['before']]
        self.assertTrue(changed)
        self.assertAlmostEqual(changed[0]['now']-first['now'],.020)
        self.assertEqual(changed[0]['width'],1404)

    def test_independent_hardware_clock_moves_during_software_gap(self):
        f=scene(reference=1400);f.feed([.86]*3)
        before=f.device.pulse;commands=len(f.device.commands)
        f.now+=.080;readback=f.device.status()
        self.assertEqual(readback['width_us']-before,16)
        self.assertEqual(len(f.device.commands),commands)

    def test_only_one_endpoint_is_used_for_one_direction_with_new_frame_renewals(self):
        f=scene(reference=1400);f.feed([.86]*14)
        self.assertEqual({c['target'] for c in f.device.commands},{1600})
        self.assertGreater(len(f.device.commands),5)
        self.assertEqual(f.device.arms,1)
        self.assertTrue(all(abs(r['width']-r['before'])<=4 for r in f.device.frames))
        self.assertTrue(all(1400<=r['width']<=1600 for r in f.device.frames))
        self.assertTrue(all(c['deadline']<=c['stamp']+c['freshness_s'] for c in f.device.commands))

    def test_ticks_cannot_renew_old_source_or_extend_original_expiry(self):
        f=scene();f.feed([.86]*5);before=len(f.device.commands)
        deadline=f.session.controller.authority_deadline_ms/1000.
        f.tick(15)
        self.assertFalse(f.session.active);self.assertEqual(f.device.status()['flags'],0)
        self.assertEqual(len(f.device.commands),before)
        self.assertTrue(all(r['now']<deadline for r in f.device.frames))

    def test_visual_center_quiesces_without_sending_a_reverse_target(self):
        f=scene(reference=1400);f.feed([.86]*4+[.70]*3+[.60]*3+[.55]*3+[.52]*3)
        self.assertGreaterEqual(f.session.visual_center_completions,1)
        self.assertFalse(f.session.active)
        self.assertEqual(f.device.status()['flags'],0)
        self.assertEqual({c['target'] for c in f.device.commands},{1600})
        self.assertTrue(all(r['width']>=r['before'] for r in f.device.frames))
        held=f.device.pulse;f.feed([.43,.55,.6,.7,.5]*4)
        self.assertEqual(f.device.pulse,held)

    def test_confirmed_center_overshoot_does_not_reverse_the_hardware_ramp(self):
        f=scene(reference=1400);f.feed([.86]*4+[.70]*3+[.60]*3+[.55]*3+[.45]*4)
        self.assertFalse(f.session.active)
        self.assertEqual({c['target'] for c in f.device.commands},{1600})
        self.assertTrue(all(r['width']>=r['before'] for r in f.device.frames))

    def test_left_box_trigger_uses_negative_hardware_slew(self):
        f=scene(reference=1600);f.feed([.30]*4+[.16]*6)
        self.assertTrue(f.device.commands)
        self.assertEqual({c['target'] for c in f.device.commands},{1400})
        self.assertTrue(all(r['width']<=r['before'] for r in f.device.frames))

    def test_actual_loss_body_or_camera_change_stops_the_hardware_ramp(self):
        for changes in (dict(state='NO_TARGET'),dict(state='UNCONFIRMED'),
                        dict(target_kind='body'),dict(camera_epoch='other'),dict(board_boot_id='other')):
            f=scene(reference=1400);f.feed([.86]*4);before=len(f.device.commands)
            f.session.step(f.packet(.86,**changes))
            self.assertFalse(f.session.active,changes)
            self.assertEqual(f.device.status()['flags'],0)
            self.assertEqual(len(f.device.commands),before)

    def test_canonical_brief_gap_also_stops_in_hardware_mode(self):
        f=scene();f.feed([.86]*4);p=f.packet(state='UNCONFIRMED')
        p['face_tracking']=dict(version=11,error='',reason='UNCONFIRMED_DETECTION')
        f.session.step(p)
        self.assertFalse(f.session.active);self.assertEqual(f.device.status()['flags'],0)

    def test_anchor_expiry_stops_even_when_images_continue(self):
        f=scene();f.feed([.86]*4);before=len(f.device.commands)
        p=f.packet(.86);p['face_detection_mono_ms']=round(f.now*1000)-501
        f.session.step(p)
        self.assertFalse(f.session.active);self.assertEqual(len(f.device.commands),before)

    def test_already_at_limit_does_not_start_pwm_or_claim_center(self):
        f=scene(reference=1600);f.feed([.86]*12)
        self.assertFalse(f.device.commands)
        self.assertFalse(f.session.controller.recenter_completed)

    def test_reaching_limit_keeps_endpoint_without_claiming_visual_center(self):
        f=scene(reference=1590);f.feed([.86]*10)
        self.assertEqual(f.device.pulse,1600)
        self.assertEqual(f.session.state,'HOLD_AT_LIMIT')
        self.assertFalse(f.session.controller.recenter_completed)

    def test_inside_faces_never_enable_hardware_motion(self):
        f=scene();f.feed([.3,.4,.5,.6,.7]*10)
        self.assertFalse(f.device.commands);self.assertEqual(f.device.arms,0)

    def test_expired_hardware_permission_is_not_rescued_by_new_face(self):
        f=scene();f.feed([.86]*4);f.device.deadline=f.now-.001
        before=len(f.device.commands);f.session.step(f.packet(.86))
        self.assertFalse(f.session.active);self.assertEqual(len(f.device.commands),before)

    def test_stop_and_disconnect_terminate_output_without_returning_home(self):
        for action in ('close','disconnected'):
            f=scene();f.feed([.86]*4);before=f.device.pulse
            getattr(f.session,action)()
            self.assertEqual(f.device.status()['flags'],0)
            self.assertEqual(f.device.pulse,before)

    def test_insufficient_first_budget_waits_without_any_pulse(self):
        f=scene();f.feed([.86]*2)
        p=f.packet(.86);p['source_mono_ms']=round(f.now*1000)-210
        p['deadline_mono_ms']=p['source_mono_ms']+250;p['face_detection_mono_ms']=p['source_mono_ms']
        f.session.step(p);f.tick(1)
        self.assertFalse(f.device.commands);self.assertFalse(f.device.active)


if __name__=='__main__':unittest.main()
