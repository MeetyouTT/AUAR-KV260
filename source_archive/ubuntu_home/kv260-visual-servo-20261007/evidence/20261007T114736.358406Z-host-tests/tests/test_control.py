"""Host-only protocol tests against a register double, not board verification."""
import unittest
from dataclasses import replace
from vsrv_driver import ID,ABI,BIND,REFERENCE,ARM,COMMIT,STOP,PhysicalReference,VSRVDriver
from face_servo_control import FaceServoController


class Registers:
    def __init__(self):
        self.time=0.;self.deadline=None;self.writes=[];self.reject=False;self.wrong_ack=False;self.write_delay=0.
        self.mem={0:ID,4:ABI,8:123,0x0c:0,0x28:0,0x2c:1500,0x30:0,0x34:0,0x38:0,0x40:1500,0x44:1500}
    def read(self, offset):
        if self.deadline is not None and self.time>=self.deadline:
            self.mem[0x0c]=0x40;self.mem[0x30]=0;self.deadline=None
        return self.mem.get(offset,0)
    def write(self, offset,value):
        self.time+=self.write_delay
        self.writes.append((offset,value))
        if offset!=0x24:
            self.mem[offset]=value;return
        if value==STOP:
            self.mem[0x0c]=0;self.mem[0x30]=0;self.deadline=None
        elif value==BIND:
            self.mem[0x34]=self.mem[0x10];self.mem[0x38]=self.mem[0x14];self.mem[0x28]=0;self.mem[0x0c]=8
        elif value==REFERENCE:
            self.mem[0x2c]=self.mem[0x40]=self.mem[0x44]=self.mem[0x3c];self.mem[0x0c]=12
        elif value==ARM:
            self.mem[0x0c]=14
        elif value==COMMIT:
            if self.reject:
                self.mem[0x0c]=self.mem[0x0c]&15|0x20
            else:
                self.mem[0x28]=self.mem[0x18]+int(self.wrong_ack)
                self.mem[0x44]=self.mem[0x1c];self.mem[0x30]=self.mem[0x20];self.mem[0x0c]=15
                self.deadline=self.time+self.mem[0x20]/1000


def reference(**kwargs):
    return replace(PhysicalReference('boot',1460,'setup','TEST_DOUBLE_ONLY',1,True,True),**kwargs)


def frame(fid,source,center=480,**kwargs):
    target={'track_id':1,'generation':1,'epoch':'cam','frame_id':fid,'observed_time':source,
            'visible':True,'confirmed':True,'consecutive':6,'score':.95,'box':[center-40,100,80,80]}
    target.update(kwargs)
    return {'frame_id':fid,'observed_time':source,'epoch':'cam','target_id':1,'tracks':[target]}


