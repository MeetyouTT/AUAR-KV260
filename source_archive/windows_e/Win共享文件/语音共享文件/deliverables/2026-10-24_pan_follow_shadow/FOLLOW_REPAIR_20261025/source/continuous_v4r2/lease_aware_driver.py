"""Preserve expiry evidence before the pinned VSRV driver clears it with STOP."""
from vsrv_driver import VSRVDriver,COMMIT


class SubmitRegisters:
    """Record successful writes without changing the verified transport."""
    def __init__(self,io):self.io=io;self.writes=[]
    def read(self,offset):return self.io.read(offset)
    def write(self,offset,value):
        self.io.write(offset,value)
        self.writes.append((offset,value))


class LeaseAwareDriver(VSRVDriver):
    def status(self):
        result = super().status()
        if getattr(self, '_submitting', False):
            self._submit_readback = dict(result)
            if self._submit_preflight is None:self._submit_preflight=dict(result)
        return result

    def stop(self):
        if getattr(self, '_submitting', False):
            # The inherited submit() calls STOP before returning a permission
            # rejection. Keep its actual pre-STOP read, not a later guess.
            self._rejection_readback = self._submit_readback
        return super().stop()

    def submit(self, target_us, source_time, freshness_s=.25, margin_s=.02):
        expected = dict(session=self.session, epoch=self.epoch, ack_seq=self.ack_seq,
                        target_us=self.accepted_target_us)
        self._submitting = True
        self._submit_readback = self._rejection_readback = None
        self._submit_preflight=None
        original=self.io;trace=SubmitRegisters(original);self.io=trace
        old_accepted=getattr(self,'_last_accepted',None)
        try:
            result = super().submit(target_us, source_time, freshness_s, margin_s)
        finally:
            self.io=original
            self._submitting = False
        if result['outcome']=='ACCEPTED':
            self._last_accepted=dict(session=self.session,epoch=self.epoch,ack_seq=self.ack_seq,
                target_us=self.accepted_target_us,expiry_not_before=source_time+freshness_s-margin_s-.002)
        before = self._rejection_readback
        if result.get('reason') == 'PERMISSION_OR_CONTEXT' and before is not None:
            result['rejected_readback'] = before
            # RTL reason 4 alone is insufficient: permission must be off and
            # every field must match this owner's previously accepted command.
            if (before['flags'] == 4 << 4 and before['lease_left_ms'] == 0
                    and 0 < expected['ack_seq'] < 0xffffffff
                    and all(before[k] == v for k, v in expected.items())):
                result['reason'] = 'SOURCE_LEASE_EXPIRED'
        if result.get('reason')=='HARDWARE_REJECTED':
            after=result.get('readback') or {};pre=self._submit_preflight or {}
            writes=trace.writes
            payload=dict(writes[:5])
            exact_writes=(len(writes)==6 and [x[0] for x in writes]==[0x10,0x14,0x18,0x1c,0x20,0x24]
                and writes[0][1]==expected['session'] and writes[1][1]==expected['epoch']
                and writes[2][1]==expected['ack_seq']+1 and writes[3][1]==target_us
                and 3<=writes[4][1]<=500 and writes[5][1]==COMMIT)
            # A rejected COMMIT after expiry overwrites RTL reason 4 with 2.
            # Permission-off alone is insufficient: require this exact live
            # preflight, prior accepted deadline, one exact submitted payload,
            # unchanged old ACK/target/context and matching shadow readback.
            if (old_accepted is not None and 0<expected['ack_seq']<0xffffffff
                    and pre.get('flags')==15 and pre.get('lease_left_ms',0)>0
                    and after.get('flags')==32 and after.get('lease_left_ms')==0
                    and all(pre.get(k)==v and after.get(k)==v and old_accepted.get(k)==v for k,v in expected.items())
                    and self.clock()>=old_accepted['expiry_not_before'] and exact_writes):
                shadow={offset:self.io.read(offset) for offset in payload}
                if shadow==payload:
                    evidence=dict(after,preflight=pre,submitted_shadow={str(k):v for k,v in shadow.items()},
                                  expiry_not_before=old_accepted['expiry_not_before'],observed_mono_s=self.clock())
                    self.stop()
                    result.update(reason='SOURCE_LEASE_EXPIRED',rejected_readback=evidence)
        return result
