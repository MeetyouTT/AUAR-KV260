"""VSRV/1 access protocol. No implicit ARM and no default physical reference.

Register transport is injected. This module does not open /dev/mem, load PL,
or adopt the simulation's 1500 us as the physical zero. A deployment must
provide a verified transport and a separately confirmed calibration.
"""
from dataclasses import dataclass
import math
import time

ID, ABI = 0x56535256, 1
BIND, REFERENCE, ARM, COMMIT, STOP = (0x42494e44, 0x52454621, 0x41524d21, 0x434d5421, 0x53544f50)


def uint32(value, nonzero=False):
    return type(value) is int and (1 if nonzero else 0) <= value <= 0xffffffff


@dataclass(frozen=True)
class PhysicalReference:
    """Measured pulse at the user's selected origin, valid for one boot/setup."""
    boot_id: str
    reference_us: int
    setup_id: str
    evidence: str
    polarity: int
    camera_moves_with_axis: bool
    confirmed: bool

    def __post_init__(self):
        if (not self.boot_id or not self.setup_id or not self.evidence or self.confirmed is not True
                or type(self.reference_us) is not int or not 1400 <= self.reference_us <= 1600
                or type(self.polarity) is not int or self.polarity not in (-1,1)
                or self.camera_moves_with_axis is not True):
            raise ValueError('A confirmed current-position pulse, polarity and moving camera are required')


