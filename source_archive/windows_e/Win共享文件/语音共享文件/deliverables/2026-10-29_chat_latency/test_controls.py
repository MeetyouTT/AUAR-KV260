"""Synthetic-only fact revisions, deletion confirmation and source dependencies."""
import json
from datetime import datetime,timezone
from unittest.mock import patch
import pytest
from common.memory_controls import parse
from common.timeline_conversations import TimelineConversationStore
from common.profile_memory import ProfileConversationStore
from common.conversation_context import build_context
from common.timeline import query
from tests.framework.test_voice_channel import owner
NOW=datetime(2026,10,29,20,tzinfo=timezone.utc).timestamp()
CID='a'*32;OTHER='b'*32;THIRD='c'*32;DIGEST='d'*64

def turn(store,n,text,*,at=NOW-100,cid=CID,profile=None,played=False,reply='收到'):
    meta=owner('controls-'+str(n),n)
    with patch('time.time',return_value=at):
        store.begin(cid,meta,text,text,profile=profile)
        if played:store.generated(meta,reply,480,DIGEST);store.played(meta,480,DIGEST)
    return meta
def command(store,n,text,*,at=NOW,cid=CID,profile=None,session=None):
    meta=owner('controls-'+str(n),n)
    if session is not None:meta['session_id']=session
    with patch('time.time',return_value=at):
        store.begin(cid,meta,text,text,profile=profile)
        reply=store.memory_command(meta,text,profile=profile)
    return meta,reply
def seq(store,meta):
    with store._connect() as db:return db.execute('SELECT seq FROM turns WHERE request_id=?',(meta['request_id'],)).fetchone()[0]
def exists(store,meta):
    with store._connect() as db:return db.execute('SELECT 1 FROM turns WHERE request_id=?',(meta['request_id'],)).fetchone() is not None
@pytest.fixture
def store(tmp_path):return TimelineConversationStore(tmp_path/'memory.sqlite3')

@pytest.mark.parametrize('text',['如果删除昨天的对话记录会怎样','他说删除昨天的对话记录','我以前喜欢蓝色','别删除昨天的对话记录'])
def test_chat_does_not_mutate(text):assert parse(text) is None
@pytest.mark.parametrize('text',['删除上个月的对话记录','删除所有对话记录','删除昨天到今天的对话记录','删除关于“杯子”的对话记录'])
def test_unclear_ranges_do_not_expand(text):assert parse(text)['op']=='help'

def test_fact_corrections_history_and_current_context(store):
    command(store,1,'记住：项目=海风',at=NOW-200);command(store,2,'更正记忆：项目=晨光',at=NOW-100)
    _,reply=command(store,3,'查看项目记忆历史')
    assert '海风' in reply and '晨光' in reply and '旧值' in reply and '当前值' in reply
    records,facts=store.context_snapshot(CID)
    history,_=build_context('test',records,'项目叫什么',memories=facts)
    text=json.dumps(history,ensure_ascii=False)
    assert '晨光' in text and '海风' not in text
    with store._connect() as db:
        rows=db.execute('SELECT value,recorded,superseded FROM memory_fact_versions ORDER BY source_seq').fetchall()
        assert [r['recorded'] for r in rows]==[NOW-200,NOW-100] and rows[0]['superseded']==NOW-100
@pytest.mark.parametrize('forget',['忘记项目的记忆','清空本次对话记忆'])
def test_forget_purges_versions(store,forget):
    command(store,1,'记住：项目=海风');command(store,2,'更正记忆：项目=晨光');command(store,3,forget)
    _,reply=command(store,4,'查看项目记忆历史')
    assert '海风' not in reply and '晨光' not in reply
    with store._connect() as db:assert db.execute('SELECT count(*) FROM memory_fact_versions').fetchone()[0]==0
def test_personal_history_scope_and_restart(store):
    profile=store.create_profile('A',consent=True);other=store.create_profile('B',consent=True)
    command(store,1,'记住：颜色=蓝色',profile=profile);command(store,2,'更正记忆：颜色=绿色',profile=profile,cid=OTHER)
    reopened=TimelineConversationStore(store.path)
    _,reply=command(reopened,3,'查看我的颜色记忆历史',profile=profile,cid=OTHER)
    assert '蓝色' in reply and '绿色' in reply
    _,reply=command(reopened,4,'查看我的颜色记忆历史',profile=other,cid=THIRD)
    assert '蓝色' not in reply
    with pytest.raises(PermissionError):command(reopened,5,'查看颜色记忆历史',cid=OTHER)
