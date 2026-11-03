"""Exact released Runtime/Jobs/controller + real speaker worker/Hub + fresh synthetic DBs."""
from contextlib import nullcontext
import copy
import hashlib
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

import pytest

HERE=Path(__file__).resolve().parent
RELEASE=HERE/'runtime'
sys.path.insert(0,str(RELEASE))
from board.runtime.board_business import BoardBusinessRuntime,LocalIdentityReplies
from board.runtime.board_speaker_business import BoardSpeakerBusiness
from board.runtime.board_dialogue import BoardDialogueController
from board.runtime.audio.board_dialogue_jobs import BoardDialogueJobs
from common.board_memory import BoardMemoryStore
from common.model_inference_wire import Owner,audio_payload,make_response
from common.speaker_identity import voiced_pcm

PINS={'board/runtime/audio/board_dialogue_jobs.py':'580b2cf796275104cf15f2295afa2de29f82f32eabdd783a4b3aff858840a464',
 'common/binding_intent.py':'8048cd5bd4f3f80cd872f373e1eed149820f37d2ec40042390c17cfb4cd94df1',
 'board/runtime/board_business.py':'d034227118063dc4dbfb69f4bc735000980bd166e91262b4953f0db4b1baf5cc',
 'board/runtime/board_speaker_business.py':'6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816',
 'tools/binding_hub_runtime.py':'80b20963160242eb06fca69dd0fd5774251d1da626f5de718cefa276bd58b375',
 'tools/speaker_device.py':'da9c199527abdf9e247661d8798f4345cf0b79524f5c2a06394b5dc9c44107de'}
assert all(hashlib.sha256((RELEASE/name).read_bytes()).hexdigest()==sha for name,sha in PINS.items())

class Mono:
    def __init__(self):self.now=1.
    def __call__(self):return self.now
class Timeline:
    boot_id='synthetic-boot'
    def event_time(self):return 1000.
    def compaction_guard(self):return nullcontext()
    def quality_snapshot(self):return dict(anchored=True,event_time_available=True,same_boot=True)
class Models:
    host='192.168.50.1';port=8797
    def __init__(self):self.calls=[]
    def request(self,kind,payload,**kwargs):
        self.calls.append(kind)
        if kind=='tts':result=dict(audio=audio_payload(b'\1\0'*2400))
        else:result=dict(text='{"reply_text":"合成普通回答。","emotion":"friendly","avatar_action":""}')
        return make_response(Owner.from_dict(payload),result=result)
    def cancel(self,owner):return None
class Asr:
    def __init__(self):self.text=''
    def transcribe(self,*a,**k):return self.text
class Encoder:
    model_id='synthetic-ecapa-model';dimension=192
    def __init__(self):self.calls=0
    def encode(self,raw):self.calls+=1;return (1.,)+(0.,)*191
class Vad:
    def __init__(self,mode):assert mode==2
    def is_speech(self,frame,rate):return True
class IdleWorker:
    thread=None
    def close(self,*a,**k):return True
    def health(self):return {}

class Composition:
    def __init__(self,path,monkeypatch):
        self.root=path;self.mono=Mono();self.timeline=Timeline();self.models=Models();self.asr=Asr();self.encoder=Encoder();self.counter=0
        monkeypatch.setitem(sys.modules,'webrtcvad',SimpleNamespace(Vad=Vad))
        # The public snapshot lacks the unrelated history_delete assembly module.
        # Explicitly wire the actual target classes in the original constructor's
        # order; retain Runtime's actual attach and analysis methods, not substitutes.
        self.runtime=object.__new__(BoardBusinessRuntime)
        self.runtime.config=SimpleNamespace(data_origin='synthetic')
        self.runtime.boot_id='synthetic-boot';self.runtime.clock=self.mono;self.runtime.timeline=self.timeline
        self.runtime.started=False;self.runtime.closed=False;self.runtime.speaker_business=None
        self.runtime.speaker_analysis_error=''
        self.runtime.store=BoardMemoryStore(path/'synthetic-timeline.sqlite3',clock=self.timeline.event_time,data_origin='synthetic')
        self.runtime.controller=BoardDialogueController(self.runtime.store,self.models,board_boot_id='synthetic-boot',
            system_prompt='只输出原三字段JSON。',asr=self.asr,clock=self.mono)
        self.runtime.identity_handler=LocalIdentityReplies('synthetic-boot',lambda:None,
            lambda c:pytest.fail('Voice entry must not issue face commands'),clock=self.mono,now_ms=lambda:round(self.mono()*1000))
        self.runtime.jobs=BoardDialogueJobs(self.runtime.controller,
            dict(enabled=True,host='192.168.50.1',port=8797,timeout_ms=120000),'synthetic-boot',asr=self.asr,
            scope_provider=lambda meta:dict(kind='conversation',id='a'*32),
            special_handlers={'identity_enrollment':self.runtime.identity_handler,'identity_query':self.runtime.identity_handler},
            clock=self.mono,start_worker=False)
        self.business=BoardSpeakerBusiness.create(path/'synthetic-speaker',encoder_factory=lambda:self.encoder,
            board_boot_id='synthetic-boot',quality=voiced_pcm,expected_model_id=self.encoder.model_id,
            anonymous_config={'enabled':True},clock=self.mono,wall_clock=self.timeline.event_time,data_origin='synthetic')
        self.runtime.attach_speaker_business(self.business)
        self.business.pool.submit(lambda:None).result(timeout=2)
    def say(self,text,*,seed=None):
        self.counter+=1;self.asr.text=text
        raw=struct.pack('<h',1000+(self.counter if seed is None else seed))*48000
        clip=SimpleNamespace(capture_id='synthetic-clip-'+str(self.counter),pcm=raw,audio=SimpleNamespace(sample_count=48000))
        meta=self.runtime.jobs.submit(clip)
        assert self.runtime.jobs.run_next()
        self.business.pool.submit(lambda:None).result(timeout=2)
        latency=copy.deepcopy(self.runtime.jobs.latency_metrics)
        # Drain solely in RAM. Never print transcripts or raw response events.
        errors=[]
        while True:
            event=self.runtime.jobs.poll()
            if event is None:break
            if 'error' in event:errors.append(event['error'])
        media=self.runtime.jobs._playback
        if media is not None:
            self.runtime.jobs.acknowledge(meta,media.result);self.runtime.jobs.drain_actions()
        return latency,errors
    def row(self):return next(iter(self.business.hub.speaker.sessions.values()))
    def voice_count(self):return self.business.pool.submit(lambda:len(self.business.hub.speaker.store.people())).result(timeout=2)
    def close(self):
        self.runtime.jobs.close()
        assert self.business.close(timeout=2)
        # BoardMemoryStore closes each SQLite connection in its _db context;
        # it has no long-lived connection and deliberately no close() method.