class ProtocolTests(unittest.TestCase):
    def setup_driver(self,**kwargs):
        regs=Registers();driver=VSRVDriver(regs,123,'boot',lambda:regs.time)
        driver.confirm_and_arm(reference(**kwargs),11,22,authorized=True)
        return regs,driver
    def test_wrong_identity_causes_no_writes(self):
        regs=Registers();regs.mem[8]=999
        with self.assertRaises(RuntimeError):VSRVDriver(regs,123,'boot')
        self.assertEqual(regs.writes,[])
    def test_missing_authorization_causes_no_writes(self):
        regs=Registers();driver=VSRVDriver(regs,123,'boot')
        with self.assertRaises(ValueError):driver.confirm_and_arm(reference(),11,22)
        self.assertEqual(regs.writes,[])
    def test_changed_build_before_submit_causes_no_writes(self):
        regs,driver=self.setup_driver();regs.time=1.05;regs.mem[8]=999
        writes=list(regs.writes)
        with self.assertRaises(RuntimeError):driver.submit(1462,1.)
        self.assertEqual(regs.writes,writes)
    def test_stop_does_not_write_into_unknown_new_build(self):
        regs,driver=self.setup_driver();regs.mem[0]=0
        writes=list(regs.writes)
        with self.assertRaises(RuntimeError):driver.stop()
        self.assertEqual(regs.writes,writes)
    def test_reference_requires_pulse_polarity_and_mounting_declaration(self):
        for change in ({'reference_us':None},{'reference_us':1300},{'polarity':0},{'camera_moves_with_axis':None},{'confirmed':False}):
            with self.subTest(change=change),self.assertRaises(ValueError):reference(**change)
    def test_reference_is_not_forced_to_1500_or_active(self):
        regs,driver=self.setup_driver()
        result=driver.status()
        self.assertEqual(result['reference_us'],1460)
        self.assertEqual(result['width_us'],1460)
        self.assertFalse(result['active'])
        self.assertTrue(result['armed'])
    def test_acceptance_updates_seq_and_target(self):
        regs,driver=self.setup_driver();regs.time=1.05
        result=driver.submit(1462,1.)
        self.assertEqual(result['outcome'],'ACCEPTED')
        self.assertEqual(driver.ack_seq,1);self.assertEqual(driver.accepted_target_us,1462)
        self.assertLessEqual(regs.deadline,1.25)
    def test_rejection_does_not_advance(self):
        regs,driver=self.setup_driver();regs.time=1.05;regs.reject=True
        result=driver.submit(1462,1.)
        self.assertEqual(result['outcome'],'REJECTED')
        self.assertEqual(driver.ack_seq,0);self.assertEqual(driver.accepted_target_us,1460)
    def test_wrong_ack_stops_instead_of_claiming_success(self):
        regs,driver=self.setup_driver();regs.time=1.05;regs.wrong_ack=True
        result=driver.submit(1462,1.)
        self.assertEqual(result['outcome'],'UNKNOWN');self.assertEqual(driver.ack_seq,0)
        self.assertEqual(regs.mem[0x0c],0)
    def test_expired_permission_does_not_rearm(self):
        regs,driver=self.setup_driver();regs.time=1.05;driver.submit(1462,1.)
        regs.time=1.4
        result=driver.submit(1463,1.35)
        self.assertEqual(result['reason'],'PERMISSION_OR_CONTEXT')
        self.assertIsNone(driver.reference);self.assertEqual(regs.mem[0x0c],0)
    def test_shadow_write_delay_uses_original_observation(self):
        regs,driver=self.setup_driver();regs.time=1.05;regs.write_delay=.045
        result=driver.submit(1462,1.)
        self.assertEqual(result['reason'],'SUBMISSION_TOO_LATE')
        self.assertNotIn((0x24,COMMIT),regs.writes)
    def test_identity_read_delay_cannot_extend_expiry(self):
        regs,driver=self.setup_driver();regs.time=1.05
        original=regs.read
        delayed=False
        def read(offset):
            nonlocal delayed
            if offset==0 and 0x20 in regs.mem and not delayed:
                regs.time+=.25;delayed=True
            return original(offset)
        regs.read=read
        result=driver.submit(1462,1.)
        self.assertEqual(result['reason'],'SUBMISSION_TOO_LATE')
        self.assertNotIn((0x24,COMMIT),regs.writes)
    def test_stale_future_and_pre_reference_rejected(self):
        for now,source in [(1.3,1.),(1.,1.01),(.05,-.01)]:
            with self.subTest(now=now):
                regs,driver=self.setup_driver();regs.time=now
                result=driver.submit(1462,source)
                self.assertEqual(result['outcome'],'REJECTED')
                self.assertNotIn((0x24,COMMIT),regs.writes)


