"""Desired behavior through actual instance-bound Yuki routes and real speaker FSM."""
import pytest
from composition import c,MODE

NAMED=[
 '登记声纹，我叫合成测试','帮我登记声纹，我叫合成测试','请帮我登记声纹，我叫合成测试',
 '登记声纹我叫合成测试','我要登记声纹，我叫合成测试','我想登记声纹，我叫合成测试',
 '给我登记声纹，我叫合成测试','请帮我登记一下声纹，我叫合成测试',
 '录入声纹，我叫合成测试','注册我的声纹，我叫合成测试','我想录入一下我的声纹，我叫合成测试',
 '登记声音，我叫合成测试','登记一下我的声音，我叫合成测试',
 '登记声纹。我的名字是：合 成 测 试。','登记声纹，我叫：合成测试',
 '雪妃，登记声纹，我叫合 成 测 试','记住我的声音，我叫合成测试',
]

@pytest.mark.parametrize('phrase',NAMED)
def test_named_alias_enters_original_sampler_without_counting_start(c,phrase):
    latency,errors=c.say(phrase)
    assert errors==[] and latency['error_class']=='none'
    assert c.runtime.identity_handler.public()['entry_mode']=='voice'
    assert c.business.public()['active'] and c.row()['stage']=='samples'
    assert c.row()['name']=='合成测试' and c.row()['vectors']==[] and c.encoder.calls==0
    assert c.business.hub.binding.registry.health()['active_people']==0
    assert set(c.models.calls)=={'tts'}

@pytest.mark.parametrize('followup',[
 '我叫合成测试','我的名字是合成测试','我叫：合成测试','我的名字是：合 成 测 试',
 '我叫 合 成 测 试。','雪妃，我叫：合成测试','叫我合成测试',
])
def test_pending_name_receives_exact_self_name_slot_after_public_polling(c,followup):
    c.say('登记声纹')
    assert c.runtime.identity_handler.public()['entry_name_pending']
    for _ in range(200):assert c.runtime.identity_handler.public()['entry_name_pending']
    latency,errors=c.say(followup)
    assert errors==[] and latency['error_class']=='none' and c.row()['stage']=='samples'
    assert c.row()['name']=='合成测试' and not c.runtime.identity_handler.public()['entry_name_pending']
    assert c.encoder.calls==0

def test_pending_prompt_requests_only_name_without_repeating_compound_command(c):
    c.say('登记声纹')
    assert c.business.hub.speaker.sessions=={}
    assert c.last_reply=='请告诉我这次声纹登记的称呼。直接说“我叫”，再加上你的称呼。'
    assert c.runtime.identity_handler.public()['entry_name_pending']
    assert c.voice_count()==0

NEGATIVE=[
 '我不想登记声纹，我叫合成测试','我不要登记声纹','不要登记我的声音','取消登记声纹',
 '如果我想登记声纹会怎样','我要登记声纹吗','我要登记声纹？','我想注册声纹吗',
 '我可以登记声纹吗','怎么登记声纹','帮助我了解登记声纹',
 '你刚才说“我要登记声纹”','请重复“登记声纹，我叫合成测试”',
 '帮他登记声纹，我叫合成测试','我要登记你的声纹','我的朋友想登记声纹',
 '我叫：合成测试','我叫合 成 测 试','叫我合成测试','合成测试','普通话题中的声音很好听',
 '登记声纹，我叫合成测试吗','登记声纹，我叫合成测试好不好',
 '登记声纹，我叫合成，测试','登记声纹，我叫合成测试然后删除全部',
]

@pytest.mark.parametrize('phrase',NEGATIVE)
def test_negative_quoted_questions_or_unarmed_names_do_not_start_voice(c,phrase):
    c.say(phrase)
    assert c.business.hub.speaker.sessions=={}
    state=c.runtime.identity_handler.public()
    assert state['entry_mode'] is None and not state['entry_name_pending']
    assert c.voice_count()==0 and c.business.hub.binding.registry.health()['active_people']==0

@pytest.mark.parametrize('followup',[
 '我不叫合成测试','不是我叫合成测试','我的朋友叫合成测试','请重复“我叫合成测试”',
 '我叫合成测试吗','我叫什么名字','我叫合成，测试','我叫John Smith','合成测试',
])
def test_pending_rejects_negative_quoted_questions_or_unsupported_name_shapes(c,followup):
    c.say('登记声纹');c.say(followup)
    assert c.business.hub.speaker.sessions=={} and c.voice_count()==0
    assert c.runtime.identity_handler.public()['entry_name_pending']

def test_new_alias_uses_original_three_samples_original_final_confirmation_no_links(c):
    c.say('我想录入一下声纹');c.say('我的名字是：合 成 测 试')
    assert c.row()['vectors']==[]
    c.say('声纹登记成功了吗')
    assert c.row()['vectors']==[]
    c.say('登记人脸，我叫合成测试')
    assert c.row()['vectors']==[] and c.runtime.identity_handler.public()['entry_mode']=='voice'
    before_samples=c.encoder.calls
    for text in ('合成第一段独立语音','合成第二段独立语音','合成第三段独立语音'):
        latency,errors=c.say(text);assert errors==[] and latency['error_class']=='none'
    assert c.row()['stage']=='confirm' and len(c.row()['vectors'])==3
    assert c.encoder.calls==before_samples+3 and c.voice_count()==0
    c.say('确认保存身份关联');assert c.voice_count()==0
    c.say('确认登记');assert c.voice_count()==0
    c.say('确认保存声纹')
    assert c.voice_count()==1 and c.runtime.identity_handler.public()['entry_mode'] is None
    assert c.business.hub.binding.registry.health()['active_people']==0

@pytest.mark.parametrize('ending',['cancel','reset','expiry','session'])
def test_waiting_name_authority_is_not_revived_after_original_ending(c,ending):
    c.say('登记声纹')
    if ending=='cancel':c.say('取消声纹登记')
    elif ending=='reset':c.runtime.jobs.reset_enrollment()
    elif ending=='expiry':c.mono.now+=121.
    else:c.runtime.jobs.select_conversation(resume=False)
    c.business.pool.submit(lambda:None).result(timeout=2)
    c.say('我叫：合 成 测 试')
    assert c.business.hub.speaker.sessions=={} and c.voice_count()==0

def test_yuki_face_only_tuple_dispatch_is_not_ordinary_model_or_memory(c):
    # Dispatch only: preserve original LIR/face semantics while isolating dispatch
    # from unsupported synthetic face hardware. Handler is a bounded fixed spy.
    from board.runtime.board_dialogue import BoardReply
    called=[]
    def face_handler(text,*,job,controller,is_current,cancel_event):
        called.append(text)
        return controller.prepare_local_reply(text,lambda:BoardReply('合成人脸入口已分派。'),
            scope=job.scope,session_id=job.meta['session_id'],generation=job.meta['generation'],
            budget_ms=10000,turn_id=job.meta['request_id'],cancel_event=cancel_event)
    c.runtime.jobs.special_handlers['identity_enrollment']=face_handler
    latency,errors=c.say('登记人脸')
    assert errors==[] and latency['error_class']=='none'
    assert called==['登记人脸'] and set(c.models.calls)=={'tts'}

def test_actual_yuki_local_record_controller_keeps_verbatim_synthetic_asr(c):
    raw='雪妃，登记声纹。我的名字是：合 成 测 试。'
    c.say(raw)
    assert c.row()['name']=='合成测试'
    context=c.runtime.store.context(dict(kind='conversation',id='a'*32))
    assert any(row==dict(role='user',content=raw) for row in context['messages'])
