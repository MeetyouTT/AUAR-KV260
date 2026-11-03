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
        budget=int((stamp+.25-self.clock()-.02)*1000)
        assert budget>=3
        self.pulse=self.accepted_target_us=target;self.ack_seq+=1;self.active=True
        self.deadline=self.clock()+budget/1000.
        self.commands.append(dict(now=self.clock(),stamp=stamp,target=target,deadline=self.deadline))
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
    def test_inside_holds_current_command_with_one_arm_and_zero_angle_changes(self):
        self.feed([.5]*30)
        self.assertEqual(self.device.arms,1);self.assertTrue(self.s.zone_holding)
        self.assertTrue(self.device.commands);self.assertTrue(all(x['target']==1469 for x in self.device.commands))
    def test_five_out_one_in_ten_cycles_keep_one_arm_and_perception(self):
        self.feed([.79]*8)
        for _ in range(10):self.feed([.812]*5+[.8])
        self.assertEqual(self.device.arms,1);self.assertEqual(self.device.finishes,0)
        self.assertGreater(self.s.controller.warmup,50);self.assertFalse(self.s.fatal)
    def test_near_boundary_tremor_does_not_create_large_pulse_steps(self):
        self.feed([.8]*8);self.feed([.808,.804]*40)
        changes=[abs(x['target']-1469) for x in self.device.commands]
        self.assertLessEqual(max(changes),2);self.assertEqual(self.device.arms,1)
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
        self.assertTrue(all(abs(x['velocity_us_s'])<=40.001 and abs(x['acceleration_us_s2'])<=80.001 for x in trace))
        for previous,current in zip(trace,trace[1:]):
            dt=(current['mono_ms']-previous['mono_ms'])/1000.
            self.assertLessEqual(abs(current['acceleration_us_s2']-previous['acceleration_us_s2']),400.*dt+.02)
    def test_soft_limit_brakes_once_without_repeated_restarts_or_creeping(self):
        self.device.pulse=self.device.accepted_target_us=1590
        self.s.current=self.device.status();self.s.controller=self.s.fresh();self.s.pva=[1590.,0.,0.]
        self.feed([.9]*120)
        self.assertTrue(self.s.limit_side);self.assertFalse(self.s.fatal)
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
        self.feed([.5]*2);packet=self.packet(.5);self.s.step(packet)
        self.assertTrue(self.s.active);self.assertEqual(self.device.commands,[])
        self.s.step(packet);self.tick(3)
        self.assertEqual(self.device.commands,[]);self.assertIsNone(self.s.authority)


if __name__=='__main__':unittest.main()
