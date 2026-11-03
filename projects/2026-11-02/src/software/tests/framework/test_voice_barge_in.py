"""Cancellation, utterance ownership and real native echo checks when available."""
import audioop
import copy
import ctypes.util
import io
from types import SimpleNamespace
import numpy as np
import pytest
from board.runtime.audio.capture import CapturedAudio,FORMAT
from host.model_service.protocol import AudioRef
from tools.barge_in_recording import BargeInRecordingController
from tests.framework.test_handsfree_dialogue import Tx,view,arm,speech
from tests.framework.test_automatic_conversation import FakeController,FakeCapture
from tests.framework.test_automatic_conversation import frames


class Barge(FakeCapture):
    def __init__(self,name):super().__init__();self.name=name
    def start(self):super().start();return self.name
    def take(self):
        self.state='IDLE'
        return CapturedAudio(self.name,AudioRef(2,0,16000,FORMAT),b'\x12\x34'*16000,100,1100)


def setup():
    now=[1.];source=[None];tx=Tx();inner=FakeController();captures=[]
    def factory():
        cap=Barge('barge-'+str(len(captures)+1));captures.append(cap);return cap
    owner=BargeInRecordingController(inner,transcriber=tx,boot_id='boot',
        attention_provider=lambda:copy.deepcopy(source[0]),clock=lambda:now[0],
        auto_capture_factory=FakeCapture,barge_capture_factory=factory)
    arm(now,source,owner);speech(owner)
    return now,source,tx,inner,owner,captures


def generating(owner,inner):
    owner.transcription.update(state='GENERATING',text='你好')
    inner.state.update(phase='SPEAKING',playing=True);owner.tick()


def test_barge_monitor_only_arms_after_valid_transcript_and_not_during_enrollment():
    now,source,tx,inner,owner,captures=setup()
    try:
        owner.tick();assert not captures
        with __import__('unittest.mock').mock.patch.object(tx,'public',return_value={'voice_enrollment':{'active':True}}):
            generating(owner,inner);assert not captures
        owner.tick();assert len(captures)==1
        assert owner.capture.state=='IDLE' and owner.capture.counter==1
    finally:owner.close()


def test_spoken_interrupt_stops_old_reply_keeps_pre_roll_and_same_conversation():
    now,source,tx,inner,owner,captures=setup()
    try:
        generating(owner,inner);cap=captures[0];cap.on_speech_start();owner.tick()
        assert not inner.state['playing'] and owner.capture is cap
        assert owner.monitor_owned and owner.auto_enabled and owner.monitor_enabled
        assert owner.barge_interruptions==1 and tx.selections==[False]
        cap.state='READY';owner.tick()
        assert tx.submitted[-1].capture_id=='barge-1'
        assert tx.submitted[-1].pcm==b'\x12\x34'*16000
        assert owner.transcription['request_id']=='req-2'
        assert tx.ack_calls==[] and tx.selections==[False]
        assert tx.entries==['cap-1','barge-1']
    finally:owner.close()


def test_late_old_completion_and_network_data_cannot_resume_or_commit():
    now,source,tx,inner,owner,captures=setup()
    try:
        generating(owner,inner);cap=captures[0];cap.on_speech_start();owner.tick()
        cap.state='READY';owner.tick()
        tx.results.append({'context':{'request_id':'req-1','capture_id':'cap-1'},
                           'channel_event':{'kind':'audio'},'pcm':b'old'})
        inner.completions.append(({'request_id':'req-1','capture_id':'cap-1'},{}));owner.tick()
        assert owner.transcription['request_id']=='req-2' and tx.ack_calls==[]
        assert not inner.state['playing']
    finally:owner.close()


def test_face_loss_closes_interrupt_monitor_without_cutting_accepted_reply():
    now,source,tx,inner,owner,captures=setup()
    try:
        generating(owner,inner);source[0]=None;owner.tick()
        assert captures[0].closed and owner.barge_capture is None
        assert inner.state['playing'] and owner.monitor_owned
    finally:owner.close()


def test_late_callback_from_closed_capture_cannot_interrupt_a_later_request():
    now,source,tx,inner,owner,captures=setup()
    try:
        generating(owner,inner);old=captures[0];owner._stop_barge()
        owner.transcription.update(request_id='req-2');owner.tick()
        assert len(captures)==2
        old.on_speech_start();owner.tick()
        assert owner.barge_interruptions==0 and inner.state['playing']
        assert owner.barge_capture is captures[1]
    finally:owner.close()


