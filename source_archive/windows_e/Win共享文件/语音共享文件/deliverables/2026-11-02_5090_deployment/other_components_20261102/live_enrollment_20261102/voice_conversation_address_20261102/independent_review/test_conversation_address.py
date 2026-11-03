"""Independent full-composition tests. All audio/models/databases are synthetic."""
import copy,hashlib,json,math,struct,threading,time,uuid
from types import SimpleNamespace
import pytest
from base_composition import c,RELEASE
from board.runtime.board_memory_policy import BoardContextBuilder,message_cost
from common.asr_wire import PROTOCOL
from recording_helpers import integration

NAME='合成测试'
STATEMENT='今天的天气很好，我想跟你聊聊最近的计划。'
SHORT=struct.pack('<h',1234)*8000

def saved(c):
    c.say('登记声纹，我叫'+NAME)
    for i in range(3):c.say('合成原登记三段'+str(i))
    c.say('确认保存声纹')
    assert c.voice_count()==1
    c.encoder.calls=0;c.models.calls.clear();c.models.requests.clear()

def messages(c):
    return [p['messages'] for k,p in c.models.requests if k=='llm'][-1]

def hint(c):
    notes=[m['content'] for m in messages(c) if '当前对话的声纹称呼候选' in m['content']]
    assert len(notes)==1
    raw=notes[0].split('：',1)[1]
    return json.JSONDecoder().raw_decode(raw)[0]['display_name']

def score(c,monkeypatch,value):
    def encode(raw):
        c.encoder.calls+=1
        return (value,math.sqrt(1-value*value))+(0.,)*190
    monkeypatch.setattr(c.encoder,'encode',encode)

def bare_analysis(c,*,seed=77,generation=300,wait=True):
    raw=struct.pack('<h',seed)*48000
    meta=dict(protocol=PROTOCOL,board_boot_id=c.runtime.boot_id,session_id=c.runtime.jobs.session_id,
        request_id=uuid.uuid4().hex,generation=generation,capture_id='synthetic-address-'+str(seed),
        sample_count=48000,pcm_sha256=hashlib.sha256(raw).hexdigest(),budget_ms=120000)
    cid=c.runtime.jobs.conversation_selection.active;event=threading.Event()
    c.business.submit_analysis(meta,raw,cid,cancel_event=event,is_current=lambda:not event.is_set(),deadline=c.mono()+120)
    if wait:c.business.pool.submit(lambda:None).result(timeout=2)
    return meta,cid,event,raw

def owner(meta):return {k:meta[k] for k in ('board_boot_id','session_id','generation','request_id')}

def test_real_production_first_ordinary_statement_uses_one_encode_and_one_named_match(c,monkeypatch):
    saved(c);calls=[]
    original=c.business.hub.speaker.store.match
    def match(vector):calls.append(1);return original(vector)
    monkeypatch.setattr(c.business.hub.speaker.store,'match',match)
    metrics,errors=c.say(STATEMENT)
    assert errors==[] and metrics['error_class']=='none'
    assert type(c.gui).__name__=='ProductionGuiBoardBusiness'
    assert c.encoder.calls==1 and len(calls)==1 and hint(c)==NAME
    state=c.business.health()['conversation_address']
    assert state['required_captures']==1 and state['matched_captures']==1 and state['session_cached']
    assert state['field_calibrated'] is False and state['identity_verified'] is False
    assert state['personal_memory_allowed'] is False
    assert c.business.hub.binding.registry.health()['active_people']==0
    assert c.business.health()['identity_match_threshold']==.35

def test_followup_uses_cached_name_while_new_encoder_is_still_pending(c,monkeypatch):
    saved(c);c.say(STATEMENT)
    entered=threading.Event();release=threading.Event();llm=threading.Event()
    original=c.encoder.encode;request=c.models.request
    def blocked(raw):entered.set();assert release.wait(3);return original(raw)
    def record(kind,payload,**kw):
        value=request(kind,payload,**kw)
        if kind=='llm':llm.set()
        return value
    monkeypatch.setattr(c.encoder,'encode',blocked);monkeypatch.setattr(c.models,'request',record)
    failures=[]
    def run():
        try:c.say('接着聊刚才的计划吧。')
        except BaseException as exc:failures.append(exc)
    t=threading.Thread(target=run);t.start()
    try:
        assert entered.wait(2) and llm.wait(2)
        assert hint(c)==NAME
    finally:release.set();t.join(3)
    assert not t.is_alive() and not failures

