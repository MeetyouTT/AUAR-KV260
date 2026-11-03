"""Bounded MCP01 capture; the caller owns playback and media-session policy.

The verified MCP01 input is S16_LE/16 kHz/mono. Playback has a different
hardware format. No model, GUI, sound-server or camera is imported here.
"""
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time
import uuid

from host.model_service.protocol import AudioFormat, AudioRef

DEVICE = 'hw:CARD=MCP01,DEV=0'
FORMAT = AudioFormat(16000, 1, 'S16_LE')


@dataclass(frozen=True)
class CapturedAudio:
    capture_id: str
    audio: AudioRef
    pcm: bytes
    started_mono_ms: int
    ended_mono_ms: int

    def metadata(self):
        return {'capture_id': self.capture_id, 'audio_epoch': self.audio.audio_epoch,
                'first_sample_index': self.audio.first_sample_index,
                'sample_count': self.audio.sample_count,
                'format': {'rate_hz': FORMAT.rate_hz, 'channels': FORMAT.channels,
                           'sample_format': FORMAT.sample_format},
                'duration_seconds': self.audio.duration_s, 'pcm_bytes': len(self.pcm),
                'pcm_sha256': hashlib.sha256(self.pcm).hexdigest(),
                'started_mono_ms': self.started_mono_ms, 'ended_mono_ms': self.ended_mono_ms}


