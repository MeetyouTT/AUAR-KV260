"""Opt-in same-weight CPU allocation/IO-binding experiment, never production.

Exact baseline sources are pinned. FFT/hop/window, recurrent ordering, output
length, float32 multiply/add rounding and Silero rules are unchanged. CPU-bound
output storage is ping-pong, never aliased to that invocation's input state.
Construction does not open devices or create a worker/service.
"""
import hashlib
from pathlib import Path
import threading
import time

import board.runtime.audio.board_gtcrn_fft as _base
import board.runtime.audio.board_asr_frontend as _front

BASELINE_SHA256 = '47cb8a2ec97ad292981bb42b67e217ed0f672a98d561d4ac8dc9c360cf8f6f06'
FRONTEND_SHA256 = 'b3d06b653876469daf5b7bb805458b187662d9862e8ece6da731cbfa3e23a093'


def verify_baseline():
    for module,expected in ((_base,BASELINE_SHA256),(_front,FRONTEND_SHA256)):
        if hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() != expected:
            raise ValueError('Candidate requires the reviewed unchanged baseline source')


class ReuseFftGtcrnDenoiser(_base.FftGtcrnDenoiser):
    def __init__(self,*args,buffer_reuse=True,io_binding=False,**kwargs):
        if type(buffer_reuse) is not bool or type(io_binding) is not bool:
            raise ValueError('Choose explicit optimization flags')
        verify_baseline()
        self.buffer_reuse,self.use_io_binding = buffer_reuse,io_binding
        super().__init__(*args,**kwargs)

    def reset(self):
        super().reset()
        np = self.np
        self._spectrum = np.empty((1,257,1,2),dtype=np.float32)
        self._windowed = np.empty(512,dtype=np.float32)
        self._complex = np.empty(257,dtype=np.complex128)
        self._synthesis = np.empty(512,dtype=np.float32)
        self._weighted = np.empty(512,dtype=np.float32)
        self._feed = dict(zip(self.input_names,[self._spectrum]+self.states))
        self._bindings = None
        if self.use_io_binding:
            if not all(callable(getattr(self.session,name,None)) for name in ('io_binding','run_with_iobinding')):
                raise ValueError('Explicit CPU IO binding is unavailable; no silent fallback')
            expected = [(1,257,1,2)]+self.state_shapes
            outputs = self.session.get_outputs()
            if any(tuple(row.shape) != shape or row.type != 'tensor(float)' for row,shape in zip(outputs,expected)):
                raise ValueError('CPU IO binding requires the pinned static float32 output layout')
            self._state_sets = [self.states,[np.empty(shape,dtype=np.float32) for shape in self.state_shapes]]
            self._enhanced = np.empty((1,257,1,2),dtype=np.float32)
            self._bindings = []
            for index in (0,1):
                binding = self.session.io_binding()
                for name,value in zip(self.input_names,[self._spectrum]+self._state_sets[index]):
                    binding.bind_cpu_input(name,value)
                for name,value in zip(self.output_names,[self._enhanced]+self._state_sets[1-index]):
                    binding.bind_output(name,device_type='cpu',device_id=0,element_type=np.float32,
                                        shape=value.shape,buffer_ptr=value.ctypes.data)
                self._bindings.append(binding)
            self._io_index = 0

    def _hop(self,samples):
        np = self.np
        start = time.monotonic() if self.profile else 0.
        self.analysis[:-256] = self.analysis[256:]
        self.analysis[-256:] = samples
        if self.buffer_reuse:
            np.multiply(self.analysis,self.window,out=self._windowed)
            transformed = np.fft.rfft(self._windowed,n=512)
        else:
            transformed = np.fft.rfft(self.analysis*self.window,n=512)
        spectrum = self._spectrum if self.buffer_reuse or self.use_io_binding else np.empty((1,257,1,2),dtype=np.float32)
        spectrum[0,:,0,0],spectrum[0,:,0,1] = transformed.real,transformed.imag
        fft_end = time.monotonic() if self.profile else 0.
        if self.use_io_binding:
            index = self._io_index
            self.session.run_with_iobinding(self._bindings[index])
            self.states = self._state_sets[1-index]
            self._io_index = 1-index
            enhanced = self._enhanced.reshape(257,2)
        else:
            if self.buffer_reuse:
                feed = self._feed
                for name,state in zip(self.input_names[1:],self.states):
                    feed[name] = state
            else:
                feed = dict(zip(self.input_names,[spectrum]+self.states))
            result = self.session.run(self.output_names,feed)
            self.states = result[1:]
            enhanced = result[0].reshape(257,2)
        ort_end = time.monotonic() if self.profile else 0.
        if self.buffer_reuse:
            self._complex.real,self._complex.imag = enhanced[:,0],enhanced[:,1]
            self._synthesis[:] = np.fft.irfft(self._complex,n=512)
            np.multiply(self._synthesis,self.window,out=self._weighted)
        else:
            complex_values = enhanced[:,0].astype(np.float64)+1j*enhanced[:,1].astype(np.float64)
            synthesis = np.asarray(np.fft.irfft(complex_values,n=512),dtype=np.float32)
            self._weighted[:] = synthesis*self.window
        self.ola[:-256] = self.ola[256:]
        self.ola[-256:] = 0
        np.add(self.ola,self._weighted,out=self.ola)
        if self.profile:
            self.last_timing['hops'] += 1
            self.last_timing['fft_ms'] += (fft_end-start)*1000
            self.last_timing['ort_ms'] += (ort_end-fft_end)*1000
            self.last_timing['ifft_ola_ms'] += (time.monotonic()-ort_end)*1000
        if not self.started:
            self.started = True
            return np.empty(0,dtype=np.float32)
        return self.ola[:256].copy()


