"""Real worker/original matcher with synthetic 192D encoder/PCM and fresh stores."""
import copy,hashlib,json,threading
import pytest
from composition import c

QUERY='你可以根据我的声音辨认我是谁吗'
PHASES={'IDLE','PROCESSING','UNAVAILABLE','NO_ENROLLMENT','COLLECTING','NO_CANDIDATE',
        'CANDIDATE','EXPIRED','SOURCE_CHANGED','CANCELLED','INSUFFICIENT_SPEECH'}

def saved(c):
    c.say('登记声纹，我叫合成测试')
    for i in range(3):c.say('合成独立登记段落'+str(i))
    c.say('确认保存声纹')
    assert c.voice_count()==1
    c.encoder.calls=0

def phase(c):return c.business.public()['self_match_probe']

def direct(c,meta=None,raw=None,text=QUERY,**kwargs):
    meta=meta or c.last_meta;raw=raw or c.last_raw
    value=c.business.turn(meta,text,raw,**kwargs)
    c.business.pool.submit(lambda:None).result(timeout=2)
    return value

def test_actual_yuki_three_queries_reuse_one_encoding_each_no_identity_or_links(c):
    saved(c)
    for i in range(1,4):
        latency,errors=c.say(QUERY)
        assert errors==[] and latency['error_class']=='none'
        assert c.encoder.calls==i and phase(c)['distinct_captures']==i
        assert phase(c)['phase']==('CANDIDATE' if i==3 else 'COLLECTING')
    assert '声音候选称呼是合成测试' in c.last_reply
    assert '对吗' not in c.last_reply
    assert c.business.public()['speaker_calibrated'] is False
    assert c.voice_count()==1 and c.business.hub.binding.registry.health()['active_people']==0
    cache=c.business.hub.binding.reused[c.business.hub.binding.key(c.last_meta)]
    assert cache['voice']['state']=='NOT_CALIBRATED' and cache['voice']['candidate_id'] is None
    assert '合成测试' not in json.dumps(cache,ensure_ascii=False)

@pytest.mark.parametrize('phrase',['查询我的声纹','声纹可用吗','声纹登记成功了吗','登记我的声纹','确认保存声纹'])
def test_original_readiness_save_and_enrollment_commands_do_not_start_probe(c,phrase):
    saved(c);c.say(phrase)
    assert c.encoder.calls==0 and phase(c)['phase']=='IDLE'

def test_empty_gallery_keeps_original_no_enrollment_no_encode(c):
    c.say(QUERY)
    assert c.encoder.calls==0 and phase(c)['phase']=='NO_ENROLLMENT'

def test_active_registration_query_does_not_consume_a_sample_or_probe(c):
    c.say('登记声纹，我叫合成测试');c.say(QUERY)
    assert c.row()['vectors']==[] and c.encoder.calls==0
    assert phase(c)['phase']=='IDLE'

def test_same_request_is_idempotent_and_expired_candidate_is_not_reissued(c):
    saved(c)
    for i in range(3):c.say(QUERY)
    result=direct(c)
    assert result==c.last_reply and c.encoder.calls==3
    c.mono.now+=2.01
    assert phase(c)['phase']=='EXPIRED'
    assert phase(c)['candidate_completed']==1 and phase(c)['completed_is_historical'] is True
    expired=direct(c)
    assert '合成测试' not in expired and c.encoder.calls==3 and phase(c)['phase']=='EXPIRED'
    assert phase(c)['candidate_completed']==1

def test_same_request_changed_text_or_pcm_is_refused_before_encoding(c):
    saved(c);c.say(QUERY)
    with pytest.raises(ValueError):direct(c,text='识别我的声音')
    changed=c.last_raw[:-2]+b'\0\0'
    with pytest.raises(ValueError):direct(c,raw=changed)
    assert c.encoder.calls==1

def test_same_pcm_new_requests_do_not_accumulate_distinct_captures(c):
    saved(c)
    for _ in range(3):c.say(QUERY,seed=100)
    assert phase(c)['phase']=='NO_CANDIDATE' and phase(c)['distinct_captures']==0
    matcher=c.business.hub.progressive_speaker.provisional
    assert len(next(iter(matcher.streaks.values()))['captures'])==1

def test_new_session_and_thirty_second_window_restart_original_streak(c):
    saved(c);c.say(QUERY);c.say(QUERY)
    c.mono.now+=30.01;c.say(QUERY)
    assert phase(c)['distinct_captures']==1
    c.runtime.jobs.select_conversation(resume=False)
    c.business.pool.submit(lambda:None).result(timeout=2)
    c.say(QUERY)
    assert phase(c)['distinct_captures']==1

