"""Voice cache integrity, cancelled jobs, and independent facial-layer invariants."""
import hashlib
import json
import threading
import time
import wave
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from board.runtime.audio.selected_voice import SelectedVoiceSynthesizer,normalize_text
from tools.facial_layers import BlinkSchedule,BlinkLayer,MouthBank,FacialController,aperture_levels,AURA
from tools.demo_script import create_demo_core
from tools.selected_voice_service import SpeechJobs


def write_wave(path,rate=24000):
    pcm=(np.sin(np.arange(rate)/rate*2*np.pi*220)*8000).astype('<i2')
    with wave.open(str(path),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes(pcm.tobytes())
    return pcm


@pytest.fixture
def synth(tmp_path):
    voice=tmp_path/'voice';voice.mkdir();reference=voice/'reference.wav';write_wave(reference)
    (voice/'selection.json').write_text(json.dumps({'reference_audio':'reference.wav','reference_text':'你好。',
        'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest()}),encoding='utf-8')
    (voice/'base_model_verification.json').write_text(json.dumps({'revision':'fixed-revision'}),encoding='utf-8')
    return SelectedVoiceSynthesizer(tmp_path/'cache',voice_root=voice)


@pytest.mark.parametrize('text',[None,'',' \n ','x'*241,'ab\x00cd'])
def test_invalid_text_rejected(text):
    with pytest.raises(ValueError):normalize_text(text)


def test_normalized_cache_reuses_audio_and_rejects_changed_wav(synth):
    key,identity=synth.identity('你好。');path=synth.cache_root/f'{key}.wav';write_wave(path)
    data={'identity':identity,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (synth.cache_root/f'{key}.json').write_text(json.dumps(data),encoding='utf-8')
    assert synth.synthesize('  你好。  ')['cache_hit'] is True
    assert synth.model is None
    path.write_bytes(path.read_bytes()+b'changed')
    assert synth.cached('你好。') is None


def test_cache_identity_tracks_prompt_model_and_text(synth):
    first=synth.identity('你好。')[0]
    assert synth.identity('再见。')[0]!=first
    synth.selection['reference_text']='另一句话。'
    assert synth.identity('你好。')[0]!=first
    synth.selection['reference_text']='你好。';synth.revision='another'
    assert synth.identity('你好。')[0]!=first


def test_blink_schedule_continues_across_turn_boundaries():
    schedule=BlinkSchedule();other=BlinkSchedule()
    assert schedule.starts==other.starts
    assert schedule.phase(1.2) is None and schedule.phase(1.43)==pytest.approx(.13)
    assert all(3.2<=b-a<=5.8 for a,b in zip(schedule.starts,schedule.starts[1:]))
    # Speech turn resets do not enter or alter this time-only layer.
    original=list(schedule.starts)
    for t in (5.2,8.88,10.08,21.84,24.09,30.49):schedule.phase(t)
    assert schedule.starts==original
    schedule.phase(7200)
    assert schedule.starts[-1]>7200


def test_amplitude_varies_aperture_and_silence_recovers():
    t=np.arange(24000)/24000;signal=np.sin(t*2*np.pi*220)
    pcm=np.concatenate([signal*1200,signal*10000,np.zeros(6000)]).astype('<i2')
    levels=aperture_levels(pcm)
    assert 0<np.median(levels[30:80])<np.median(levels[130:180])<=1
    assert levels[-1]<.001
    assert aperture_levels(np.zeros(1000,dtype='<i2'))==[0]*5
    with pytest.raises(ValueError):aperture_levels([])


@pytest.fixture(scope='module')
def real_core():return create_demo_core(assets='reuse')


def test_eye_layer_preserves_mouth_body_and_original_alpha(real_core):
    eyes=BlinkLayer()
    for name in eyes.images:
        base=Image.open(AURA/'assets/avatar'/name/'000000.png').convert('RGBA')
        meta={'asset':name,'index':0,'image':base}
        closed=eyes.apply(meta,1.43)['image']
        a=np.asarray(base);b=np.asarray(closed)
        assert np.array_equal(a[:,:,3],b[:,:,3])
        assert np.array_equal(a[143:],b[143:])
        assert np.any(a[105:143,178:277,:3]!=b[105:143,178:277,:3])
        mask=np.ones(a.shape[:2],dtype=bool);mask[100:149,173:283]=False
        assert np.array_equal(a[mask],b[mask])
        assert np.array_equal(np.asarray(eyes.apply(meta,0)['image']),a)
    assert eyes.overlay('ack_nod',1.43)[0] is None


def test_all_mouth_sets_open_without_moving_eyes(real_core):
    mouths=MouthBank(real_core)
    for name in mouths.keys:
        closed=np.asarray(mouths.image(name,0,1));opened=np.asarray(mouths.image(name,1,1))
        assert np.any(closed[143:165,211:241,:3]!=opened[143:165,211:241,:3])
        assert np.array_equal(closed[:138],opened[:138])
        assert np.array_equal(np.asarray(mouths.image(name,1,0)),closed)


def test_cancel_tail_keeps_final_aperture_and_fades_to_closed(real_core):
    from tools.selected_voice_demo import VoicePlan
    plan=VoicePlan();facials=FacialController(real_core,plan);real_core.idle_gain=0
    row=plan.utterances[-1];asset='talking_high_reuse_v1';anchor=real_core._reuse_anchors[asset]
    images=[];levels=[]
    for offset,gain in ((-.0001,1),(.0001,1),(.09,.5),(.18,0)):
        meta={'image':anchor,'asset':asset,'index':0,'speech_gain':gain,'transitioning':offset>0}
        result=facials.apply(meta,row['end']+offset);images.append(np.array(result['image']));levels.append(result['mouth_level'])
    assert levels[0]==pytest.approx(levels[1],abs=.002)
    assert levels[1]==levels[2]
    region=(slice(143,166),slice(205,246),slice(0,3))
    assert np.abs(images[0][region].astype(float)-images[1][region]).mean()<.5
    assert np.array_equal(images[-1][region],np.array(anchor)[region])


class BlockingWorker:
    def __init__(self,path):
        self.path=path;write_wave(path);self.started=threading.Event();self.release=threading.Event();self.calls=[]
    def generate(self,text):
        self.calls.append(text);self.started.set();assert self.release.wait(5)
        if text=='失败':raise RuntimeError('fake generation failure')
        return {'key':'a'*64,'path':str(self.path),'duration_seconds':1,'cache_hit':False,
                'generation_seconds':.1,'sha256':hashlib.sha256(self.path.read_bytes()).hexdigest()}
    def close(self):self.release.set()


def terminal(jobs,key):
    end=time.monotonic()+5
    while time.monotonic()<end:
        result=jobs.get(key)
        if result['status'] not in {'QUEUED','GENERATING'}:return result
        time.sleep(.01)
    raise AssertionError('Speech job failed to settle')


def test_cancelled_running_and_queued_jobs_never_publish_late_audio(tmp_path):
    worker=BlockingWorker(tmp_path/'test.wav');jobs=SpeechJobs(tmp_path,worker)
    try:
        first=jobs.submit('第一句');assert worker.started.wait(2)
        second=jobs.submit('第二句');jobs.cancel(first['id']);jobs.cancel(second['id'])
        worker.release.set();jobs.executor.shutdown(wait=True)
        assert jobs.get(first['id'])['status']=='CANCELLED'
        assert 'result' not in jobs.get(first['id'])
        assert worker.calls==['第一句']
    finally:jobs.close()


def test_complete_job_publishes_envelope_and_failure_is_reported(tmp_path):
    worker=BlockingWorker(tmp_path/'test.wav');worker.release.set();jobs=SpeechJobs(tmp_path,worker)
    try:
        result=terminal(jobs,jobs.submit('你好','happy')['id'])
        assert result['status']=='COMPLETE' and result['emotion']=='happy'
        assert len(result['result']['envelope']['levels'])==100
        assert max(result['result']['envelope']['gains'])==1
        result=terminal(jobs,jobs.submit('失败')['id'])
        assert result['status']=='FAILED' and 'result' not in result
    finally:jobs.close()


def test_queue_has_bounded_pending_work(tmp_path):
    worker=BlockingWorker(tmp_path/'test.wav');jobs=SpeechJobs(tmp_path,worker)
    try:
        for _ in range(4):jobs.submit('你好')
        with pytest.raises(ValueError,match='queue is full'):jobs.submit('第五句')
    finally:worker.release.set();jobs.executor.shutdown(wait=True);jobs.close()
