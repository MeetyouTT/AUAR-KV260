"""YuNet DPU adapter with YOLO priority and explicit CPU fallback on overrun."""
from board.vision.dpu_vision_runtime import (PinnedRunner, encode, make_yunet,
    SlotAdmissionDenied, OptionalJobDisabled)
from contextlib import contextmanager
import hashlib
from pathlib import Path
import time
import math


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
        self.runner = PinnedRunner(config['face_backend']['model'], config['face_backend']['manifest'], owner)
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
        if check is not None:
            # An expired round must not seek another slot after preparation.
            check()
            return self.runner.execute_encoded(source,
                slot=self._guarded_slot(), pre_execute=check)
        return self.runner.execute_encoded(source, slot=self._completed_slot())

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
            return self.fallback.detect(image)
        result = self.detector.detect(image)
        self.kind = 'DPU_YUNET_INT8'
        return result

    def close(self):
        self.runner.close()
