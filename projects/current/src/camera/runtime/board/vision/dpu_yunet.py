"""YuNet DPU adapter with YOLO priority and explicit CPU fallback on overrun."""
from board.vision.dpu_vision_runtime import (PinnedRunner, encode, make_yunet,
    SlotAdmissionDenied, OptionalJobDisabled)
from contextlib import contextmanager
import hashlib
from pathlib import Path
import time
import math
import threading


class DpuYuNet:
    kind = 'DPU_YUNET_INT8'

    def __init__(self, config, schedule, owner):
        from board.vision.reference_faces import YuNetCompat
        if schedule is None or owner is None:
            raise ValueError('DPU YuNet requires the camera owner and scheduler')
        for key in ('model', 'manifest'):
            path = Path(config['face_backend'][key])
            if hashlib.sha256(path.read_bytes()).hexdigest() != config['face_backend'][key + '_sha256']:
                raise ValueError('Pinned YuNet artifact mismatch: ' + key)
        self.schedule = schedule
        self._health_lock=threading.Lock()
        self.fallback_calls=self.fallback_failures=0
        self.fallback_last_ms=None;self.fallback_total_ms=0.;self.fallback_reason=None
        backend = config['face_backend']
        if getattr(schedule,'native_critical',False):
            from board.vision.native_runtime import NativePinnedRunner
            self.runner = NativePinnedRunner(backend['model'],backend['manifest'],owner,task='yunet',
                model_sha256=backend['model_sha256'],manifest_sha256=backend['manifest_sha256'])
            self.native_critical = True
        else:
            self.runner = PinnedRunner(backend['model'],backend['manifest'],owner)
        if self.runner.input_fix != 7 or list(self.runner.inputs[0].dims) != [1, 320, 320, 3]:
            self.runner.close()
            raise ValueError('Unexpected YuNet candidate input')
        self.detector = make_yunet(config['face_model'], self.runner,
            threshold=config['minimum_face_score'], execute=self.scheduled)
        self.fallback = YuNetCompat(config['face_model'], score_threshold=config['minimum_face_score'], input_size=320)

    def scheduled(self, normalized):
        # CPU input conversion is outside the DPU critical section.
        source = encode(normalized, self.runner.input_fix)
        check = getattr(self, '_admission_check', None)
        if getattr(self,'native_critical',False):
            return self._native_scheduled(source,check)
        if check is not None:
            # An expired round must not seek another slot after preparation.
            check()
            return self.runner.execute_encoded(source,
                slot=self._guarded_slot(), pre_execute=check)
        return self.runner.execute_encoded(source, slot=self._completed_slot())

    def _native_scheduled(self, source, check):
        from board.vision.dpu_vision_runtime import AdmissionCancelled, SlotUnavailable
        if check is None:
            raise ValueError('Native YuNet requires the source frame admission guard')
        expires = getattr(check,'source_expires_monotonic_ns',None)
        if type(expires) is not int or expires <= 0:
            raise ValueError('Native YuNet requires the original source expiry')
        began = time.monotonic()
        wait_ms = self.schedule.yunet_slot_wait_ms
        until = min(began+wait_ms/1000.,expires/1e9)
        deadline = getattr(check,'deadline_monotonic',None)
        if deadline is not None:
            if type(deadline) not in (int,float) or not math.isfinite(deadline):
                raise ValueError('Invalid face retry deadline')
            until = min(until,deadline)
            expires = min(expires,int(deadline*1e9))
        attempted = False
        while True:
            check()
            if attempted and (not wait_ms or time.monotonic() >= until):
                raise SlotAdmissionDenied(began)
            values = self.runner.execute_encoded(source,source_expires_ns=expires,pre_execute=check)
            report = self.runner.last_report
            if report is None:raise RuntimeError('Native YuNet omitted its execution report')
            if report['submitted'] or report['completed']:
                if values is not None:return values
                if time.monotonic_ns() >= expires:raise AdmissionCancelled('expired')
                if self.schedule.disabled('yunet'):
                    raise OptionalJobDisabled('YuNet disabled by native DPU protection')
                raise SlotUnavailable('Native YuNet completed but business result is withheld')
            attempted = True
            if self.schedule.disabled('yunet') and not self.schedule.recovery_ready('yunet'):
                raise OptionalJobDisabled('YuNet disabled by native DPU protection')
            if not wait_ms or not self.schedule.wait_for_optional('yunet',until):
                check()
                raise SlotAdmissionDenied(began)

    @contextmanager
    def _completed_slot(self):
        with self.schedule.optional('yunet') as acquired:
            yield acquired
            if acquired:
                self._confirm_completed()

    def _confirm_completed(self):
        # PinnedRunner exits its slot only after wait returned status 0.
        # Exceptions and pre-execute withdrawals never reach this marker.
        marker = getattr(self.schedule, 'native_completed', None)
        if marker is not None:
            marker('yunet')

    @contextmanager
    def _guarded_slot(self):
        # Start the denial window BEFORE scheduler/diagnostic bookkeeping.
        # This is a conservative admission-attempt time, not an exact sample
        # of the scheduler's decision. Slow diagnostics cannot extend it.
        admission_started_at = time.monotonic()
        wait_ms = getattr(self.schedule, 'yunet_slot_wait_ms', 0)
        check = getattr(self, '_admission_check', None)
        until = admission_started_at+wait_ms/1000.
        outer_deadline = getattr(check, 'deadline_monotonic', None)
        if wait_ms and outer_deadline is not None:
            if type(outer_deadline) not in (int, float) or not math.isfinite(outer_deadline):
                raise ValueError('Invalid face retry deadline')
            until = min(until, outer_deadline)
        attempted = False
        while True:
            if wait_ms and attempted and time.monotonic() >= until:
                if check is not None:check()
                raise SlotAdmissionDenied(admission_started_at)
            with self.schedule.optional('yunet') as acquired:
                if acquired:
                    yield True
                    self._confirm_completed()
                    return
            attempted = True
            if self.schedule.disabled('yunet'):
                raise OptionalJobDisabled('YuNet disabled by original DPU protection')
            if not wait_ms:
                raise SlotAdmissionDenied(admission_started_at)
            if not self.schedule.wait_for_optional('yunet', until):
                if check is not None:check()
                if self.schedule.disabled('yunet'):
                    raise OptionalJobDisabled('YuNet disabled by original DPU protection')
                raise SlotAdmissionDenied(admission_started_at)

    def detect_with_admission_guard(self, image, check):
        # FaceTargetService has one worker. Reject accidental nested use;
        # this is not an API for sharing a runner across threads.
        if getattr(self, '_admission_check', None) is not None:
            raise RuntimeError('YuNet admission guard is already active')
        check()
        self._admission_check = check
        try:
            return self.detect(image)
        finally:
            self._admission_check = None

    def detect(self, image):
        recovering = getattr(self.schedule, 'recovery_ready', lambda kind: False)
        if self.schedule.disabled('yunet') and not recovering('yunet'):
            self.kind = 'CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN'
            status=getattr(self.schedule,'optional_status',lambda kind:{})('yunet')
            reason=(status.get('recovery') or {}).get('reason') or 'optional_protection_disabled'
            started=time.monotonic()
            with self._health_lock:
                self.fallback_calls += 1;self.fallback_reason=reason
            try:
                return self.fallback.detect(image)
            except BaseException:
                with self._health_lock:self.fallback_failures += 1
                raise
            finally:
                elapsed=(time.monotonic()-started)*1000.
                with self._health_lock:
                    self.fallback_last_ms=elapsed;self.fallback_total_ms += elapsed
        result = self.detector.detect(image)
        self.kind = 'DPU_YUNET_INT8'
        return result

    def health(self):
        with self._health_lock:
            return {'kind':self.kind,'fallback_calls':self.fallback_calls,
                    'fallback_failures':self.fallback_failures,'fallback_last_ms':self.fallback_last_ms,
                    'fallback_total_ms':self.fallback_total_ms,'fallback_reason':self.fallback_reason}

    def close(self):
        self.runner.close()