@pytest.mark.parametrize('query',['你知道我是谁吗','我是谁','你还记得我是谁吗','你可以根据我的声音辨别我是谁吗','辨别我的声音'])
def test_daily_identity_query_first_turn_uses_ordinary_context_not_face_or_three_probe(c,query):
    saved(c);metrics,errors=c.say(query)
    assert errors==[] and metrics['error_class']=='none' and c.encoder.calls==1
    assert hint(c)==NAME and c.models.calls.count('llm')==1
    assert c.business.health()['self_match_probe']['candidate_completed']==0
    assert c.runtime.identity_handler.flow.public()['active'] is False

def test_first_short_sentence_stays_normal_then_next_valid_sentence_acquires_name(c):
    saved(c);_,errors=c.say('你好。',pcm=SHORT)
    assert errors==[] and c.encoder.calls==0 and hint(c) is None
    c.say(STATEMENT)
    assert c.encoder.calls==1 and hint(c)==NAME

def test_short_followup_keeps_adopted_name(c):
    saved(c);c.say(STATEMENT);calls=c.encoder.calls
    c.say('好的。',pcm=SHORT)
    assert c.encoder.calls==calls and hint(c)==NAME

def test_effective_unknown_clears_for_next_context(c,monkeypatch):
    saved(c);c.say(STATEMENT);score(c,monkeypatch,.34)
    c.say('换一段有效的合成语音。')
    assert c.business.health()['conversation_address']['session_cached'] is False
    c.say('继续。',pcm=SHORT)
    assert hint(c) is None

def test_ambiguous_first_capture_does_not_produce_name(c,monkeypatch):
    saved(c)
    q=(.5,math.sqrt(.75));second=.45
    v=(second*q[0]-math.sqrt(1-second*second)*q[1],second*q[1]+math.sqrt(1-second*second)*q[0])+(0.,)*190
    def add():
        # Synthetic fixture construction, not an enrollment behavior shortcut.
        # The original production write guard remains unchanged and exercised
        # by saved(c)'s actual three samples plus final confirmation.
        store=c.business.hub.speaker.store.original
        store.enroll('synthetic-other','合成其他人',v,consent=True,expected_revision=store.revision)
    c.business.pool.submit(add).result(timeout=2)
    score(c,monkeypatch,.5);c.say(STATEMENT)
    assert hint(c) is None and c.business.health()['conversation_address']['phase']=='NO_MATCH'

def test_reset_synchronously_clears_lease_and_short_capture_does_not_restore(c):
    saved(c);c.say(STATEMENT);assert c.business._address_leases
    c.business.reset();assert not c.business._address_leases
    c.business.pool.submit(lambda:None).result(timeout=2)
    c.say('重新你好。',pcm=SHORT)
    assert hint(c) is None

def test_select_new_conversation_resets_name(c):
    saved(c);c.say(STATEMENT)
    c.runtime.jobs.select_conversation(resume=False)
    c.business.pool.submit(lambda:None).result(timeout=2)
    c.say('新的对话。',pcm=SHORT)
    assert hint(c) is None

def test_foreign_conversation_id_cannot_read_name(c):
    saved(c);c.say(STATEMENT)
    assert c.business.conversation_address(owner(c.last_meta),'f'*32,cancel_event=threading.Event(),deadline=c.mono()+10) is None

def test_profile_context_does_not_call_address_provider(c,monkeypatch):
    def forbidden(turn):pytest.fail('profile must never read conversational voice hint')
    monkeypatch.setattr(c.runtime.controller,'speaker_address_provider',forbidden)
    raw={'messages':[dict(role='user',content='合成普通输入')]}
    assert c.runtime.controller._address_context(raw,SimpleNamespace(scope={'kind':'profile'})) is raw