def test_detection_to_stop_time_excludes_the_vad_onset_duration():
    now,source,tx,inner,owner,captures=setup()
    try:
        generating(owner,inner);captures[0].on_speech_start();now[0]+=.125
        owner.tick()
        assert owner.barge_stop_latency_ms==125 and owner.barge_interruptions==1
    finally:owner.close()


def test_explicit_pause_releases_both_capture_owners_and_never_rearms():
    now,source,tx,inner,owner,captures=setup()
    try:
        generating(owner,inner);owner.cancel();owner.tick()
        assert captures[0].closed and owner.capture.closed is False
        assert owner.capture.state=='CANCELLED' and not owner.monitor_enabled
        assert len(captures)==1 and owner.barge_capture is None
    finally:owner.close()


def test_normal_complete_answer_keeps_ack_tail_guard_and_releases_barge_capture():
    now,source,tx,inner,owner,captures=setup()
    try:
        generating(owner,inner)
        inner.state.update(phase='IDLE',playing=False);tx.pending=False
        inner.completions.append(({'request_id':'req-1','capture_id':'cap-1'},{}));owner.tick()
        assert captures[0].closed and len(tx.ack_calls)==1
        assert not owner._recording()
        tx.last_ack={'request_id':'req-1','committed':True};now[0]+=.6
        source[0]=view(2200,3);owner.tick()
        assert owner._recording() and owner.capture.counter==2
        assert owner.barge_interruptions==0
    finally:owner.close()


class EchoStub:
    reference_gaps=0
    def __init__(self,transform=lambda raw:raw,ready=True):
        self.transform=transform;self.ready=ready;self.closed=False
    def process(self,raw):return self.transform(raw)
    def healthy(self):return self.ready
    def close(self):self.closed=True


def test_capture_keeps_the_new_utterance_preroll_after_echo_processing():
    from tools.barge_in_capture import BargeInCapture
    output=SimpleNamespace();capture=BargeInCapture(output)
    capture._capture_timer();capture.echo=EchoStub();starts=[]
    capture.on_speech_start=lambda:starts.append(capture.endpoint.total_samples)
    raw=frames(30)+frames(30,True)+frames(35)
    try:
        result=capture._read_pcm(SimpleNamespace(stdout=io.BytesIO(raw)))
        assert len(starts)==1 and starts[0]==42*320
        assert result==raw[20*640:] and capture._sample_count==len(result)//2
    finally:capture.close()


def test_capture_never_uses_raw_echo_or_unreferenced_energy_as_user_speech():
    from tools.barge_in_capture import BargeInCapture
    for ready,transform in ((True,lambda raw:bytes(640)),(False,lambda raw:raw)):
        capture=BargeInCapture(SimpleNamespace());capture._capture_timer()
        echo=EchoStub(transform,ready);capture.echo=echo;starts=[]
        capture.on_speech_start=lambda:starts.append(True)
        try:
            with pytest.raises(RuntimeError,match='ended unexpectedly'):
                capture._read_pcm(SimpleNamespace(stdout=io.BytesIO(frames(80,True))))
            assert not starts and echo.closed
            assert not capture.endpoint.active
        finally:capture.close()


@pytest.mark.skipif(not ctypes.util.find_library('speexdsp'),reason='Native SpeexDSP is a board dependency')
def test_real_speex_rejects_simulated_echo_and_keeps_near_end_speech():
    from board.runtime.audio.echo_cancel import SpeexEcho
    now=[1.];echo=SpeexEcho(clock=lambda:now[0]);rng=np.random.default_rng(417)
    delay=[bytes(640),bytes(640)];rate=None;far=[];clean=[];near=[]
    try:
        for i in range(600):
            # Band-limited far audio is independent of the near user's harmonic.
            x=rng.normal(0,2500,480);x=np.convolve(x,np.ones(5)/5,mode='same').astype('<i2').tobytes()
            ref,rate=audioop.ratecv(x,2,1,24000,16000,rate)
            assert len(ref)==640
            echo.reference(x,now[0],i)
            reflected=np.frombuffer(delay.pop(0),dtype='<i2').astype(float)*.55;delay.append(ref)
            user=np.sin((np.arange(320)+i*320)*2*np.pi*211/16000)*2000 if 450<=i<500 else 0
            mic=np.clip(reflected+user,-32768,32767).astype('<i2').tobytes()
            result=echo.process(mic)
            if 300<=i<400:far.append(audioop.rms(mic,2));clean.append(audioop.rms(result,2))
            if 460<=i<490:near.append(audioop.rms(result,2))
            now[0]+=.02
        assert echo.healthy()
        assert np.mean(clean)<np.mean(far)*.3,(np.mean(clean),np.mean(far))
        assert np.mean(near)>250,np.mean(near)
    finally:echo.close()
