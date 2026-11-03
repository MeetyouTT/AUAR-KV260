"""Natural explicit-fact answers, exact scope, history browsing and unknown writers."""
import io,json
from unittest.mock import patch
import pytest
from common.fact_answers import question
from common.memory_controls import parse
from common.timeline_conversations import TimelineConversationStore
from common.profile_memory import ProfileConversationStore
from test_controls import CID,OTHER,THIRD,NOW,DIGEST,command,turn,seq,exists

@pytest.fixture
def store(tmp_path):return TimelineConversationStore(tmp_path/'natural.db')
@pytest.mark.parametrize('text,key',[
 ('我喜欢什么颜色','颜色偏好'),('我最喜欢的颜色是什么','颜色偏好'),('你还记得我喜欢什么颜色吗','颜色偏好'),
 ('我的颜色偏好是什么','颜色偏好'),('我叫什么名字','称呼'),('我的名字是什么','称呼'),
 ('你应该怎么称呼我','称呼'),('我的项目叫什么','项目'),('我的项目名称是什么','项目')])
def test_exact_current_questions(text,key):assert question(text)['key']==key and question(text)['op']=='fact'
@pytest.mark.parametrize('text',[
 '如果我喜欢什么颜色你会怎么回答','他说我喜欢什么颜色','假装知道我的名字是什么',
 '“我喜欢什么颜色”是什么意思','我是谁','她喜欢什么颜色','我喜欢什么颜色，为什么','我的项目是做什么的',
 '我喜欢蓝色还是绿色','你喜欢什么颜色','我最喜欢什么颜色，顺便删除昨天的记录'])
def test_ambiguous_other_people_or_combined_questions_are_not_fast_paths(text):assert question(text) is None
@pytest.mark.parametrize('text',['我以前喜欢什么颜色','以前我最喜欢什么颜色','我之前叫什么名字','我的项目以前叫什么'])
def test_previous_questions_are_explicit_history(text):assert question(text)['op']=='history' and question(text)['previous']

def test_natural_fact_is_current_and_correction_forget_are_immediate(store):
    command(store,1,'记住：颜色=蓝色')
    _,reply=command(store,2,'我喜欢什么颜色');assert '蓝色' in reply
    command(store,3,'更正记忆：颜色=绿色')
    _,reply=command(store,4,'你还记得我喜欢什么颜色吗');assert '绿色' in reply and '蓝色' not in reply
    command(store,5,'忘记颜色的记忆')
    _,reply=command(store,6,'我喜欢什么颜色');assert '没有明确' in reply and '绿色' not in reply and '蓝色' not in reply

def test_guest_never_reads_another_conversation_or_personal_fact(store):
    profile=store.create_profile('A',consent=True)
    command(store,1,'记住：颜色=蓝色',profile=profile,cid=OTHER)
    command(store,2,'记住：颜色=红色',cid=THIRD)
    _,reply=command(store,3,'我喜欢什么颜色')
    assert '没有明确' in reply and '蓝色' not in reply and '红色' not in reply
    with pytest.raises(PermissionError):command(store,4,'我喜欢什么颜色',cid=OTHER)

def test_current_conversation_override_matches_ordinary_context(store):
    profile=store.create_profile('A',consent=True)
    command(store,1,'记住：颜色=蓝色',profile=profile)
    command(store,2,'记住本次对话：颜色=绿色',profile=profile)
    _,reply=command(store,3,'我喜欢什么颜色',profile=profile)
    assert '绿色' in reply and '蓝色' not in reply
    _,reply=command(store,4,'我的长期记忆里我喜欢什么颜色',profile=profile)
    assert '蓝色' in reply and '绿色' not in reply
    _,reply=command(store,5,'本次对话里我喜欢什么颜色',profile=profile)
    assert '绿色' in reply
    _,reply=command(store,6,'查看颜色记忆历史',profile=profile)
    assert '绿色' in reply and '蓝色' not in reply

def test_explicit_personal_query_requires_grant(store):
    command(store,1,'记住：颜色=绿色')
    _,reply=command(store,2,'我的长期记忆里我喜欢什么颜色')
    assert '选择个人档案' in reply and '绿色' not in reply

def test_indexed_history_returns_untruncated_explicit_value(store):
    long_value='这是一个没有省略的完整项目说明'+'甲'*35
    command(store,1,'记住：项目='+long_value,at=NOW-300)
    command(store,2,'更正记忆：项目=晨光',at=NOW-200)
    command(store,3,'更正记忆：项目=海风',at=NOW-100)
    _,reply=command(store,4,'查看项目第3条记忆历史')
    assert long_value in reply and '从新到旧' in reply and '旧值' in reply
    _,reply=command(store,5,'查看项目第1条记忆历史')
    assert '海风' in reply and '当前值' in reply
    _,reply=command(store,6,'查看项目第4条记忆历史')
    assert '没有找到' in reply
    command(store,7,'忘记项目的记忆')
    _,reply=command(store,8,'查看项目第3条记忆历史')
    assert long_value not in reply

@pytest.mark.parametrize('text',['查看记忆历史','查看全部记忆历史','查看颜色第0条记忆历史','查看颜色第33条记忆历史'])
def test_history_help_never_suggests_deletion(store,text):
    _,reply=command(store,1,text)
    assert '记忆历史' in reply and '删除' not in reply

def test_no_old_value_is_not_reported_as_previous(store):
    command(store,1,'记住：颜色=绿色')
    _,reply=command(store,2,'我以前喜欢什么颜色')
    assert '没有有效的旧值' in reply and '不能据此推断以前' in reply

