"""Existing single-capture owners with an explicit local frontend factory.

No capture starts on import or construction. Failure never falls back to the
old Windows frontend or an energy-only detector. Original PCM remains the ASR
waveform; the exact existing endpoint retains onset/silence/pre-roll limits.
"""
from board.runtime.audio.automatic_capture import AutomaticMcp01Capture, SpeechEndpoint
from tools.barge_in_capture import BargeInCapture
from board.runtime.audio.board_pcm_queue import BoundedPcmCaptureMixin
import threading


class BoardFrontendPool:
    """One preloaded local model; cheap single-capture leases, never overlap.

    Construct the reviewed gate once during explicit initialization, before the
    UI begins listening. Capture rearming resets its original states and never
    imports/warms a second ONNX model on the audio/render owner.
    """
    def __init__(self, gate):
        if not callable(gate) or not all(hasattr(gate, name) for name in ('lock', 'denoiser', 'vad', 'close')):
            raise TypeError('A reviewed stateful board speech gate is required')
        self.gate = gate
        self.lock = threading.RLock()
        self.active = None
        self.closed = False

    def acquire(self):
        with self.lock:
            if self.closed or self.active is not None:
                raise RuntimeError('Board frontend is unavailable or still owned by another capture')
            if not self.gate.lock.acquire(blocking=False):
                raise RuntimeError('Previous board frontend frame is still finishing')
            try:
                self.gate.denoiser.reset()
                self.gate.vad.reset()
                self.gate.closed = False
                self.gate.error = ''
                self.gate.frames = self.gate.samples = 0
                self.gate.last_ms = None
                self.gate.max_ms = 0.
                lease = _FrontendLease(self)
                self.active = lease
                return lease
            finally:
                self.gate.lock.release()

    def _release(self, lease):
        with self.lock:
            if self.active is lease and lease.cancelled:
                # A native call already in progress must return before another
                # capture can reset/reuse its recurrent state.
                if self.gate.lock.acquire(blocking=False):
                    self.gate.lock.release()
                    self.active = None

    def close(self):
        with self.lock:
            self.closed = True
            if self.active is not None:
                self.active.close()
            else:
                self.gate.close()


class _FrontendLease:
    def __init__(self, pool):
        self.pool = pool
        self.cancelled = False

    def __call__(self, frame):
        if self.cancelled:
            raise InterruptedError('Board frontend capture lease was cancelled')
        try:
            result = self.pool.gate(frame)
            if self.cancelled:
                raise InterruptedError('Late board frontend decision discarded')
            return result
        finally:
            self.pool._release(self)

    def close(self):
        with self.pool.lock:
            if not self.cancelled:
                self.cancelled = True
                self.pool.gate.close()
            self.pool._release(self)

    def public(self):
        return dict(self.pool.gate.public(), capture_lease_closed=self.cancelled)


class _BoardEndpoint:
    def _endpoint(self):
        gate = self.frontend_factory()
        if not callable(gate) or not callable(getattr(gate, 'close', None)):
            raise TypeError('A closeable board frontend is required')
        return SpeechEndpoint(self.max_seconds, frame_classifier=gate, pre_roll_ms=500)


class BoardAutomaticCapture(_BoardEndpoint, BoundedPcmCaptureMixin, AutomaticMcp01Capture):
    def __init__(self, *args, frontend_factory, **kwargs):
        if not callable(frontend_factory):
            raise TypeError('An explicit board frontend factory is required')
        if kwargs.get('audio_frontend') is not None:
            raise ValueError('Board capture must not receive a legacy network frontend')
        self.frontend_factory = frontend_factory
        super().__init__(*args, **kwargs)


class BoardBargeCapture(_BoardEndpoint, BoundedPcmCaptureMixin, BargeInCapture):
    def __init__(self, *args, frontend_factory, **kwargs):
        if not callable(frontend_factory):
            raise TypeError('An explicit board frontend factory is required')
        if kwargs.get('audio_frontend') is not None:
            raise ValueError('Board capture must not receive a legacy network frontend')
        self.frontend_factory = frontend_factory
        super().__init__(*args, **kwargs)
