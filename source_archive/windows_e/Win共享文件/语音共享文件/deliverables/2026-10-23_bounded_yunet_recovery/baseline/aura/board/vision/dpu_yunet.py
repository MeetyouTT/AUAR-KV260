"""YuNet DPU adapter with YOLO priority and explicit CPU fallback on overrun."""
from board.vision.dpu_vision_runtime import (PinnedRunner, encode, make_yunet,
    SlotAdmissionDenied, OptionalJobDisabled)
from contextlib import contextmanager
import hashlib
from pathlib import Path
import time


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
        return self.runner.execute_encoded(source, slot=self.schedule.optional('yunet'))

    @contextmanager
    def _guarded_slot(self):
        # Start the denial window BEFORE scheduler/diagnostic bookkeeping.
        # This is a conservative admission-attempt time, not an exact sample
        # of the scheduler's decision. Slow diagnostics cannot extend it.
        admission_started_at = time.monotonic()
        with self.schedule.optional('yunet') as acquired:
            if not acquired:
                if self.schedule.disabled('yunet'):
                    raise OptionalJobDisabled('YuNet disabled by original DPU protection')
                raise SlotAdmissionDenied(admission_started_at)
            yield True

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
        if self.schedule.disabled('yunet'):
            self.kind = 'CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN'
            return self.fallback.detect(image)
        return self.detector.detect(image)

    def close(self):
        self.runner.close()
