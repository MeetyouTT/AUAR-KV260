"""Exact missing synonym through original fullYuki/real worker composition."""
import pytest
from composition import c,MODE
from common.feature_intents import speaker_text,speaker_query_requested
from board.runtime.board_speaker_business import BoardSpeakerBusiness

QUERIES=['你可以根据我的声音辨别我是谁吗','辨别我的声音']

def saved(c):
    c.say('登记声纹，我叫合成测试')
    for i in range(3):c.say('合成独立登记段落'+str(i))
    c.say('确认保存声纹')
    assert c.voice_count()==1;c.encoder.calls=0

@pytest.mark.parametrize('query',QUERIES)
def test_exact_synonym_baseline_misses_candidate_runs_three_original_matches(c,query):
    accepted=MODE=='candidate'
    assert speaker_query_requested(query) is accepted
    assert BoardSpeakerBusiness._explicit_self_match(query) is accepted
    assert speaker_text(query)==('查询我的声纹' if accepted else None)
    saved(c)
    for n in (1,2,3):
        latency,errors=c.say(query)
        assert errors==[] and latency['error_class']=='none'
        probe=c.business.health()['self_match_probe']
        if accepted:
            assert probe['distinct_captures']==n and c.encoder.calls==n
            assert probe['phase']==('CANDIDATE' if n==3 else 'COLLECTING')
        else:assert probe['phase']=='IDLE' and probe['candidate_completed']==0
    assert ('llm' in c.models.calls) is (not accepted)
    assert c.voice_count()==1 and c.business.hub.binding.registry.health()['active_people']==0
    assert c.business.public()['speaker_calibrated'] is False
    assert probe['identity_verified'] is False and probe['personal_memory_allowed'] is False
    if accepted:assert c.last_reply=='声音候选称呼是合成测试。完整现场校准尚未完成。'

@pytest.mark.parametrize('query',[
 '不要辨别我的声音','如果你可以根据我的声音辨别我是谁吗','你刚才说“辨别我的声音”',
 '怎么辨别我的声音','分辨我的声音','查询我的声纹','声纹可用吗',
])
def test_no_unrequested_alias_or_non_explicit_query_enters_probe(query):
    assert BoardSpeakerBusiness._explicit_self_match(query) is False
