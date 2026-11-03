"""Independent lease/PWM time keeps advancing while Python holds an old ACK."""
import importlib.util
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'offline_host_driver')]
from deadline_driver import DeadlineDriver
from vsrv_driver import COMMIT,STOP


class TimedPWMRegisters:
    def __init__(self,clock,write_pause=0.):
        self.clock=clock;self.write_pause=write_pause;self.commits=[];self.pulses=[];self.stops=0
        self.expiry=self.next_frame=None
        self.values={0:0x56535256,4:2,8:0x778d2512,0x0c:14,0x28:0,0x2c:1469,
                     0x30:0,0x34:7,0x38:9,0x40:1469,0x44:1469}
    def advance(self):
        if self.expiry is not None and self.values[0x0c]&1:
            while self.next_frame<=self.clock[0] and self.next_frame<self.expiry:
                old,target=self.values[0x2c],self.values[0x44]
                self.values[0x2c]=old+max(-4,min(4,target-old))
                self.pulses.append((self.next_frame,self.values[0x2c]));self.next_frame+=.02
            if self.clock[0]>=self.expiry:self.values.update({0x0c:64,0x30:0})
            else:self.values[0x30]=math.ceil((self.expiry-self.clock[0])*1000.-1e-8)
    def read(self,n):self.advance();return self.values.get(n,0)
    def read_many(self,offsets):return [self.read(n) for n in offsets]
    def write(self,n,v):
        self.advance()
        if n==0x24 and v==STOP:
            self.stops+=1;self.values.update({0x0c:0,0x30:0});return
        if n==0x24 and v==COMMIT:
            self.clock[0]+=self.write_pause
            if not self.values[0x0c]&1:
                self.next_frame=self.clock[0]+.02;self.pulses.append((self.clock[0],self.values[0x2c]))
            self.expiry=self.clock[0]+self.values[0x20]/1000.
            self.values.update({0x0c:15,0x28:self.values[0x18],0x44:self.values[0x1c],0x30:self.values[0x20]})
            self.commits.append((self.clock[0],self.expiry))
        else:self.values[n]=v


def rig(driver_type=DeadlineDriver,*,cached_pause=0.,fresh_pause=0.,before_fresh_pause=0.,
        native_pause=0.,mutate_after_cached=None,fresh_error=None,stop_error=None):
    now=[10.];io=TimedPWMRegisters(now,native_pause)
    device=driver_type(io,0x778d2512,'boot',clock=lambda:now[0])
    device.reference=SimpleNamespace();device.reference_time=9.
    device.session,device.epoch,device.ack_seq,device.accepted_target_us=7,9,0,1469
    original=device.status;active_reads=[0]
    def status():
        # Once COMMIT has occurred, the second read is the fresh recheck.
        if io.commits and active_reads[0]==1:
            active_reads[0]+=1
            now[0]+=before_fresh_pause
            if fresh_error is not None:raise fresh_error
            value=original();now[0]+=fresh_pause
            return value
        value=original()
        if value['flags']==15 and active_reads[0]==0:
            active_reads[0]=1;now[0]+=cached_pause
            if mutate_after_cached:mutate_after_cached(io)
        return value
    device.status=status
    if stop_error is not None:
        write=io.write
        def failed(offset,value):
            if offset==0x24 and value==STOP:raise stop_error
            write(offset,value)
        io.write=failed
    return device,io,now,original


