"""Thin CPU adapter for pinned upstream Silero v4/v5 ONNX exports.

The learned detector is supplied by Silero/k2-fsa; this module only handles
20 ms PCM framing, recurrent state ownership and the existing endpoint API.
No model download, device access or network operation occurs here.
"""
import hashlib
import math
from pathlib import Path

import numpy as np


MODEL_HASHES = {
    '9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6': 'silero-v4-fp32-k2',
    'c36d490aff5ab924ca6c7aeec4d8f6bd3d22db6fa17611b9c5b17eae58ac3a20': 'silero-v4-int8-k2',
    # k2-fsa release asset 176977129. Upstream has no published digest;
    # this local fingerprint pins the downloaded official release artifact.
    '6b99cbfd39246b6706f98ec13c7c50c6b299181f2474fa05cbc8046acc274396': 'silero-v5-k2-release',
}


class SileroFrameGate:
    """One instance per capture, non-overlapping 512-sample model windows.

    A 20 ms endpoint frame uses the most recent complete window's decision;
    the initial incomplete window is not speech. Audio samples are untouched,
    so the existing pre-roll remains available for the utterance's onset.
    """
    def __init__(self, model_path, *, threshold=.5, session_factory=None):
        if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 < threshold < 1:
            raise ValueError('Require a finite probability threshold within (0, 1)')
        path = Path(model_path)
        if not 0 < path.stat().st_size <= 3*1024*1024:
            raise ValueError('Unexpected Silero export size')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest not in MODEL_HASHES:
            raise ValueError('Unverified Silero export')
        if session_factory is None:
            import onnxruntime as ort
            options = ort.SessionOptions()
            options.intra_op_num_threads = options.inter_op_num_threads = 1
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            self.session = ort.InferenceSession(str(path), sess_options=options,
                                                providers=['CPUExecutionProvider'])
        else:
            self.session = session_factory(path)
        inputs = [(v.name, v.shape, v.type) for v in self.session.get_inputs()]
        expected = [('x', [1, 512], 'tensor(float)'),
                    ('h', [2, 1, 64], 'tensor(float)'), ('c', [2, 1, 64], 'tensor(float)')]
        outputs = [v.name for v in self.session.get_outputs()]
        self.v5 = MODEL_HASHES[digest] == 'silero-v5-k2-release'
        if self.v5:
            expected = [('input', [None, None], 'tensor(float)'),
                        ('state', [2, None, 128], 'tensor(float)'), ('sr', [], 'tensor(int64)')]
        if inputs != expected or outputs != (['output', 'stateN'] if self.v5 else ['prob', 'new_h', 'new_c']):
            raise ValueError('Unexpected Silero export contract')
        self.model_id = MODEL_HASHES[digest]
        self.threshold = float(threshold)
        self.reset()

    def reset(self):
        self.h = np.zeros((2, 1, 64), dtype=np.float32)
        self.c = np.zeros((2, 1, 64), dtype=np.float32)
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.context = np.zeros((1, 64), dtype=np.float32)
        self.pending = np.empty(0, dtype=np.float32)
        self.probability = 0.
        self.windows = 0
        self.failed = False

    def __call__(self, frame):
        if self.failed:
            raise RuntimeError('Reset failed detector before reuse')
        samples = np.asarray(frame, dtype=np.float32)
        if samples.shape != (320,) or not np.isfinite(samples).all() or np.max(np.abs(samples)) > 1:
            raise ValueError('Require exactly 20 ms normalized 16 kHz mono audio')
        self.pending = np.concatenate((self.pending, samples))
        if len(self.pending) >= 512:
            window = self.pending[:512].reshape(1, 512)
            self.pending = self.pending[512:].copy()
            try:
                if self.v5:
                    combined = np.concatenate((self.context, window), axis=1)
                    prob, state = self.session.run(['output', 'stateN'],
                        {'input': combined, 'state': self.state, 'sr': np.array(16000, dtype=np.int64)})
                    if state.shape != (2, 1, 128) or not np.isfinite(state).all():
                        raise ValueError('Invalid v5 recurrent state')
                else:
                    prob, h, c = self.session.run(['prob', 'new_h', 'new_c'],
                                                   {'x': window, 'h': self.h, 'c': self.c})
                    if (h.shape != (2, 1, 64) or c.shape != (2, 1, 64)
                            or not np.isfinite(h).all() or not np.isfinite(c).all()):
                        raise ValueError('Invalid v4 recurrent state')
                p = float(np.asarray(prob).reshape(-1)[0])
                if np.asarray(prob).size != 1 or not math.isfinite(p) or not 0 <= p <= 1:
                    raise ValueError('Invalid detector output')
                if self.v5:
                    self.state = state
                    self.context = window[:, -64:].copy()
                else:
                    self.h, self.c = h, c
                self.probability = p
                self.windows += 1
            except Exception:
                self.failed = True
                raise
        return self.probability >= self.threshold

    def public(self):
        return {'model_id': self.model_id, 'threshold': self.threshold,
                'windows': self.windows, 'pending_samples': len(self.pending),
                'failed': self.failed, 'backend': 'onnxruntime-cpu-1-thread'}
