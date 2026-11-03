import hashlib,unittest
from pathlib import Path
from types import SimpleNamespace
import test_deadline_driver as driver_fixtures
from continuous_face_control import EdgeConfig
from continuous_session import ContinuousSession
from deadline_driver import DeadlineDriver
from pwm_budget import INITIAL_PWM_MINIMUM_LEASE_MS
from pwm_fake_device import PWMDevice
from trajectory import Trajectory
from common.motion_observation import PROTOCOL
from vsrv_driver import COMMIT,STOP


class Scene:
    def __init__(self,anchor=947):
        self.now=1.;self.fid=0;self.anchor=anchor
        self.device=PWMDevice(lambda:self.now)
        lib=Path(__file__).parent.parent/'ps_trajectory_v1/libaura_trajectory_compat_host.so'
        trajectory=Trajectory(lib,hashlib.sha256(lib.read_bytes()).hexdigest())
        config=EdgeConfig(left_ratio=.1,confirm_frames=2,maximum_correction_us=None,
            prearm_confirmed_face=True,maximum_speed_us_s=20.,minimum_edge_speed_us_s=6.,velocity_gain_us=12.)
        self.session=ContinuousSession(self.device,'boot',config,lambda p:SimpleNamespace(reference_us=p),
            trajectory=trajectory,clock=lambda:self.now,allow_fixture=True)
    def packet(self,center=.808,anchor=None,**extra):
        self.fid+=1;stamp=round(self.now*1000)
        value=dict(protocol_version=PROTOCOL,source_kind='fixture',target_kind='face',board_boot_id='boot',
            service_epoch='service',camera_epoch='camera',state='READY',source_frame_id=self.fid,
            source_mono_ms=stamp,deadline_mono_ms=stamp+250,
            face_detection_mono_ms=self.anchor if anchor is None else anchor,
            frame_width=640,frame_height=480,mirror_horizontal=True,
            target=dict(track_id=1,track_generation=1,box=[center*640-40,100.,80.,80.],score=.95))
        value.update(extra);return value
    def tick(self,count=1):
        for _ in range(count):self.now+=.02;self.session.tick()
    def feed(self,center,frames,*,fresh_anchor=False):
        for _ in range(frames):
            self.session.step(self.packet(center,anchor=round(self.now*1000) if fresh_anchor else None));self.tick(4)
    def wait_at_edge(self):
        self.feed(.79,3);self.feed(.808,2)
        self.session.step(self.packet());self.tick()
        assert self.session.reason=='WAITING_FOR_INITIAL_PWM_BUDGET'


class InitialPWMTests(unittest.TestCase):
    def test_short_first_frame_leases_do_not_emit_old_width_pulses(self):
        # Original r12 would commit after 180ms with leases 6/11/19ms.
        for anchor in (947,952,960):
            with self.subTest(anchor=anchor):
                f=Scene(anchor);f.feed(.79,3);f.feed(.808,5)
                self.assertEqual(f.device.commands,[]);self.assertEqual(f.device.pulses,[])
                self.assertEqual(f.device.pulse,1469);self.assertFalse(f.session.fatal)
                self.assertGreater(f.session.initial_pwm_budget_waits,0)
                self.assertFalse(f.session.active)
    def test_adequate_first_lease_outputs_changed_target_next_frame(self):
        f=Scene(1000);f.feed(.79,3);f.feed(.808,3)
        self.assertTrue(f.device.commands)
        first=f.device.commands[0]
        self.assertEqual(first['minimum_lease_ms'],INITIAL_PWM_MINIMUM_LEASE_MS)
        self.assertGreaterEqual(round((first['deadline']-first['now'])*1000),INITIAL_PWM_MINIMUM_LEASE_MS)
        self.assertEqual(f.device.pulses[0]['pulse'],1469)
        self.assertEqual(f.device.pulses[1]['pulse'],1470)
        self.assertAlmostEqual(f.device.pulses[1]['now']-f.device.pulses[0]['now'],.02)
    def test_waiting_does_not_bank_unexecuted_position_or_velocity(self):
        f=Scene();f.feed(.79,3);f.feed(.808,2);f.session.step(f.packet())
        old_deadline=f.session.controller.authority_deadline_ms
        for _ in range(3):
            f.now+=.007;f.session.tick();self.assertEqual(f.session.pva,[1469.,0.,0.])
            self.assertEqual(f.session.controller.authority_deadline_ms,old_deadline)
        self.assertEqual(f.device.commands,[])
    def test_new_actual_frame_and_anchor_resume_from_rest_without_large_first_step(self):
        f=Scene();f.wait_at_edge()
        old_authority=f.session.authority
        f.session.step(f.packet(anchor=round(f.now*1000)))
        self.assertNotEqual(f.session.authority,old_authority)
        self.assertEqual(f.session.pva,[1469.,0.,0.]);f.tick()
        self.assertLess(abs(f.session.pva[1]),.2);self.assertEqual(f.device.commands,[])
        f.feed(.808,6,fresh_anchor=True)
        self.assertTrue(f.device.commands);self.assertEqual(f.device.commands[0]['target'],1470)
        self.assertEqual(f.device.arms,1)
    def test_duplicate_packet_does_not_renew_waiting_source_or_anchor(self):
        f=Scene();f.wait_at_edge();packet=f.packet();f.session.step(packet)
        deadline=f.session.controller.authority_deadline_ms
        for _ in range(5):f.session.step(packet);f.tick()
        self.assertEqual(f.device.commands,[]);self.assertFalse(f.session.active)
        self.assertEqual(deadline,947+500)
    def test_new_image_with_same_old_anchor_cannot_extend_first_frame_budget(self):
        f=Scene();f.wait_at_edge();deadline=f.session.controller.authority_deadline_ms
        f.session.step(f.packet());self.assertEqual(f.session.controller.authority_deadline_ms,deadline)
        f.tick();self.assertEqual(f.device.commands,[]);self.assertFalse(f.session.active)
    def test_inside_faces_never_start_pwm_even_with_short_anchors(self):
        f=Scene();f.feed(.79,10)
        self.assertEqual(f.device.commands,[]);self.assertEqual(f.device.pulses,[])
    def test_face_loss_while_waiting_stops_without_any_pwm(self):
        f=Scene();f.wait_at_edge();f.session.step(f.packet(state='NO_TARGET',target=None))
        self.assertFalse(f.session.active);self.assertEqual(f.device.pulses,[])
        self.assertEqual(f.device.status()['flags'],0)
    def test_changed_person_cannot_inherit_waiting_motion(self):
        f=Scene();f.wait_at_edge();p=f.packet();p['target']['track_generation']=2
        f.session.step(p)
        self.assertFalse(f.session.active);self.assertEqual(f.device.commands,[])
        self.assertEqual(f.session.reason,'FACE_CONTEXT_CHANGED')
    def test_already_running_renewals_do_not_receive_first_frame_minimum(self):
        f=Scene();f.feed(.79,3,fresh_anchor=True);f.feed(.9,20,fresh_anchor=True)
        self.assertGreater(len(f.device.commands),10);self.assertEqual(f.device.arms,1)
        self.assertEqual(f.device.commands[0]['minimum_lease_ms'],23)
        self.assertTrue(all(c['minimum_lease_ms']==0 for c in f.device.commands[1:]))
        self.assertTrue(all(abs(c['target']-1469)<=100 for c in f.device.commands))
        self.assertFalse(f.session.fatal)


