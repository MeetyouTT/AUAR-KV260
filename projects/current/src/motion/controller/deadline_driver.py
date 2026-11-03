"""Reject detected delayed submissions; PL relative leases still have a final-write race.

This narrows and detects software stalls. It is not a hardware guarantee of an
absolute source deadline: a pause inside native write can precede MMIO commit.
"""
import math
from pulse_driver import PulseDriver
from vsrv_driver import COMMIT


class DelayedSubmission(RuntimeError):
    pass


class CommitGuard:
    def __init__(self,io,clock,deadline,margin,evidence,minimum_lease_ms=0):
        self.io,self.clock,self.deadline,self.margin,self.evidence=io,clock,deadline,margin,evidence
        self.lease_ms=None
        self.minimum_lease_ms=minimum_lease_ms
    def __getattr__(self,name):return getattr(self.io,name)
    def read(self,offset):return self.io.read(offset)
    def write(self,offset,value):
        if offset==0x20:self.lease_ms=value
        if offset==0x24 and value==COMMIT:
            now=self.clock()
            if (self.lease_ms is None or now>=self.deadline-self.margin-.003
                    or now+self.lease_ms/1000.>self.deadline):
                self.evidence.update(detected_phase='before_native_commit',observed_mono_s=now,
                    original_deadline_mono_s=self.deadline,requested_lease_ms=self.lease_ms)
                raise DelayedSubmission('Original image or anchor deadline cannot cover this lease')
            if self.lease_ms<self.minimum_lease_ms:
                self.evidence.update(detected_phase='before_initial_pwm_commit',observed_mono_s=now,
                    original_deadline_mono_s=self.deadline,requested_lease_ms=self.lease_ms,
                    minimum_lease_ms=self.minimum_lease_ms)
                raise DelayedSubmission('First PWM lease cannot cover the changed target frame')
        self.io.write(offset,value)


class DeadlineDriver(PulseDriver):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.delayed_submissions=0;self.last_delayed_submission=None
        self.readback_rechecks=0;self.readback_false_alarms_avoided=0
        self.last_readback_recheck=None
    def submit(self,target_us,source_time,freshness_s=.25,margin_s=.02,*,minimum_lease_ms=0):
        if type(minimum_lease_ms) is not int or not 0<=minimum_lease_ms<=250:
            raise ValueError('Minimum output lease must be an integer in 0..250ms')
        if not all(type(v) in (int,float) and math.isfinite(v) for v in (source_time,freshness_s,margin_s)):
            return super().submit(target_us,source_time,freshness_s,margin_s)
        deadline=source_time+freshness_s;evidence={};original=self.io
        self.io=CommitGuard(original,self.clock,deadline,margin_s,evidence,minimum_lease_ms)
        try:
            try:result=super().submit(target_us,source_time,freshness_s,margin_s)
            except DelayedSubmission:
                self.delayed_submissions+=1;self.last_delayed_submission=dict(evidence)
                # The pinned parent stops on all write exceptions. Verify it.
                stopped=self.status()
                if stopped['flags'] or stopped['lease_left_ms']:raise
                return dict(outcome='REJECTED',reason='SUBMISSION_TOO_LATE',readback=stopped,
                            rejected_readback=dict(evidence))
            if result['outcome']=='ACCEPTED':
                rb=result.get('readback') or self.status();now=self.clock()
                if now<deadline-margin_s and now+rb['lease_left_ms']/1000.>deadline:
                    # The parent's ACK snapshot can precede a Python/GIL
                    # pause. Adding its OLD remaining lease to a later now
                    # can invent a late hardware expiry. Read once again;
                    # this sends no COMMIT and cannot renew the actual lease.
                    self.readback_rechecks+=1
                    recheck=dict(cached_checked_mono_s=now,original_deadline_mono_s=deadline,
                                 cached_readback=dict(rb))
                    self.last_readback_recheck=recheck
                    try:
                        rb=self.status();now=self.clock()
                    except BaseException as exc:
                        recheck.update(outcome='READ_ERROR',error_type=type(exc).__name__)
                        self.stop()
                        raise
                    recheck.update(fresh_checked_mono_s=now,fresh_readback=dict(rb))
                    same=(rb['session']==self.session and rb['epoch']==self.epoch
                          and rb['ack_seq']==self.ack_seq and rb['target_us']==self.accepted_target_us)
                    if not (same and rb['flags']==15 and rb['reason']==0 and rb['lease_left_ms']>0):
                        expired=(same and rb['flags']==64 and rb['reason']==4 and rb['lease_left_ms']==0)
                        recheck['outcome']='LEASE_EXPIRED' if expired else 'CONTEXT_NOT_CONFIRMED'
                        stopped=self.stop()
                        return dict(outcome='REJECTED' if expired else 'UNKNOWN',
                            reason='SOURCE_LEASE_EXPIRED' if expired else 'ACK_MISMATCH',
                            readback=stopped,rejected_readback=dict(rb))
                    result=dict(result,readback=rb)
                    if now<deadline-margin_s and now+rb['lease_left_ms']/1000.<=deadline:
                        recheck['outcome']='FRESH_READBACK_CONFIRMED'
                        self.readback_false_alarms_avoided+=1
                    else:recheck['outcome']='ORIGINAL_DEADLINE_NOT_CONFIRMED'
                if now>=deadline-margin_s or now+rb['lease_left_ms']/1000.>deadline:
                    evidence.update(detected_phase='after_commit_readback',observed_mono_s=now,
                        original_deadline_mono_s=deadline,accepted_readback=dict(rb))
                    stopped=self.stop();self.delayed_submissions+=1;self.last_delayed_submission=dict(evidence)
                    return dict(outcome='REJECTED',reason='SUBMISSION_TOO_LATE',readback=stopped,
                                rejected_readback=dict(evidence))
            return result
        finally:self.io=original