def test_original_quality_failure_returns_instruction_without_encoding_or_count(c,monkeypatch):
    saved(c)
    def bad(raw):raise ValueError('synthetic quality refusal')
    monkeypatch.setattr(c.business,'quality',bad)
    c.say(QUERY)
    assert c.encoder.calls==0 and phase(c)['phase']=='INSUFFICIENT_SPEECH'
    assert '两点五秒' in c.last_reply and phase(c)['distinct_captures']==0

def test_unknown_match_never_produces_named_candidate(c,monkeypatch):
    saved(c)
    monkeypatch.setattr(c.encoder,'encode',lambda raw:(0.,1.)+(0.,)*190)
    for _ in range(3):c.say(QUERY)
    assert phase(c)['phase']=='NO_CANDIDATE' and '合成测试' not in c.last_reply

def test_original_ambiguity_rejects_named_candidate(c):
    saved(c)
    def add_other():
        store=c.business.hub.speaker.store.original
        store.enroll('synthetic-other','另一个合成称呼',(1.,)+(0.,)*191,consent=True,expected_revision=store.revision)
    c.business.pool.submit(add_other).result(timeout=2)
    for _ in range(3):c.say(QUERY)
    assert phase(c)['phase']=='NO_CANDIDATE' and '合成测试' not in c.last_reply

@pytest.mark.parametrize('change',['revision','template','name','model'])
def test_same_request_source_change_never_reuses_old_candidate_or_encodes_again(c,change):
    saved(c)
    for _ in range(3):c.say(QUERY)
    calls=c.encoder.calls
    def mutate():
        device=c.business.hub.speaker
        if change=='revision':device.store.db.execute("UPDATE metadata SET value=value+1 WHERE key='revision'")
        elif change=='template':device.store.db.execute('UPDATE templates SET embedding=?',(json.dumps((0.,1.)+(0.,)*190),))
        elif change=='name':device.store.db.execute('UPDATE identities SET name=?',('改动的合成称呼',))
        else:device.encoder.model_id='synthetic-model-changed'
        device.store.db.commit()
    c.business.pool.submit(mutate).result(timeout=2)
    value=direct(c)
    assert '合成测试' not in value and c.encoder.calls==calls and phase(c)['phase']=='SOURCE_CHANGED'

def test_new_query_source_revision_change_starts_from_one(c):
    saved(c);c.say(QUERY);c.say(QUERY)
    def mutate():
        db=c.business.hub.speaker.store.db
        db.execute("UPDATE metadata SET value=value+1 WHERE key='revision'");db.commit()
    c.business.pool.submit(mutate).result(timeout=2)
    c.say(QUERY)
    assert phase(c)['distinct_captures']==1

def test_none_original_turn_or_analyzer_never_creates_a_false_candidate(c,monkeypatch):
    saved(c)
    original=c.business.hub.speaker.turn
    monkeypatch.setattr(c.business.hub.speaker,'turn',lambda *a:None)
    c.say(QUERY)
    assert c.encoder.calls==0 and phase(c)['phase']=='UNAVAILABLE'
    monkeypatch.setattr(c.business.hub.speaker,'turn',original)
    monkeypatch.setattr(c.business.hub.progressive_speaker,'analyze',lambda *a,**k:None)
    c.say(QUERY)
    assert c.encoder.calls==0 and phase(c)['phase']=='UNAVAILABLE'

def test_cancel_after_original_observe_clears_capture_contribution(c,monkeypatch):
    saved(c);c.say(QUERY);c.say(QUERY)
    matcher=c.business.hub.progressive_speaker.provisional
    original=matcher.observe
    def cancel_after(*a,**k):
        result=original(*a,**k)
        c.runtime.jobs.cancel()
        return result
    monkeypatch.setattr(matcher,'observe',cancel_after)
    c.say(QUERY)
    assert not matcher.streaks and not matcher.results
    monkeypatch.setattr(matcher,'observe',original)
    c.say(QUERY)
    assert phase(c)['distinct_captures']==1

def test_public_metadata_is_fixed_private_data_free_and_copy_isolated(c):
    saved(c);c.say(QUERY)
    value=phase(c)
    assert set(value)=={'version','phase','distinct_captures','required_captures','candidate_completed',
                        'completed_is_historical','field_calibrated','identity_verified','personal_memory_allowed'}
    assert value['phase'] in PHASES and value['field_calibrated'] is False
    assert '合成测试' not in json.dumps(value,ensure_ascii=False)
    value['distinct_captures']=99
    assert phase(c)['distinct_captures']==1