def test_upgrade_seeds_only_current_fact(tmp_path):
    path=tmp_path/'old.db';old=ProfileConversationStore(path)
    command(old,1,'记住：项目=海风');command(old,2,'更正记忆：项目=晨光')
    store=TimelineConversationStore(path)
    _,reply=command(store,3,'查看项目记忆历史')
    assert '晨光' in reply and '海风' not in reply
def test_version_bound_and_old_writer_compatibility(store):
    for n in range(1,36):command(store,n,'更正记忆：项目=版本'+str(n),at=NOW+n)
    with store._connect() as db:
        assert db.execute('PRAGMA recursive_triggers').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM memory_fact_versions').fetchone()[0]==32
    old=ProfileConversationStore(store.path);command(old,40,'更正记忆：项目=旧代码新值',at=NOW+40)
    _,reply=command(store,41,'查看项目记忆历史',at=NOW+41)
    assert '旧代码新值' in reply and '版本35' in reply
    command(old,42,'忘记项目的记忆',at=NOW+42)
    with store._connect() as db:assert db.execute('SELECT count(*) FROM memory_fact_versions').fetchone()[0]==0
def test_preview_and_exact_delete_scope(store):
    target=turn(store,1,'杯子在左边',at=NOW-86400,played=True)
    kept=turn(store,2,'电池在右边',at=NOW-86400,played=True)
    other=turn(store,3,'杯子在中间',at=NOW-86400,cid=OTHER,played=True)
    _,reply=command(store,4,'删除昨天关于杯子的对话记录')
    assert '找到1轮' in reply and exists(store,target)
    _,reply=command(store,5,'确认删除这些对话记录',at=NOW+1)
    assert '已删除1轮' in reply and not exists(store,target) and exists(store,kept) and exists(store,other)
    with store._connect() as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    with pytest.raises(ValueError):store.played(target,480,DIGEST)
@pytest.mark.parametrize('reason',['session','expired','cancelled'])
def test_confirmation_binding_and_expiry(store,reason):
    target=turn(store,1,'杯子',at=NOW-86400);command(store,2,'删除昨天关于杯子的对话记录')
    if reason=='session':command(store,3,'确认删除这些对话记录',at=NOW+1,session='different-session')
    elif reason=='expired':command(store,3,'确认删除这些对话记录',at=NOW+61)
    else:
        command(store,3,'取消删除对话记录',at=NOW+1);command(store,4,'确认删除这些对话记录',at=NOW+2)
    assert exists(store,target)
def test_changed_records_abort_without_delete(store):
    target=turn(store,1,'杯子',at=NOW-86400);command(store,2,'删除昨天关于杯子的对话记录')
    store.generated(target,'new',480,DIGEST)
    _,reply=command(store,3,'确认删除这些对话记录',at=NOW+1)
    assert '已变化' in reply and exists(store,target)
def test_personal_delete_own_conversations_only(store):
    profile=store.create_profile('A',consent=True);other=store.create_profile('B',consent=True)
    first=turn(store,1,'杯子左边',at=NOW-86400,profile=profile)
    second=turn(store,2,'杯子右边',at=NOW-86400,profile=profile,cid=OTHER)
    kept=turn(store,3,'杯子中间',at=NOW-86400,profile=other,cid=THIRD)
    command(store,4,'删除我的昨天关于杯子的对话记录',profile=profile,cid=OTHER)
    _,reply=command(store,5,'确认删除这些对话记录',profile=profile,cid=OTHER,at=NOW+1)
    assert '已删除2轮' in reply and not exists(store,first) and not exists(store,second) and exists(store,kept)
def test_guest_cannot_delete_personal_scope(store):
    target=turn(store,1,'杯子',at=NOW-86400)
    _,reply=command(store,2,'删除我的昨天关于杯子的对话记录')
    assert '选择个人档案' in reply and exists(store,target)
def test_transitive_dependencies_invalidate_later_replies(store):
    original=turn(store,1,'杯子左边',at=NOW-86400,played=True)
    derived=turn(store,2,'继续',at=NOW-100,played=True,reply='它在左边')
    store.attach_sources(derived,[seq(store,original)])
    following=turn(store,3,'然后呢',at=NOW-50,played=True,reply='还是那里')
    store.attach_sources(following,[seq(store,derived)])
    command(store,4,'删除昨天关于杯子的对话记录')
    _,reply=command(store,5,'确认删除这些对话记录',at=NOW+1)
    assert '2轮关联历史' in reply and not store.records(CID)
    assert exists(store,derived) and exists(store,following)
    with pytest.raises(ValueError):store.played(derived,480,DIGEST)
def test_dependency_cannot_cross_guest_scope(store):
    first=turn(store,1,'source',cid=OTHER);second=turn(store,2,'target')
    with pytest.raises(PermissionError):store.attach_sources(second,[seq(store,first)])