def test_known_fact_bypasses_llm_and_volatile_cache(tmp_path):
    from tests.framework.test_long_conversation import host
    from tests.framework.test_voice_channel import VoiceChannelTests,owner
    from tools.voice_channel_source import channel_frames
    from common.voice_channel import read_frame
    models=host(tmp_path);models.conversations=TimelineConversationStore(tmp_path/'host.db')
    models.voice=VoiceChannelTests().fixture_models(tmp_path).voice
    command(models.conversations,1,'记住：颜色=绿色')
    def forbidden(*a,**kw):raise AssertionError('Fast fact accessed an unnecessary model/cache route')
    models.conversation_context=forbidden;models.history_for_stream=forbidden;models.history_with_preferences=forbidden
    models.latency_options={'reply_first':True,'reuse_history':True,'coalesce_chat':True}
    packets=list(channel_frames(models,owner('natural-2',2),'我喜欢什么颜色',5,model='test',host='unused',conversation=CID,stream_factory=forbidden))
    stream=io.BytesIO(b''.join(packets));rows=[]
    while stream.tell()<len(stream.getvalue()):rows.append(read_frame(stream)[0])
    end=next(r for r in rows if r['kind']=='end')
    assert '绿色' in end['reply_text'] and end['timing']['memory_command'] and end['timing']['history_messages']==0

def test_fact_query_cannot_ack_after_correction(store):
    command(store,1,'记住：颜色=蓝色')
    meta,reply=command(store,2,'我喜欢什么颜色')
    store.generated(meta,reply,480,DIGEST)
    command(store,3,'更正记忆：颜色=绿色')
    with pytest.raises(ValueError):store.played(meta,480,DIGEST)

def test_unknown_writer_after_upgrade_is_still_protected(store):
    old=ProfileConversationStore(store.path)
    original=turn(old,1,'杯子在左边',at=NOW-86400,played=True)
    later=turn(old,2,'刚才的位置',at=NOW-100,played=True,reply='在左侧')
    # legacy_cutoff was zero when the new store was created. New untracked rows
    # must not be assumed covered just because their sequence is newer.
    command(store,3,'删除昨天关于杯子的对话记录')
    command(store,4,'确认删除这些对话记录',at=NOW+1)
    assert exists(store,later) and not exists(store,original) and not store.records(CID)

def test_unknown_profile_reply_across_conversation_is_withheld(store):
    profile=store.create_profile('A',consent=True)
    old=ProfileConversationStore(store.path)
    original=turn(old,1,'杯子左边',at=NOW-86400,profile=profile,played=True)
    later=turn(old,2,'在哪里',at=NOW-100,profile=profile,cid=OTHER,played=True,reply='左边')
    command(store,3,'删除昨天关于杯子的对话记录',profile=profile)
    command(store,4,'确认删除这些对话记录',profile=profile,at=NOW+1)
    assert exists(store,later) and not exists(store,original) and not store.records(OTHER,profile=profile)

def test_explicit_zero_source_coverage_preserves_independent_reply(store):
    original=turn(store,1,'杯子左边',at=NOW-86400,played=True)
    independent=turn(store,2,'新话题',at=NOW-100,played=True,reply='今天聊音乐')
    store.attach_sources(independent,[],mark_complete=True)
    command(store,3,'删除昨天关于杯子的对话记录')
    command(store,4,'确认删除这些对话记录',at=NOW+1)
    assert not exists(store,original) and [r['request_id'] for r in store.records(CID)]==[independent['request_id']]

def test_actual_host_marks_zero_source_coverage(tmp_path):
    from tests.framework.test_long_conversation import host
    from tests.framework.test_voice_channel import owner
    models=host(tmp_path);models.conversations=TimelineConversationStore(tmp_path/'coverage.db')
    meta=owner('empty-snapshot',1);models.begin_conversation(meta,CID,'你好','你好');models.conversation_context(meta,'你好')
    with models.conversations._connect() as db:
        assert db.execute('SELECT version FROM memory_source_coverage WHERE seq=?',(seq(models.conversations,meta),)).fetchone()[0]==1

def test_history_previous_does_not_change_current_recall(store):
    command(store,1,'记住：颜色=蓝色')
    command(store,2,'更正记忆：颜色=绿色')
    _,reply=command(store,3,'我以前喜欢什么颜色')
    assert '蓝色' in reply and '绿色' in reply
    _,reply=command(store,4,'我喜欢什么颜色')
    assert '绿色' in reply and '蓝色' not in reply

@pytest.mark.parametrize('word,number',[('一',1),('二',2),('两',2),('十',10),('十一',11),('二十',20),('二十三',23),('三十',30),('三十二',32),('３',3)])
def test_spoken_history_ordinals(word,number):
    request=parse('查看颜色第'+word+'条记忆历史')
    assert request['op']=='history' and request['index']==number

@pytest.mark.parametrize('word',['0','33','三十三','一一','十十'])
def test_invalid_history_ordinals_are_help(word):
    assert parse('查看颜色第'+word+'条记忆历史')['op']=='history_help'

def test_chinese_ordinal_returns_full_requested_record(store):
    command(store,1,'记住：颜色=蓝色')
    command(store,2,'更正记忆：颜色=绿色')
    _,reply=command(store,3,'查看颜色第二条记忆历史')
    assert '蓝色' in reply and '绿色' not in reply

