"""Read-only candidate review using fresh synthetic stores and real selected GUI path."""
import ast,json,math
import pytest
from base_composition import c,HERE,RELEASE
from recording_helpers import integration
from board.runtime.board_speaker_business import BoardSpeakerBusiness
from common.anonymous_voice import AnonymousPolicy
from common.speaker_identity import voiced_pcm

QUERY='你可以根据我的声音辨别我是谁吗'

def saved(c):
    c.say('登记声纹，我叫合成测试')
    for i in range(3):c.say('合成登记原三段'+str(i))
    c.say('确认保存声纹')
    assert c.voice_count()==1;c.encoder.calls=0

def set_score(c,score,monkeypatch):
    vector=(score,math.sqrt(1-score*score))+(0.,)*190
    def encode(raw):c.encoder.calls+=1;return vector
    monkeypatch.setattr(c.encoder,'encode',encode)

def test_actual_selected_gui_passes_035_into_real_device_store_and_public_values(c):
    def values():
        device=c.business.hub.speaker
        return device.threshold,device.store.threshold,device.margin,device.store.ambiguity_margin,device.consistency,device.calibrated
    assert c.business.pool.submit(values).result(timeout=2)==(.35,.35,.1,.1,.6,False)
    assert c.business.calibration==dict(threshold=.35,margin=.1,consistency=.6,field_calibrated=False)
    for state in (c.business.public(),c.business.health()):
        assert state['identity_match_threshold']==.35
        assert state['identity_ambiguity_margin']==.1 and state['enrollment_consistency']==.6
        assert state['speaker_calibrated'] is False and state['automatic_profile_access'] is False
    assert c.readback_verifications==[{'synthetic':True}]
    assert c.model_constructions==[dict(expected_manifest_sha256='0'*64,threads=1)]

@pytest.mark.parametrize('score',[.5,.7,.350001])
def test_newly_allowed_scores_still_require_three_distinct_real_worker_matches(c,monkeypatch,score):
    saved(c);set_score(c,score,monkeypatch)
    for count in (1,2,3):
        latency,errors=c.say(QUERY)
        assert errors==[] and latency['error_class']=='none'
        probe=c.business.health()['self_match_probe']
        assert probe['distinct_captures']==count and c.encoder.calls==count
        assert probe['phase']==('CANDIDATE' if count==3 else 'COLLECTING')
        assert probe['field_calibrated'] is False and probe['identity_verified'] is False
        assert probe['personal_memory_allowed'] is False
        if count<3:assert '声音候选称呼是' not in c.last_reply
    assert c.last_reply=='声音候选称呼是合成测试。完整现场校准尚未完成。'
    assert c.business.hub.binding.registry.health()['active_people']==0 and c.voice_count()==1

@pytest.mark.parametrize('score',[.34,.349999])
def test_score_below_user_threshold_stays_no_candidate(c,monkeypatch,score):
    saved(c);set_score(c,score,monkeypatch)
    for _ in range(3):c.say(QUERY)
    state=c.business.health()['self_match_probe']
    assert state['phase']=='NO_CANDIDATE' and state['candidate_completed']==0
    assert '合成测试' not in c.last_reply

@pytest.mark.parametrize('policy',[
 {'threshold':.34},{'threshold':float('nan')},{'threshold':True},
 {'threshold':.35,'margin':.09},{'threshold':.35,'consistency':.59},
 {'threshold':.35,'field_calibrated':True},
])
def test_new_floor_does_not_weaken_other_constructor_guards(c,tmp_path,policy):
    root=tmp_path/'synthetic-rejected-policy'
    with pytest.raises(ValueError):
        BoardSpeakerBusiness.create(root,encoder_factory=lambda:c.encoder,quality=voiced_pcm,
            board_boot_id='synthetic-boot',expected_model_id=c.encoder.model_id,
            clock=c.mono,wall_clock=c.timeline.event_time,data_origin='synthetic',calibration=policy)
    assert not root.exists()

