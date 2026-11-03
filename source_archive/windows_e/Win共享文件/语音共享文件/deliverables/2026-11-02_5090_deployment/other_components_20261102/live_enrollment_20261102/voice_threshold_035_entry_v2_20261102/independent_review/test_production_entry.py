"""Focused actual-production-override test, not another candidate GUI test."""
import ast,math,os
from base_composition import c,RELEASE
from tools.production_board_business_gui import ProductionGuiBoardBusiness,prepare_board_business
from tools.board_business_gui import GuiBoardBusiness

EXPECTED=float(os.environ['AURA_EXPECTED_THRESHOLD'])

def test_actual_factory_and_override_are_not_the_base_or_yuki_method(monkeypatch):
    seen=[]
    def init(self,*args):seen.append((type(self),args))
    monkeypatch.setattr(ProductionGuiBoardBusiness,'__init__',init)
    args=(object(),object(),object())
    gui=prepare_board_business(*args)
    assert type(gui) is ProductionGuiBoardBusiness and seen==[(ProductionGuiBoardBusiness,args)]
    assert issubclass(ProductionGuiBoardBusiness,GuiBoardBusiness)
    assert ProductionGuiBoardBusiness._attach_speaker is not GuiBoardBusiness._attach_speaker
    tree=ast.parse((RELEASE/'tools/board_avatar_gtk.py').read_text(encoding='utf-8'))
    imports=[node.module for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)
             and any(x.name=='prepare_board_business' for x in node.names)]
    assert 'tools.production_board_business_gui' in imports
    assert 'tools.yuki_business_gui' not in imports

def test_real_production_override_actual_device_store_and_public_threshold(c):
    def props():
        d=c.business.hub.speaker
        return d.threshold,d.store.threshold,d.margin,d.store.ambiguity_margin,d.consistency,d.calibrated
    assert type(c.gui) is ProductionGuiBoardBusiness
    assert c.business.pool.submit(props).result(timeout=2)==(EXPECTED,EXPECTED,.1,.1,.6,False)
    for state in (c.business.public(),c.business.health()):
        assert state['identity_match_threshold']==EXPECTED
        assert state['identity_ambiguity_margin']==.1 and state['enrollment_consistency']==.6
        assert state['speaker_calibrated'] is False and state['automatic_profile_access'] is False
    assert c.business.hub.progressive_speaker.anonymous_store.policy.threshold==.9
    assert c.model_constructions==[dict(expected_manifest_sha256='0'*64,threads=1)]
    assert c.readback_verifications==[{'synthetic':True}]

def test_three_distinct_05_queries_through_production_override(c,monkeypatch):
    c.say('登记声纹，我叫合成测试')
    for i in range(3):c.say('合成登记原三段'+str(i))
    c.say('确认保存声纹')
    assert c.voice_count()==1
    c.encoder.calls=0
    def encode(raw):
        c.encoder.calls+=1
        return (.5,math.sqrt(.75))+(0.,)*190
    monkeypatch.setattr(c.encoder,'encode',encode)
    for count in (1,2,3):
        latency,errors=c.say('你可以根据我的声音辨别我是谁吗')
        assert errors==[] and latency['error_class']=='none' and c.encoder.calls==count
        state=c.business.health()['self_match_probe']
        if EXPECTED==.35:
            assert state['distinct_captures']==count
            assert state['phase']==('CANDIDATE' if count==3 else 'COLLECTING')
        else:
            assert EXPECTED==.8 and state['phase']=='NO_CANDIDATE'
        assert state['field_calibrated'] is False and state['identity_verified'] is False
        assert state['personal_memory_allowed'] is False
    assert c.business.hub.binding.registry.health()['active_people']==0
    assert c.voice_count()==1
    if EXPECTED==.35:assert c.last_reply=='声音候选称呼是合成测试。完整现场校准尚未完成。'
    else:assert '合成测试' not in c.last_reply