class Mcp01Capture:
    """One active recording, one bounded result, explicit half-duplex check.

    ``playback_active`` must read the playback owner's real state and raise
    when it cannot be read. It is called before opening the microphone.
    The caller must serialize later playback starts with recording starts.
    """
    def __init__(self, playback_active, *, max_seconds=20, device=DEVICE,
                 lock_path='/tmp/aura-mcp01-capture.lock', process_factory=subprocess.Popen,
                 clock=time.monotonic):
        if (not callable(playback_active) or type(max_seconds) not in (int, float)
                or not math.isfinite(max_seconds) or not .2 <= max_seconds <= 20):
            raise ValueError('Configure a playback-state reader and 0.2–20 seconds capture limit')
        if device != DEVICE:
            raise ValueError('This adapter requires the verified MCP01 capture device')
        self.playback_active, self.max_seconds = playback_active, max_seconds
        self.device, self.lock_path = device, Path(lock_path)
        self.process_factory, self.clock = process_factory, clock
        self.max_samples = int(max_seconds * FORMAT.rate_hz)
        self._lock = threading.RLock()
        self._thread = self._process = self._timer = self._owner = None
        self._result = None
        self._stopping = self._cancelled = self._closed = False
        self._forced_error = self.error = ''
        self._sample_count = 0
        self.state = 'IDLE'
        self.epoch = uuid.uuid4().int & 0x7fffffff

    def _acquire_owner(self):
        import fcntl
        fd = os.open(str(self.lock_path), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            os.close(fd)
            raise RuntimeError('MCP01 capture is already owned by another process') from None
        self._owner = fd

    def _release_owner(self):
        if self._owner is not None:
            os.close(self._owner)
            self._owner = None

    def start(self):
        with self._lock:
            if self._closed or self.state == 'RECORDING' or self._thread and self._thread.is_alive():
                raise RuntimeError('Capture is closed or already recording')
            if self._result is not None:
                raise RuntimeError('Consume or cancel the previous recording first')
            if self.playback_active() is not False:
                raise RuntimeError('Stop playback before recording')
            self._acquire_owner()
            log = tempfile.TemporaryFile()
            try:
                process = self.process_factory(['arecord', '--quiet', '--device', self.device,
                    '--format', 'S16_LE', '--rate', '16000', '--channels', '1',
                    '--file-type', 'raw', '--samples', str(self.max_samples)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=log)
            except Exception:
                log.close()
                self._release_owner()
                raise
            self.epoch += 1
            capture_id = uuid.uuid4().hex
            self._process = process
            self._stopping = self._cancelled = False
            self._forced_error = self.error = ''
            self._sample_count = 0
            self.state = 'RECORDING'
            started = round(self.clock() * 1000)
            self._timer = threading.Timer(self.max_seconds + 2, self._timeout)
            self._timer.daemon = True
            self._thread = threading.Thread(target=self._read,
                args=(process, log, capture_id, self.epoch, started),
                name='aura-mcp01-capture', daemon=True)
            self._timer.start()
            self._thread.start()
            return capture_id

    def _timeout(self):
        with self._lock:
            if self.state == 'RECORDING':
                self._forced_error = 'Microphone capture exceeded its time limit'
                self._signal(signal.SIGKILL)

    def _signal(self, signum):
        if self._process is not None and self._process.poll() is None:
            try:
                self._process.send_signal(signum)
            except ProcessLookupError:
                pass

    def _read(self, process, log, capture_id, epoch, started):
        pcm, error = bytearray(), ''
        try:
            while True:
                chunk = process.stdout.read(min(4096, self.max_samples * 2 - len(pcm) + 1))
                if not chunk:
                    break
                pcm.extend(chunk)
                with self._lock:
                    self._sample_count = len(pcm)//2
                if len(pcm) > self.max_samples * 2:
                    raise ValueError('Capture exceeded the declared sample limit')
            rc = process.wait(timeout=2)
            with self._lock:
                stopping = self._stopping
            if rc != 0 and not (stopping and rc in (1, -signal.SIGINT)):
                raise RuntimeError('arecord failed with exit code ' + str(rc))
            if len(pcm) % 2 or len(pcm) < 3200:
                raise ValueError('Recording is truncated or shorter than 100 ms')
        except Exception as exc:
            error = str(exc)
        finally:
            diagnostic = ''
            try:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=2)
                log.seek(0)
                diagnostic = log.read(2000).decode('utf-8', 'replace').strip()
            except Exception as exc:
                error = error or ('Capture cleanup failed: ' + str(exc))
            finally:
                process.stdout.close()
                log.close()
            with self._lock:
                self._timer.cancel()
                self._release_owner()
                self._process = None
                if self._cancelled:
                    self._result, self.state = None, 'CANCELLED'
                elif self._forced_error or error:
                    self.error = self._forced_error or error
                    if diagnostic:
                        self.error += ': ' + diagnostic
                    self._result, self.state = None, 'ERROR'
                else:
                    self._result = CapturedAudio(capture_id,
                        AudioRef(epoch, 0, len(pcm)//2, FORMAT), bytes(pcm),
                        started, round(self.clock()*1000))
                    self.state = 'READY'

    def _finish(self, cancel):
        with self._lock:
            if cancel:
                self._cancelled, self._result = True, None
            self._stopping = True
            self._signal(signal.SIGINT)
            thread = self._thread
        if thread is not None:
            thread.join(timeout=3)
            if thread.is_alive():
                with self._lock:
                    self._forced_error = 'Microphone did not stop in time'
                    self._signal(signal.SIGKILL)
                thread.join(timeout=2)
                if thread.is_alive():
                    raise RuntimeError('Microphone cleanup did not complete')
        with self._lock:
            if cancel:
                self.state = 'CANCELLED'

    def stop(self):
        self._finish(False)
        with self._lock:
            if self._result is None:
                raise RuntimeError(self.error or 'No completed recording')
            return self._result

    def take(self):
        with self._lock:
            if self._result is None:
                raise RuntimeError(self.error or 'No completed recording')
            result, self._result = self._result, None
            self.state = 'IDLE'
            return result

    def cancel(self):
        self._finish(True)

    def snapshot(self):
        with self._lock:
            return {'state': self.state, 'error': self.error, 'device': self.device,
                    'max_seconds': self.max_seconds, 'sample_count': self._sample_count,
                    'has_result': self._result is not None}

    def close(self):
        self.cancel()
        with self._lock:
            self._closed, self.state = True, 'CLOSED'

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
