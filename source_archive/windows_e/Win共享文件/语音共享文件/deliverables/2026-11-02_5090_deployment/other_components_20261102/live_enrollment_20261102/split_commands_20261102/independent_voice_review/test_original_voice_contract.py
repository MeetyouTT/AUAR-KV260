"""Independent public SpeakerDevice contract. RAM store and synthetic PCM only."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

HERE=Path(__file__).resolve().parent
LIVE=HERE.parents[1]
RUNTIME=LIVE/'start_sync_fix/candidate_runtime'
sys.path.insert(0,str(RUNTIME))
from common.feature_intents import speaker_text,speaker_requested,speaker_query_requested
from common.speaker_identity import voiced_pcm
from tools.speaker_device import SpeakerDevice

class Clock:
    def __init__(self):self.now=1.
    def __call__(self):return self.now

class Store:
    def __init__(self):self.revision=0;self.rows=[];self.enrolls=[];self.deletes=[];self.other=None
    def people(self):return copy.deepcopy(self.rows)
    def best_other_score(self,vector):return self.other
    def enroll(self,identity_id,name,vector,*,consent,expected_revision,max_people):
        assert consent is True and expected_revision==self.revision and max_people==32
        assert all(r['person_id']!=identity_id for r in self.rows)
        self.rows.append(dict(person_id=identity_id,display_name=name));self.revision+=1
        self.enrolls.append(dict(identity_id=identity_id,name=name,consent=consent))
    def delete(self,identity_id,*,expected_revision):
        assert expected_revision==self.revision
        self.rows=[r for r in self.rows if r['person_id']!=identity_id];self.revision+=1;self.deletes.append(identity_id)

class Encoder:
    model_id='synthetic-voice-model';dimension=2
    def __init__(self):self.calls=0;self.vector=(1.,0.)
    def encode(self,raw):self.calls+=1;return self.vector

class VAD:
    voiced_frames=100000
    def __init__(self,mode):assert mode==2;self.index=0
    def is_speech(self,frame,rate):
        assert len(frame)==960 and rate==16000
        self.index+=1;return self.index<=self.voiced_frames

def pcm(seed,seconds=3):return struct.pack('<h',1000+seed)*round(16000*seconds)

def meta(index,raw):
    return dict(protocol='aura-asr-1',board_boot_id='synthetic-boot',session_id='synthetic-session',
        request_id='request-'+str(index),generation=index,capture_id='capture-'+str(index),
        sample_count=len(raw)//2,pcm_sha256=hashlib.sha256(raw).hexdigest(),budget_ms=60000)

class Fixture:
    def __init__(self):
        self.clock=Clock();self.encoder=Encoder();self.store=Store();self.calls=0
        # Avoid SpeakerDevice.__init__: no path or database is opened.
        self.device=object.__new__(SpeakerDevice)
        self.device.encoder=self.encoder;self.device.database=None;self.device.clock=self.clock
        self.device.sessions={};self.device.latest={};self.device.replies={};self.device.store=self.store
        self.device.calibrated=False;self.device.threshold=.8;self.device.margin=.1;self.device.consistency=.6
        self.device.quality=lambda raw:voiced_pcm(raw)
    def turn(self,text,seed=None,seconds=3):
        self.calls+=1;raw=pcm(self.calls if seed is None else seed,seconds)
        with patch.dict(sys.modules,{'webrtcvad':SimpleNamespace(Vad=VAD)}):return self.device.turn(meta(self.calls,raw),text,raw)
    def active(self):return self.device.state(meta(self.calls or 1,pcm(self.calls or 1)))['active']
    def row(self):return self.device.sessions[('synthetic-boot','synthetic-session')]
    def begin(self):
        result=self.turn('帮我登记声纹，我叫合成声纹')
        assert '分三次' in result and self.row()['vectors']==[] and self.encoder.calls==0
    def samples(self):
        for text in ('合成样本一','合成样本二','合成样本三'):self.turn(text)
        assert self.row()['stage']=='confirm'

@pytest.mark.parametrize('phrase',['登记声纹','帮我登记声纹','请帮我登记声纹','注册我的声纹'])
def test_bare_original_voice_command_requires_name_and_never_collects_start_pcm(phrase):
    f=Fixture();assert speaker_text(phrase)=='登记我的声纹'
    assert '我叫某某' in f.turn(phrase) and not f.active()
    assert f.encoder.calls==0 and f.store.enrolls==[]

@pytest.mark.parametrize('phrase',['登记声纹，我叫合成声纹','帮我登记声纹，我叫合成声纹','登记我的声纹，我叫合成声纹','记住我的声音，我叫合成声纹'])
def test_named_voice_start_opens_only_original_three_sample_session(phrase):
    f=Fixture();assert speaker_requested(phrase)
    assert '分三次' in f.turn(phrase)
    assert f.row()['stage']=='samples' and f.row()['vectors']==[] and f.row()['until']==181.
    assert f.encoder.calls==0 and f.store.enrolls==[]

def test_three_distinct_pcm_and_explicit_voice_save_required_without_visual():
    f=Fixture();f.begin();f.samples()
    assert f.encoder.calls==3 and len(f.row()['hashes'])==3 and f.store.enrolls==[]
    for text in ('好的','确认','确认登记','确认保存声纹吗'):
        assert '确认保存声纹' in f.turn(text)
        assert f.store.enrolls==[] and f.row()['stage']=='confirm'
    assert '已保存' in f.turn('确认保存声纹')
    assert len(f.store.enrolls)==1 and not f.active() and f.encoder.calls==3
    assert f.device.state(meta(f.calls,pcm(f.calls)))['automatic_profile_access'] is False
    assert not hasattr(f.device,'visual') and not hasattr(f.device,'profile_grant')

def test_duplicate_pcm_is_not_an_independent_second_sample():
    f=Fixture();f.begin();f.turn('合成第一段',seed=99)
    assert '已经用过' in f.turn('换了文字但PCM完全相同',seed=99)
    assert len(f.row()['vectors'])==1 and f.encoder.calls==1 and f.store.enrolls==[]

def test_short_recording_is_rejected_without_consuming_sample():
    f=Fixture();f.begin();assert '不足或不清楚' in f.turn('合成短句',seconds=2.5)
    assert f.row()['vectors']==[] and f.encoder.calls==0

def test_original_vad_249s_rejects_and_252s_accepts_inside_three_second_recording():
    f=Fixture();f.begin()
    with patch.object(VAD,'voiced_frames',83):assert '不足或不清楚' in f.turn('合成不足有效语音')
    assert f.row()['vectors']==[]
    with patch.object(VAD,'voiced_frames',84):assert '再说一句' in f.turn('合成满足有效语音')
    assert len(f.row()['vectors'])==1 and f.encoder.calls==1

def test_status_question_is_never_a_voice_sample_or_save():
    f=Fixture();f.begin();f.turn('样本一')
    count=len(f.row()['vectors']);calls=f.encoder.calls
    assert speaker_query_requested('声纹保存了吗')
    assert '尚未提交保存' in f.turn('查询声纹保存状态')
    assert len(f.row()['vectors'])==count and f.encoder.calls==calls and f.store.enrolls==[]

def test_inconsistent_three_vectors_cancel_without_save():
    f=Fixture();f.begin();f.turn('样本一');f.turn('样本二');f.encoder.vector=(0.,1.)
    assert '不够一致' in f.turn('样本三')
    assert not f.active() and f.store.enrolls==[]

def test_same_name_close_existing_voice_is_rejected_without_update():
    f=Fixture();f.store.rows=[dict(person_id='synthetic-existing',display_name='合成声纹')];f.store.revision=1;f.store.other=.8
    original=copy.deepcopy(f.store.rows);f.begin();f.samples()
    assert '已有声纹过于接近' in f.turn('确认保存声纹')
    assert f.store.rows==original and f.store.enrolls==[] and f.store.revision==1

def test_original_same_name_far_voice_is_new_identity_not_replacement():
    f=Fixture();f.store.rows=[dict(person_id='synthetic-existing',display_name='合成声纹')];f.store.revision=1;f.store.other=.1
    f.begin();f.samples();f.turn('确认保存声纹')
    assert len(f.store.rows)==2 and f.store.rows[0]['person_id']=='synthetic-existing'
    assert f.store.rows[0]['display_name']==f.store.rows[1]['display_name']=='合成声纹'
    assert f.store.rows[1]['person_id']!='synthetic-existing' and len(f.store.enrolls)==1

@pytest.mark.parametrize('phrase',['取消声纹登记','停止声纹登记','不登记声纹了','不要保存声纹','取消'])
def test_original_voice_cancel_discards_uncommitted_samples(phrase):
    f=Fixture();f.begin();f.turn('样本一');assert '已取消' in f.turn(phrase)
    assert not f.active() and f.store.enrolls==[]

def test_original_180_second_expiry_does_not_save():
    f=Fixture();f.begin();f.samples();f.clock.now=181.
    assert '没有待确认' in f.turn('确认保存声纹')
    assert not f.active() and f.store.enrolls==[]

def test_original_save_reply_idempotency_has_one_memory_store_write():
    f=Fixture();f.begin();f.samples();index=f.calls+1;raw=pcm(index);owner=meta(index,raw)
    a=f.device.turn(owner,'确认保存声纹',raw);b=f.device.turn(owner,'确认保存声纹',raw)
    assert a==b and len(f.store.enrolls)==1
    with pytest.raises(ValueError):f.device.turn(owner,'确认保存声纹。',raw)

def test_explicit_face_phrase_would_be_consumed_if_wrongly_dispatched_to_active_voice():
    # This is a counterexample for routing reviewers, not a desired product
    # behavior: modality dispatch must intercept before original sampler.turn.
    f=Fixture();f.begin();f.turn('登记视觉，我叫合成视觉')
    assert len(f.row()['vectors'])==1
    assert f.store.enrolls==[]
