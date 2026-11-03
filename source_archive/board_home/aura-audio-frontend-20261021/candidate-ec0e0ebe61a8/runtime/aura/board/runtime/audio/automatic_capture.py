"""Energy endpointing only: one bounded speech turn from an idle microphone.

No ASR/TTS/model inference runs here. Idle PCM is discarded; a short pre-roll
retains quiet initial consonants. The existing MCP01 owner closes capture
before the controller can start playback.
"""
from collections import deque
import signal
import threading

from board.runtime.audio.capture import Mcp01Capture
from board.runtime.audio.vad import EnergyVad, VadConfig


class SpeechEndpoint:
    def __init__(self, max_seconds=20, *, frame_classifier=None,pre_roll_ms=200):
        if not 1 <= max_seconds <= 20: raise ValueError('Speech limit must be 1–20 seconds')
        self.config = VadConfig(min_silence_ms=700, max_utterance_ms=int(max_seconds*1000)-200)
        self.vad = EnergyVad(self.config, frame_classifier=frame_classifier)
        self.frame_bytes = self.config.frame_samples*2
        if type(pre_roll_ms) is not int or not 200<=pre_roll_ms<=1000:raise ValueError('Invalid speech pre-roll')
        self.frame_classifier=frame_classifier
        self.pre_frames = pre_roll_ms//self.config.frame_ms
        self.start_frames = (self.config.min_speech_ms+self.config.frame_ms-1)//self.config.frame_ms
        self.ring = deque(maxlen=self.pre_frames+self.start_frames)
        self.pending = bytearray(); self.prefix = b''
        self.total_samples = self.speech_samples = self.start_sample = 0
        self.active = self.done = False

    def feed(self, pcm):
        import numpy as np
        if self.done: raise ValueError('Speech turn already completed')
        self.pending.extend(pcm)
        while len(self.pending) >= self.frame_bytes:
            raw = bytes(self.pending[:self.frame_bytes]); del self.pending[:self.frame_bytes]
            self.total_samples += self.config.frame_samples
            self.ring.append(raw)
            if self.active: self.speech_samples += self.config.frame_samples
            samples = np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
            for event in self.vad.accept(samples):
                if event.kind == 'speech_start':
                    self.active = True
                    self.prefix = b''.join(list(self.ring)[:-self.start_frames])
                    self.speech_samples = len(self.prefix)//2+self.start_frames*self.config.frame_samples
                elif event.kind == 'speech_end':
                    # PCM16 -> float32 / 32768 -> PCM16 is exact for these samples.
                    result = self.prefix + np.rint(event.audio*32768).clip(-32768,32767).astype('<i2').tobytes()
                    self.start_sample = self.total_samples-len(result)//2
                    self.speech_samples = len(result)//2
                    self.active = False; self.done = True
                    return result
        return None


class AutomaticMcp01Capture(Mcp01Capture):
    buffer_time_us = 160000

    def __init__(self,*args,audio_frontend=None,**kwargs):
        from common.frontend_wire import configuration
        self.audio_frontend=configuration(audio_frontend)
        super().__init__(*args,**kwargs)

    def _endpoint(self):
        from board.runtime.audio.remote_frontend import RemoteSpeechGate
        enabled=self.audio_frontend['enabled']
        return SpeechEndpoint(self.max_seconds,
            frame_classifier=RemoteSpeechGate(self.audio_frontend) if enabled else None,
            pre_roll_ms=500 if enabled else 200)

    def _close_endpoint(self):
        classifier=getattr(getattr(self,'endpoint',None),'frame_classifier',None)
        if classifier is not None and hasattr(classifier,'close'):classifier.close()

    def _finish(self,cancel):
        # Shut down an in-flight frame before waiting for the capture thread.
        # A cancelled socket cannot publish a late speech callback.
        if cancel:self._close_endpoint()
        return super()._finish(cancel)

    def _command(self):
        # Continuous only while waiting for one speech turn. Its memory stays
        # bounded even if the user remains silent for several minutes.
        return super()._command()[:-2]+['--buffer-time='+str(self.buffer_time_us),'--period-time=20000']

    def _capture_timer(self):
        self.input_ready = False
        self._close_endpoint()
        self.endpoint = self._endpoint()
        return None

    def _captured_start(self, started):
        return round(started+self.endpoint.start_sample*1000/16000)

    def _read_pcm(self,process):
        try:return self._read_automatic_pcm(process)
        finally:self._close_endpoint()

    def _read_automatic_pcm(self, process):
        while True:
            raw = process.stdout.read(self.endpoint.frame_bytes)
            if not raw:
                if self._cancelled: return b''
                raise RuntimeError('Microphone ended before a complete speech turn')
            self.input_ready = True
            was_active = self.endpoint.active
            result = self.endpoint.feed(raw)
            if self.endpoint.active and not was_active:
                callback=getattr(self,'on_speech_start',None)
                if callback:callback()
            with self._lock:
                self._sample_count = self.endpoint.speech_samples
                if self.endpoint.active and not was_active and self._timer is None:
                    self._timer = threading.Timer(self.max_seconds+2,self._timeout)
                    self._timer.daemon = True; self._timer.start()
                if result is not None:
                    if len(result) > self.max_samples*2: raise ValueError('Speech turn exceeds input budget')
                    self._stopping = True; self._signal(signal.SIGINT)
                    return result

    def snapshot(self):
        with self._lock:
            value = super().snapshot()
            endpoint = getattr(self,'endpoint',None)
            value.update(automatic=True,speech_active=bool(endpoint and endpoint.active),
                         input_ready=bool(getattr(self,'input_ready',False)),
                         listening_seconds=endpoint.total_samples/16000 if endpoint else 0)
            classifier=getattr(endpoint,'frame_classifier',None)
            value['audio_frontend']=(classifier.public() if classifier is not None else {'enabled':False})
            return value
