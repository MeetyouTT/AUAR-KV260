"""Bounded raw capture pump; model/endpoint work stays on the consumer.

The producer does only fixed-size PCM reads and bounded queue insertion. Any
overflow invalidates the ENTIRE capture; no frame is silently dropped or
rejoined across a gap. The original single-capture owner remains responsible
for stopping its process and for final process/pipe cleanup. No input device
or process starts on import or construction.
"""
from collections import deque
import math
import signal
import threading
import time


class PcmInputError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class BoundedPcmInput:
    FRAME_BYTES = 640

    def __init__(self, stream, *, stop_source, cancelled=lambda: False,
                 max_frames=8, join_timeout=.5, clock=time.monotonic):
        if (not callable(getattr(stream, 'read', None)) or not callable(stop_source)
                or not callable(cancelled)):
            raise TypeError('Require an owned source and cancellation callbacks')
        if type(max_frames) is not int or not 1 <= max_frames <= 64:
            raise ValueError('Bound raw input to 1-64 frames')
        if (type(join_timeout) not in (int, float) or not math.isfinite(join_timeout)
                or not .05 <= join_timeout <= 2):
            raise ValueError('Bound source-reader cleanup wait')
        self.stream, self.stop_source, self.cancelled = stream, stop_source, cancelled
        self.max_frames, self.join_timeout, self.clock = max_frames, join_timeout, clock
        self.condition = threading.Condition()
        self.queue = deque()
        self.thread = None
        self.closed = self.eof = self.was_cancelled = False
        self.error = ''
        self.stop_requested = False
        self.frames_read = self.frames_delivered = self.peak_frames = 0
        self.read_ms_total = self.read_ms_max = 0.
        self.queue_ms_total = self.queue_ms_max = 0.

    def start(self):
        with self.condition:
            if self.thread is not None or self.closed:
                raise RuntimeError('PCM input pump is already started or closed')
            self.thread = threading.Thread(target=self._produce, name='aura-board-raw-pcm', daemon=True)
            self.thread.start()
        return self

    def _fail_locked(self, code):
        if not self.error:
            self.error = code
        self.queue.clear()
        self.condition.notify_all()

    def _produce(self):
        try:
            while True:
                if self.cancelled():
                    self.cancel()
                    return
                with self.condition:
                    if self.closed or self.error:
                        return
                began = self.clock()
                raw = self.stream.read(self.FRAME_BYTES)
                finished = self.clock()
                with self.condition:
                    # Stop/late EOF cannot publish into a newer capture.
                    if self.closed or self.error:
                        return
                    if raw == b'':
                        self.eof = True
                        self.condition.notify_all()
                        return
                    if not isinstance(raw, bytes) or len(raw) != self.FRAME_BYTES:
                        self._fail_locked('pcm_input_truncated_frame')
                        return
                    self.frames_read += 1
                    elapsed = max(0., (finished-began)*1000)
                    self.read_ms_total += elapsed
                    self.read_ms_max = max(self.read_ms_max, elapsed)
                    if len(self.queue) >= self.max_frames:
                        self._fail_locked('pcm_input_queue_overflow')
                        return
                    self.queue.append((finished, raw))
                    self.peak_frames = max(self.peak_frames, len(self.queue))
                    self.condition.notify_all()
        except Exception:
            with self.condition:
                if not self.closed:
                    self._fail_locked('pcm_input_read_failed')

    def read(self, size=FRAME_BYTES):
        """Consumer-only file-like read; never invokes a frontend model.

        A zero-length result means source EOF/normal close. Queue overflow and
        truncation always raise, including when previously queued frames were
        otherwise valid. Cancellation is checked at most every 20 ms of wait.
        """
        if type(size) is not int or size != self.FRAME_BYTES:
            raise ValueError('Consumer must request one 20 ms PCM16 frame')
        while True:
            if self.cancelled():
                self.cancel()
            with self.condition:
                if self.error:
                    raise PcmInputError(self.error)
                if self.was_cancelled:
                    raise InterruptedError('PCM input cancelled')
                if self.queue:
                    queued, raw = self.queue.popleft()
                    elapsed = max(0., (self.clock()-queued)*1000)
                    self.queue_ms_total += elapsed
                    self.queue_ms_max = max(self.queue_ms_max, elapsed)
                    self.frames_delivered += 1
                    return raw
                if self.eof or self.closed:
                    return b''
                if self.thread is None:
                    raise RuntimeError('Start the PCM input pump before reading')
                self.condition.wait(.02)

    def _stop(self, *, cancel=False):
        with self.condition:
            self.closed = True
            self.was_cancelled = bool(self.was_cancelled or cancel)
            self.queue.clear()
            self.condition.notify_all()
            thread = self.thread
            stop = bool(thread is not None and thread.is_alive() and not self.stop_requested)
            if stop:
                self.stop_requested = True
        if stop:
            try:
                # Caller supplies a stop signal for ONLY its own capture
                # process. Never close a BufferedReader underneath a blocking
                # read: its lock could turn cancellation into a deadlock.
                self.stop_source()
            except Exception:
                with self.condition:
                    self._fail_locked('pcm_input_source_stop_failed')
        return thread

    def cancel(self):
        self._stop(cancel=True)

    def close(self):
        thread = self._stop()
        if thread is not None and thread is not threading.current_thread():
            thread.join(self.join_timeout)
        return thread is None or not thread.is_alive()

    def finish(self):
        """Claim a complete turn only after stopping reads and checking faults."""
        stopped = self.close()
        with self.condition:
            if self.error:
                raise PcmInputError(self.error)
            if self.was_cancelled:
                raise InterruptedError('PCM input cancelled')
            if not stopped:
                raise PcmInputError('pcm_input_reader_not_stopped')

    def public(self):
        with self.condition:
            return dict(enabled=True, backend='bounded-board-raw-pcm',
                frame_bytes=self.FRAME_BYTES, capacity_frames=self.max_frames,
                capacity_ms=self.max_frames*20, queued_frames=len(self.queue),
                peak_frames=self.peak_frames, frames_read=self.frames_read,
                frames_delivered=self.frames_delivered,
                source_read_mean_ms=round(self.read_ms_total/max(1,self.frames_read),3),
                source_read_max_ms=round(self.read_ms_max,3),
                queue_mean_ms=round(self.queue_ms_total/max(1,self.frames_delivered),3),
                queue_max_ms=round(self.queue_ms_max,3),
                error=self.error, eof=self.eof, closed=self.closed,
                cancelled=self.was_cancelled,
                reader_alive=bool(self.thread and self.thread.is_alive()))


