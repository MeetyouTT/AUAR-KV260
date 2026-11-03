import unittest
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(1,str(Path(__file__).parents[1]/'offline_host_driver'))
from deadline_driver import DeadlineDriver,CommitGuard,DelayedSubmission
from pulse_driver import PulseDriver
from vsrv_driver import COMMIT,STOP


class TimedRegisters:
    def __init__(self,clock,delay=0.,delay_phase='commit'):
        self.clock=clock;self.delay=delay;self.delay_phase=delay_phase;self.commits=[]
        self.values={0:0x56535256,4:2,8:0x778d2512,0x0c:14,0x28:0,0x2c:1469,
                     0x30:0,0x34:7,0x38:9,0x40:1469,0x44:1469}
    def read_many(self,offsets):return [self.read(n) for n in offsets]
    def read(self,n):return self.values.get(n,0)
    def write(self,n,v):
        if n==0x24 and v==STOP:self.values.update({0x0c:0,0x30:0});return
        if n==0x24 and v==COMMIT:
            if self.delay_phase=='commit':self.clock[0]+=self.delay
            self.values.update({0x0c:15,0x28:self.values[0x18],0x44:self.values[0x1c],0x30:self.values[0x20]})
            self.commits.append((self.clock[0],self.clock[0]+self.values[0x20]/1000.))
            if self.delay_phase=='after_commit':self.clock[0]+=self.delay
        else:
            self.values[n]=v
            if n==0x1c and self.delay_phase=='shadow':self.clock[0]+=self.delay


class DeadlineTests(unittest.TestCase):
    def device(self,driver,delay=0.,phase='commit'):
        clock=[10.];io=TimedRegisters(clock,delay,phase)
        d=driver(io,0x778d2512,'boot',clock=lambda:clock[0])
        d.reference=SimpleNamespace();d.reference_time=9.
        d.session,d.epoch,d.ack_seq,d.accepted_target_us=7,9,0,1469
        return d,io,clock
    def test_windows_delayed_native_write_reproduces_old_acceptance(self):
        d,io,c=self.device(PulseDriver,.3)
        r=d.submit(1470,10.)
        self.assertEqual(r['outcome'],'ACCEPTED');self.assertGreater(io.commits[0][0],10.25)
        self.assertGreater(io.commits[0][1],10.25)
    def test_delayed_native_write_is_detected_and_stopped_after_commit(self):
        d,io,c=self.device(DeadlineDriver,.3)
        r=d.submit(1470,10.)
        self.assertEqual(r['outcome'],'REJECTED');self.assertEqual(r['reason'],'SUBMISSION_TOO_LATE')
        self.assertEqual(d.status()['flags'],0);self.assertEqual(d.delayed_submissions,1)
        self.assertEqual(d.last_delayed_submission['detected_phase'],'after_commit_readback')
        # Software cannot prevent a pause INSIDE native write before MMIO.
        self.assertGreater(io.commits[0][0],10.25)
    def test_guard_rejects_known_delay_before_entering_native_write(self):
        d,io,c=self.device(DeadlineDriver);evidence={}
        g=CommitGuard(io,lambda:c[0],10.25,.02,evidence)
        g.write(0x20,230);c[0]=10.1
        with self.assertRaises(DelayedSubmission):g.write(0x24,COMMIT)
        self.assertEqual(io.commits,[])
    def test_shadow_delay_cannot_commit(self):
        d,io,c=self.device(DeadlineDriver,.3,'shadow');r=d.submit(1470,10.)
        self.assertEqual(r['outcome'],'REJECTED');self.assertEqual(io.commits,[])
        self.assertEqual(d.status()['flags'],0)
    def test_timely_acceptance_and_short_anchor_keep_original_deadlines(self):
        for freshness in (.25,.05):
            d,io,c=self.device(DeadlineDriver);r=d.submit(1470,10.,freshness_s=freshness)
            self.assertEqual(r['outcome'],'ACCEPTED')
            self.assertLessEqual(io.commits[0][1],10.+freshness)
            self.assertEqual(d.delayed_submissions,0)
    def test_post_write_pause_revokes_instead_of_reporting_acceptance(self):
        d,io,c=self.device(DeadlineDriver,.3,'after_commit');r=d.submit(1470,10.)
        self.assertEqual(r['outcome'],'REJECTED');self.assertEqual(d.status()['flags'],0)