def test_cancel_after_worker_complete_before_adoption_never_creates_lease(c):
    saved(c);meta,cid,event,raw=bare_analysis(c)
    assert c.business.analysis_result(meta,cid)['status']=='COMPLETE'
    event.set()
    assert not c.business.adopt_conversation_address(meta,cid,cancel_event=event)
    assert not c.business._address_leases

def test_analysis_retry_does_not_encode_again(c):
    saved(c);meta,cid,event,raw=bare_analysis(c)
    assert c.encoder.calls==1
    c.business.submit_analysis(meta,raw,cid,cancel_event=event)
    assert c.encoder.calls==1

def test_template_deletion_invalidates_cached_address(c):
    saved(c);c.say(STATEMENT)
    def delete():
        # Synthetic external-source change fixture on the sole SQLite owner.
        store=c.business.hub.speaker.store.original
        store.delete(store.people()[0]['person_id'],expected_revision=store.revision)
        c.business._refresh_public()
    c.business.pool.submit(delete).result(timeout=2)
    c.say('继续正常聊。',pcm=SHORT)
    assert hint(c) is None

@pytest.mark.parametrize('attribute,value',[('model_id','synthetic-different-model'),('dimension',193)])
def test_model_or_dimension_mismatch_does_not_adopt_old_store_name(c,monkeypatch,attribute,value):
    saved(c)
    # The production _GuardedEncoder pins its public model/dimension when it
    # wraps the synthetic IO encoder. Change those canonical device fields;
    # relabeling only the inner IO object does not change the declared model.
    monkeypatch.setattr(c.business.hub.speaker.encoder,attribute,value)
    c.say(STATEMENT)
    assert hint(c) is None

def test_context_note_stays_inside_original_context_limit(c):
    saved(c)
    builder=BoardContextBuilder('合成人格。')
    text='合成内容'*120
    original=builder({},text)
    assert 1600<message_cost(original,builder.reserve)<=builder.maximum
    result=builder({'conversation_address':dict(display_name=NAME)},text)
    assert message_cost(result,builder.reserve)<=builder.maximum
    assert result[-1]['content']==text and builder.metrics['conversational_address'] is False

def test_small_context_includes_budgeted_address_and_explicit_history_excludes_it():
    builder=BoardContextBuilder('合成人格。')
    context={'conversation_address':dict(display_name=NAME)}
    result=builder(context,'聊聊计划。')
    assert builder.metrics['conversational_address'] is True and message_cost(result,builder.reserve)<=2048
    history=dict(items=[],status=dict(boundary_incomplete=True,result_limited=True))
    with_address=builder(context,'之前的记录呢？',history)
    without_address=builder({},'之前的记录呢？',history)
    assert with_address==without_address and builder.metrics['conversational_address'] is False

def test_actual_recording_stream_ACK_rearm_first_statement_gets_name_and_keeps_it(integration):
    value=integration
    for index in (1,2):
        _,row=value.say(STATEMENT,index+80)
        assert row['reset_calls']==0 and row['committed']
        assert hint(value.base)==NAME
    assert value.base.encoder.calls==2
    assert value.speaker.health()['conversation_address']['session_cached']

def test_cancel_during_actual_encoder_prevents_lease(c,monkeypatch):
    saved(c);entered=threading.Event();release=threading.Event();original=c.encoder.encode
    def block(raw):entered.set();assert release.wait(3);return original(raw)
    monkeypatch.setattr(c.encoder,'encode',block)
    failures=[]
    def run():
        try:c.say(STATEMENT)
        except BaseException as exc:failures.append(exc)
    t=threading.Thread(target=run);t.start()
    try:
        assert entered.wait(2)
        c.runtime.jobs.cancel()
    finally:release.set();t.join(3)
    assert not t.is_alive() and not c.business._address_leases

