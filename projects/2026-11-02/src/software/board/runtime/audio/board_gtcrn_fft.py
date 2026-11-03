"""Opt-in FFT candidate for the unchanged GTCRN ONNX model.

The framing follows sherpa-onnx v1.13.8's online STFT contract: periodic
sqrt-Hann, 512-point transform, 256-sample hop, float32 complex pairs, three
recurrent states, first-hop latency, overlap-add, and length-preserving flush.
Only the private quadratic DFT is replaced with NumPy's rfft/irfft. This is a
candidate until SDK PCM/VAD/ASR comparisons and ARM throughput gates pass.

References (implementation is independent Python):
https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.8/sherpa-onnx/csrc/online-speech-denoiser-stft-impl.h
https://github.com/csukuangfj/kaldi-native-fbank/blob/master/kaldi-native-fbank/csrc/feature-window.cc
"""
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import threading
import time

from .board_asr_frontend import BoardSpeechGate, HASHES


@dataclass
class DenoisedAudio:
    samples: object
    sample_rate: int = 16000


class FftGtcrnDenoiser:
    def __init__(self, model_path, *, num_threads=1, session_factory=None, profile=False):
        import numpy as np
        path=Path(model_path)
        if (not path.is_file() or path.is_symlink()
                or hashlib.sha256(path.read_bytes()).hexdigest()!=HASHES['gtcrn_simple.onnx']):
            raise ValueError('GTCRN candidate requires the pinned existing model')
        if type(num_threads) is not int or not 1<=num_threads<=2:
            raise ValueError('GTCRN candidate supports one or two CPU threads')
        if session_factory is None:
            import onnxruntime as ort
            options=ort.SessionOptions()
            options.intra_op_num_threads=num_threads
            options.inter_op_num_threads=1
            self.session=ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
            self.ort_version=ort.__version__
        else:
            self.session=session_factory(str(path),num_threads=num_threads)
            self.ort_version='injected'
        meta=self.session.get_modelmeta().custom_metadata_map
        expected={'model_type':'gtcrn','n_fft':'512','hop_length':'256',
                  'window_length':'512','sample_rate':'16000','window_type':'hann_sqrt'}
        if any(meta.get(key)!=value for key,value in expected.items()):
            raise ValueError('Unexpected GTCRN framing metadata')
        self.np,self.profile=np,bool(profile)
        self.input_names=[value.name for value in self.session.get_inputs()]
        self.output_names=[value.name for value in self.session.get_outputs()]
        if self.input_names!=['mix','conv_cache','tra_cache','inter_cache']:
            raise ValueError('Unexpected GTCRN recurrent input layout')
        if self.output_names!=['enh','conv_cache_out','tra_cache_out','inter_cache_out']:
            raise ValueError('Unexpected GTCRN recurrent output layout')
        self.state_shapes=[tuple(int(part) for part in meta[key].split(',')) for key in
                           ('conv_cache_shape','tra_cache_shape','inter_cache_shape')]
        # Kaldi's "hann" is periodic. Cast before sqrt, as in the SDK's
        # float32 window construction; np.hanning would use the wrong denominator.
        hann=np.asarray([.5-.5*math.cos(2*math.pi*i/512) for i in range(512)],dtype=np.float32)
        self.window=np.sqrt(hann)
        self.reset()

    def reset(self):
        np=self.np
        self.analysis=np.zeros(512,dtype=np.float32)
        self.ola=np.zeros(512,dtype=np.float32)
        self.pending=np.empty(0,dtype=np.float32)
        self.states=[np.zeros(shape,dtype=np.float32) for shape in self.state_shapes]
        self.started=False;self.total_input=0;self.total_output=0
        self.last_timing=dict(hops=0,fft_ms=0.,ort_ms=0.,ifft_ola_ms=0.)

    def _hop(self, samples):
        np=self.np
        start=time.monotonic() if self.profile else 0.
        self.analysis[:-256]=self.analysis[256:]
        self.analysis[-256:]=samples
        transformed=np.fft.rfft(self.analysis*self.window,n=512)
        spectrum=np.empty((1,257,1,2),dtype=np.float32)
        spectrum[0,:,0,0]=transformed.real
        spectrum[0,:,0,1]=transformed.imag
        fft_end=time.monotonic() if self.profile else 0.
        feed=dict(zip(self.input_names,[spectrum]+self.states))
        result=self.session.run(self.output_names,feed)
        self.states=result[1:]
        ort_end=time.monotonic() if self.profile else 0.
        enhanced=result[0].reshape(257,2)
        complex_values=enhanced[:,0].astype(np.float64)+1j*enhanced[:,1].astype(np.float64)
        synthesis=np.asarray(np.fft.irfft(complex_values,n=512),dtype=np.float32)
        self.ola[:-256]=self.ola[256:]
        self.ola[-256:]=0
        self.ola+=synthesis*self.window
        if self.profile:
            self.last_timing['hops']+=1
            self.last_timing['fft_ms']+=(fft_end-start)*1000
            self.last_timing['ort_ms']+=(ort_end-fft_end)*1000
            self.last_timing['ifft_ola_ms']+=(time.monotonic()-ort_end)*1000
        if not self.started:
            self.started=True
            return np.empty(0,dtype=np.float32)
        return self.ola[:256].copy()

    def _consume(self):
        chunks=[];offset=0
        while len(self.pending)-offset>=256:
            chunks.append(self._hop(self.pending[offset:offset+256]));offset+=256
        if offset:self.pending=self.pending[offset:].copy()
        return self.np.concatenate(chunks) if chunks else self.np.empty(0,dtype=self.np.float32)

    def __call__(self,samples,sample_rate=16000):
        np=self.np
        values=np.asarray(samples,dtype=np.float32)
        if (sample_rate!=16000 or values.ndim!=1 or len(values)>320000
                or not np.isfinite(values).all()):
            raise ValueError('GTCRN candidate requires bounded finite 16 kHz mono samples')
        self.last_timing=dict(hops=0,fft_ms=0.,ort_ms=0.,ifft_ola_ms=0.)
        if not len(values):return DenoisedAudio(np.empty(0,dtype=np.float32))
        self.total_input+=len(values)
        self.pending=np.concatenate((self.pending,values))
        output=self._consume();self.total_output+=len(output)
        return DenoisedAudio(output)

    def flush(self):
        np=self.np
        chunks=[self._consume()]
        if len(self.pending):
            padded=np.zeros(256,dtype=np.float32);padded[:len(self.pending)]=self.pending
            chunks.append(self._hop(padded));self.pending=np.empty(0,dtype=np.float32)
        if self.started:chunks.append(self._hop(np.zeros(256,dtype=np.float32)))
        output=np.concatenate(chunks)[:max(0,self.total_input-self.total_output)]
        self.reset()
        return DenoisedAudio(output)


