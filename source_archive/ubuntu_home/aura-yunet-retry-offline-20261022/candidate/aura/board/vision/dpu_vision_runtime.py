"""Pinned candidate runners; caller supplies the single DPU owner and scheduler.

No camera, network, service control, identity database or FPGA loading here.
The four YuNet heads are matched by geometry, never VART's output ordering.
"""
import hashlib
import json
from pathlib import Path
import time
from contextlib import contextmanager
import numpy as np

FINGERPRINT = '0x101000056010407'


@contextmanager
def unrestricted_slot():
    yield True


def encode(values, fix_point):
    values = np.asarray(values, dtype=np.float32)
    if not np.isfinite(values).all():
        raise ValueError('Non-finite DPU input')
    return np.ascontiguousarray(np.clip(np.floor(values * (2. ** fix_point) + .5), -128, 127).astype(np.int8))


def tensor_meta(t):
    return {'name': t.name, 'dims': list(t.dims), 'dtype': str(t.dtype),
            'fix_point': t.get_attr('fix_point') if t.has_attr('fix_point') else None}


class PinnedRunner:
    def __init__(self, model_path, manifest_path, owner):
        # Production should pass its DpuYoloX instance; a fixed-input bench can
        # supply an equivalent owner holding the SAME project lock in this PID.
        if owner.fingerprint != FINGERPRINT or owner.ownership is None:
            raise RuntimeError('An active matching DPU owner is required')
        owner.ownership.fileno()
        self.owner = owner
        path = Path(model_path)
        manifest = json.loads(Path(manifest_path).read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['sha256']:
            raise ValueError('Candidate xmodel SHA256 mismatch')
        expected = [s for s in manifest['partitions'] if s['device'] == 'DPU']
        if len(expected) != 1 or expected[0]['fingerprint'] != FINGERPRINT:
            raise ValueError('Candidate manifest DPU mismatch')
        import xir
        import vart
        self.graph = xir.Graph.deserialize(str(path))
        subs = [s for s in self.graph.get_root_subgraph().toposort_child_subgraph()
                if s.has_attr('device') and s.get_attr('device') == 'DPU']
        if len(subs) != 1 or hex(int(subs[0].get_attr('dpu_fingerprint'))) != FINGERPRINT:
            raise ValueError('Compiled DPU fingerprint mismatch')
        # XIR exposes an unordered tensor set. VART's port order is the ABI for
        # execute_async; using XIR order can overrun a smaller output buffer.
        self.runner = vart.Runner.create_runner(subs[0], 'run')
        self.inputs = list(self.runner.get_input_tensors())
        self.outputs = list(self.runner.get_output_tensors())
        if ({t.name: tensor_meta(t) for t in self.inputs} != {t['name']: t for t in expected[0]['inputs']} or
                {t.name: tensor_meta(t) for t in self.outputs} != {t['name']: t for t in expected[0]['outputs']}):
            raise ValueError('Compiled tensor interface differs from manifest')
        if len(self.inputs) != 1 or any(str(t.dtype) != 'xint8' for t in self.inputs + self.outputs):
            raise ValueError('Expected INT8 tensors and exactly one input')
        self.input_fix = self.inputs[0].get_attr('fix_point')
        from board.vision.pipeline_metrics import PipelineMetrics
        self.metrics=getattr(owner,'pipeline_metrics',None) or PipelineMetrics()
        self.stage_kind='sface' if list(self.inputs[0].dims)==[1,112,112,3] else 'yunet'
        self.last_ms = None

    def execute(self, normalized_nhwc):
        return self.execute_encoded(encode(normalized_nhwc, self.input_fix))

    def _diagnostic_mark(self, phase, status=None):
        diagnostics = getattr(self.metrics,'optional_diagnostics',None)
        if diagnostics is not None and diagnostics.enabled:
            try:diagnostics.native_mark(self.stage_kind,phase,status)
            except Exception:diagnostics.error()

    def execute_encoded(self, source, *, slot=None, pre_execute=None):
        if self.runner is None:
            raise RuntimeError('DPU runner is closed')
        self.owner.ownership.fileno()
        if (not isinstance(source, np.ndarray) or source.dtype != np.int8
                or not source.flags.c_contiguous or list(source.shape) != list(self.inputs[0].dims)):
            raise ValueError('DPU input shape mismatch')
        allocate_started=time.monotonic_ns()
        outputs = [np.empty(tuple(t.dims), dtype=np.int8) for t in self.outputs]
        self.metrics.elapsed(self.stage_kind+'.allocate',allocate_started)
        slot_started=time.monotonic_ns()
        with (slot if slot is not None else unrestricted_slot()) as acquired:
            slot_wait_ms=(time.monotonic_ns()-slot_started)/1e6
            if not acquired:
                self.metrics.value(self.stage_kind+'.slot_wait',slot_wait_ms)
                return None
            started = time.monotonic()
            self._diagnostic_mark('execute_start')
            try:
                # After all preparation/admission/diagnostic overhead, directly
                # before VART. Raising releases the original slot and submits
                # no native job. The default path has no guard invocation.
                if pre_execute is not None:
                    pre_execute()
                job = self.runner.execute_async([source], outputs)
                self._diagnostic_mark('execute_return')
                self._diagnostic_mark('wait_start')
                status = self.runner.wait(job)
                self._diagnostic_mark('wait_end',status)
            except BaseException:
                self._diagnostic_mark('exception')
                raise
            self.last_ms = (time.monotonic() - started) * 1000
            if status != 0:
                raise RuntimeError('VART execution failed: ' + str(status))
        self.metrics.value(self.stage_kind+'.slot_wait',slot_wait_ms)
        self.metrics.value(self.stage_kind+'.execute_wait',self.last_ms)
        # Output conversion is CPU work; the next YOLO job can own the DPU now.
        dequantize_started=time.monotonic_ns()
        result={t.name: a.astype(np.float32) * (2. ** -t.get_attr('fix_point'))
                for t, a in zip(self.outputs, outputs)}
        self.metrics.elapsed(self.stage_kind+'.dequantize',dequantize_started)
        return result

    def close(self):
        self.runner = self.graph = None


def yunet_outputs(values):
    shapes = {(40, 40, 51), (20, 20, 34), (10, 10, 34), (5, 5, 51)}
    by_shape = {tuple(x.shape[1:]): x for x in values.values()}
    if len(values) != 4 or set(by_shape) != shapes:
        raise ValueError('YuNet must have four unique 320px output heads')
    raw = np.concatenate([by_shape[s].reshape(1, -1) for s in sorted(shapes, reverse=True)], axis=1).reshape(-1, 17)
    logits = raw[:, 14:16]
    e = np.exp(logits - logits.max(axis=1, keepdims=True))
    return raw[:, :14].copy(), e / e.sum(axis=1, keepdims=True), raw[:, 16:17].copy()


class YuNetNetwork:
    def __init__(self, runner, execute=None):
        self.runner = runner
        # The camera integration supplies a scheduling callback. The isolated
        # benchmark calls sequentially under its exclusive process owner.
        self.execute = execute or runner.execute

    def setInput(self, nchw_bgr):
        self.source = np.ascontiguousarray(nchw_bgr.transpose(0, 2, 3, 1) / 256.)

    def forward(self, names):
        if names != ['loc', 'conf', 'iou']:
            raise ValueError('Unsupported YuNet CPU outputs')
        result = self.execute(self.source)
        if result is None:
            # A skipped scheduling slot must not look like "no face" and break
            # a live identity binding. Integration must discard this packet.
            raise SlotUnavailable('Face detection skipped for a primary DPU deadline')
        return yunet_outputs(result)


class SlotUnavailable(RuntimeError):
    pass


class SlotAdmissionDenied(SlotUnavailable):
    """Enabled optional admission denied; rejected_at precedes its bookkeeping.

    The timestamp is the conservative admission-attempt start, not the exact
    scheduler decision. Only this exact exception is eligible for retry.
    """
    def __init__(self, rejected_at):
        super().__init__('YuNet optional slot admission denied')
        self.rejected_at = rejected_at


class AdmissionCancelled(RuntimeError):
    """The caller closed, its source expired, or its retry round expired."""
    def __init__(self, reason):
        super().__init__('YuNet admission cancelled: ' + reason)
        self.reason = reason


class OptionalJobDisabled(RuntimeError):
    """Overrun protection disabled this job; it is never a retry signal."""


def make_yunet(reference_model, runner, *, threshold=.9, execute=None):
    from board.vision.reference_faces import YuNetCompat
    result = YuNetCompat(reference_model, score_threshold=threshold, input_size=320)
    result.net = YuNetNetwork(runner, execute)
    return result


def sface_feature(crop, runner, execute=None):
    if not isinstance(crop, np.ndarray) or crop.dtype != np.uint8 or crop.shape != (112, 112, 3):
        raise ValueError('SFace needs an aligned uint8 112x112 BGR crop')
    prepare_started=time.monotonic_ns()
    source = (crop[:, :, ::-1].astype(np.float32)[None] - 127.5) / 128.
    metrics=getattr(runner,'metrics',None)
    if metrics:metrics.elapsed('sface.normalize_input',prepare_started)
    result = (execute or runner.execute)(source)
    if result is None:
        return None
    if len(result) != 1:
        raise ValueError('SFace must have one output')
    validate_started=time.monotonic_ns()
    feature = next(iter(result.values())).reshape(-1)
    if feature.shape != (128,) or not np.isfinite(feature).all() or np.linalg.norm(feature) <= 1e-8:
        raise ValueError('Invalid SFace INT8 feature')
    if metrics:metrics.elapsed('sface.validate_output',validate_started)
    return feature