def test_reset_during_actual_encoder_prevents_late_lease(c,monkeypatch):
    saved(c);entered=threading.Event();release=threading.Event();original=c.encoder.encode
    def block(raw):entered.set();assert release.wait(3);return original(raw)
    monkeypatch.setattr(c.encoder,'encode',block)
    failures=[]
    def run():
        try:c.say(STATEMENT)
        except BaseException as exc:failures.append(exc)
    t=threading.Thread(target=run);t.start()
    try:
        assert entered.wait(2);c.business.reset()
    finally:release.set();t.join(3)
    assert not t.is_alive() and not c.business._address_leases

def test_old_completed_packet_cannot_adopt_after_new_owner_adopts(c):
    saved(c);old,cid,event,_=bare_analysis(c,seed=77,generation=300)
    new,_,new_event,_=bare_analysis(c,seed=78,generation=301)
    assert c.business.adopt_conversation_address(new,cid,cancel_event=new_event)
    before=copy.deepcopy(c.business._address_leases)
    assert not c.business.adopt_conversation_address(old,cid,cancel_event=event)
    assert c.business._address_leases==before

def test_packet_expiry_and_adopted_lease_expiry_fail_closed(c):
    saved(c);meta,cid,event,_=bare_analysis(c)
    c.mono.now+=21
    assert not c.business.adopt_conversation_address(meta,cid,cancel_event=event)
    assert not c.business._address_leases
    meta,_,event,_=bare_analysis(c,seed=78,generation=301)
    assert c.business.adopt_conversation_address(meta,cid,cancel_event=event)
    c.mono.now+=301
    assert c.business.conversation_address(owner(meta),cid,cancel_event=event,deadline=c.mono()+10) is None

def test_original_registration_requires_three_samples_and_final_confirmation(c):
    c.say('登记声纹，我叫'+NAME)
    assert c.voice_count()==0 and c.row()['stage']=='samples'
    for i in range(3):
        c.say('合成登记独立段'+str(i))
        assert c.voice_count()==0
    assert c.row()['stage']=='confirm'
    c.say('确认保存声纹')
    assert c.voice_count()==1

def test_identity_query_during_active_registration_does_not_consume_sample(c):
    c.say('登记声纹，我叫'+NAME);c.say('合成第一段。')
    before=c.encoder.calls
    c.say('你知道我是谁吗')
    assert c.encoder.calls==before and len(c.row()['vectors'])==1

def test_public_metadata_and_private_cache_do_not_retain_audio_or_closures(c):
    saved(c);c.say(STATEMENT)
    for data in (c.business.public(),c.business.health()):
        assert NAME not in json.dumps(data,ensure_ascii=False)
    def check(value):
        assert not isinstance(value,(bytes,bytearray,memoryview))
        assert not callable(value)
        if isinstance(value,dict):
            assert not set(value)&{'pcm','embedding','vector','job','is_current'}
            for v in value.values():check(v)
        elif isinstance(value,(tuple,list)):
            for v in value:check(v)
    check(c.business._address_pending);check(c.business._address_leases)

@pytest.mark.parametrize('ending',['cancel','analysis_deadline'])
def test_first_address_wait_exits_on_cancel_or_original_analysis_deadline(c,monkeypatch,ending):
    saved(c);entered=threading.Event();release=threading.Event();original=c.encoder.encode
    def blocked(raw):entered.set();assert release.wait(3);return original(raw)
    monkeypatch.setattr(c.encoder,'encode',blocked)
    meta,cid,event,_=bare_analysis(c,wait=False)
    assert entered.wait(2)
    replies=[];failures=[]
    def read():
        try:replies.append(c.business.conversation_address(owner(meta),cid,cancel_event=event,deadline=c.mono()+120))
        except BaseException as exc:failures.append(exc)
    t=threading.Thread(target=read);t.start()
    try:
        time.sleep(.03)
        if ending=='cancel':event.set()
        else:c.mono.now+=13
        t.join(.5)
        assert not t.is_alive() and replies==[None] and not failures
        if ending=='analysis_deadline':
            assert event.is_set() and c.business.analysis_result(meta,cid)['status']=='EXPIRED'
        assert not c.business._address_leases
    finally:
        event.set();release.set();t.join(2)
        c.business.pool.submit(lambda:None).result(timeout=2)
