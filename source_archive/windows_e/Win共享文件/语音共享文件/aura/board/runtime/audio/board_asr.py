"""Opt-in same-model Paraformer PCM adapter; no capture, downloads or fallback.

Pins model and tokens by caller-reviewed SHA256. Runtime imports are lazy so
candidate control/memory tests run without ARM inference dependencies.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import threading
import time


class BoardAsrUnavailable(RuntimeError):
    pass


class BoardParaformer:
    SAMPLE_RATE = 16000
    MAX_SAMPLES = SAMPLE_RATE * 20

    def __init__(self, model_dir, *, model_sha256, tokens_sha256, num_threads=2,
                 clock=time.monotonic, recognizer_factory=None):
        if type(num_threads) is not int or not 1 <= num_threads <= 2:
            raise ValueError('Use one or two board ASR threads')
        root = Path(model_dir)
        paths = {'model.int8.onnx': model_sha256, 'tokens.txt': tokens_sha256}
        for name, expected in paths.items():
            path = root / name
            if (not isinstance(expected, str) or len(expected) != 64
                    or not path.is_file() or path.is_symlink()):
                raise BoardAsrUnavailable('Pinned Paraformer resource is missing')
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            if digest.hexdigest() != expected:
                raise BoardAsrUnavailable('Pinned Paraformer resource hash mismatch')
        try:
            import numpy as np
            if recognizer_factory is None:
                from sherpa_onnx import OfflineRecognizer
                recognizer_factory = OfflineRecognizer.from_paraformer
            self._recognizer = recognizer_factory(
                paraformer=str(root / 'model.int8.onnx'), tokens=str(root / 'tokens.txt'),
                num_threads=num_threads, sample_rate=self.SAMPLE_RATE, feature_dim=80,
                decoding_method='greedy_search', provider='cpu')
        except ImportError as exc:
            raise BoardAsrUnavailable('Board requires compatible numpy/sherpa-onnx') from exc
        self.np, self.clock, self._lock = np, clock, threading.Lock()
        self.model_sha256, self.tokens_sha256 = model_sha256, tokens_sha256

    def transcribe(self, pcm, *, sample_rate=16000, deadline, cancelled=lambda: False):
        if (type(sample_rate) is not int or sample_rate != self.SAMPLE_RATE
                or not isinstance(pcm, bytes) or not pcm or len(pcm) % 2
                or len(pcm) // 2 > self.MAX_SAMPLES):
            raise ValueError('ASR requires bounded 16 kHz mono PCM16')
        if cancelled():
            raise InterruptedError('ASR cancelled')
        if self.clock() >= deadline:
            raise TimeoutError('Original turn deadline expired before ASR')
        if not self._lock.acquire(blocking=False):
            raise RuntimeError('Board ASR is busy')
        try:
            samples = self.np.frombuffer(pcm, dtype='<i2').astype(self.np.float32) / 32768
            stream = self._recognizer.create_stream()
            stream.accept_waveform(self.SAMPLE_RATE, samples)
            self._recognizer.decode_stream(stream)
            if cancelled():
                raise InterruptedError('ASR cancelled; stale result discarded')
            if self.clock() >= deadline:
                raise TimeoutError('Original turn deadline expired during ASR')
            text = str(stream.result.text or '').strip()
            if not text:
                raise ValueError('Board ASR returned no speech')
            return text
        finally:
            self._lock.release()