class VSRVDriver:
    """Single-owner protocol adapter for an already verified register transport.

    An AXI write returning is not acceptance: seq, target, session, epoch and
    status must match afterwards. Independent hardware lease remains required.
    Transport exceptions are not converted into assumed successful motion.
    """
    def __init__(self, registers, build_id, boot_id, clock=time.monotonic):
        if not uint32(build_id) or not boot_id:
            raise ValueError('Exact build and boot identity required')
        self.io, self.build_id, self.boot_id, self.clock = registers, build_id, boot_id, clock
        self.session = self.epoch = None
        self.ack_seq = 0
        self.accepted_target_us = None
        self.reference = None
        self.reference_time = None
        self.commit_attempts = 0
        self.verify_identity()

    def verify_identity(self):
        values=[self.io.read(offset) for offset in (0,4,8)]
        if values != [ID,ABI,self.build_id]:
            raise RuntimeError('VSRV build/ABI mismatch; no command sent')

    def status(self):
        self.verify_identity()
        # Seq fences detect a changing result; single writer is a transport
        # requirement. Lease/active are allowed to fall during this read.
        for _ in range(3):
            seq=self.io.read(0x28)
            result={name:self.io.read(offset) for name,offset in
                    [('flags',0x0c),('width_us',0x2c),('lease_left_ms',0x30),
                     ('session',0x34),('epoch',0x38),('reference_us',0x40),('target_us',0x44)]}
            if seq==self.io.read(0x28):
                result['ack_seq']=seq
                result['active']=bool(result['flags']&1)
                result['armed']=bool(result['flags']&2)
                result['referenced']=bool(result['flags']&4)
                result['bound']=bool(result['flags']&8)
                result['reason']=result['flags']>>4&15
                return result
        raise RuntimeError('Unstable command acknowledgement')

    def stop(self):
        self.verify_identity()
        self.io.write(0x24,STOP)
        result=self.status()
        self.session=self.epoch=self.reference=None
        self.reference_time=None
        if result['flags']&15 or result['lease_left_ms']:
            raise RuntimeError('STOP not confirmed; hardware expiry must terminate output')
        return result

    def _command(self, value):
        self.verify_identity()
        self.io.write(0x24,value)
        result=self.status()
        if result['reason']:
            raise RuntimeError('Hardware rejected setup command: '+str(result['reason']))
        return result

    def confirm_and_arm(self, reference, session, epoch, *, authorized=False):
        if (authorized is not True or not isinstance(reference,PhysicalReference)
                or reference.boot_id!=self.boot_id or not uint32(session,True) or not uint32(epoch,True)):
            raise ValueError('Explicit authorization and matching physical reference required')
        self.verify_identity()
        self.stop()
        try:
            self.io.write(0x10,session);self.io.write(0x14,epoch)
            result=self._command(BIND)
            if result['session']!=session or result['epoch']!=epoch or result['ack_seq']!=0:
                raise RuntimeError('BIND readback mismatch')
            self.io.write(0x3c,reference.reference_us)
            result=self._command(REFERENCE)
            if (result['reference_us']!=reference.reference_us or result['width_us']!=reference.reference_us
                    or result['target_us']!=reference.reference_us or result['active']):
                raise RuntimeError('Reference readback mismatch')
            result=self._command(ARM)
            if result['flags']&15!=14:
                raise RuntimeError('ARM state mismatch')
            self.reference,self.session,self.epoch=reference,session,epoch
            self.reference_time=self.clock()
            self.ack_seq,self.accepted_target_us=0,reference.reference_us
            return result
        except Exception:
            self.stop()
            raise

    def submit(self, target_us, source_time, freshness_s=.25, margin_s=.02):
        # Times belong to this boot's monotonic domain. Target never extrapolates
        # the caller's budget through an old lease from a previous observation.
        if (type(target_us) is not int or not 1400<=target_us<=1600
                or not self.reference or self.session is None or self.epoch is None
                or type(source_time) not in (int,float) or not math.isfinite(source_time)
                or type(freshness_s) not in (int,float) or not math.isfinite(freshness_s)
                or type(margin_s) not in (int,float) or not math.isfinite(margin_s)
                or not 0<margin_s<freshness_s<=.5):
            raise ValueError('Invalid physical command/context')
        age=self.clock()-source_time
        budget=math.floor((freshness_s-age-margin_s)*1000)
        if age<0 or budget<1 or source_time<self.reference_time:
            self.stop()
            return {'outcome':'REJECTED','reason':'STALE_SOURCE','ack_seq':self.ack_seq}
        before=self.status()
        if (before['flags']&14!=14 or before['session']!=self.session or before['epoch']!=self.epoch
                or before['ack_seq']!=self.ack_seq or self.ack_seq==0xffffffff):
            self.stop()
            return {'outcome':'REJECTED','reason':'PERMISSION_OR_CONTEXT','ack_seq':self.ack_seq}
        seq=self.ack_seq+1
        try:
            self.io.write(0x10,self.session);self.io.write(0x14,self.epoch)
            self.io.write(0x18,seq);self.io.write(0x1c,target_us)
            # Recompute after shadow writes. Never extend source-based expiry.
            age=self.clock()-source_time
            budget=math.floor((freshness_s-age-margin_s)*1000)
            if age<0 or budget<1:
                self.stop()
                return {'outcome':'REJECTED','reason':'SUBMISSION_TOO_LATE','ack_seq':self.ack_seq}
            self.io.write(0x20,budget)
            self.verify_identity()
            remaining=math.floor((freshness_s-(self.clock()-source_time))*1000)
            if remaining<budget:
                self.stop()
                return {'outcome':'REJECTED','reason':'SUBMISSION_TOO_LATE','ack_seq':self.ack_seq}
            self.commit_attempts += 1
            self.io.write(0x24,COMMIT)
            after=self.status()
            if (after['reason']==0 and after['active'] and after['ack_seq']==seq
                    and after['target_us']==target_us and after['session']==self.session and after['epoch']==self.epoch):
                self.ack_seq,self.accepted_target_us=seq,target_us
                return {'outcome':'ACCEPTED','ack_seq':seq,'target_us':target_us,
                        'source_time':source_time,'lease_ms':budget,'readback':after}
            if (after['reason']==2 and after['ack_seq']==self.ack_seq
                    and after['target_us']==self.accepted_target_us and after['session']==self.session and after['epoch']==self.epoch):
                return {'outcome':'REJECTED','reason':'HARDWARE_REJECTED','ack_seq':self.ack_seq,'readback':after}
            self.stop()
            return {'outcome':'UNKNOWN','reason':'ACK_MISMATCH','ack_seq':self.ack_seq,'readback':after}
        except Exception:
            self.stop()
            raise
