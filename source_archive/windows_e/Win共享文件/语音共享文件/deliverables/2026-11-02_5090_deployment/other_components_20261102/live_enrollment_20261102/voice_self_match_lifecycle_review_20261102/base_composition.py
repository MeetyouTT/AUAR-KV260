"""Exact released Runtime/Jobs/controller + real speaker worker/Hub + fresh synthetic DBs."""
from contextlib import nullcontext
import copy
import hashlib
import os
import json
import threading
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

import pytest

HERE=Path(__file__).resolve().parent
MODE=os.environ.get('AURA_ENTRY_VARIANT','candidate')
assert MODE in ('baseline','candidate')
RELEASE=HERE/'integration_runtime'
sys.path.insert(0,str(RELEASE))
from board.runtime.board_business import BoardBusinessRuntime,BoardBusinessConfig,LocalIdentityReplies
from board.runtime.board_speaker_business import BoardSpeakerBusiness
from board.runtime.board_dialogue import BoardDialogueController
from board.runtime.audio.board_dialogue_jobs import BoardDialogueJobs
from common.board_memory import BoardMemoryStore
from common.conversation_selection import ConversationSelection
from common.model_inference_wire import Owner,audio_payload,make_response
from common.speaker_identity import voiced_pcm

PINS={'common/feature_intents.py': '901c74d8de825bf6f22ac7cca608db3840ea7d39cc104ac4b5392dca3f7d8f6c', 'board/runtime/board_speaker_business.py': '28d36d1f35ed173098df50e51b829a89b0f5d09c1f7281dc34381a3cedac6cfe', 'board/runtime/board_business.py': 'bf185a86dfd1f94924759c194b0246b51e64cb0a09654c935e8e1310f7bbea51', 'tools/yuki_jobs_candidate.py': 'd7bade70cf15cd5c7dd9bb17be702f86c5f2d1a32ad5c5809dddffde7a71d200', 'tools/formal_yuki.py': 'c74b5f00d52208d992e8ee82c998250001c781c900d31b1f72a18bdda6f492e9', 'tools/streaming_controller.py': '4b76e137d49994f01ae43a7a608e0b9feb13b9eff66cc981346823bace576899', 'tools/realtime_controller.py': '53e13fc026ddbf513090a13b3cdab0aef98eeafb560077fc60e6446ab7ba0e1a', 'tools/voice_first_recording.py': '54fa17ac97e3fdbeeb2725b6534a86dec9ece60839f2b14ffa77c348e714dafc', 'tools/handsfree_recording.py': 'a7e1a55e797e97fa605725ad7423e80704612c3ed4a703db177345ca4fe6a924', 'tools/barge_in_recording.py': '59794f4f234ba0e6433e8b26a44ca65dbd5616af513a5111fb2c6d6738530b6d', 'tools/board_recording.py': 'e70a9f4ca4768b3a1fabfc33145e39edbcb8cf20e0c76f269cc0b032fb54ce26', 'tools/production_memory_presentation.py': 'de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2', 'board/runtime/history_delete.py': '647b5cf85ad5595305067bcced2b118f83e89ca79ba45b7ad91090fd9515023f'}
assert all(hashlib.sha256((RELEASE/name).read_bytes()).hexdigest()==sha for name,sha in PINS.items())

class Mono:
    def __init__(self):self.now=1.
    def __call__(self):return self.now
class Timeline:
    boot_id='synthetic-boot'
    def event_time(self):return 1000.+self.mono()
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
        self.timeline.mono=self.mono
        self.last_meta=None;self.last_raw=None;self.last_events=[]
        monkeypatch.setitem(sys.modules,'webrtcvad',SimpleNamespace(Vad=Vad))
        from common.character_profile import selected_profile
        self.runtime=BoardBusinessRuntime(BoardBusinessConfig(str(path.resolve()),utc_bounds=(900.,2000.),data_origin='synthetic'),
            'synthetic-boot',asr=self.asr,system_prompt=selected_profile().persona_full_prompt,
            conversation_selection=ConversationSelection(path/'synthetic-conversation.json'),
            identity_snapshot=lambda:None,identity_command=lambda command:pytest.fail('Synthetic voice must not command camera'),
            client=self.models,timeline=self.timeline,clock=self.mono)
        self.runtime.jobs.select_conversation(resume=False)
        self.business=BoardSpeakerBusiness.create(path/'synthetic-speaker',encoder_factory=lambda:self.encoder,
            board_boot_id='synthetic-boot',quality=voiced_pcm,expected_model_id=self.encoder.model_id,
            anonymous_config={'enabled':True},clock=self.mono,wall_clock=self.timeline.event_time,data_origin='synthetic')
        self.runtime.attach_speaker_business(self.business)
        # Use actual current formal pair policy plus actual bind_runtime_pair.
        # Only native frame readiness is synthetic; no renderer/GL/device exists.
        from common.character_profile import selected_profile
        from tools.formal_yuki import CandidatePair
        from tools.board_persona_candidate import BoardPersonaCandidate
        from tools.yuki_business_candidate import bind_runtime_pair
        from board.runtime.board_memory_policy import BoardContextBuilder,BoardMemoryCommands
        profile=selected_profile()
        pair_meta=json.loads((HERE/'yuki_pair.formal.public.json').read_text(encoding='utf-8'))
        identity=pair_meta['identity']
        persona=BoardPersonaCandidate(identity['profile_version'],identity['display_name'],identity['persona_config_sha256'],
            identity['render_profile_id'],identity['render_source_profile_sha256'],profile.persona_full_prompt)
        pair=CandidatePair(RELEASE,pair_meta,persona)
        pair.attach_mailbox(SimpleNamespace(ready=True,lock=threading.RLock()))
        pair.observe_native_frame({'frames':1})
        self.runtime.controller.context_builder=BoardContextBuilder(profile.persona_full_prompt)
        self.runtime.controller.command_handler=BoardMemoryCommands(self.runtime.store)
        bind_runtime_pair(self.runtime,pair)
        from tools import yuki_jobs_candidate
        assert self.runtime.jobs._route.__func__ is yuki_jobs_candidate._route
        assert self.runtime.jobs._admit_text.__func__ is yuki_jobs_candidate._admit_text

        self.business.pool.submit(lambda:None).result(timeout=2)
    def say(self,text,*,seed=None):
        self.counter+=1;self.asr.text=text
        raw=struct.pack('<h',1000+(self.counter if seed is None else seed))*48000
        clip=SimpleNamespace(capture_id='synthetic-clip-'+str(self.counter),pcm=raw,audio=SimpleNamespace(sample_count=48000))
        meta=self.runtime.jobs.submit(clip)
        self.last_meta=meta;self.last_raw=raw;self.last_events=[]
        assert self.runtime.jobs.run_next()
        self.business.pool.submit(lambda:None).result(timeout=2)
        latency=copy.deepcopy(self.runtime.jobs.latency_metrics)
        # Drain solely in RAM. Never print transcripts or raw response events.
        errors=[]
        while True:
            event=self.runtime.jobs.poll()
            if event is None:break
            self.last_events.append(event)
            if 'error' in event:errors.append(event['error'])
        media=self.runtime.jobs._playback
        self.last_reply=media.plan.reply.text if media is not None else None
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

