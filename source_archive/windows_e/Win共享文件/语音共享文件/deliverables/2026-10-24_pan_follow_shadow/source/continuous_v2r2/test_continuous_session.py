import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parent));sys.path.insert(0,str(Path(__file__).parents[1]))
from continuous_session import ContinuousSession
from continuous_face_control import EdgeConfig
from common.motion_observation import PROTOCOL

class Device:
    def __init__(self,clock):
        self.clock=clock;self.pulse=1476;self.reason=0;self.armed=False;self.reference_time=None
        self.epoch=11;self.session=1;self.commit_attempts=0;self.acks=[];self.arms=0;self.finishes=0;self.reference=None
    def status(self):return dict(flags=(15 if self.acks and self.armed else 14 if self.armed else 0),
        lease_left_ms=0,width_us=self.pulse,target_us=self.pulse,reason=self.reason,armed=self.armed,
        epoch=self.epoch,session=self.session,ack_seq=len(self.acks),reference_us=self.pulse)
    def confirm_and_arm(self,reference,session,epoch,**kwargs):
        self.reference=reference;self.reference_time=self.clock();self.armed=True;self.session=session;self.epoch=epoch;self.arms+=1
    def submit(self,pulse,stamp,**kwargs):
        assert self.armed and self.reference_time<=stamp<=self.clock() and self.clock()-stamp<.23
        self.pulse=pulse;self.acks.append((pulse,stamp));self.commit_attempts+=1
        return dict(outcome='ACCEPTED',readback=self.status())
    def stop(self):self.armed=False;self.reason=0;self.reference=None;return self.status()
    def finish(self):self.finishes+=1;return self.stop()

class ContinuousTests(unittest.TestCase):
    def setUp(self):
        self.now=1.;self.fid=0;self.device=Device(lambda:self.now)
        self.s=ContinuousSession(self.device,'boot',EdgeConfig(),lambda p:SimpleNamespace(reference_us=p),clock=lambda:self.now,allow_fixture=True)
    def packet(self,center=.5,**updates):
        self.now+=.05;self.fid+=1;stamp=int(self.now*1000)
        p=dict(protocol_version=PROTOCOL,source_kind='fixture',target_kind='face',board_boot_id='boot',
          service_epoch='service',camera_epoch='camera',state='READY',source_frame_id=self.fid,
          source_mono_ms=stamp,deadline_mono_ms=stamp+250,frame_width=640,frame_height=480,mirror_horizontal=True,
          target=dict(track_id=1,track_generation=1,box=[max(0.,center*640-40),100.,80.,80.],score=.95))
        p.update(updates);return p
    def feed(self,centers):
        for center in centers:self.s.step(self.packet(center))
    def test_inside_never_arms_even_as_face_and_body_move(self):
        self.feed([.2,.4,.6,.8]*12)
        self.assertEqual(self.device.arms,0);self.assertEqual(self.device.acks,[])
    def test_multiple_move_hold_cycles_without_restarting_process(self):
        for _ in range(2):
            self.feed([.85]*14);self.feed([.7]*6)
        self.assertGreaterEqual(self.s.segments,2);self.assertGreater(len(self.device.acks),0)
        self.assertFalse(self.s.active);self.assertFalse(self.s.fatal);self.assertEqual(self.device.status()['flags'],0)
    def test_loss_stops_then_fresh_face_reconfirms_before_rearming(self):
        self.feed([.85]*14);before=len(self.device.acks)
        self.s.step(self.packet(state='NO_TARGET',target=None))
        self.assertFalse(self.s.active);self.assertEqual(self.device.status()['flags'],0)
        self.feed([.85]*2);self.assertEqual(len(self.device.acks),before)
        self.feed([.85]*12);self.assertGreater(len(self.device.acks),before)
    def test_body_is_fatal_and_face_cannot_rearm_it(self):
        self.feed([.85]*12);self.s.step(self.packet(target_kind='body'))
        self.assertTrue(self.s.fatal);before=len(self.device.acks)
        self.feed([.85]*10);self.assertEqual(len(self.device.acks),before)
    def test_duplicate_frozen_frame_never_refreshes_lease(self):
        self.feed([.85]*12);p=self.packet(.85);self.s.step(p);before=len(self.device.acks)
        for _ in range(8):self.now+=.05;self.s.step(p)
        self.assertEqual(len(self.device.acks),before);self.assertFalse(self.s.active)
    def test_left_edge_uses_face_box_touch_for_actual_image_edge(self):
        self.feed([.0625]*14)
        self.assertGreater(len(self.device.acks),0);self.assertLess(self.device.pulse,1476)
    def test_limit_stops_and_outside_face_does_not_repeatedly_arm(self):
        self.feed([.94]*70);arms=self.device.arms
        self.feed([.94]*40)
        self.assertEqual(self.device.arms,arms);self.assertFalse(self.s.active)
        self.assertTrue(all(1425<=pulse<=1505 for pulse,stamp in self.device.acks))
    def test_disconnect_stops_and_no_frame_means_no_replay(self):
        self.feed([.85]*14);before=len(self.device.acks);self.s.disconnected()
        self.assertEqual(self.device.status()['flags'],0)
        self.now+=1;self.s.disconnected();self.assertEqual(len(self.device.acks),before)
    def test_hardware_error_latches_and_operator_close_is_stopped(self):
        self.feed([.85]*14);self.device.reason=3
        self.s.step(self.packet(.85));self.assertTrue(self.s.fatal)
        self.assertEqual(self.s.close()['readback']['flags'],0)
    def test_fresh_packet_cannot_turn_wrong_boot_into_recovery(self):
        self.s.step(self.packet(board_boot_id='other'));self.assertTrue(self.s.fatal)
    def test_perception_survives_arm_but_old_frames_and_commands_do_not(self):
        self.feed([.70,.72,.74,.76,.78,.80])
        self.s.step(self.packet(.82));old=self.packet(.84);self.s.step(old)
        self.assertTrue(self.s.active);self.assertEqual(self.device.acks,[])
        self.assertIsNone(self.s.controller.source);self.assertEqual(self.s.controller.velocity,0)
        self.assertGreater(self.s.controller.face_velocity,.2)
        self.now+=.01;self.s.step(old);self.assertEqual(self.device.acks,[])
        self.assertIsNone(self.s.controller.source)
        self.s.step(self.packet(.7));self.assertFalse(self.s.active)
        self.assertEqual(self.device.acks,[])

if __name__=='__main__':unittest.main()