def test_margin_01_still_rejects_two_above_threshold_nearby_identities(c,monkeypatch):
    saved(c)
    score=.5;second=.45;query=(score,math.sqrt(1-score*score))
    other=(second*query[0]-math.sqrt(1-second*second)*query[1],
           second*query[1]+math.sqrt(1-second*second)*query[0])+(0.,)*190
    def add():
        store=c.business.hub.speaker.store.original
        store.enroll('synthetic-second','合成另一人',other,consent=True,expected_revision=store.revision)
    c.business.pool.submit(add).result(timeout=2)
    set_score(c,score,monkeypatch)
    for _ in range(3):c.say(QUERY)
    assert c.business.health()['self_match_probe']['phase']=='NO_CANDIDATE'
    assert '合成测试' not in c.last_reply

def test_anonymous_clustering_default_and_floor_are_unmodified(c):
    assert c.business.hub.progressive_speaker.anonymous_store.policy.threshold==.9
    assert AnonymousPolicy().threshold==.9
    with pytest.raises(ValueError):AnonymousPolicy(threshold=.79)

def test_real_record_stream_ACK_rearm_chain_at_05_with_actual_gui_035(integration,monkeypatch):
    value=integration;set_score(value.base,.5,monkeypatch)
    for count in (1,2,3):
        reply,row=value.say(QUERY,100+count)
        assert row['reset_calls']==0 and row['distinct']==count
        assert row['after_rearm_phase']==('CANDIDATE' if count==3 else 'COLLECTING')
    assert value.base.encoder.calls==3 and '声音候选称呼是合成测试' in reply
    assert value.speaker.health()['identity_match_threshold']==.35

def test_low_threshold_does_not_make_repeated_PCM_three_distinct_matches(c,monkeypatch):
    saved(c);set_score(c,.5,monkeypatch)
    for _ in range(3):c.say(QUERY,seed=999)
    state=c.business.health()['self_match_probe']
    assert state['phase']!='CANDIDATE' and state['candidate_completed']==0
    assert len(next(iter(c.business.hub.progressive_speaker.provisional.streaks.values()))['captures'])==1

def test_shared_original_duplicate_voice_check_uses_035_without_adding_identity(c,monkeypatch):
    saved(c);set_score(c,.5,monkeypatch)
    c.say('登记声纹，我叫合成另一个')
    for index in range(3):c.say('合成新登记段落'+str(index))
    assert c.row()['stage']=='confirm'
    c.say('确认保存声纹')
    assert '已有声纹过于接近' in c.last_reply and c.voice_count()==1
    assert c.business.hub.binding.registry.health()['active_people']==0

def test_patch_scope_preserves_all_other_worker_logic_and_selected_GUI_guards():
    baseline=HERE.parent/'baseline_runtime'
    def functions(path,cls):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
        return {n.name:ast.dump(n,include_attributes=False) for n in node.body if isinstance(n,ast.FunctionDef)}
    old=functions(baseline/'board/runtime/board_speaker_business.py','BoardSpeakerBusiness')
    new=functions(RELEASE/'board/runtime/board_speaker_business.py','BoardSpeakerBusiness')
    assert old.keys()==new.keys()
    assert {name for name in old if old[name]!=new[name]}=={'__init__','_refresh_public','_self_match_query'}
    before=ast.parse((baseline/'tools/yuki_business_gui.py').read_text(encoding='utf-8'))
    after=ast.parse((RELEASE/'tools/yuki_business_gui.py').read_text(encoding='utf-8'))
    found=[]
    for node in ast.walk(after):
        if isinstance(node,ast.Call) and any(k.arg=='calibration' for k in node.keywords):
            found.append(node);node.keywords=[k for k in node.keywords if k.arg!='calibration']
    assert len(found)==1 and ast.dump(after,include_attributes=False)==ast.dump(before,include_attributes=False)
