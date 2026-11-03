"""Optional local SFace inference under the camera's existing DPU owner.

There is deliberately no per-vector FP32 fallback: those vectors belong to a
different template space. Rollback selects the preserved Windows config/store.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import time

from board.identity.deferred import DeferredIdentity
from board.identity.model_store import MODEL_ID, MODEL_SHA256
from board.vision.dpu_vision_runtime import PinnedRunner, encode, sface_feature


class DpuSFace:
    kind = 'DPU_SFACE_INT8'
    model_id = MODEL_ID

    def __init__(self, config, schedule, owner, clock):
        if schedule is None or owner is None or not callable(clock):
            raise ValueError('DPU SFace requires the camera DPU owner and scheduler')
        backend = config['feature_backend']
        if config['model_id'] != MODEL_ID or backend['model_sha256'] != MODEL_SHA256:
            raise ValueError('DPU SFace model version mismatch')
        for key in ('model', 'manifest'):
            if hashlib.sha256(Path(backend[key]).read_bytes()).hexdigest() != backend[key + '_sha256']:
                raise ValueError('Pinned SFace artifact mismatch: ' + key)
        self.schedule, self.clock = schedule, clock
        self.source_ttl = backend['max_source_age_ms']
        self.requests = self.execution_attempts = self.completed = self.features_returned = 0
        self.deferred = self.slot_denials = self.expired_after_admission = 0
        self._closed = False
        self.runner = PinnedRunner(backend['model'], backend['manifest'], owner)
        if (self.runner.input_fix != 7 or list(self.runner.inputs[0].dims) != [1, 112, 112, 3]
                or len(self.runner.outputs) != 1 or list(self.runner.outputs[0].dims) != [1, 128]
                or self.runner.outputs[0].get_attr('fix_point') != 5):
            self.runner.close()
            raise ValueError('Unexpected SFace INT8 tensor contract')

    def _fresh(self, stamp):
        return type(stamp) is int and 0 <= self.clock() - stamp < self.source_ttl

    @contextmanager
    def _slot(self, stamp):
        wait_ms=getattr(self.schedule,'sface_slot_wait_ms',0)
        until=time.monotonic()+wait_ms/1000.
        while True:
            with self.schedule.optional('sface') as acquired:
                fresh=self._fresh(stamp)
                if acquired:
                    if not fresh:self.expired_after_admission+=1
                    else:self.execution_attempts+=1
                    yield fresh
                    return
                self.slot_denials+=1
            # No slot or state lock is held while waiting for the same owner.
            if (not wait_ms or not fresh or self.schedule.disabled('sface')
                    or time.monotonic()>=until
                    or not self.schedule.wait_for_optional('sface',until)):
                yield False
                return

    def _defer(self, message, *, retryable=False):
        self.deferred += 1
        raise DeferredIdentity(message,retryable=retryable)

    def feature(self, crop, *, source_mono_ms):
        self.requests += 1
        if not self._fresh(source_mono_ms) or not self.availability()['ready']:
            self._defer('SFace source expired or optional task disabled')

        attempts_before=self.execution_attempts
        def scheduled(normalized):
            source = encode(normalized, self.runner.input_fix)
            if not self._fresh(source_mono_ms):
                return None
            # Encoding and runner output allocation/dequantization are outside
            # the scheduling lock. Only execute_async/wait hold the DPU slot.
            result = self.runner.execute_encoded(source, slot=self._slot(source_mono_ms))
            if result is not None:
                self.completed += 1
            return result

        result = sface_feature(crop, self.runner, execute=scheduled)
        if result is None or not self._fresh(source_mono_ms):
            self._defer('SFace optional slot unavailable or result expired',
                retryable=self.execution_attempts==attempts_before and self._fresh(source_mono_ms)
                    and not self.schedule.disabled('sface'))
        self.features_returned += 1
        return result

    def availability(self):
        """Persistent protection is unavailable; ordinary slot contention is not."""
        reason = ('DPU_SFACE_CLOSED' if self._closed else
                  'DPU_SFACE_OPTIONAL_DISABLED' if self.schedule.disabled('sface') else None)
        return {'ready': reason is None, 'unavailable_reason': reason,
                'detail': '人脸识别服务暂不可用，请恢复服务后重试' if reason else '',
                'recovery_required': reason == 'DPU_SFACE_OPTIONAL_DISABLED'}

    def health(self):
        return {'kind': self.kind, 'model_id': self.model_id,
                **self.availability(),
                'requests': self.requests, 'execution_attempts': self.execution_attempts,
                'completed': self.completed, 'features_returned': self.features_returned,
                'deferred': self.deferred, 'slot_denials': self.slot_denials,
                'expired_after_admission': self.expired_after_admission,
                'last_dpu_wait_ms': self.runner.last_ms,
                'scheduler_calls_mean_admissions': True}

    def close(self):
        self._closed = True
        self.runner.close()
