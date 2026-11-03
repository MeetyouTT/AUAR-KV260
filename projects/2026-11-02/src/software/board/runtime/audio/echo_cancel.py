"""Bounded SpeexDSP echo cancellation; no model, device or files are loaded.

Use the library's asynchronous playback/capture API with 20ms frames.
Reference samples are the actual PCM queued to playback, including silence.
They must reach the canceller before the corresponding acoustic echo.
"""
import audioop
import ctypes as C
import ctypes.util
import threading
import time


class SpeexEcho:
    frame_samples=320
    def __init__(self,clock=time.monotonic):
        name=ctypes.util.find_library('speexdsp')
        if not name:raise RuntimeError('SpeexDSP echo cancellation is unavailable')
        self.lib=C.CDLL(name);lib=self.lib;P=C.c_void_p;I=C.c_int;S=C.POINTER(C.c_int16)
        for fn,args,result in (
            ('speex_echo_state_init',[I,I],P),('speex_echo_ctl',[P,I,P],I),
            ('speex_echo_playback',[P,S],None),('speex_echo_capture',[P,S,S],None),
            ('speex_echo_state_destroy',[P],None),('speex_preprocess_state_init',[I,I],P),
            ('speex_preprocess_ctl',[P,I,P],I),('speex_preprocess_run',[P,S],I),
            ('speex_preprocess_state_destroy',[P],None)):
            f=getattr(lib,fn);f.argtypes=args;f.restype=result
        self.lock=threading.RLock();self.clock=clock;self.state=self.pre=None
        self.pending=bytearray();self.rate_state=None;self.last_reference=None;self.sequence=None
        self.reference_frames=0;self.reference_gaps=0;self.capture_frames=0
        self.state=lib.speex_echo_state_init(320,5120)
        if not self.state:raise RuntimeError('Cannot allocate echo canceller')
        try:
            rate=I(16000)
            if lib.speex_echo_ctl(self.state,24,C.byref(rate)):raise RuntimeError('Cannot configure echo sample rate')
            self.pre=lib.speex_preprocess_state_init(320,16000)
            if not self.pre:raise RuntimeError('Cannot allocate residual echo suppressor')
            if lib.speex_preprocess_ctl(self.pre,24,self.state):raise RuntimeError('Cannot bind residual echo suppressor')
            for key,value in ((0,1),(2,0),(18,-15),(20,-45),(22,-15)):
                v=I(value)
                if lib.speex_preprocess_ctl(self.pre,key,C.byref(v)):raise RuntimeError('Cannot configure residual echo suppression')
        except Exception:self.close();raise

    def reference(self,pcm,at,sequence):
        with self.lock:
            if not self.state:return
            if self.sequence is not None and sequence!=self.sequence+1:self.reference_gaps+=1
            self.sequence=sequence
            if not 0<=self.clock()-at<.25:return
            if self.last_reference is not None and at-self.last_reference>.12:self.reference_gaps+=1
            raw,self.rate_state=audioop.ratecv(pcm,2,1,24000,16000,self.rate_state)
            self.pending.extend(raw);self.last_reference=at
            while len(self.pending)>=640:
                frame=bytes(self.pending[:640]);del self.pending[:640]
                self.lib.speex_echo_playback(self.state,(C.c_int16*320).from_buffer_copy(frame))
                self.reference_frames+=1

    def healthy(self):
        with self.lock:return bool(self.state and self.reference_frames>=3 and self.last_reference is not None
                                   and 0<=self.clock()-self.last_reference<.25 and not self.reference_gaps)

    def process(self,pcm):
        if len(pcm)!=640:raise ValueError('Echo input must contain exactly 20ms PCM16')
        with self.lock:
            if not self.state:raise RuntimeError('Echo canceller is closed')
            out=(C.c_int16*320)();raw=(C.c_int16*320).from_buffer_copy(pcm)
            self.lib.speex_echo_capture(self.state,raw,out);self.lib.speex_preprocess_run(self.pre,out)
            self.capture_frames+=1
            return bytes(out)

    def close(self):
        with self.lock:
            if self.pre:self.lib.speex_preprocess_state_destroy(self.pre);self.pre=None
            if self.state:self.lib.speex_echo_state_destroy(self.state);self.state=None