def test_delete_fact_source_does_not_restore_older_fact(store):
    command(store,1,'记住：项目=海风',at=NOW-2*86400);command(store,2,'更正记忆：项目=晨光',at=NOW-86400)
    command(store,3,'删除昨天关于晨光的对话记录');command(store,4,'确认删除这些对话记录',at=NOW+1)
    assert store.facts(CID)==[]
    _,reply=command(store,5,'查看项目记忆历史',at=NOW+2)
    assert '海风' not in reply and '晨光' not in reply
def test_unknown_legacy_reply_lineage_is_withheld(tmp_path):
    path=tmp_path/'legacy.db';old=ProfileConversationStore(path)
    target=turn(old,1,'杯子左边',at=NOW-86400,played=True);later=turn(old,2,'在哪里',at=NOW-100,played=True,reply='左边')
    store=TimelineConversationStore(path)
    command(store,3,'删除昨天关于杯子的对话记录');command(store,4,'确认删除这些对话记录',at=NOW+1)
    assert exists(store,later) and not exists(store,target) and not store.records(CID)
def test_playback_outside_date_does_not_expand_range(store):
    target=turn(store,1,'杯子',at=NOW-2*86400);store.generated(target,'left',480,DIGEST)
    with patch('time.time',return_value=NOW-50):store.played(target,480,DIGEST)
    _,reply=command(store,2,'删除昨天关于杯子的对话记录')
    assert '没有找到' in reply and exists(store,target)
def test_digest_invalidation_same_transaction(store):
    original=turn(store,1,'杯子左边',at=NOW-86400,played=True)
    from common.timeline_summaries import DigestWorker
    worker=DigestWorker(store.path,store._digest_sources,zone='America/Los_Angeles',clock=lambda:NOW)
    worker.step();q=query('昨天聊了什么',now=NOW)
    assert store.summary_events(CID,q)
    command(store,2,'删除昨天关于杯子的对话记录');command(store,3,'确认删除这些对话记录',at=NOW+1)
    assert store.summary_events(CID,q)==[] and not exists(store,original)
def test_recent_context_source_ids(store):
    first=turn(store,1,'甲',played=True);second=turn(store,2,'乙',played=True)
    _,metrics=build_context('test',store.records(CID),'继续')
    assert metrics['recent_source_turns']==[seq(store,first),seq(store,second)]

def test_memory_command_skips_unused_context(tmp_path):
    from tools.voice_channel_source import channel_frames
    from tests.framework.test_long_conversation import host
    models=host(tmp_path)
    from tests.framework.test_voice_channel import VoiceChannelTests
    models.voice=VoiceChannelTests().fixture_models(tmp_path).voice
    models.conversation_context=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Unused context was queried'))
    def no_llm(*a,**kw):raise AssertionError('Direct memory command invoked LLM')
    packets=list(channel_frames(models,owner('direct-query',1),'查看记忆',5,model='test',host='unused',conversation=CID,stream_factory=no_llm))
    import io
    from common.voice_channel import read_frame
    stream=io.BytesIO(b''.join(packets));frames=[]
    while stream.tell()<len(stream.getvalue()):frames.append(read_frame(stream)[0])
    assert any(row['kind']=='text' for row in frames)

def test_tts_failure_keeps_fact_but_marks_reply_failed(tmp_path):
    from tools.voice_channel_source import channel_frames
    from tests.framework.test_long_conversation import host
    from tests.framework.test_voice_channel import VoiceChannelTests
    models=host(tmp_path);models.voice=VoiceChannelTests().fixture_models(tmp_path).voice
    models.voice.generate=lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('synthetic voice failure'))
    meta=owner('failed-memory',1)
    packets=list(channel_frames(models,meta,'记住：项目=海风',5,model='test',host='unused',conversation=CID))
    assert models.conversations.facts(CID)[0]['value']=='海风'
    with models.conversations._connect() as db:
        assert db.execute('SELECT status FROM turns WHERE request_id=?',(meta['request_id'],)).fetchone()[0]=='interrupted'

def test_unplayed_stored_reply_is_also_removed_by_topic_delete(store):
    target=turn(store,1,'还有什么',at=NOW-86400)
    store.generated(target,'杯子在左边',480,DIGEST)
    command(store,2,'删除昨天关于杯子的对话记录')
    _,reply=command(store,3,'确认删除这些对话记录',at=NOW+1)
    assert '已删除1轮' in reply and not exists(store,target)

