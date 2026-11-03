"""YOLO business owner after controlled adoption by the common native gate."""
import time
import numpy as np

from board.vision.yolo_dpu import original_person_boxes
from board.vision.native_errors import PrimaryAdmissionDeferred


PrimaryFrameDeferred = PrimaryAdmissionDeferred


class NativeYoloOwner:
    backend_kind = 'DPU'
    kind = 'DPU_YOLOX_NANO_PERSON'
    native_critical = True

    def __init__(self, original, context, schedule):
        if not context.adopted or original.handle is not None:
            raise ValueError('YOLO must be exclusively adopted before business use')
        self.original, self.native_context, self.native_schedule = original, context, schedule
        self.config, self.fingerprint = dict(original.config), original.fingerprint
        self.reference_check = getattr(original,'reference_check',None)
        self.startup_native_checks = dict(scope='reference/blank before context and workers; not recovery primary progression',
                                         result=self.reference_check)
        self.pipeline_metrics = getattr(original,'pipeline_metrics',None)
        self._closed = False

    @property
    def ownership(self):return self.original.ownership

    def detect_bgr(self, image, *, source_mono_ms):
        if self._closed:raise RuntimeError('Native YOLO is closed')
        if (not isinstance(image,np.ndarray) or image.dtype != np.uint8 or
                image.ndim != 3 or image.shape[2] != 3):
            raise ValueError('YOLO expects uint8 BGR image data')
        if type(source_mono_ms) is not int or source_mono_ms < 0:
            raise ValueError('Original captured monotonic millisecond stamp required')
        image = np.ascontiguousarray(image)
        height,width = image.shape[:2]
        execution = self.native_context.execute_yolo(image,width=width,height=height,
            stride=image.strides[0], source_expires_ns=(source_mono_ms+750)*1_000_000,
            primary_finish_ns=self.native_schedule.primary_deadline_ns())
        if not execution.usable:raise PrimaryFrameDeferred('YOLO source or original primary deadline expired')
        return original_person_boxes(execution.outputs,width,height,self.config['score_threshold'],
                                     self.config.get('person_nms_iou',.45))

    def verify_runtime(self):return self.fingerprint

    def close(self):
        if not self._closed:
            self.native_context.close()
            self._closed = True