class _InputProcess:
    def __init__(self, process, stream):
        self.process, self.stdout = process, stream

    def __getattr__(self, name):
        return getattr(self.process, name)


class BoundedPcmCaptureMixin:
    """Put before AutomaticMcp01Capture/BargeInCapture in the candidate MRO.

    Both original read loops and all endpoint/echo/verification sample logic
    remain the consumer. The existing capture owner retains arecord and its
    device lock, signal/kill cleanup, 20-second bound and original PCM receipt.
    """
    frontend_queue_frames = 8

    def _read_pcm(self, process):
        pump = BoundedPcmInput(process.stdout,
            stop_source=lambda: self._signal(signal.SIGINT),
            cancelled=lambda: bool(self._cancelled),
            max_frames=self.frontend_queue_frames)
        self._board_pcm_input = pump
        try:
            pump.start()
            result = super()._read_pcm(_InputProcess(process, pump))
            # An overflow concurrent with the final model decision must still
            # invalidate this entire result instead of acknowledging a gap.
            pump.finish()
            return result
        finally:
            pump.close()

    def _finish(self, cancel):
        pump = getattr(self, '_board_pcm_input', None)
        if cancel and pump is not None:
            pump.cancel()
        return super()._finish(cancel)

    def snapshot(self):
        value = super().snapshot()
        pump = getattr(self, '_board_pcm_input', None)
        value['input_queue'] = (pump.public() if pump is not None else
            dict(enabled=True, capacity_frames=self.frontend_queue_frames, reader_alive=False))
        return value
