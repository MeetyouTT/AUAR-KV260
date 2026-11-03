import bootstrap
import base64,io,json,threading,sqlite3,time
from email.message import Message
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock
import pytest
from tools.device_hub import Handler
from tools.speaker_turns import SpeakerTurns
from common.conversation_store import ConversationStore
from common.speaker_visual import build_visual
from test_helpers import meta,pcm,CID,snapshot

@pytest.fixture
def hub():
    value=SimpleNamespace(speaker=None,speaker_gate=threading.Lock(),speaker_pool=ThreadPoolExecutor(max_workers=1))
    value.speaker_turns=SpeakerTurns(value)
    try:yield value
    finally:value.speaker_pool.shutdown(wait=True)

def request(hub,path,value,*,address='127.0.0.1'):
    handler=Handler.__new__(Handler);handler.client_address=(address,1);handler.path=path
    handler.headers=Message();body=json.dumps(value).encode();handler.headers['Content-Length']=str(len(body))
    handler.headers['Content-Type']='application/json';handler.rfile=io.BytesIO(body)
    handler.connection=SimpleNamespace(settimeout=lambda *args:None);handler.server=SimpleNamespace(hub=hub)
    reply=[];handler.reply=lambda code,out:reply.append((code,out));handler.do_POST();return reply[0]

def test_unavailable_speaker_is_fast_anonymous_metadata_and_pure_model_route(hub):
    body={'context':meta(),'conversation_id':CID,'pcm':base64.b64encode(pcm()).decode(),'visual':None}
    code,out=request(hub,'/v1/speaker/analysis/submit',body)
    assert code==200 and out['status']=='UNAVAILABLE' and out['voice'] is None
    code,result=request(hub,'/v1/speaker/analysis/result',{'context':meta(),'conversation_id':CID})
    assert code==200 and result['context']==meta() and not result['personal_memory_allowed']

def test_board_cannot_use_model_only_attribution_endpoints(hub):
    code,_=request(hub,'/v1/speaker/analysis/submit',{'context':meta(),'conversation_id':CID,
      'pcm':base64.b64encode(pcm()).decode(),'visual':None},address='192.168.50.2')
    assert code==400 and hub.speaker_turns.health()['buffered_results']==0

def test_unexpected_profile_raw_template_and_foreign_query_fields_are_rejected(hub):
    body={'context':meta(),'conversation_id':CID,'pcm':base64.b64encode(pcm()).decode(),'visual':None}
    for extra in ({'profile_id':'p'},{'embedding':[1,0]},{'identity_id':'face-one'}):
        assert request(hub,'/v1/speaker/analysis/submit',dict(body,**extra))[0]==400
    assert request(hub,'/v1/speaker/analysis/result',{'context':meta(),'conversation_id':CID,'text':'secret'})[0]==400
    assert request(hub,'/v1/speaker/analysis/submit',dict(body,pcm=base64.b64encode(b'bad').decode()))[0]==400

def test_new_attribution_db_write_wait_has_small_busy_bound(tmp_path):
    path=tmp_path/'store.sqlite3';store=ConversationStore(path);store.begin(CID,meta(),'public','public')
    with sqlite3.connect(path) as blocker:
        blocker.execute('BEGIN IMMEDIATE');began=time.monotonic()
        with pytest.raises(sqlite3.OperationalError):store.attribution_pending(meta(),CID)
        assert time.monotonic()-began<.3
    assert store.attribution_for_turn(meta(),CID) is None

def test_known_face_camera_epoch_and_crop_source_cannot_disagree():
    for mutate in (lambda s:s['preview'].update(camera_epoch='different'),
                   lambda s:s['modules']['identity'].update(face_preview={
                     'target':s['modules']['identity']['face_target'],'frame_id':41,'captured_mono_ms':3970,'ttl_ms':3000})):
        end=snapshot(4000,40);mutate(end)
        assert build_visual(snapshot(1000,10),end,meta(),4050)['state']=='UNAVAILABLE'

def test_native_social_feedback_branch_is_preserved(monkeypatch,tmp_path):
    from board.runtime.audio import channel_jobs
    from test_helpers import wait
    calls=[]
    def cache(config,root,*,social=False):
        calls.append((config['port'],social))
        return {} if social else {'thinking':{'path':'public-fixture'}}
    monkeypatch.setattr(channel_jobs,'feedback_cache',cache)
    config={'enabled':True,'host':'192.168.50.1','port':8792,'timeout_ms':120000}
    jobs=channel_jobs.ChannelConversationJobs(config,'fixture-boot',tmp_path)
    try:
        wait(lambda:(8792,True) in calls)
        jobs.prepare_feedback(dict(config,port=8793))
        assert calls==[(8792,False),(8792,True),(8793,False),(8793,True)]
    finally:jobs.close()