def test_store_encoder_model_mismatch_cannot_form_a_new_candidate(c):
    saved(c)
    c.business.pool.submit(lambda:setattr(c.business.hub.speaker.encoder,'model_id','synthetic-foreign-model')).result(timeout=2)
    for _ in range(3):c.say(QUERY)
    assert c.encoder.calls==0 and phase(c)['phase']=='SOURCE_CHANGED'
    assert phase(c)['candidate_completed']==0

def test_cancel_during_original_inference_cannot_contribute_a_capture(c,monkeypatch):
    saved(c)
    entered=threading.Event();release=threading.Event();original=c.encoder.encode
    def blocked(raw):
        entered.set()
        assert release.wait(3)
        return original(raw)
    monkeypatch.setattr(c.encoder,'encode',blocked)
    failures=[]
    def say():
        try:c.say(QUERY)
        except BaseException as exc:failures.append(type(exc).__name__)
    thread=threading.Thread(target=say,daemon=True);thread.start()
    assert entered.wait(3)
    c.runtime.jobs.cancel();release.set();thread.join(4)
    assert not thread.is_alive() and not failures
    c.business.pool.submit(lambda:None).result(timeout=2)
    matcher=c.business.hub.progressive_speaker.provisional
    assert not matcher.streaks and not matcher.results
    assert phase(c)['phase']=='CANCELLED' and phase(c)['candidate_completed']==0
    monkeypatch.setattr(c.encoder,'encode',original)
    c.say(QUERY)
    assert phase(c)['distinct_captures']==1

@pytest.mark.parametrize('getter',['public','health'])
def test_actual_public_and_health_clock_failure_expires_metadata_but_worker_still_raises(c,monkeypatch,getter):
    from common.board_timeline_clock import ClockUnavailable
    saved(c)
    for _ in range(3):c.say(QUERY)
    failure=ClockUnavailable('synthetic fixed clock failure')
    def unavailable():raise failure
    monkeypatch.setattr(c.business,'wall_clock',unavailable)
    value=getattr(c.business,getter)()['self_match_probe']
    assert value['phase']=='EXPIRED' and value['candidate_completed']==1
    with pytest.raises(ClockUnavailable) as caught:direct(c)
    assert caught.value is failure

@pytest.mark.parametrize('getter',['public','health'])
def test_time_projection_calls_timeline_outside_service_lock_and_preserves_atomic_state(c,monkeypatch,getter):
    saved(c)
    for _ in range(3):c.say(QUERY)
    original=c.business.wall_clock;owned=[]
    def clock():
        owned.append(c.business.lock._is_owned())
        return original()
    monkeypatch.setattr(c.business,'wall_clock',clock)
    value=getattr(c.business,getter)()
    assert value['self_match_probe']['phase']=='CANDIDATE' and owned==[False]
    if getter=='health':assert value['queued_or_active']==0 and value['active'] is False
    c.mono.now+=2.01
    assert getattr(c.business,getter)()['self_match_probe']['phase']=='EXPIRED'

def test_capture_ledger_keeps_only_metadata_event_and_adoption_flag_without_pcm_or_closure(c):
    saved(c);c.say(QUERY)
    ledger=next(iter(c.business._probe_captures.values()))
    value=next(iter(ledger.values()))
    assert set(value)=={'meta','cancelled','adopted'} and value['adopted'] is True
    assert isinstance(value['cancelled'],threading.Event)
    assert not any(isinstance(item,(bytes,bytearray,memoryview)) for item in value['meta'].values())

def test_worker_complete_but_adopted_after_two_seconds_cannot_return_candidate_text(c,monkeypatch):
    saved(c);c.say(QUERY);c.say(QUERY)
    original=c.business._job_current;seen=[]
    capture='synthetic-clip-'+str(c.counter+1)
    def delayed(job):
        if (job['meta']['capture_id']==capture and threading.current_thread().name=='MainThread'
                and job.get('future') is not None and job['future'].done() and not seen):
            seen.append(True);c.mono.now+=2.01
        return original(job)
    monkeypatch.setattr(c.business,'_job_current',delayed)
    c.say(QUERY)
    assert seen and '合成测试' not in c.last_reply and '过期' in c.last_reply
    assert phase(c)['phase']=='EXPIRED' and phase(c)['candidate_completed']==0

@pytest.mark.parametrize('value',[None,{'original':'typed binding response'},'original unrelated reply'])
def test_non_probe_call_return_objects_are_never_changed_by_same_meta_probe_cache(c,value):
    saved(c)
    for _ in range(3):c.say(QUERY)
    c.mono.now+=2.01
    result=c.business._call(lambda raw:value,c.last_meta,c.last_raw)
    assert result is value
    assert phase(c)['candidate_completed']==1
