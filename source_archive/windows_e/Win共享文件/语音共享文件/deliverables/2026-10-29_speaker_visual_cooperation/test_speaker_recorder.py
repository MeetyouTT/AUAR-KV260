import bootstrap
import threading,time
from contextlib import contextmanager
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import pytest
from common.speaker_turns import record
from common.timeline_conversations import TimelineConversationStore
from tools.speaker_conversation import SpeakerConversation
from tools.speaker_turns import SpeakerTurns
from test_helpers import CID,meta,pcm,voice,wait

class Client:
    def __init__(self,service):self.service=service
    def submit_speaker_turn(self,meta,raw,cid,visual=None,**kwargs):return self.service.submit(meta,raw,cid,visual)
    def speaker_turn_result(self,meta,cid,**kwargs):return self.service.result(meta,cid)
    def cancel_speaker_turn(self,meta,cid,**kwargs):return self.service.cancel(meta,cid)

@pytest.fixture
def rig(tmp_path):
    store=TimelineConversationStore(tmp_path/'conversations.sqlite3')
    gate=threading.Event();entered=threading.Event()
    def analyze(*args):entered.set();gate.wait(1.);return voice()
    hub=SimpleNamespace(speaker=SimpleNamespace(analyze=analyze),speaker_gate=threading.Lock(),
      speaker_pool=ThreadPoolExecutor(max_workers=1))
    service=SpeakerTurns(hub);recorder=SpeakerConversation(store,client=Client(service),poll_seconds=.01)
    try:yield store,recorder,service,gate,entered
    finally:
        gate.set();recorder.close();hub.speaker_pool.shutdown(wait=True)

def begin(store,owner,*,profile=None):store.begin(CID,owner,'公开测试输入','公开测试输入',profile=profile)
def read(store,owner):return store.attribution_for_turn(owner,CID)

def test_slow_result_fills_original_played_turn_after_next_normal_turn_begins(rig):
    store,recorder,service,gate,entered=rig;a=meta(1);begin(store,a)
    started=time.monotonic();assert recorder.begin(a,CID,pcm(1))
    assert time.monotonic()-started<.2 and entered.wait(.3)
    assert read(store,a)['status']=='PENDING'
    store.generated(a,'公开回复',24000,'e'*64);store.played(a,24000,'e'*64)
    b=meta(2);begin(store,b);assert recorder.begin(b,CID,pcm(2))
    assert read(store,b)['status']=='PENDING'
    gate.set()
    wait(lambda:read(store,a)['status']=='COMPLETE' and read(store,b)['status']=='COMPLETE')
    assert read(store,a)['context']==a and read(store,b)['context']==b
    assert store.records(CID)[0]['status']=='played' and store.records(CID)[1]['status']=='submitted'
    assert read(store,a)['personal_memory_allowed'] is False

def test_explicit_cancel_discards_delayed_result_and_next_turn_stays_independent(rig):
    store,recorder,service,gate,entered=rig;a=meta(1);begin(store,a);recorder.begin(a,CID,pcm(1));assert entered.wait(.3)
    assert recorder.cancel(a)
    b=meta(2);begin(store,b);recorder.begin(b,CID,pcm(2));gate.set()
    wait(lambda:recorder.health()['active_jobs']==0)
    assert read(store,a)['status']=='CANCELLED' and read(store,a)['voice'] is None
    assert read(store,b)['context']==b and read(store,b)['status'] in ('COMPLETE','UNAVAILABLE')

def test_service_outage_preserves_anonymous_dialogue_and_terminal_record(tmp_path):
    class Offline:
        def submit_speaker_turn(self,*args,**kwargs):raise OSError('service down')
    store=TimelineConversationStore(tmp_path/'conversations.sqlite3');owner=meta();begin(store,owner)
    recorder=SpeakerConversation(store,client=Offline())
    try:
        assert recorder.begin(owner,CID,pcm())
        wait(lambda:read(store,owner)['status']=='UNAVAILABLE')
        assert store.records(CID)[0]['user']=='公开测试输入' and read(store,owner)['voice'] is None
    finally:recorder.close()

def test_persistent_pending_is_expired_even_if_tts_does_not_call_back(tmp_path):
    class Pending:
        def submit_speaker_turn(self,owner,raw,cid,visual=None,**kwargs):return record(owner,cid)
        def speaker_turn_result(self,owner,cid,**kwargs):return record(owner,cid)
        def cancel_speaker_turn(self,owner,cid,**kwargs):return record(owner,cid,status='CANCELLED',reason='REQUEST_CANCELLED')
    store=TimelineConversationStore(tmp_path/'conversations.sqlite3');owner=meta();begin(store,owner)
    recorder=SpeakerConversation(store,client=Pending(),poll_seconds=.005,analysis_seconds=.05)
    try:
        assert recorder.begin(owner,CID,pcm())
        wait(lambda:read(store,owner)['status']=='EXPIRED')
        assert read(store,owner)['voice'] is None and recorder.health()['expired']>=1
    finally:recorder.close()

def test_profile_revocation_while_cpu_is_running_does_not_grant_or_write_identity(rig):
    store,old,service,gate,entered=rig;old.close();allowed=[True]
    pid=store.create_profile('公开档案',consent=True);owner=meta();begin(store,owner,profile=pid)
    @contextmanager
    def scope(meta):
        if not allowed[0]:raise PermissionError('revoked')
        yield pid
    recorder=SpeakerConversation(store,scope_for=scope,client=Client(service),poll_seconds=.005)
    try:
        assert recorder.begin(owner,CID,pcm());assert entered.wait(.3)
        allowed[0]=False;gate.set()
        wait(lambda:recorder.health()['active_jobs']==0)
        result=store.attribution_for_turn(owner,CID,profile=pid)
        assert result['status']=='CANCELLED' and result['voice'] is None
        assert store.facts(CID,profile=pid)==[]
    finally:recorder.close()

def test_missing_profile_grant_never_falls_back_to_anonymous_read(rig):
    store,recorder,service,gate,entered=rig
    pid=store.create_profile('公开档案',consent=True);owner=meta();begin(store,owner,profile=pid)
    assert not recorder.begin(owner,CID,pcm())
    assert store.attribution_for_turn(owner,CID,profile=pid) is None
    assert recorder.health()['store_errors']==1

def test_queue_and_pcm_lifetime_are_bounded(rig):
    store,recorder,service,gate,entered=rig
    for i in range(1,5):
        owner=meta(i,session='s'+str(i));begin(store,owner)
        recorder.begin(owner,CID,pcm(i))
    assert recorder.health()['active_jobs']<=3 and recorder.health()['queued']<=2
    assert read(store,meta(4,session='s4'))['status']=='UNAVAILABLE'
    gate.set();wait(lambda:recorder.health()['active_jobs']==0)
    assert recorder.health()['maximum_job_slots']==3

def test_newest_hub_submission_does_not_cancel_older_original_result(rig):
    store,recorder,service,gate,entered=rig;a=meta(1)
    service.submit(a,pcm(1),CID);assert entered.wait(.3)
    b=meta(2);busy=service.submit(b,pcm(2),CID)
    assert busy['status']=='UNAVAILABLE'
    gate.set();wait(lambda:service.result(a,CID)['status']=='COMPLETE')
    assert service.result(a,CID)['context']==a and service.result(b,CID)['voice'] is None
