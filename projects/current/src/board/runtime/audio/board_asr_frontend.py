"""Same-model local GTCRN/Silero decision adapter for the board endpoint.

Preserves the accepted frontend semantics: denoising feeds the speech detector;
the caller's original PCM remains the ASR waveform. The existing board endpoint
continues to own pre-roll, onset, 700 ms silence and utterance duration limits.
No microphone, capture thread, network service or automatic fallback is opened.
"""
import hashlib
from pathlib import Path
import threading
import time

HASHES={
    'gtcrn_simple.onnx':'e77603ac0c23dac3227dd2d7135b3a585cbee2679048aecfa886657d3ae1b534',
    'silero_vad_v5.onnx':'6b99cbfd39246b6706f98ec13c7c50c6b299181f2474fa05cbc8046acc274396',
}


class BoardSpeechGate:
    def __init__(self, directory, *, clock=time.monotonic, sherpa=None):
        import numpy as np
        if sherpa is None:
            import sherpa_onnx as sherpa
        root=Path(directory)
        for name,expected in HASHES.items():
            path=root/name
            if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                raise ValueError('Pinned board frontend resource mismatch')
        self.np,self.clock=np,clock
        self.lock=threading.Lock()
        self.closed=False;self.error='';self.frames=0;self.samples=0;self.last_ms=None;self.max_ms=0.
        config=sherpa.OnlineSpeechDenoiserConfig(model=sherpa.OfflineSpeechDenoiserModelConfig(
            gtcrn=sherpa.OfflineSpeechDenoiserGtcrnModelConfig(model=str(root/'gtcrn_simple.onnx')),
            num_threads=1,provider='cpu'))
        if not config.validate():raise ValueError('Invalid GTCRN configuration')
        self.denoiser=sherpa.OnlineSpeechDenoiser(config)
        vc=sherpa.VadModelConfig();vc.silero_vad.model=str(root/'silero_vad_v5.onnx')
        vc.silero_vad.threshold=.5
        vc.silero_vad.min_speech_duration=0.;vc.silero_vad.min_silence_duration=0.
        vc.silero_vad.max_speech_duration=19.;vc.num_threads=1;vc.sample_rate=16000
        self.vad=sherpa.VoiceActivityDetector(vc,buffer_size_in_seconds=22)
        for _ in range(32):self._process(bytes(640))
        self.denoiser.reset();self.vad.reset();self.samples=0

    def _process(self,pcm):
        samples=self.np.frombuffer(pcm,dtype='<i2').astype(self.np.float32)/32768
        output=self.denoiser(samples,16000)
        self.samples+=len(output.samples)
        if len(output.samples):self.vad.accept_waveform(output.samples)
        speech=bool(self.vad.is_speech_detected())
        while not self.vad.empty():self.vad.pop()
        return speech

    def __call__(self,frame):
        if self.closed or self.error:raise RuntimeError('Board frontend capture closed or failed')
        values=self.np.asarray(frame,dtype=self.np.float32)
        if values.shape!=(320,) or not self.np.isfinite(values).all() or self.np.max(self.np.abs(values))>1:
            raise ValueError('Board frontend requires normalized 20 ms/16 kHz mono frames')
        if not self.lock.acquire(blocking=False):raise RuntimeError('Board frontend is busy')
        try:
            if self.closed:raise InterruptedError('Board frontend capture cancelled')
            start=self.clock()
            raw=self.np.rint(values*32768).clip(-32768,32767).astype('<i2').tobytes()
            speech=self._process(raw)
            if self.closed:raise InterruptedError('Board frontend result belongs to cancelled capture')
            self.frames+=1
            if not 0<=self.frames*320-self.samples<=1024:
                raise ValueError('Invalid board frontend sample timeline')
            self.last_ms=round((self.clock()-start)*1000,3)
            self.max_ms=max(self.max_ms,self.last_ms)
            return speech
        except Exception as exc:
            self.error=type(exc).__name__;self.closed=True;raise
        finally:self.lock.release()

    def close(self):
        # A native kernel already in progress finishes without publishing a
        # decision. No new capture can reuse this gate after close().
        self.closed=True

    def public(self):
        return dict(enabled=True,backend='gtcrn-silero-v5-board-cpu',frames=self.frames,
                    processed_samples=self.samples,closed=self.closed,error=self.error,
                    last_roundtrip_ms=self.last_ms,max_roundtrip_ms=self.max_ms)