class BoardFftSpeechGate(BoardSpeechGate):
    """The same Silero rules and endpoint API with the candidate FFT denoiser."""
    def __init__(self,directory,*,num_threads=1,clock=time.monotonic,profile=False):
        import numpy as np
        import sherpa_onnx as s
        root=Path(directory)
        for name,expected in HASHES.items():
            path=root/name
            if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                raise ValueError('Pinned frontend resource mismatch')
        self.np,self.clock=np,clock;self.lock=threading.Lock()
        self.closed=False;self.error='';self.frames=0;self.samples=0;self.last_ms=None;self.max_ms=0.
        self.denoiser=FftGtcrnDenoiser(root/'gtcrn_simple.onnx',num_threads=num_threads,profile=profile)
        vc=s.VadModelConfig();vc.silero_vad.model=str(root/'silero_vad_v5.onnx')
        vc.silero_vad.threshold=.5;vc.silero_vad.min_speech_duration=0.;vc.silero_vad.min_silence_duration=0.
        vc.silero_vad.max_speech_duration=19.;vc.num_threads=1;vc.sample_rate=16000
        self.vad=s.VoiceActivityDetector(vc,buffer_size_in_seconds=22)
        for _ in range(32):self._process(bytes(640))
        self.denoiser.reset();self.vad.reset();self.samples=0

    def public(self):
        value=super().public()
        value['backend']='gtcrn-numpy-fft-silero-v5-board-candidate'
        value['onnxruntime']=self.denoiser.ort_version
        return value
