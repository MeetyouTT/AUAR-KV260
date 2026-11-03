"""Optional local SFace inference under the camera's existing DPU owner.

There is deliberately no per-vector FP32 fallback: those vectors belong to a
different template space. Rollback selects the preserved Windows config/store.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path

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
        with self.schedule.optional('sface') as acquired:
            # Check after admission as well as before preprocessing. No stale
            # packet may start a non-preemptible VART job.
            fresh = self._fresh(stamp)
            if not acquired:
                self.slot_denials += 1
            elif not fresh:
                self.expired_after_admission += 1
            else:
                # An attempt is not a completed job: execute_async/wait may
                # still fail. completed below counts successful actual output.
                self.execution_attempts += 1
            yield acquired and fresh

    def _defer(self, message):
        self.deferred += 1
        raise DeferredIdentity(message)

    def feature(self, crop, *, source_mono_ms):
        self.requests += 1
        if not self._fresh(source_mono_ms) or self.schedule.disabled('sface'):
            self._defer('SFace source expired or optional task disabled')

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
            self._defer('SFace optional slot unavailable or result expired')
        self.features_returned += 1
        return result

    def health(self):
        return {'kind': self.kind, 'model_id': self.model_id,
                'requests': self.requests, 'execution_attempts': self.execution_attempts,
                'completed': self.completed, 'features_returned': self.features_returned,
                'deferred': self.deferred, 'slot_denials': self.slot_denials,
                'expired_after_admission': self.expired_after_admission,
                'last_dpu_wait_ms': self.runner.last_ms,
                'scheduler_calls_mean_admissions': True}

    def close(self):
        self.runner.close()