class InitialPWMGuardTests(unittest.TestCase):
    def device(self,*args,**kwargs):
        return driver_fixtures.DeadlineTests().device(DeadlineDriver,*args,**kwargs)
    def test_short_first_leases_are_rejected_before_commit_and_verified_stopped(self):
        for freshness in (.027,.032,.039):
            d,io,clock=self.device();r=d.submit(1470,10.,freshness_s=freshness,minimum_lease_ms=23)
            self.assertEqual(r['outcome'],'REJECTED');self.assertEqual(r['reason'],'SUBMISSION_TOO_LATE')
            self.assertEqual(io.commits,[]);self.assertEqual(d.status()['flags'],0)
            self.assertEqual(d.last_delayed_submission['detected_phase'],'before_initial_pwm_commit')
    def test_sufficient_minimum_keeps_original_lease_formula(self):
        results=[]
        for minimum in (0,23):
            d,io,clock=self.device();r=d.submit(1470,10.,freshness_s=.06,minimum_lease_ms=minimum)
            self.assertEqual(r['outcome'],'ACCEPTED');results.append(r['lease_ms'])
            self.assertLessEqual(io.commits[0][1],10.06)
        self.assertEqual(results[0],results[1])
    def test_exact_full_frame_minimum_is_accepted(self):
        d,io,clock=self.device();r=d.submit(1470,10.,freshness_s=.044,minimum_lease_ms=23)
        self.assertEqual(r['outcome'],'ACCEPTED');self.assertGreaterEqual(r['lease_ms'],23)
        self.assertLess(r['lease_ms'],25)
    def test_shadow_io_consuming_first_frame_budget_rejects_before_commit(self):
        d,io,clock=self.device(.03,'shadow')
        r=d.submit(1470,10.,freshness_s=.07,minimum_lease_ms=23)
        self.assertEqual(r['outcome'],'REJECTED');self.assertEqual(io.commits,[])
        self.assertLess(d.last_delayed_submission['requested_lease_ms'],23)
        self.assertEqual(d.status()['flags'],0);self.assertIs(d.io,io)
    def test_running_short_renewal_is_not_subject_to_first_frame_minimum(self):
        d,io,clock=self.device();d.ack_seq=1;io.values.update({0x28:1,0x0c:15})
        r=d.submit(1469,10.,freshness_s=.027)
        self.assertEqual(r['outcome'],'ACCEPTED');self.assertLess(r['lease_ms'],20)
    def test_invalid_minimum_does_not_touch_hardware(self):
        for value in (-1,251,23.,True,None):
            d,io,clock=self.device()
            with self.assertRaises(ValueError):d.submit(1470,10.,minimum_lease_ms=value)
            self.assertEqual(io.commits,[]);self.assertEqual(io.values[0x0c],14)
    def test_stop_failure_on_first_frame_rejection_still_propagates(self):
        d,io,clock=self.device();original=io.write
        def failed(n,v):
            if n==0x24 and v==STOP:raise OSError('initial-stop-failure')
            return original(n,v)
        io.write=failed
        with self.assertRaisesRegex(OSError,'initial-stop-failure'):
            d.submit(1470,10.,freshness_s=.027,minimum_lease_ms=23)
        self.assertEqual(io.commits,[]);self.assertIs(d.io,io)
    def test_native_commit_error_with_initial_minimum_still_propagates(self):
        d,io,clock=self.device();original=io.write
        def failed(n,v):
            if n==0x24 and v==COMMIT:raise OSError('initial-native-failure')
            return original(n,v)
        io.write=failed
        with self.assertRaisesRegex(OSError,'initial-native-failure'):
            d.submit(1470,10.,minimum_lease_ms=23)
        self.assertEqual(d.status()['flags'],0);self.assertIs(d.io,io)


if __name__=='__main__':unittest.main()