@pytest.fixture
def c(tmp_path,monkeypatch):
    value=Composition(tmp_path/'synthetic-composition',monkeypatch)
    try:yield value
    finally:value.close()

@pytest.mark.parametrize('phrase',['登记声纹，我叫合成测试','帮我登记声纹，我叫合成测试','请帮我登记声纹，我叫合成测试'])
def test_actual_runtime_jobs_worker_hub_accepts_named_voice_start(c,phrase):
    latency,errors=c.say(phrase)
    assert errors==[] and latency['error_class']=='none'
    assert c.runtime.identity_handler.public()['entry_mode']=='voice'
    assert c.business.public()['active'] is True and c.row()['stage']=='samples' and c.row()['vectors']==[]
    assert c.encoder.calls==0
    assert c.business.health()['submitted']>=2 and c.business.health()['complete']>=2
    assert c.business.hub.binding.registry.health()['active_people']==0
    assert c.models.calls and set(c.models.calls)=={'tts'}

def test_actual_worker_after_original_voice_hook_and_analysis_do_not_erase_session(c):
    c.say('登记声纹，我叫合成测试')
    for text in ('合成第一段不同语音','合成第二段不同语音','合成第三段不同语音'):
        latency,errors=c.say(text);assert errors==[] and latency['error_class']=='none'
    assert c.row()['stage']=='confirm' and c.encoder.calls==3
    assert c.voice_count()==0
    latency,errors=c.say('确认保存声纹')
    assert errors==[] and c.voice_count()==1
    assert c.business.hub.binding.registry.health()['active_people']==0
    assert c.runtime.identity_handler.public()['entry_mode'] is None

def test_actual_bare_voice_name_followup_does_not_require_face(c):
    c.say('登记声纹')
    assert c.business.hub.speaker.sessions=={}
    assert c.runtime.identity_handler.public()['entry_name_pending'] is True
    c.say('我叫合成测试')
    assert c.row()['stage']=='samples' and c.runtime.identity_handler.public()['entry_mode']=='voice'
    assert c.encoder.calls==0

def test_actual_wrong_or_missing_input_kind_falls_back_without_starting_but_is_not_live_proof(c):
    latency,errors=c.say('今天说一句合成普通聊天')
    assert errors==[] and latency['error_class']=='none' and c.business.hub.speaker.sessions=={}
    assert c.runtime.identity_handler.public()['entry_mode'] is None
    assert 'llm' in c.models.calls and c.business.health()['submitted']>=1

@pytest.mark.parametrize('phrase',[
    '我要登记声纹，我叫合成测试',
    '我想登记声纹，我叫合成测试',
    '登记声音，我叫合成测试',
    '录入声音，我叫合成测试',
])
def test_actual_noncanonical_phrase_can_complete_with_no_entry_and_no_error_only_synthetic(c,phrase):
    # An intentional counterexample to inferring successful routing from ASR
    # completion/healthy analysis alone. This is not the live user's transcript.
    from common.binding_intent import binding_intent
    from common.feature_intents import speaker_requested
    assert binding_intent(phrase)['kind']=='ordinary' and speaker_requested(phrase) is False
    latency,errors=c.say(phrase)
    assert errors==[] and latency['error_class']=='none'
    assert c.runtime.identity_handler.public()['entry_mode'] is None
    assert c.business.public()['active'] is False and c.business.hub.speaker.sessions=={}
    assert 'llm' in c.models.calls and c.business.health()['complete']>=1

def test_actual_external_reset_after_success_leaves_prior_success_latency_but_no_active_entry(c):
    latency,errors=c.say('登记声纹，我叫合成测试')
    assert errors==[] and latency['error_class']=='none' and c.row()['stage']=='samples'
    c.runtime.jobs.reset_enrollment()
    c.business.pool.submit(lambda:None).result(timeout=2)
    assert c.runtime.identity_handler.public()['entry_mode'] is None
    assert c.business.public()['active'] is False and c.business.hub.speaker.sessions=={}
    assert c.runtime.jobs.latency_metrics['error_class']=='none'
    assert c.voice_count()==0 and c.business.hub.binding.registry.health()['active_people']==0