class ControllerTests(unittest.TestCase):
    def setup_control(self,**kwargs):
        regs=Registers();driver=VSRVDriver(regs,123,'boot',lambda:regs.time)
        driver.confirm_and_arm(reference(**kwargs),11,22,authorized=True)
        return regs,driver,FaceServoController(driver,'cam')
    def observe(self,regs,control,fid,t,center=480,**kwargs):
        regs.time=t+.05
        return control.observe(frame(fid,t,center,**kwargs),640,480,regs.time,'boot')
    def test_first_face_initializes_without_commit(self):
        regs,driver,control=self.setup_control()
        result=self.observe(regs,control,1,1.)
        self.assertEqual(result['reason'],'TARGET_INITIALIZED')
        self.assertEqual(driver.ack_seq,0)
    def test_five_confirmations_required(self):
        regs,driver,control=self.setup_control()
        result=self.observe(regs,control,1,1.,consecutive=4)
        self.assertEqual(result['reason'],'NEED_FIVE_CONFIRMATIONS');self.assertEqual(driver.ack_seq,0)
    def test_direction_polarity_and_actual_dt(self):
        for polarity,expected in [(1,1462),(-1,1458)]:
            regs,driver,control=self.setup_control(polarity=polarity)
            self.observe(regs,control,1,1.);r=self.observe(regs,control,2,1.1)
            self.assertEqual(r['outcome'],'ACCEPTED');self.assertEqual(control.accepted_us,expected)
            prior=control.accepted_us;self.observe(regs,control,3,1.25)
            self.assertEqual(abs(control.accepted_us-prior),3)
    def test_limit_and_max_step(self):
        regs,driver,control=self.setup_control();self.observe(regs,control,1,1.,580)
        prior=control.accepted_us
        for fid in range(2,90):
            r=self.observe(regs,control,fid,1.+fid*.1,580)
            self.assertEqual(r['outcome'],'ACCEPTED')
            self.assertLessEqual(abs(control.accepted_us-prior),4)
            self.assertLessEqual(control.accepted_us,1500);prior=control.accepted_us
        self.assertEqual(control.accepted_us,1500)
    def test_rejection_does_not_accumulate_target(self):
        regs,driver,control=self.setup_control();self.observe(regs,control,1,1.)
        regs.reject=True;self.observe(regs,control,2,1.1)
        self.assertEqual(control.requested_continuous,1460)
        regs.reject=False;self.observe(regs,control,3,1.2)
        self.assertEqual(control.accepted_us,1462)
    def test_lost_target_stops_and_reappearance_does_not_rearm(self):
        regs,driver,control=self.setup_control();self.observe(regs,control,1,1.);self.observe(regs,control,2,1.1)
        r=self.observe(regs,control,3,1.2,visible=False)
        self.assertEqual(r['reason'],'TARGET_LOST')
        r=self.observe(regs,control,4,1.3)
        self.assertEqual(r['reason'],'EXPLICIT_RECOVERY_REQUIRED');self.assertEqual(regs.mem[0x0c],0)
    def test_repeated_frame_does_not_renew(self):
        regs,driver,control=self.setup_control();self.observe(regs,control,1,1.);self.observe(regs,control,2,1.1)
        deadline=regs.deadline;self.observe(regs,control,2,1.1)
        self.assertEqual(regs.deadline,deadline)
    def test_invalid_quality_context_and_generation_stop(self):
        for changes in ({'box':[0,0,640,480]},{'score':.5},{'generation':2},{'frame_id':1}):
            regs,driver,control=self.setup_control();self.observe(regs,control,1,1.)
            with self.subTest(changes=changes):
                r=self.observe(regs,control,2,1.1,**changes)
                self.assertEqual(r['outcome'],'STOPPED');self.assertEqual(driver.ack_seq,0)
    def test_malformed_tracks_stop(self):
        regs,driver,control=self.setup_control();snapshot=frame(1,1.);snapshot['tracks']=None;regs.time=1.05
        r=control.observe(snapshot,640,480,1.05,'boot')
        self.assertEqual(r['reason'],'INVALID_TRACKS');self.assertEqual(regs.mem[0x0c],0)


if __name__=='__main__':unittest.main()
