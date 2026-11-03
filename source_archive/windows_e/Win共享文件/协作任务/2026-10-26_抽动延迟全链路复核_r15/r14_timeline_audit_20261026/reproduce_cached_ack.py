"""Pure software counterexample; no transport, hardware, or release changes."""
import importlib.util
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT=Path('/home/ghmd/aura-pan-follow-shadow-20261024')
C=ROOT/'continuous_v10r14_candidate'
sys.path[:0]=[str(C),str(ROOT/'offline_host_driver')]
from deadline_driver import DeadlineDriver,CommitGuard,DelayedSubmission
from pulse_driver import PulseDriver
from vsrv_driver import COMMIT,STOP


class ClockRegisters:
    def __init__(self,clock,write_pause=0.):
        self.clock=clock;self.write_pause=write_pause;self.commits=[];self.stops=0
        self.expiry=self.next_frame=None;self.pulses=[]
        self.values={0:0x56535256,4:2,8:0x778d2512,0x0c:14,0x28:0,0x2c:1469,
                     0x30:0,0x34:7,0x38:9,0x40:1469,0x44:1469}
    def advance(self):
        if self.expiry is not None and self.values[0x0c]&1:
            while self.next_frame<=self.clock[0] and self.next_frame<self.expiry:
                target=self.values[0x44];width=self.values[0x2c]
                self.values[0x2c]=width+max(-4,min(4,target-width))
                self.pulses.append(dict(at=self.next_frame,width_us=self.values[0x2c]))
                self.next_frame+=.02
            if self.clock[0]>=self.expiry:
                self.values.update({0x0c:64,0x30:0})
            else:self.values[0x30]=math.ceil((self.expiry-self.clock[0])*1000.-1e-8)
    def read(self,n):
        self.advance();return self.values.get(n,0)
    def read_many(self,offsets):return [self.read(n) for n in offsets]
    def write(self,n,v):
        self.advance()
        if n==0x24 and v==STOP:
            self.values.update({0x0c:0,0x30:0});self.stops+=1;return
        if n==0x24 and v==COMMIT:
            self.clock[0]+=self.write_pause
            if not self.values[0x0c]&1:
                self.next_frame=self.clock[0]+.02
                self.pulses.append(dict(at=self.clock[0],width_us=self.values[0x2c]))
            self.expiry=self.clock[0]+self.values[0x20]/1000.
            self.values.update({0x0c:15,0x28:self.values[0x18],0x44:self.values[0x1c],0x30:self.values[0x20]})
            self.commits.append(dict(committed_at=self.clock[0],hardware_expiry=self.expiry))
        else:self.values[n]=v


class OneFreshReadbackDriver(DeadlineDriver):
    """Analysis-only variant: stale cached lease cannot be paired with later time.

    This is not production code. It preserves the original write guard, 20ms
    source margin, first-PWM minimum, and final STOP on uncertain context.
    """
    def submit(self,target_us,source_time,freshness_s=.25,margin_s=.02,*,minimum_lease_ms=0):
        deadline=source_time+freshness_s;evidence={};original=self.io
        self.io=CommitGuard(original,self.clock,deadline,margin_s,evidence,minimum_lease_ms)
        try:
            try:result=PulseDriver.submit(self,target_us,source_time,freshness_s,margin_s)
            except DelayedSubmission:
                stopped=self.status()
                assert stopped['flags']==0 and stopped['lease_left_ms']==0
                return dict(outcome='REJECTED',reason='SUBMISSION_TOO_LATE',readback=stopped)
            if result['outcome']=='ACCEPTED':
                now=self.clock();rb=result.get('readback') or self.status()
                if now<deadline-margin_s and now+rb['lease_left_ms']/1000.>deadline:
                    rb=self.status();now=self.clock()
                    matching=(rb['flags']==15 and rb['reason']==0 and rb['session']==self.session
                              and rb['epoch']==self.epoch and rb['ack_seq']==self.ack_seq
                              and rb['target_us']==self.accepted_target_us)
                    if not matching:
                        return dict(outcome='REJECTED',reason='FRESH_READBACK_CONTEXT_LOST',readback=self.stop())
                    result=dict(result,readback=rb)
                if now>=deadline-margin_s or now+rb['lease_left_ms']/1000.>deadline:
                    return dict(outcome='REJECTED',reason='SUBMISSION_TOO_LATE',readback=self.stop())
            return result
        finally:self.io=original


def run(driver_type,*,post_snapshot_pause=0.,native_pause=0.,corrupt_fresh=False):
    now=[10.];io=ClockRegisters(now,native_pause)
    driver=driver_type(io,0x778d2512,'boot',clock=lambda:now[0])
    driver.reference=SimpleNamespace();driver.reference_time=9.
    driver.session,driver.epoch,driver.ack_seq,driver.accepted_target_us=7,9,0,1469
    original_status=driver.status;paused=[False]
    def delayed_snapshot():
        status=original_status()
        if status['flags']==15 and not paused[0]:
            paused[0]=True
            now[0]+=post_snapshot_pause
            if corrupt_fresh:io.values[0x38]+=1
        return status
    driver.status=delayed_snapshot
    result=driver.submit(1470,10.,minimum_lease_ms=23)
    return dict(driver=driver_type.__name__,snapshot_pause_ms=post_snapshot_pause*1000,
        native_write_pause_ms=native_pause*1000,clock_now=now[0],original_deadline=10.25,
        hardware_commits=io.commits,hardware_was_inside_original_deadline=all(c['hardware_expiry']<=10.25 for c in io.commits),
        result=result['outcome'],reason=result.get('reason'),stop_writes=io.stops,
        final_readback=original_status(),pulse_outputs=io.pulses,physical_verified=False)


def main():
    rows=[]
    for scenario in [dict(post_snapshot_pause=.025),dict(post_snapshot_pause=.08),
                     dict(native_pause=.3),dict(post_snapshot_pause=.3),
                     dict(post_snapshot_pause=.025,corrupt_fresh=True),dict()]:
        rows.append(dict(scenario=scenario,before=run(DeadlineDriver,**scenario),
                         analysis_variant=run(OneFreshReadbackDriver,**scenario)))
    for row in rows[:2]:
        assert row['before']['result']=='REJECTED' and row['before']['hardware_was_inside_original_deadline']
        assert row['analysis_variant']['result']=='ACCEPTED' and row['analysis_variant']['stop_writes']==0
        assert len(row['analysis_variant']['hardware_commits'])==1
    assert all(row['analysis_variant']['result']=='REJECTED' for row in rows[2:5])
    assert rows[-1]['before']['result']==rows[-1]['analysis_variant']['result']=='ACCEPTED'
    print(json.dumps(dict(status='CACHED_ACK_FALSE_REJECTION_REPRODUCED',rows=rows,
        scope='independent decrementing hardware lease plus delayed Python return; no board or production modification'),indent=2))


if __name__=='__main__':main()
