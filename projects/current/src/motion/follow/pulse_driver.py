"""Keep precise expiry evidence if the hardware expires during QUIESCE."""
from batch_driver import BatchDriver


class PulseDriver(BatchDriver):
    def status(self):
        value=super().status()
        if getattr(self,'_finishing_visual',False):self._finish_readback=dict(value)
        return value

    def stop(self):
        if getattr(self,'_finishing_visual',False):self._finish_rejection=self._finish_readback
        return super().stop()

    def finish(self,*args,**kwargs):
        expected=dict(session=self.session,epoch=self.epoch,ack_seq=self.ack_seq,target_us=self.accepted_target_us)
        self._finishing_visual=True;self._finish_readback=self._finish_rejection=None
        try:
            return super().finish(*args,**kwargs)
        except RuntimeError:
            rejected=self._finish_rejection
            # Parent finish already issued and verified STOP on failure. Only
            # the exact current owner's natural expiry is a completed stop.
            # Context changes, stuck output and other faults still propagate.
            if (rejected is None or rejected.get('flags')!=64 or rejected.get('lease_left_ms')!=0
                    or not 0<expected['ack_seq']<0xffffffff
                    or any(rejected.get(k)!=v for k,v in expected.items())):raise
            stopped=self.status()
            if stopped['flags'] or stopped['lease_left_ms'] or any(stopped.get(k)!=v for k,v in expected.items()):raise
            return stopped
        finally:self._finishing_visual=False