def test_delete_limit_does_not_partially_apply(store):
    first=turn(store,1,'杯子',at=NOW-86400)
    with store._connect() as db:
        db.executemany("INSERT INTO turns(request_id,conversation_id,context,user,raw_user,status,created) VALUES(?,?,?,?,?,'submitted',?)",
            [('bound-'+str(n),CID,'{}','杯子','杯子',NOW-86400) for n in range(1000)])
    _,reply=command(store,2,'删除昨天关于杯子的对话记录')
    assert '超过1000轮' in reply and exists(store,first)
    _,reply=command(store,3,'确认删除这些对话记录',at=NOW+1)
    assert '没有有效' in reply and exists(store,first)

def test_delete_calendar_handles_both_dst_fold_hours(store):
    now=datetime(2026,11,3,4,tzinfo=timezone.utc).timestamp()
    first=turn(store,1,'杯子',at=datetime(2026,11,1,8,30,tzinfo=timezone.utc).timestamp())
    second=turn(store,2,'杯子',at=datetime(2026,11,1,9,30,tzinfo=timezone.utc).timestamp())
    command(store,3,'删除昨天关于杯子的对话记录',at=now)
    _,reply=command(store,4,'确认删除这些对话记录',at=now+1)
    assert '已删除2轮' in reply and not exists(store,first) and not exists(store,second)

@pytest.mark.parametrize('replacement',['删除上个月的对话记录','删除昨天关于电池的对话记录'])
def test_new_delete_request_revokes_old_preview(store,replacement):
    original=turn(store,1,'杯子',at=NOW-86400)
    _,reply=command(store,2,'删除昨天关于杯子的对话记录')
    assert '昨天关于杯子' in reply
    command(store,3,replacement,at=NOW+.5)
    _,reply=command(store,4,'确认删除这些对话记录',at=NOW+1)
    assert '没有有效' in reply and exists(store,original)

def test_personal_forget_clears_history_across_conversations(store):
    profile=store.create_profile('A',consent=True)
    command(store,1,'记住：项目=海风',profile=profile)
    command(store,2,'更正记忆：项目=晨光',profile=profile,cid=OTHER)
    command(store,3,'忘记长期记忆项目的记忆',profile=profile,cid=OTHER)
    _,reply=command(store,4,'查看我的项目记忆历史',profile=profile)
    assert '海风' not in reply and '晨光' not in reply

def test_stale_preview_after_fact_change_aborts(store):
    target=turn(store,1,'杯子',at=NOW-86400)
    command(store,2,'删除昨天关于杯子的对话记录')
    command(store,3,'记住：项目=海风',at=NOW+.5)
    _,reply=command(store,4,'确认删除这些对话记录',at=NOW+1)
    assert '已变化' in reply and exists(store,target)

def test_confirmation_replay_does_not_delete_a_new_turn(store):
    turn(store,1,'杯子',at=NOW-86400)
    command(store,2,'删除昨天关于杯子的对话记录');command(store,3,'确认删除这些对话记录',at=NOW+1)
    fresh=turn(store,4,'杯子',at=NOW+2)
    _,reply=command(store,5,'确认删除这些对话记录',at=NOW+3)
    assert '没有有效' in reply and exists(store,fresh)

def test_new_dependency_after_preview_requires_new_confirmation(store):
    target=turn(store,1,'杯子',at=NOW-86400)
    command(store,2,'删除昨天关于杯子的对话记录')
    later=turn(store,3,'继续',at=NOW+.5)
    store.attach_sources(later,[seq(store,target)])
    _,reply=command(store,4,'确认删除这些对话记录',at=NOW+1)
    assert '已变化' in reply and exists(store,target)

def test_source_attachment_integrated_with_actual_host_context(tmp_path):
    from tests.framework.test_long_conversation import host
    models=host(tmp_path);models.conversations=TimelineConversationStore(tmp_path/'actual.db')
    original=turn(models.conversations,1,'杯子在左边',played=True)
    meta=owner('context-new',2)
    models.begin_conversation(meta,CID,'杯子在哪','杯子在哪')
    models.conversation_context(meta,'杯子在哪')
    with models.conversations._connect() as db:
        assert db.execute('SELECT source_seq FROM memory_source_dependencies WHERE seq=?',(seq(models.conversations,meta),)).fetchone()[0]==seq(models.conversations,original)

def test_digest_sources_resolve_to_authoritative_turns(store):
    original=turn(store,1,'杯子',at=NOW-86400,played=True)
    from common.timeline_summaries import DigestWorker
    worker=DigestWorker(store.path,store._digest_sources,zone='America/Los_Angeles',clock=lambda:NOW)
    worker.step();rows=store.summary_events(CID,query('昨天聊了什么',now=NOW))
    assert rows and all(r['source_seqs']==[seq(store,original)] for r in rows)

