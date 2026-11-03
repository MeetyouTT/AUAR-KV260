"""Native execution with unchanged encoded INT8/dequantized model interfaces."""
import time
import numpy as np

from board.vision.native_binding import NativeRunner, CompletionUnknown
from board.vision.dpu_vision_runtime import NativeExecutionError, encode, AdmissionCancelled


class TensorPort:
    def __init__(self, meta):
        self.name, self.dims, self.dtype = meta['name'], list(meta['dims']), meta['dtype']
        self.fix_point = meta['fix_point']
    def has_attr(self, name):return name == 'fix_point'
    def get_attr(self, name):
        if name != 'fix_point':raise ValueError('Unsupported tensor attribute')
        return self.fix_point


class NativePinnedRunner:
    native_critical = True

    def __init__(self, model_path, manifest_path, owner, *, task, model_sha256, manifest_sha256):
        self.owner = owner
        self.schedule = owner.native_schedule
        self.runner = NativeRunner(owner.native_context, task, model_path, model_sha256,
                                   manifest_path, manifest_sha256)
        self.inputs = [TensorPort(meta) for meta in self.runner.inputs]
        self.outputs = [TensorPort(meta) for meta in self.runner.outputs]
        self.input_fix = self.inputs[0].fix_point
        self.stage_kind = task
        self.metrics = owner.pipeline_metrics
        self.last_ms = None
        self.last_execution = self.last_report = None

    def execute_encoded(self, source, *, source_expires_ns, pre_execute=None):
        self.last_execution = self.last_report = None
        if (not isinstance(source,np.ndarray) or source.dtype != np.int8 or
                not source.flags.c_contiguous or list(source.shape) != self.inputs[0].dims):
            raise ValueError('DPU input shape mismatch')
        if pre_execute is not None:
            try:pre_execute()
            except AdmissionCancelled as exc:
                exc.native_not_submitted=True
                raise
        try:
            execution = self.runner.execute_encoded(source, source_expires_ns=source_expires_ns)
            self.last_execution, self.last_report = execution, execution.report
            execution = self.owner.native_context.confirm_result(execution)
            self.last_execution, self.last_report = execution, execution.report
        except CompletionUnknown as exc:
            self.last_report = getattr(exc,'native_report',None) or self.last_report
            error = NativeExecutionError('Native C++ completion was not confirmed')
            error.native_report = self.last_report
            raise error from exc
        report = execution.report
        self.schedule.note_result(self.stage_kind, report)
        if report['start_ns']:
            self.last_ms = (report['release_decision_ns']-report['start_ns'])/1e6
            self.metrics.value(self.stage_kind+'.native_lease',self.last_ms)
            self.metrics.value(self.stage_kind+'.python_return_after_release',
                max(0.,execution.returned_mono_ns-report['after_unlock_ns'])/1e6)
        if not execution.usable:return None
        if len(execution.outputs) != len(self.outputs):raise RuntimeError('Native port count changed')
        began = time.monotonic_ns()
        values = {port.name:np.frombuffer(raw,dtype=np.int8).reshape(port.dims).astype(np.float32)
                  * (2.**-port.fix_point) for port,raw in zip(self.outputs,execution.outputs)}
        self.metrics.elapsed(self.stage_kind+'.dequantize',began)
        return values

    def close(self):
        if self.runner is not None:
            self.runner.close()
            self.runner = None
