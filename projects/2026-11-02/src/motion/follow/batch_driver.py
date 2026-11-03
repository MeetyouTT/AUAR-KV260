"""Read one fenced status snapshot without per-word filesystem queries."""
from lease_aware_driver import LeaseAwareDriver
from vsrv_driver import ID,ABI


class BatchDriver(LeaseAwareDriver):
    def verify_identity(self):
        many=getattr(self.io,'read_many',None)
        if many is None:return super().verify_identity()
        if many((0,4,8))!=[ID,ABI,self.build_id]:
            raise RuntimeError('VSRV build/ABI mismatch; no command sent')

    def status(self):
        many=getattr(self.io,'read_many',None)
        if many is None:return super().status()
        fields=[('flags',0x0c),('width_us',0x2c),('lease_left_ms',0x30),
                ('session',0x34),('epoch',0x38),('reference_us',0x40),('target_us',0x44)]
        offsets=[0,4,8,0x28]+[offset for _,offset in fields]+[0x28]
        for _ in range(3):
            values=many(offsets)
            if values[:3]!=[ID,ABI,self.build_id]:
                raise RuntimeError('VSRV build/ABI mismatch; no command sent')
            if values[3]!=values[-1]:continue
            result={name:values[i+4] for i,(name,_) in enumerate(fields)}
            result.update(ack_seq=values[3],active=bool(result['flags']&1),armed=bool(result['flags']&2),
                referenced=bool(result['flags']&4),bound=bool(result['flags']&8),reason=result['flags']>>4&15)
            if getattr(self,'_submitting',False):
                self._submit_readback=dict(result)
                if self._submit_preflight is None:self._submit_preflight=dict(result)
            return result
        raise RuntimeError('Unstable command acknowledgement')
