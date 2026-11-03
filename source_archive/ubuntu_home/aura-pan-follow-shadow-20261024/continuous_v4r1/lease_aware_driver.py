"""Preserve expiry evidence before the pinned VSRV driver clears it with STOP."""
from vsrv_driver import VSRVDriver


class LeaseAwareDriver(VSRVDriver):
    def status(self):
        result = super().status()
        if getattr(self, '_submitting', False):
            self._submit_readback = dict(result)
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
        try:
            result = super().submit(target_us, source_time, freshness_s, margin_s)
        finally:
            self._submitting = False
        before = self._rejection_readback
        if result.get('reason') == 'PERMISSION_OR_CONTEXT' and before is not None:
            result['rejected_readback'] = before
            # RTL reason 4 alone is insufficient: permission must be off and
            # every field must match this owner's previously accepted command.
            if (before['flags'] == 4 << 4 and before['lease_left_ms'] == 0
                    and 0 < expected['ack_seq'] < 0xffffffff
                    and all(before[k] == v for k, v in expected.items())):
                result['reason'] = 'SOURCE_LEASE_EXPIRED'
        return result
