import bootstrap
import copy,threading,time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import pytest
from tools.speaker_device import SpeakerDevice
from tools.speaker_turns import SpeakerTurns
from test_helpers import CID,meta,pcm,voice,wait

class Encoder:
    model_id='synthetic-ecapa';dimension=2
    def __init__(self):self.calls=0
    def encode(self,raw):self.calls+=1;return [1,0]

def device(tmp_path,calibrated=True):
    encoder=Encoder()
    calibration={'model_id':encoder.model_id,'field_calibrated':calibrated,'evidence':'synthetic-fixture-only'}
    return SpeakerDevice(encoder,tmp_path/'speakers.sqlite3',calibration=calibration)

def test_uncalibrated_ordinary_turn_stays_anonymous_and_skips_embedding(tmp_path):
    item=device(tmp_path,False);before=item.store.revision
    result=item.analyze(meta(),pcm())
    assert result['state']=='NOT_CALIBRATED' and result['candidate_id'] is None
    assert not result['single_speaker_verified'] and item.encoder.calls==0 and item.store.revision==before
    item.store.close()

def test_calibrated_readonly_matching_never_enrolls_or_proves_single_speaker(tmp_path,monkeypatch):
    import tools.speaker_device as module
    item=device(tmp_path);item.store.enroll('voice-one','公开声纹',[1,0],consent=True,expected_revision=0)
    revision=item.store.revision
    monkeypatch.setattr(module,'voiced_pcm',lambda raw:(raw,{'vad_speech_seconds':3.}))
    result=item.analyze(meta(),pcm())
    assert result['state']=='CANDIDATE' and result['candidate_id']=='voice-one'
    assert result['single_speaker_verified'] is False and item.store.revision==revision
    assert item.store.people()==[{'person_id':'voice-one','display_name':'公开声纹'}]
    item.store.close()

def test_too_short_or_bad_speech_never_carries_old_identity(tmp_path,monkeypatch):
    import tools.speaker_device as module
    item=device(tmp_path);item.store.enroll('voice-one','公开声纹',[1,0],consent=True)
    def refuse(raw):raise ValueError('No voice')
    monkeypatch.setattr(module,'voiced_pcm',refuse)
    result=item.analyze(meta(),pcm())
    assert result['state']=='INSUFFICIENT_SPEECH' and result['candidate_id'] is None
    item.store.close()

@pytest.fixture
def hub():
    item=SimpleNamespace(speaker=SimpleNamespace(analyze=lambda *args:voice()),speaker_gate=threading.Lock(),
      speaker_pool=ThreadPoolExecutor(max_workers=1))
    try:yield item
    finally:item.speaker_pool.shutdown(wait=True)

def turn(service,owner,raw):
    service.submit(owner,raw,CID)
    wait(lambda:service.result(owner,CID)['status']!='PENDING')
    return service.result(owner,CID)

def test_three_distinct_calibrated_captures_produce_only_a_descriptive_candidate(hub):
    service=SpeakerTurns(hub)
    values=[turn(service,meta(i),pcm(i)) for i in (1,2,3)]
    assert [r['voice']['consecutive_distinct'] for r in values]==[1,2,3]
    assert values[-1]['voice']['state']=='CANDIDATE_STABLE'
    assert all(not r['personal_memory_allowed'] and r['relation']=='INDEPENDENT_EVIDENCE' for r in values)

def test_repeated_pcm_or_capture_replays_do_not_accumulate_identity(hub):
    service=SpeakerTurns(hub)
    for i,n in enumerate((1,2,1,1,1,2),1):
        raw=pcm(n);owner=meta(i,raw=raw)
        value=turn(service,owner,raw)
        assert value['voice']['state']=='CANDIDATE' and value['voice']['consecutive_distinct']<=2

def test_gallery_revision_or_uncertain_match_resets_continuity(hub):
    service=SpeakerTurns(hub);turn(service,meta(1),pcm(1));turn(service,meta(2),pcm(2))
    hub.speaker.analyze=lambda *args:voice(revision=2)
    assert turn(service,meta(3),pcm(3))['voice']['consecutive_distinct']==1
    hub.speaker.analyze=lambda *args:voice(state='UNKNOWN')
    assert turn(service,meta(4),pcm(4))['voice']['candidate_id'] is None
    hub.speaker.analyze=lambda *args:voice()
    assert turn(service,meta(5),pcm(5))['voice']['consecutive_distinct']==1

def test_cancel_and_expiry_drop_late_cpu_result(hub):
    gate=threading.Event();entered=threading.Event()
    def slow(*args):entered.set();gate.wait(.5);return voice()
    hub.speaker.analyze=slow;clock=[0.];service=SpeakerTurns(hub,clock=lambda:clock[0])
    try:
        service.submit(meta(),pcm(),CID);assert entered.wait(.2)
        value=service.cancel(meta(),CID);assert value['status']=='CANCELLED'
        gate.set();wait(lambda:not hub.speaker_gate.locked())
        assert service.result(meta(),CID)['voice'] is None
        gate.clear();entered.clear();service.submit(meta(2),pcm(2),CID);assert entered.wait(.2)
        clock[0]=20
        assert service.result(meta(2),CID)['status']=='EXPIRED'
        gate.set();wait(lambda:not hub.speaker_gate.locked())
        assert service.result(meta(2),CID)['voice'] is None
    finally:gate.set()

def test_cpu_busy_is_recorded_without_queueing_or_blocking_conversation(hub):
    service=SpeakerTurns(hub);hub.speaker_gate.acquire()
    try:
        value=service.submit(meta(),pcm(),CID)
        assert value['status']=='UNAVAILABLE' and value['reason']=='SPEAKER_WORKER_BUSY'
        assert service.health()['pending']==0
    finally:hub.speaker_gate.release()

def test_foreign_receipt_and_stale_generation_are_rejected(hub):
    service=SpeakerTurns(hub);turn(service,meta(2),pcm(2))
    with pytest.raises(ValueError):service.result(dict(meta(2),capture_id='other'),CID)
    with pytest.raises(ValueError):service.result(meta(2),'b'*32)
    with pytest.raises(ValueError):service.submit(meta(1),pcm(1),CID)

def test_buffer_is_bounded_and_contains_no_pcm_embedding_or_transcript(hub):
    hub.speaker=None;service=SpeakerTurns(hub)
    for i in range(300):service.submit(meta(i,session='s'+str(i)),pcm(i),CID)
    assert service.health()['buffered_results']==256
    assert all('pcm' not in row and 'embedding' not in row and 'text' not in row for row in service.rows.values())
