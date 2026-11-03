"""Spoken phase guidance remains a single ASR exchange and never calls an LLM."""
import copy
import io
import threading
import time
import pytest
from common import voice_enrollment as speech
from board.identity.voice_enrollment import VoiceEnrollment
from tools.identity_voice_host import IdentityReplyStream
from tests.framework.test_voice_enrollment import snapshot
from tests.framework.test_voice_channel import owner


class FlowFixture:
    def __init__(self,replacement=False):
        self.view=snapshot();self.commands=[]
        self.sample={'session_id':'','stage':'idle','counts':{'front':0,'left':0,'right':0,'validate':0},
                     'total':0,'total_required':15,'detail':'sample'}
        self.view['modules']['identity']['enrollment_sampling']=self.sample
        self.view['capabilities'].update(identity_enroll=False,identity_sample_start=True,identity_sample_cancel=False)
        if replacement:self.view['modules']['identity']['people']=[{'person_id':'original','display_name':'小林'}]
        self.flow=VoiceEnrollment('boot',lambda:copy.deepcopy(self.view),self.command,now_ms=lambda:1000)

    def command(self,command):
        self.commands.append(copy.deepcopy(command))
        if command['action']=='identity_sample_start':
            self.sample.update(session_id='current-sample',stage='front')
            self.view['capabilities'].update(identity_sample_start=False,identity_sample_cancel=True)
        elif command['action']=='identity_sample_cancel':self.sample.update(session_id='',stage='idle')
        else:
            self.view['modules']['identity'].update(state='KNOWN',db_version=1,
                last_operation={'command_id':command['command_id'],'action':'identity_enroll','state':'COMMITTED',
                                'db_version':1,'detail':'已登记'})
        return {'accepted':True,'command_id':command['command_id']}

    def say(self,text):return self.flow.handle(text,copy.deepcopy(self.view))

    def ready(self):
        self.sample.update(stage='ready',counts={'front':4,'left':3,'right':3,'validate':5},total=15)
        self.view['capabilities']['identity_enroll']=True


def test_guidance_finishes_with_name_confirmation_without_writing_identity():
    f=FlowFixture();assert f.say('帮我登记身份')['code']=='ask_name'
    assert f.say('我叫小林')['code']=='sample_front'
    assert [c['action'] for c in f.commands]==['identity_sample_start']
    f.ready();emitted=[];f.flow.guide(lambda reply,final:emitted.append((reply,final)))
    assert emitted==[(speech.result('confirm_name','小林'),True)]
    assert len(f.commands)==1
    assert f.say('确认登记')['code']=='registered'
    assert [c['action'] for c in f.commands].count('identity_enroll')==1


def test_existing_name_requires_explicit_update_phrase_and_preserves_id():
    f=FlowFixture(True);f.say('帮我登记身份');f.say('我叫小林')
    assert f.commands[0]['params']['replace_person_id']=='original'
    f.ready();emitted=[];f.flow.guide(lambda reply,final:emitted.append(reply))
    assert emitted[-1]==speech.result('confirm_update_name','小林')
    assert f.say('确认登记')['code']=='retry_update'
    assert not any(c['action']=='identity_enroll' for c in f.commands)
    assert f.say('确认更新登记')['code']=='registered'
    assert next(c for c in f.commands if c['action']=='identity_enroll')['params']['replace_person_id']=='original'


def test_failure_or_cancellation_never_emits_registration_success():
    f=FlowFixture();f.say('帮我登记身份');f.say('我叫小林');f.sample['stage']='failed'
    emitted=[];f.flow.guide(lambda reply,final:emitted.append(reply))
    assert emitted==[speech.result('sample_failed')]
    assert not any(c['action']=='identity_enroll' for c in f.commands)


def test_ordered_progress_rejects_replay_and_cannot_claim_intermediate_success():
    meta=owner();s=IdentityReplyStream(meta,3)
    s.accept(meta,s.token,speech.result('sample_front'),sequence=0,final=False)
    with pytest.raises(ValueError):s.accept(meta,s.token,speech.result('sample_left'),sequence=0,final=False)
    with pytest.raises(ValueError):s.accept(meta,s.token,speech.result('registered'),sequence=1,final=False)
    s.accept(meta,s.token,speech.result('sample_left'),sequence=1,final=False)
    s.accept(meta,s.token,speech.result('confirm_name','小林'),sequence=2,final=True)
    events=list(s);assert sum(k=='speech_ready' for k,v in events)==3
    assert events[-1][1]['reply_text']==''.join(speech.render(speech.result(code,'小林' if code=='confirm_name' else ''))
                                              for code in ('sample_front','sample_left','confirm_name'))
    with pytest.raises(ValueError):s.accept(meta,s.token,speech.result('registered'),sequence=3,final=True)


def test_actual_http_stream_delivers_first_guidance_before_sampling_finishes(tmp_path):
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    from board.runtime.audio.voice_channel import VoiceChannel
    from tests.framework.test_history_reuse import host
    from tests.framework import test_voice_channel as vf
    model=host();model.voice=vf.VoiceChannelTests().fixture_models(tmp_path).voice
    model.lock=threading.Lock();model.latency_options={'reply_first':True,'coalesce_chat':True}
    class Engine:
        model_id='TEST_ONLY';calls=0
        def transcribe(self,pcm):self.calls+=1;return '我叫小林'
    engine=Engine();server=AsrServer(('127.0.0.1',0),engine,handler=ModelHandler);server.models=model
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    channel=VoiceChannel('127.0.0.1',server.server_port);meta=owner();first_audio=threading.Event();final_sent=[];errors=[]
    def receive(header,pcm):
        if header['kind']=='transcript':
            token=header['identity_request']
            def guide():
                try:
                    channel.identity_result(meta,token,speech.result('sample_front'),sequence=0,final=False)
                    assert first_audio.wait(2)
                    for seq,code in enumerate(('sample_left','sample_right','sample_validate','confirm_name'),1):
                        channel.identity_result(meta,token,speech.result(code,'小林' if code=='confirm_name' else ''),sequence=seq,final=seq==4)
                    final_sent.append(True)
                except BaseException as exc:errors.append(exc);channel.cancel()
            threading.Thread(target=guide,daemon=True).start()
        elif header['kind']=='audio':first_audio.set()
    try:
        result=channel.exchange(meta,vf.PCM,receive,enrollment_state=True)
        assert engine.calls==1 and len(model.voice.calls)==5 and final_sent and not errors
        assert result['reply_text'].endswith(speech.render(speech.result('confirm_name','小林')))
        assert model.histories=={}
    finally:
        channel.close();server.shutdown();server.server_close();worker.join(2)
