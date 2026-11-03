"""Finite bench register adapter; transport, locks and physical authority are external.

No device is opened here. The caller must verify current boot/firmware/owner,
an attended physical-reference receipt and the approved narrow window before
constructing the pinned transport. This adapter never constructs face packets
or calls the production face-submit API. Native final-write pauses (Q09) can
only be detected afterwards; hardware absolute deadlines are NOT guaranteed.
"""
import hashlib
import math
from pathlib import Path
import time

import batch_driver
import lease_aware_driver
import vsrv_driver
from batch_driver import BatchDriver
from vsrv_driver import BIND, REFERENCE, ARM, COMMIT, QUIESCE, PhysicalReference, BUILD_ID

DEPENDENCY_SHA256 = {
    'batch_driver': '2e7814b604a421e9462ec3ff4403c6524c53f6578fe626d83af0a821bdac8db3',
    'lease_aware_driver': '9f0d1e2ae2de2dc7b01311467bbf97ffdbc5bf9a5478caff1b51809880020d62',
    'vsrv_driver': '10e17c980a775fe11085e33fb2065920494e773a55cb734db63de52c9bafda6b',
}


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


class FixedBenchDriver(BatchDriver):
    hardware_absolute_deadline_guaranteed = False

    def __init__(self, registers, build_id, boot_id, *, minimum_us, maximum_us,
                 clock=time.monotonic, sleep=time.sleep):
        for module in (batch_driver, lease_aware_driver, vsrv_driver):
            require(hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() == DEPENDENCY_SHA256[module.__name__],
                    'PINNED_DRIVER_DEPENDENCY_CHANGED')
        require(build_id == BUILD_ID and type(minimum_us) is int and type(maximum_us) is int
                and 1400 <= minimum_us < maximum_us <= 1600 and maximum_us - minimum_us <= 20,
                'APPROVED_NARROW_BENCH_WINDOW_REQUIRED')
        self.minimum_us, self.maximum_us, self.sleep = minimum_us, maximum_us, sleep
        self._armed_at = self._bench_deadline = self._prior_target = None
        self.last_failure = None
        super().__init__(registers, build_id, boot_id, clock=clock)

    def _sample(self):
        began = self.clock()
        result = super().status()
        ended = self.clock()
        require(math.isfinite(began) and math.isfinite(ended) and ended >= began, 'INVALID_STATUS_CLOCK')
        # The batch API does not expose the exact lease-register sampling time.
        # Preserve its interval: ended is a conservative expiry upper bound,
        # began + (lease-1)ms is a conservative still-live lower bound.
        return dict(result), began, ended

    def status(self):
        return self._sample()[0]

    def _stop_preserving(self, error):
        evidence = dict(error_type=type(error).__name__, error=str(error), stop_confirmed=False)
        try:
            stopped = self.stop()
            evidence['stopped'] = dict(stopped)
            evidence['stop_confirmed'] = stopped['flags'] == 0 and stopped['lease_left_ms'] == 0
        except BaseException as stop_error:
            evidence['stop_error'] = dict(type=type(stop_error).__name__, message=str(stop_error))
        self.last_failure = evidence
        # Keep the original exception identity/traceback even if STOP failed.
        try:
            error.bench_cleanup = evidence
        except BaseException:
            pass

    def stop(self):
        result = super().stop()
        require(result['flags'] == 0 and result['lease_left_ms'] == 0 and result['reason'] == 0,
                'EXACT_STOP_NOT_CONFIRMED')
        self._armed_at = self._bench_deadline = self._prior_target = None
        return result

    def confirm_and_arm(self, reference, session, epoch, *, authorized=False):
        try:
            require(authorized is True and isinstance(reference, PhysicalReference)
                    and reference.boot_id == self.boot_id and reference.confirmed is True
                    and self.minimum_us <= reference.reference_us <= self.maximum_us,
                    'CURRENT_OBSERVED_REFERENCE_REQUIRED')
            require(type(session) is int and 0 < session <= 0xffffffff and type(epoch) is int and 0 < epoch <= 0xffffffff,
                    'EXPLICIT_BENCH_SESSION_REQUIRED')
            before = self.status()
            require(before['flags'] == 0 and before['lease_left_ms'] == 0 and before['reason'] == 0
                    and before['width_us'] == before['target_us'] == reference.reference_us
                    and epoch == before['epoch'] + 1, 'STOPPED_POSITION_OR_EPOCH_NOT_CONFIRMED')
            armed_at = self.clock()
            self.stop()
            self.io.write(0x10, session)
            self.io.write(0x14, epoch)
            bound = self._command(BIND)
            require(bound['flags'] == 8 and bound['session'] == session and bound['epoch'] == epoch
                    and bound['ack_seq'] == 0, 'BIND_ACK_MISMATCH')
            self.io.write(0x3c, reference.reference_us)
            defined = self._command(REFERENCE)
            require(defined['flags'] == 12 and defined['reference_us'] == defined['width_us'] == defined['target_us'] == reference.reference_us,
                    'REFERENCE_ACK_MISMATCH')
            armed = self._command(ARM)
            require(armed['flags'] == 14 and armed['session'] == session and armed['epoch'] == epoch
                    and armed['ack_seq'] == 0 and armed['lease_left_ms'] == 0, 'ARM_ACK_MISMATCH')
            self.reference, self.session, self.epoch = reference, session, epoch
            self.reference_time, self.ack_seq, self.accepted_target_us = self.clock(), 0, reference.reference_us
            self._armed_at, self._bench_deadline, self._prior_target = armed_at, None, reference.reference_us
            self.last_failure = None
            return armed
        except BaseException as error:
            self._stop_preserving(error)
            raise

    def submit(self, *args, **kwargs):
        error = RuntimeError('FACE_SOURCE_SUBMIT_DISABLED_FOR_FINITE_BENCH')
        self._stop_preserving(error)
        raise error

    def _context(self, value, seq, target, widths, *, first=False):
        require(value['flags'] == (14 if first else 15) and value['reason'] == 0
                and value['session'] == self.session and value['epoch'] == self.epoch
                and value['ack_seq'] == seq and value['target_us'] == target
                and value['reference_us'] == self.reference.reference_us, 'BENCH_CONTEXT_OR_LEASE_LOST')
        require(value['lease_left_ms'] == 0 if first else 0 < value['lease_left_ms'] <= 100, 'BENCH_LEASE_INVALID')
        require(value['width_us'] in widths and self.minimum_us <= value['width_us'] <= self.maximum_us,
                'PWM_WIDTH_OUTSIDE_ACKNOWLEDGED_TRANSITION')

    def submit_bench(self, target_us, *, absolute_deadline_s, maximum_lease_ms, margin_ms):
        try:
            require(type(absolute_deadline_s) in (int, float) and math.isfinite(absolute_deadline_s)
                    and type(maximum_lease_ms) is int and 3 <= maximum_lease_ms <= 100
                    and type(margin_ms) is int and margin_ms == 20, 'INVALID_FINITE_BENCH_BUDGET')
            require(self.reference is not None and self._armed_at is not None and self.session is not None
                    and self.ack_seq < 0xffffffff, 'BENCH_NOT_ARMED')
            if self._bench_deadline is None:
                require(self.clock() < absolute_deadline_s <= self._armed_at + 5. + 1e-9,
                        'BENCH_DEADLINE_EXCEEDS_FIVE_SECONDS')
                self._bench_deadline = absolute_deadline_s
            require(absolute_deadline_s == self._bench_deadline, 'ORIGINAL_BENCH_DEADLINE_CHANGED')
            require(type(target_us) is int and self.minimum_us <= target_us <= self.maximum_us
                    and abs(target_us - self.reference.reference_us) <= 15
                    and abs(target_us - self.accepted_target_us) <= 1, 'BENCH_TARGET_OR_STEP_OUTSIDE_WINDOW')
            first, old_target, seq = self.ack_seq == 0, self.accepted_target_us, self.ack_seq + 1
            before, _, _ = self._sample()
            self._context(before, self.ack_seq, old_target, (self._prior_target, old_target), first=first)
            self.io.write(0x10, self.session)
            self.io.write(0x14, self.epoch)
            self.io.write(0x18, seq)
            self.io.write(0x1c, target_us)
            # 3ms preparation reserve accompanies the required 20ms margin.
            budget = min(maximum_lease_ms, math.floor((absolute_deadline_s - self.clock()) * 1000. - margin_ms - 3))
            require(budget >= (23 if first else 3), 'BENCH_LEASE_TOO_SHORT_BEFORE_COMMIT')
            self.io.write(0x20, budget)
            self.verify_identity()
            before_commit = self.clock()
            require(before_commit < absolute_deadline_s - .023
                    and before_commit + budget / 1000. <= absolute_deadline_s - .020,
                    'BENCH_DEADLINE_EXPIRED_BEFORE_NATIVE_COMMIT')
            self.commit_attempts += 1
            self.io.write(0x24, COMMIT)
            after, began, observed = self._sample()
            self._context(after, seq, target_us, (before['width_us'], old_target, target_us))
            require(observed < absolute_deadline_s - .020
                    and observed + after['lease_left_ms'] / 1000. <= absolute_deadline_s - .020 + 1e-9,
                    'BENCH_NATIVE_WRITE_OR_READBACK_LATE')
            require(self.clock() < began + (after['lease_left_ms'] - 1) / 1000., 'BENCH_ACK_LEASE_NO_LONGER_PROVEN_LIVE')
            self.ack_seq, self.accepted_target_us, self._prior_target = seq, target_us, old_target
            return dict(outcome='ACCEPTED', observed_mono_s=observed, snapshot_started_mono_s=began,
                        snapshot_timing='bounded_read_interval_end', readback=dict(after), lease_ms=budget,
                        lease_expiry_lower_bound_mono_s=began + (after['lease_left_ms'] - 1) / 1000.,
                        lease_expiry_upper_bound_mono_s=observed + after['lease_left_ms'] / 1000.,
                        absolute_deadline_mono_s=absolute_deadline_s, hardware_absolute_deadline_guaranteed=False)
        except BaseException as error:
            self._stop_preserving(error)
            raise

    def finish(self, *, absolute_deadline_s):
        try:
            require(self._bench_deadline is not None and absolute_deadline_s == self._bench_deadline,
                    'FINISH_REQUIRES_ORIGINAL_BENCH_DEADLINE')
            before, _, _ = self._sample()
            self._context(before, self.ack_seq, self.accepted_target_us,
                          (self._prior_target, self.accepted_target_us), first=self.ack_seq == 0)
            started = self.clock()
            require(started < absolute_deadline_s, 'FINISH_DEADLINE_ALREADY_EXPIRED')
            finish_deadline = min(absolute_deadline_s, started + .025)
            self.io.write(0x24, QUIESCE)
            for _ in range(1024):
                value, _, observed = self._sample()
                require(observed <= finish_deadline, 'QUIESCE_RETURNED_AFTER_FINISH_DEADLINE')
                require(all(value[k] == before[k] for k in ('session', 'epoch', 'ack_seq', 'target_us'))
                        and value['reason'] == 0, 'QUIESCE_CONTEXT_OR_LEASE_LOST')
                require(value['width_us'] in (before['width_us'], before['target_us']), 'QUIESCE_WIDTH_MISMATCH')
                if value['flags'] == 0 and value['lease_left_ms'] == 0:
                    self.session = self.epoch = self.reference = self.reference_time = None
                    return value
                require(value['flags'] == 15 and value['lease_left_ms'] > 0, 'QUIESCE_OUTPUT_NOT_CONFIRMED')
                require(observed < finish_deadline, 'QUIESCE_DEADLINE_EXPIRED')
                self.sleep(min(.0002, max(0., finish_deadline - self.clock())))
            raise RuntimeError('QUIESCE_POLL_BOUND_EXHAUSTED')
        except BaseException as error:
            self._stop_preserving(error)
            raise
