"""Pinned engineering SFace INT8 runner in the existing camera/DPU process.

YuNet/landmark alignment and matching remain on CPU. No second camera/process
or live xdputil query is created here. The owner has already checked hardware.
"""
import hashlib
from pathlib import Path
import re
import time


def quantize_crop(crop):
    import numpy as np
    if not isinstance(crop, np.ndarray) or crop.dtype != np.uint8 or crop.shape != (112, 112, 3):
        raise ValueError('DPU SFace needs an aligned uint8 BGR 112x112 crop')
    rgb = crop[:, :, ::-1].astype(np.float32)
    normalized = (rgb-np.float32(127.5))/np.float32(128.)
    return np.ascontiguousarray(np.clip(np.floor(normalized*128.+.5), -128, 127).astype(np.int8)[None])


def checked_subgraph(graph, fingerprint):
    subs = [s for s in graph.get_root_subgraph().toposort_child_subgraph()
            if s.has_attr('device') and s.get_attr('device') == 'DPU']
    if len(subs) != 1 or hex(int(subs[0].get_attr('dpu_fingerprint'))) != fingerprint:
        raise RuntimeError('SFace DPU partition/fingerprint mismatch')
    inputs, outputs = list(subs[0].get_input_tensors()), list(subs[0].get_output_tensors())
    if (len(inputs) != 1 or len(outputs) != 1 or list(inputs[0].dims) != [1,112,112,3]
            or list(outputs[0].dims) != [1,128] or inputs[0].get_attr('fix_point') != 7
            or outputs[0].get_attr('fix_point') != 5
            or any(str(t.dtype) != 'xint8' for t in inputs+outputs)):
        raise RuntimeError('SFace tensor layout/fix-point mismatch')
    return subs[0]


class DpuSFace:
    kind = 'DPU_SFACE_INT8'

    def __init__(self, config, schedule, owner_fingerprint):
        if schedule is None or owner_fingerprint != config['arch_fingerprint']:
            raise RuntimeError('DPU SFace requires the verified camera DPU owner/scheduler')
        expected = config['embedding_model_sha256']
        if (not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected)
                or config['model_id'] != 'sface-int8-'+expected[:16]):
            raise ValueError('SFace templates must use the exact INT8 model identity')
        path = Path(config['embedding_model'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('SFace xmodel hash mismatch')
        import xir
        import vart
        from board.vision.reference_faces import SFaceCompat
        self.graph = xir.Graph.deserialize(str(path))
        self.subgraph = checked_subgraph(self.graph, owner_fingerprint)
        self.runner = vart.Runner.create_runner(self.subgraph, 'run')
        self.align_crop = SFaceCompat.align_crop
        self.schedule, self.last_reason = schedule, ''
        self.last_ms = None

    def feature(self, crop):
        import numpy as np
        if self.runner is None:raise RuntimeError('DPU SFace runner is closed')
        data = quantize_crop(crop)
        output = np.empty((1,128), dtype=np.int8)
        with self.schedule.identity() as acquired:
            if not acquired:
                self.last_reason = '人体检测优先，等待身份推理时隙'
                return None
            before = time.monotonic()
            job = self.runner.execute_async([data], [output])
            # This board's VART binding takes the execute_async tuple as ONE
            # argument; a second wait timeout is unsupported.
            status = self.runner.wait(job)
            self.last_ms = (time.monotonic()-before)*1000
            if status != 0:raise RuntimeError('DPU SFace execution failed: '+str(status))
        if self.schedule.health()['identity_disabled']:
            raise RuntimeError('DPU身份推理超出预算，身份已暂停')
        values = output.reshape(128).astype(np.float32)/32.
        if not np.isfinite(values).all() or np.linalg.norm(values) <= 1e-8:
            raise RuntimeError('Invalid DPU SFace embedding')
        self.last_reason = ''
        return values

    def close(self):
        self.runner = None
        self.subgraph = self.graph = None