class ReuseFftSpeechGate(_base.BoardFftSpeechGate):
    def __init__(self,directory,*,num_threads=1,clock=time.monotonic,profile=False,
                 buffer_reuse=True,io_binding=False):
        verify_baseline()
        import numpy as np
        import sherpa_onnx as s
        root = Path(directory)
        for name,expected in _front.HASHES.items():
            path = root/name
            if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('Pinned frontend resource mismatch')
        self.np,self.clock,self.lock = np,clock,threading.Lock()
        self.closed,self.error,self.frames,self.samples,self.last_ms,self.max_ms = False,'',0,0,None,0.
        self.buffer_reuse,self.use_io_binding = buffer_reuse,io_binding
        self._quantized = np.empty(320,dtype=np.float32)
        self.denoiser = ReuseFftGtcrnDenoiser(root/'gtcrn_simple.onnx',num_threads=num_threads,
            profile=profile,buffer_reuse=buffer_reuse,io_binding=io_binding)
        vc = s.VadModelConfig()
        vc.silero_vad.model = str(root/'silero_vad_v5.onnx')
        vc.silero_vad.threshold = .5
        vc.silero_vad.min_speech_duration = vc.silero_vad.min_silence_duration = 0.
        vc.silero_vad.max_speech_duration = 19.
        vc.num_threads,vc.sample_rate = 1,16000
        self.vad = s.VoiceActivityDetector(vc,buffer_size_in_seconds=22)
        for _ in range(32):
            self._process(bytes(640))
        self.denoiser.reset()
        self.vad.reset()
        self.samples = 0

    def __call__(self,frame):
        if not self.buffer_reuse:
            return super().__call__(frame)
        if self.closed or self.error:
            raise RuntimeError('Board frontend capture closed or failed')
        np = self.np
        values = np.asarray(frame,dtype=np.float32)
        if values.shape != (320,) or not np.isfinite(values).all() or np.max(np.abs(values))>1:
            raise ValueError('Board frontend requires normalized 20 ms/16 kHz mono frames')
        if not self.lock.acquire(blocking=False):
            raise RuntimeError('Board frontend is busy')
        try:
            if self.closed:
                raise InterruptedError('Board frontend capture cancelled')
            began = self.clock()
            # Exactly the original PCM16 grid/clipping, without materializing
            # int16 bytes only to convert those bytes back to float32.
            np.multiply(values,32768,out=self._quantized)
            np.rint(self._quantized,out=self._quantized)
            np.clip(self._quantized,-32768,32767,out=self._quantized)
            np.add(self._quantized,0,out=self._quantized)  # int16 round-trip canonicalizes signed zero.
            np.multiply(self._quantized,1/32768,out=self._quantized)
            output = self.denoiser(self._quantized,16000)
            self.samples += len(output.samples)
            if len(output.samples):
                self.vad.accept_waveform(output.samples)
            speech = bool(self.vad.is_speech_detected())
            while not self.vad.empty():
                self.vad.pop()
            if self.closed:
                raise InterruptedError('Board frontend result belongs to cancelled capture')
            self.frames += 1
            if not 0 <= self.frames*320-self.samples <= 1024:
                raise ValueError('Invalid board frontend sample timeline')
            self.last_ms = round((self.clock()-began)*1000,3)
            self.max_ms = max(self.max_ms,self.last_ms)
            return speech
        except Exception as exc:
            self.error,self.closed = type(exc).__name__,True
            raise
        finally:
            self.lock.release()

    def public(self):
        return dict(super().public(),backend='opt-in-gtcrn-cpu-reuse-binding-candidate',
            buffer_reuse=self.buffer_reuse,cpu_io_binding=self.use_io_binding,
            baseline_sha256=BASELINE_SHA256)
