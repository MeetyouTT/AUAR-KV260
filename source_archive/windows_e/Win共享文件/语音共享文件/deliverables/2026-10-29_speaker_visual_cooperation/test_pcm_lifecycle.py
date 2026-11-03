"""Owned reference release only; no claim of hard deletion inside native code."""
import bootstrap
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from common.timeline_conversations import TimelineConversationStore
from tools.speaker_conversation import SpeakerConversation
from tools.speaker_turns import SpeakerTurns
from test_helpers import meta,pcm,voice,CID,wait
from test_speaker_recorder import Client

def test_cancel_queued_tracker_job_immediately_releases_pcm_without_encoding(tmp_path):
    entered=threading.Event();release=threading.Event();encoded=[]
    def encode(owner,raw):
        encoded.append(owner['request_id']);entered.set();release.wait(1.);return voice()
    pool=ThreadPoolExecutor(max_workers=1)
    hub=SimpleNamespace(speaker=SimpleNamespace(analyze=encode),speaker_pool=pool,speaker_gate=threading.Lock())
    service=SpeakerTurns(hub);store=TimelineConversationStore(tmp_path/'conversations.sqlite3')
    recorder=SpeakerConversation(store,client=Client(service),poll_seconds=.005)
    first,second=meta(1),meta(2)
    try:
        for owner in (first,second):store.begin(CID,owner,'public','public')
        assert recorder.begin(first,CID,pcm(1)) and entered.wait(.3)
        assert recorder.begin(second,CID,pcm(2))
        queued=recorder.jobs[second['request_id']]
        assert queued['stage']=='QUEUED' and queued['pcm'] is not None
        assert recorder.cancel(second)
        assert queued['pcm'] is None and not release.is_set()
        assert service.key(second) not in service.rows
        release.set();wait(lambda:recorder.health()['active_jobs']==0)
        assert encoded==[first['request_id']]
        assert store.attribution_for_turn(second,CID)['status']=='CANCELLED'
    finally:release.set();recorder.close();pool.shutdown(wait=True)

def test_expired_tracker_queue_is_swept_while_first_native_job_is_still_active(tmp_path):
    entered=threading.Event();release=threading.Event();encoded=[];clock=[0.]
    def encode(owner,raw):encoded.append(owner['request_id']);entered.set();release.wait(1.);return voice()
    pool=ThreadPoolExecutor(max_workers=1)
    hub=SimpleNamespace(speaker=SimpleNamespace(analyze=encode),speaker_pool=pool,speaker_gate=threading.Lock())
    service=SpeakerTurns(hub);store=TimelineConversationStore(tmp_path/'conversations.sqlite3')
    recorder=SpeakerConversation(store,client=Client(service),clock=lambda:clock[0],poll_seconds=.005)
    first,second=meta(1),dict(meta(2),budget_ms=500)
    try:
        for owner in (first,second):store.begin(CID,owner,'public','public')
        assert recorder.begin(first,CID,pcm(1)) and entered.wait(.3)
        assert recorder.begin(second,CID,pcm(2));queued=recorder.jobs[second['request_id']]
        clock[0]=1.
        wait(lambda:store.attribution_for_turn(second,CID)['status']=='EXPIRED')
        assert queued['pcm'] is None and not release.is_set()
        release.set();wait(lambda:recorder.health()['active_jobs']==0)
        assert encoded==[first['request_id']]
    finally:release.set();recorder.close();pool.shutdown(wait=True)

def test_hub_cancels_unstarted_future_and_clears_its_mutable_pcm_descriptor():
    blocker=threading.Event();entered=threading.Event();encoded=[]
    pool=ThreadPoolExecutor(max_workers=1)
    def occupy():entered.set();blocker.wait(1.)
    occupied=pool.submit(occupy);assert entered.wait(.3)
    hub=SimpleNamespace(speaker=SimpleNamespace(analyze=lambda *args:encoded.append(True) or voice()),
      speaker_pool=pool,speaker_gate=threading.Lock());service=SpeakerTurns(hub);owner=meta()
    try:
        service.submit(owner,pcm(),CID);job=service.work[service.key(owner)]
        assert not job['started'] and job['pcm'] is not None
        service.cancel(owner,CID)
        assert job['pcm'] is None and job['future'].cancelled()
        blocker.set();occupied.result(timeout=.5);pool.shutdown(wait=True)
        assert encoded==[] and service.result(owner,CID)['status']=='CANCELLED'
    finally:blocker.set();pool.shutdown(wait=True)

def test_hub_observed_expiry_releases_unstarted_future_pcm():
    blocker=threading.Event();entered=threading.Event();encoded=[];clock=[0.]
    pool=ThreadPoolExecutor(max_workers=1)
    def occupy():entered.set();blocker.wait(1.)
    occupied=pool.submit(occupy);assert entered.wait(.3)
    hub=SimpleNamespace(speaker=SimpleNamespace(analyze=lambda *args:encoded.append(True) or voice()),
      speaker_pool=pool,speaker_gate=threading.Lock());service=SpeakerTurns(hub,clock=lambda:clock[0]);owner=meta()
    try:
        service.submit(owner,pcm(),CID);job=service.work[service.key(owner)];clock[0]=20.
        assert service.result(owner,CID)['status']=='EXPIRED'
        assert job['pcm'] is None and job['future'].cancelled()
        blocker.set();occupied.result(timeout=.5);pool.shutdown(wait=True)
        assert encoded==[] and service.result(owner,CID)['voice'] is None
    finally:blocker.set();pool.shutdown(wait=True)

def test_active_native_call_finishes_naturally_but_cancelled_result_is_not_written():
    release=threading.Event();entered=threading.Event();returned=threading.Event()
    def encode(owner,raw):
        assert raw;entered.set();release.wait(1.);returned.set();return voice()
    pool=ThreadPoolExecutor(max_workers=1)
    hub=SimpleNamespace(speaker=SimpleNamespace(analyze=encode),speaker_pool=pool,speaker_gate=threading.Lock())
    service=SpeakerTurns(hub);owner=meta()
    try:
        service.submit(owner,pcm(),CID);assert entered.wait(.3);job=service.work[service.key(owner)]
        assert job['started'] and job['pcm'] is None
        service.cancel(owner,CID)
        assert not job['future'].cancelled() and job['future'].running() and not returned.is_set()
        assert service.result(owner,CID)['voice'] is None
        release.set();job['future'].result(timeout=.5)
        assert returned.is_set() and service.result(owner,CID)['status']=='CANCELLED'
    finally:release.set();pool.shutdown(wait=True)

def test_lost_submit_ack_still_cancels_the_original_hub_job(tmp_path):
    from common.speaker_turns import record
    cancelled=[]
    class LostAck:
        def submit_speaker_turn(self,*args,**kwargs):raise TimeoutError('Hub may already have accepted')
        def cancel_speaker_turn(self,owner,cid,**kwargs):
            cancelled.append((owner,cid));return record(owner,cid,status='CANCELLED',reason='REQUEST_CANCELLED')
    store=TimelineConversationStore(tmp_path/'conversations.sqlite3');owner=meta()
    store.begin(CID,owner,'public','public');recorder=SpeakerConversation(store,client=LostAck())
    try:
        recorder.begin(owner,CID,pcm());wait(lambda:recorder.health()['active_jobs']==0)
        assert cancelled==[(owner,CID)]
        assert store.attribution_for_turn(owner,CID)['status']=='UNAVAILABLE'
    finally:recorder.close()
