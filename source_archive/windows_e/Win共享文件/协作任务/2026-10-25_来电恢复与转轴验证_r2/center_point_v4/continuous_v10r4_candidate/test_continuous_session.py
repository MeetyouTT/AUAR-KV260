import hashlib,sys,unittest
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent))
from continuous_session import ContinuousSession
from continuous_face_control import EdgeConfig
from trajectory import Trajectory
from common.motion_observation import PROTOCOL


class Device:
    def __init__(self,clock):
        self.clock=clock;self.pulse=self.accepted_target_us=1469;self.armed=self.active=False
        self.reason=0;self.epoch=80;self.session=1;self.ack_seq=0;self.reference_time=None
        self.deadline=None;self.commands=[];self.arms=0;self.finishes=0
    def status(self):
        if self.active and self.clock()>=self.deadline:self.active=self.armed=False;self.reason=4
        flags=(15 if self.active else 14 if self.armed else 0)|(self.reason<<4)
        return dict(flags=flags,width_us=self.pulse,target_us=self.pulse,lease_left_ms=max(0,int((self.deadline-self.clock())*1000)) if self.active else 0,
                    session=self.session,epoch=self.epoch,ack_seq=self.ack_seq,reference_us=1469,reason=self.reason,armed=self.armed)
    def confirm_and_arm(self,reference,session,epoch,**kwargs):
        self.armed=True;self.active=False;self.reason=0;self.session=session;self.epoch=epoch
        self.ack_seq=0;self.reference_time=self.clock();self.arms+=1
    def submit(self,target,stamp,**kwargs):
        self.status();assert self.armed and self.reference_time<stamp<=self.clock()
        freshness=kwargs.get('freshness_s',.25);margin=kwargs.get('margin_s',.02)
        budget=int((stamp+freshness-self.clock()-margin)*1000)
        assert budget>=3
        self.pulse=self.accepted_target_us=target;self.ack_seq+=1;self.active=True
        self.deadline=self.clock()+budget/1000.
        self.commands.append(dict(now=self.clock(),stamp=stamp,target=target,deadline=self.deadline,freshness_s=freshness))
        return dict(outcome='ACCEPTED',lease_ms=budget,readback=self.status())
    def stop(self):self.armed=self.active=False;self.reason=0;return self.status()
    def finish(self):self.finishes+=1;return self.stop()


class SessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=HERE.parent/'ps_trajectory_v1/libaura_trajectory_compat_host.so'
        cls.trajectory=Trajectory(p,hashlib.sha256(p.read_bytes()).hexdigest())
    def setUp(self):
        self.now=1.;self.fid=0;self.device=Device(lambda:self.now)
        self.s=ContinuousSession(self.device,'boot',EdgeConfig(),lambda p:SimpleNamespace(reference_us=p),
            trajectory=self.trajectory,clock=lambda:self.now,allow_fixture=True)
    def packet(self,center=.5,**extra):
        self.fid+=1;stamp=int(self.now*1000)
        p=dict(protocol_version=PROTOCOL,source_kind='fixture',target_kind='face',board_boot_id='boot',
            service_epoch='service',camera_epoch='camera',state='READY',source_frame_id=self.fid,source_mono_ms=stamp,
            deadline_mono_ms=stamp+250,frame_width=640,frame_height=480,mirror_horizontal=True,
            target=dict(track_id=1,track_generation=1,box=[max(0.,center*640-40),100.,80.,80.],score=.95))
        p.update(extra);return p
    def tick(self,count=4):
        for _ in range(count):self.now+=.02;self.s.tick()
    def feed(self,centers):
        for center in centers:self.s.step(self.packet(center));self.tick()
    def test_inside_never_reenergizes_servo_and_has_zero_angle_changes(self):
        self.feed([.5]*30)
        self.assertEqual(self.device.arms,0)
        self.assertEqual(self.device.commands,[])
    def test_five_out_one_in_ten_cycles_keep_one_arm_and_perception(self):
        self.feed([.79]*8)
        for _ in range(10):self.feed([.812]*5+[.8])
        self.assertEqual(self.device.arms,1);self.assertEqual(self.device.finishes,0)
        self.assertGreater(self.s.controller.warmup,50);self.assertFalse(self.s.fatal)
    def test_near_boundary_tremor_does_not_create_large_pulse_steps(self):
        self.feed([.8]*8);self.feed([.808,.804]*40)
        changes=[abs(x['target']-1469) for x in self.device.commands]
        self.assertLessEqual(max(changes or [0]),2);self.assertEqual(self.device.arms,1)
    def test_same_source_ticks_keep_original_deadline_and_four_us_budget(self):
        self.feed([.85]*20);p=self.packet(.85);self.s.step(p)
        origin=self.s.source_origin;stamp=p['source_mono_ms']/1000.;before=len(self.device.commands)
        self.tick(9)
        commands=[x for x in self.device.commands[before:] if x['stamp']==stamp]
        self.assertTrue(commands)
        self.assertTrue(all(x['deadline']<=stamp+.25 for x in commands))
        self.assertTrue(all(abs(x['target']-origin)<=4.5 for x in commands))
        self.tick(5);self.assertFalse(self.s.active);self.assertEqual(self.device.status()['flags'],0)
    def test_return_inside_freezes_target_and_keeps_same_arm(self):
        self.feed([.85]*20);self.feed([.79]);pulse=self.device.pulse
        self.feed([.7]*8)
        self.assertEqual(self.device.pulse,pulse);self.assertEqual(self.device.arms,1)
        self.assertTrue(self.s.zone_holding)
    def test_large_single_frame_spike_cannot_become_new_motion_authority(self):
        self.feed([.5]*10);authority=self.s.authority;before=len(self.device.commands)
        self.s.step(self.packet(.85));self.assertEqual(self.s.authority,authority);self.tick()
        self.assertTrue(all(x['target']==1469 for x in self.device.commands[before:]))
        self.feed([.5]*4);self.assertFalse(self.s.fatal)
    def test_loss_body_wrong_boot_and_disconnect_are_stopped(self):
        for extra in [dict(state='NO_TARGET',target=None),dict(target_kind='body'),dict(board_boot_id='other')]:
            self.setUp();self.feed([.85]*12);self.s.step(self.packet(.85,**extra))
            self.assertFalse(self.s.active);self.assertEqual(self.device.status()['flags'],0)
        self.setUp();self.feed([.85]*12);self.s.disconnected();self.assertFalse(self.s.active)
    def test_late_control_tick_stops_instead_of_catching_up_with_large_jump(self):
        self.feed([.85]*12);before=len(self.device.commands);self.now+=.15;self.s.tick()
        self.assertFalse(self.s.active);self.assertEqual(len(self.device.commands),before)
    def test_hardware_fault_stays_fatal(self):
        self.feed([.85]*12);self.device.reason=3;self.tick(1)
        self.assertTrue(self.s.fatal);self.assertEqual(self.device.status()['flags'],0)
    def test_continuous_trajectory_keeps_small_steps_and_jerk_outside_zone(self):
        self.feed([.9]*24)
        trace=list(self.s.command_trace)
        self.assertTrue(any(x['delta_us'] for x in trace))
        self.assertTrue(all(abs(x['delta_us'])<=2 for x in trace))
        self.assertTrue(all(abs(x['velocity_us_s'])<=10.001 and abs(x['acceleration_us_s2'])<=100.001 for x in trace))
        for previous,current in zip(trace,trace[1:]):
            if previous['state']!='FOLLOWING' or current['state']!='FOLLOWING':continue
            dt=(current['mono_ms']-previous['mono_ms'])/1000.
            self.assertLessEqual(abs(current['acceleration_us_s2']-previous['acceleration_us_s2']),800.*dt+.02)
    def test_soft_limit_brakes_once_without_repeated_restarts_or_creeping(self):
        self.device.pulse=self.device.accepted_target_us=1590
        self.s.current=self.device.status();self.s.controller=self.s.fresh();self.s.pva=[1590.,0.,0.]
        self.feed([.9]*120)
        self.assertFalse(self.s.fatal)
        self.assertTrue(all(1400<=x['target']<=1600 for x in self.device.commands))
        self.assertEqual(len({x['target'] for x in self.device.commands[-20:]}),1)
        self.assertEqual(self.device.arms,1)
    def test_duplicate_mutation_and_reordered_packets_do_not_grant_authority(self):
        self.feed([.85]*12);p=self.packet(.85);self.s.step(p)
        mutated=dict(p,target=dict(p['target'],box=[500.,100.,80.,80.]))
        self.s.step(mutated);self.assertTrue(self.s.fatal);self.assertEqual(self.device.status()['flags'],0)
    def test_pre_arm_stamp_never_hides_loss_wrong_boot_or_body(self):
        for changes in [dict(state='NO_TARGET',target=None),dict(state='MULTIPLE_FACES',target=None),
                        dict(board_boot_id='other'),dict(target_kind='body'),dict(protocol_version='invalid')]:
            self.setUp();self.feed([.85]*12);packet=self.packet(.85,**changes)
            packet['source_mono_ms']=int(self.device.reference_time*1000)
            packet['deadline_mono_ms']=packet['source_mono_ms']+250
            self.s.step(packet);self.assertFalse(self.s.active);self.assertEqual(self.device.status()['flags'],0)
    def test_valid_pre_arm_packet_never_produces_commands(self):
        self.feed([.85]*2);packet=self.packet(.85);self.s.step(packet)
        self.assertTrue(self.s.active);self.assertEqual(self.device.commands,[])
        self.s.step(packet);self.tick(3)
        self.assertEqual(self.device.commands,[]);self.assertIsNone(self.s.authority)
    def test_same_outside_episode_is_bounded_even_across_source_loss_reconfirmation(self):
        self.feed([.9]*45);origin=1469
        self.assertTrue(all(abs(x['target']-origin)<=3 for x in self.device.commands))
        arms=self.device.arms;self.s.disconnected();self.feed([.9]*30)
        self.assertEqual(self.device.arms,arms)
        self.assertTrue(all(abs(x['target']-origin)<=3 for x in self.device.commands))
        # A large return first needs pixel-jump confirmation; subsequent
        # distinct in-zone images must span the full stable-inside interval.
        self.feed([.7]*6);self.feed([.9]*25)
        self.assertGreater(self.device.arms,arms)
    def test_single_inside_frames_never_replenish_outside_correction_budget(self):
        self.feed([.5]*10)
        for _ in range(6):self.feed([.85]*20);self.feed([.8])
        self.assertTrue(self.device.commands)
        self.assertTrue(all(1469<=command['target']<=1472 for command in self.device.commands))
        self.assertEqual(self.s.correction_releases,0)
        self.assertEqual(self.device.arms,1)
    def test_duplicate_inside_packet_does_not_count_as_stable_return(self):
        self.feed([.85]*25);origin=self.s.correction_origin
        packet=self.packet(.8);self.s.step(packet)
        for _ in range(8):
            self.now+=.02;self.s.step(packet);self.s.tick()
        self.assertEqual(self.s.correction_origin,origin)
        self.assertEqual(self.s.correction_releases,0)
    def test_source_loss_discards_partial_inside_confirmation(self):
        self.feed([.85]*25);self.feed([.8]*3)
        self.assertGreater(self.s.rearm.count,0)
        self.s.disconnected();self.assertEqual(self.s.rearm.count,0)
        self.feed([.8]*3);self.assertEqual(self.s.correction_releases,0)
    def expired_refresh(self,**changes):
        packet=self.packet(.85,state='EXPIRED',source_frame_id=None,source_mono_ms=None,
            deadline_mono_ms=None,target=None,face_tracking=dict(version=11,error='',reason='FACE_TEMPLATE_VISIBLE_CLIP'))
        packet.update(changes);return packet
    def test_brief_refresh_expiry_keeps_only_the_original_valid_image_authority(self):
        self.feed([.85]*12);authority=self.s.authority;origin=self.s.source_origin;arms=self.device.arms
        self.now+=.02;self.s.step(self.expired_refresh());self.s.tick()
        self.assertTrue(self.s.active);self.assertEqual(self.s.authority,authority)
        self.assertEqual(self.s.source_origin,origin)
        self.assertEqual(self.s.controller.reason,'WAITING_WITH_ORIGINAL_FACE_DEADLINE')
        self.now+=.04;self.s.step(self.packet(.85));self.s.tick()
        self.assertTrue(self.s.active);self.assertEqual(self.device.arms,arms)
    def test_repeated_expired_refreshes_cannot_extend_the_old_source_deadline(self):
        self.feed([.85]*12);stamp=self.s.authority[1]/1000.;before=len(self.device.commands)
        for _ in range(12):
            self.now+=.02;self.s.step(self.expired_refresh());self.s.tick()
        self.assertFalse(self.s.active);self.assertEqual(self.device.status()['flags'],0)
        self.assertTrue(all(c['deadline']<=stamp+.25 for c in self.device.commands[before:]))
    def test_refresh_grace_cannot_hide_changed_context_orientation_or_a_real_loss(self):
        cases=[dict(camera_epoch='other'),dict(mirror_horizontal=False),dict(frame_width=800),dict(frame_width=640.),
               dict(state='NO_TARGET'),dict(state='MULTIPLE_FACES'),
               dict(face_tracking=dict(version=11,error='failed',reason='FACE_TEMPLATE_VISIBLE_CLIP')),
               dict(face_tracking=dict(version=11,reason='FACE_TEMPLATE_VISIBLE_CLIP'))]
        for changes in cases:
            self.setUp();self.feed([.85]*12);self.now+=.02
            self.s.step(self.expired_refresh(**changes))
            self.assertFalse(self.s.active);self.assertEqual(self.device.status()['flags'],0)
    def test_expired_refresh_after_arm_never_grants_an_output_source(self):
        self.feed([.85]*2);self.s.step(self.packet(.85));self.assertTrue(self.s.active)
        self.now+=.02;self.s.step(self.expired_refresh());self.s.tick()
        self.assertTrue(self.s.active);self.assertIsNone(self.s.authority)
        self.assertEqual(self.device.commands,[])
        self.tick(14)
        self.assertFalse(self.s.active);self.assertEqual(self.device.commands,[])
    def test_green_left_line_uses_the_same_stable_rearm_rule(self):
        self.s=ContinuousSession(self.device,'boot',EdgeConfig(left_ratio=.1),lambda p:SimpleNamespace(reference_us=p),
            trajectory=self.trajectory,clock=lambda:self.now,allow_fixture=True)
        self.feed([.5]*10)
        for _ in range(6):self.feed([.08]*26);self.feed([.12])
        self.assertTrue(self.device.commands)
        self.assertTrue(all(1466<=command['target']<=1469 for command in self.device.commands))
        self.assertEqual(self.s.correction_releases,0)
        self.feed([.3]*8);self.assertEqual(self.s.correction_releases,1)
        self.feed([.08]*30);self.assertLess(self.device.pulse,1466)
    def test_lease_is_bounded_by_both_image_age_and_actual_detection_anchor(self):
        self.feed([.85]*20);before=len(self.device.commands)
        packet=self.packet(.85);anchor=packet['source_mono_ms']-450
        packet['face_detection_mono_ms']=anchor;self.s.step(packet);self.tick(1)
        self.assertEqual(self.s.controller.authority_deadline_ms,anchor+500)
        commands=self.device.commands[before:];self.assertTrue(commands)
        self.assertTrue(all(c['deadline']<=(anchor+500)/1000. for c in commands))
        self.assertTrue(all(c['freshness_s']<=.05 for c in commands))
        self.tick(3);self.assertFalse(self.s.active)
    def test_refresh_wait_cannot_survive_expired_face_anchor_with_fresh_image(self):
        self.feed([.85]*20)
        packet=self.packet(.85);packet['face_detection_mono_ms']=packet['source_mono_ms']-470
        self.s.step(packet);self.now+=.035
        self.s.step(self.expired_refresh());self.s.tick()
        self.assertFalse(self.s.active);self.assertEqual(self.device.status()['flags'],0)
    def test_larger_remaining_image_budget_never_extends_anchor_permission(self):
        self.feed([.85]*20)
        packet=self.packet(.85);packet['face_detection_mono_ms']=packet['source_mono_ms']-480
        self.s.step(packet);before=len(self.device.commands);self.tick(1)
        self.assertEqual(len(self.device.commands),before);self.assertFalse(self.s.active)
    def test_invalid_future_anchor_is_not_admitted(self):
        for offset in [1,100]:
            self.setUp();self.feed([.85]*12);packet=self.packet(.85)
            packet['face_detection_mono_ms']=packet['source_mono_ms']+offset
            self.s.step(packet);self.assertTrue(self.s.fatal)
            self.assertEqual(self.device.status()['flags'],0)
    def test_actual_face_source_requires_exact_anchor_provenance(self):
        self.feed([.85]*12);packet=self.packet(.85,source_kind='actual')
        self.s.step(packet);self.assertTrue(self.s.fatal)
        self.setUp();self.feed([.85]*12);packet=self.packet(.85,source_kind='actual')
        packet['face_detection_mono_ms']=packet['source_mono_ms']-100
        self.s.step(packet);self.assertFalse(self.s.fatal);self.assertTrue(self.s.active)
    def test_duplicate_packet_cannot_mutate_face_anchor_to_extend_deadline(self):
        self.feed([.85]*12);packet=self.packet(.85)
        packet['face_detection_mono_ms']=packet['source_mono_ms']-100
        self.s.step(packet)
        packet['face_detection_mono_ms']+=50
        self.s.step(packet);self.assertTrue(self.s.fatal)
        self.assertEqual(self.device.status()['flags'],0)
    def test_unconfirmed_packet_interrupts_stable_inside_confirmation_without_new_authority(self):
        self.feed([.85]*25);self.feed([.8]*3);self.assertGreater(self.s.rearm.count,0)
        authority=self.s.authority
        self.now+=.02;self.s.step(self.packet(state='UNCONFIRMED',target=None,source_frame_id=None,
            source_mono_ms=None,deadline_mono_ms=None))
        self.assertEqual(self.s.rearm.count,0);self.assertEqual(self.s.authority,authority)
        self.feed([.8]*3);self.assertEqual(self.s.correction_releases,0)
    def test_unconfirmed_packet_cannot_hide_new_camera_context(self):
        self.feed([.85]*12)
        self.s.step(self.packet(state='UNCONFIRMED',target=None,source_frame_id=None,
            source_mono_ms=None,deadline_mono_ms=None,camera_epoch='other'))
        self.assertFalse(self.s.active);self.assertEqual(self.device.status()['flags'],0)
    def test_unadmitted_jump_interrupts_stable_inside_confirmation(self):
        self.feed([.85]*25);self.feed([.8]*3);self.assertGreater(self.s.rearm.count,0)
        authority=self.s.authority;self.s.step(self.packet(.5))
        self.assertEqual(self.s.controller.reason,'MEASUREMENT_JUMP_PENDING')
        self.assertEqual(self.s.rearm.count,0);self.assertEqual(self.s.authority,authority)
    def test_expired_refresh_packet_cannot_supply_a_new_deadline(self):
        self.feed([.85]*12);packet=self.expired_refresh(deadline_mono_ms=int(self.now*1000)+5000)
        self.s.step(packet);self.assertFalse(self.s.active)
    def prepare_nearly_expired_lease(self):
        self.feed([.85]*20)
        arrival=self.device.deadline-.01
        while self.now+.02<arrival:self.tick(1)
        self.now=arrival
        packet=self.packet(.85);packet['source_mono_ms']=int(self.now*1000)-60
        packet['deadline_mono_ms']=packet['source_mono_ms']+250
        packet['face_detection_mono_ms']=int(self.now*1000)-100
        return packet
    def test_new_image_near_old_lease_deadline_renews_same_angle_before_next_tick(self):
        packet=self.prepare_nearly_expired_lease();old=self.device.pulse;arms=self.device.arms
        before=len(self.device.commands);self.s.step(packet)
        self.assertEqual(len(self.device.commands),before+1)
        self.assertEqual(self.device.commands[-1]['target'],old)
        self.assertEqual(self.s.fresh_image_lease_renewals,1)
        self.assertEqual(self.s.command_trace[-1]['command_kind'],'FRESH_IMAGE_SAME_TARGET_RENEWAL')
        self.tick(2);self.assertTrue(self.s.active);self.assertEqual(self.device.arms,arms)
    def test_expired_refresh_near_lease_deadline_never_renews(self):
        self.prepare_nearly_expired_lease();before=len(self.device.commands)
        self.s.step(self.expired_refresh())
        self.assertEqual(len(self.device.commands),before)
        self.tick(1);self.assertFalse(self.s.active)
    def test_new_image_renewal_retains_its_own_short_anchor_deadline(self):
        packet=self.prepare_nearly_expired_lease()
        packet['face_detection_mono_ms']=int(self.now*1000)-450
        self.s.step(packet);last=self.device.commands[-1]
        self.assertLessEqual(last['deadline'],(packet['face_detection_mono_ms']+500)/1000.)
        self.tick(3);self.assertFalse(self.s.active)
    def test_duplicate_image_never_renews_near_expiring_lease(self):
        self.feed([.85]*20);packet=self.packet(.85);self.s.step(packet);self.tick(1)
        arrival=self.device.deadline-.01
        while self.now+.02<arrival:self.tick(1)
        self.now=arrival;before=len(self.device.commands)
        self.s.step(packet);self.assertEqual(len(self.device.commands),before)
        self.tick(1);self.assertFalse(self.s.active)
    def test_expired_anchor_on_new_image_does_not_rescue_old_lease(self):
        packet=self.prepare_nearly_expired_lease();before=len(self.device.commands)
        packet['face_detection_mono_ms']=int(self.now*1000)-500
        self.s.step(packet)
        self.assertEqual(len(self.device.commands),before);self.assertFalse(self.s.fatal)
        self.assertFalse(self.s.active)
        self.assertEqual(self.device.status()['flags'],0)
    def test_ready_packet_anchor_expiring_in_transport_stops_and_recovers_normally(self):
        self.feed([.85]*12);packet=self.packet(.85)
        packet['face_detection_mono_ms']=packet['source_mono_ms']-490
        self.now+=.02;before=len(self.device.commands);self.s.step(packet)
        self.assertFalse(self.s.active);self.assertFalse(self.s.fatal)
        self.assertEqual(len(self.device.commands),before)
        self.assertEqual(self.device.status()['flags'],0)
        self.feed([.8]*8);self.feed([.85]*12)
        self.assertFalse(self.s.fatal);self.assertTrue(self.s.active)
    def test_boundary_false_start_does_not_energize_same_position(self):
        self.feed([.8]*8);self.feed([.808]*4);self.feed([.8]*4)
        self.assertEqual(self.device.commands,[])
    def test_visual_loss_uses_full_pulse_finish_while_real_fault_is_immediate(self):
        self.feed([.9]*18);self.assertTrue(self.device.commands)
        finishes=self.device.finishes
        self.s.step(self.packet(state='NO_TARGET',target=None))
        self.assertEqual(self.device.finishes,finishes+1)
        self.assertEqual(self.device.status()['flags'],0)
        self.assertGreater(self.s.full_pulse_visual_stops,0)
        self.setUp();self.feed([.9]*18);finishes=self.device.finishes
        self.device.reason=3;self.tick(1)
        self.assertTrue(self.s.fatal);self.assertEqual(self.device.finishes,finishes)
    def test_visible_left_center_can_make_first_small_correction_without_one_second_wait(self):
        self.s=ContinuousSession(self.device,'boot',EdgeConfig(left_ratio=.1),lambda p:SimpleNamespace(reference_us=p),
            trajectory=self.trajectory,clock=lambda:self.now,allow_fixture=True)
        self.feed([.2]*8);began=self.now
        for _ in range(10):
            self.feed([.0625])
            if self.device.pulse<1469:break
        self.assertLess(self.device.pulse,1469)
        self.assertLess(self.now-began,.7)
        self.assertGreaterEqual(self.device.pulse,1466)

    def test_face_box_over_left_line_keeps_still_until_center_crosses(self):
        self.s=ContinuousSession(self.device,'boot',EdgeConfig(left_ratio=.1),lambda p:SimpleNamespace(reference_us=p),
            trajectory=self.trajectory,clock=lambda:self.now,allow_fixture=True)
        self.feed([.15]*30)
        self.assertEqual(self.device.arms,0);self.assertEqual(self.device.commands,[])
        self.feed([.08]*30)
        self.assertGreater(self.device.arms,0);self.assertLess(self.device.pulse,1469)

    def test_center_on_either_line_is_inside_and_keeps_still(self):
        for center in (.1,.8):
            self.setUp()
            self.s=ContinuousSession(self.device,'boot',EdgeConfig(left_ratio=.1,right_ratio=.8),lambda p:SimpleNamespace(reference_us=p),
                trajectory=self.trajectory,clock=lambda:self.now,allow_fixture=True)
            self.feed([center]*25)
            self.assertEqual(self.device.arms,0);self.assertEqual(self.device.commands,[])


if __name__=='__main__':unittest.main()