class CachedAckTests(unittest.TestCase):
    def test_pinned_r14_false_rejection_while_hardware_deadline_remains_legal(self):
        path=HERE.parent/'continuous_v10r14_candidate/deadline_driver.py'
        spec=importlib.util.spec_from_file_location('frozen_r14_deadline_test',path)
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        d,io,now,read=rig(old.DeadlineDriver,cached_pause=.025)
        result=d.submit(1470,10.,minimum_lease_ms=23)
        self.assertEqual(result['reason'],'SUBMISSION_TOO_LATE')
        self.assertEqual(io.stops,1);self.assertEqual(len(io.commits),1)
        self.assertLess(io.commits[0][1],10.25)
        self.assertEqual(io.pulses[1],(10.02,1470))

    def test_single_fresh_read_does_not_recommit_or_extend_hardware_lease(self):
        for pause in (.025,.08):
            with self.subTest(pause=pause):
                d,io,now,read=rig(cached_pause=pause)
                result=d.submit(1470,10.,minimum_lease_ms=23)
                self.assertEqual(result['outcome'],'ACCEPTED');self.assertEqual(io.stops,0)
                self.assertEqual(len(io.commits),1);self.assertAlmostEqual(io.expiry,10.23)
                self.assertEqual(d.readback_rechecks,1);self.assertEqual(d.readback_false_alarms_avoided,1)
                self.assertEqual(d.last_readback_recheck['outcome'],'FRESH_READBACK_CONFIRMED')
                self.assertEqual(result['readback']['lease_left_ms'],read()['lease_left_ms'])
                self.assertEqual(read()['width_us'],1470)

    def test_normal_timely_submission_does_not_add_readback_retry(self):
        d,io,now,read=rig();result=d.submit(1470,10.)
        self.assertEqual(result['outcome'],'ACCEPTED');self.assertEqual(d.readback_rechecks,0)
        self.assertEqual(d.readback_false_alarms_avoided,0);self.assertIsNone(d.last_readback_recheck)

    def test_small_real_native_delay_crossing_source_deadline_remains_rejected(self):
        d,io,now,read=rig(native_pause=.025);result=d.submit(1470,10.)
        self.assertEqual(result['reason'],'SUBMISSION_TOO_LATE');self.assertEqual(io.stops,1)
        self.assertGreater(io.commits[0][1],10.25);self.assertEqual(d.readback_rechecks,1)
        self.assertEqual(d.last_readback_recheck['outcome'],'ORIGINAL_DEADLINE_NOT_CONFIRMED')

    def test_large_native_delay_is_stopped_without_stale_recheck(self):
        d,io,now,read=rig(native_pause=.3);result=d.submit(1470,10.)
        self.assertEqual(result['reason'],'SUBMISSION_TOO_LATE');self.assertEqual(read()['flags'],0)
        self.assertEqual(d.readback_rechecks,0)

    def test_true_source_expiry_after_ack_is_never_rescued(self):
        d,io,now,read=rig(cached_pause=.3);result=d.submit(1470,10.)
        self.assertEqual(result['reason'],'SUBMISSION_TOO_LATE');self.assertEqual(read()['flags'],0)
        self.assertEqual(d.readback_rechecks,0)

    def test_pause_during_fresh_read_must_still_fit_original_deadline(self):
        d,io,now,read=rig(cached_pause=.025,fresh_pause=.03)
        result=d.submit(1470,10.)
        self.assertEqual(result['reason'],'SUBMISSION_TOO_LATE');self.assertEqual(read()['flags'],0)
        self.assertEqual(d.readback_rechecks,1);self.assertEqual(d.readback_false_alarms_avoided,0)
        self.assertEqual(len(io.commits),1)

    def test_short_fresh_read_delay_with_remaining_margin_is_legal(self):
        d,io,now,read=rig(cached_pause=.025,fresh_pause=.005)
        result=d.submit(1470,10.)
        self.assertEqual(result['outcome'],'ACCEPTED');self.assertEqual(io.stops,0)
        self.assertAlmostEqual(io.expiry,10.23)

    def test_hardware_lease_expiry_during_fresh_read_returns_exact_expiry(self):
        d,io,now,read=rig(cached_pause=.025,before_fresh_pause=.21)
        result=d.submit(1470,10.)
        self.assertEqual(result['reason'],'SOURCE_LEASE_EXPIRED');self.assertEqual(result['outcome'],'REJECTED')
        self.assertEqual(result['rejected_readback']['flags'],64);self.assertEqual(read()['flags'],0)

    def test_each_owner_ack_target_or_flags_change_stops_as_unknown(self):
        for offset,value in [(0x34,8),(0x38,10),(0x28,9),(0x44,1471),(0x0c,14),(0x0c,47)]:
            with self.subTest(offset=offset):
                d,io,now,read=rig(cached_pause=.025,mutate_after_cached=lambda io:io.values.update({offset:value}))
                result=d.submit(1470,10.)
                self.assertEqual(result['outcome'],'UNKNOWN');self.assertEqual(result['reason'],'ACK_MISMATCH')
                self.assertEqual(read()['flags'],0);self.assertEqual(d.readback_false_alarms_avoided,0)

    def test_fresh_read_io_failure_stops_and_preserves_exception(self):
        failure=OSError('fresh-read-failed');d,io,now,read=rig(cached_pause=.025,fresh_error=failure)
        with self.assertRaises(OSError) as raised:d.submit(1470,10.)
        self.assertIs(raised.exception,failure);self.assertEqual(read()['flags'],0)
        self.assertIs(d.io,io);self.assertEqual(d.last_readback_recheck['outcome'],'READ_ERROR')

    def test_stop_failure_is_not_swallowed_by_fresh_io_error(self):
        original=OSError('fresh-read-failed');stop=OSError('stop-failed')
        d,io,now,read=rig(cached_pause=.025,fresh_error=original,stop_error=stop)
        with self.assertRaises(OSError) as raised:d.submit(1470,10.)
        self.assertIs(raised.exception,stop);self.assertIs(raised.exception.__context__,original)
        self.assertIs(d.io,io)

    def test_context_rejection_cannot_hide_stop_failure(self):
        stop=OSError('stop-context-failed')
        d,io,now,read=rig(cached_pause=.025,mutate_after_cached=lambda io:io.values.update({0x38:10}),stop_error=stop)
        with self.assertRaises(OSError) as raised:d.submit(1470,10.)
        self.assertIs(raised.exception,stop);self.assertIs(d.io,io)

    def test_first_pwm_minimum_lease_guard_remains_before_commit(self):
        d,io,now,read=rig(cached_pause=.025)
        result=d.submit(1470,10.,freshness_s=.04,minimum_lease_ms=23)
        self.assertEqual(result['reason'],'SUBMISSION_TOO_LATE');self.assertEqual(io.commits,[])
        self.assertEqual(d.readback_rechecks,0);self.assertEqual(read()['flags'],0)


if __name__=='__main__':unittest.main()
