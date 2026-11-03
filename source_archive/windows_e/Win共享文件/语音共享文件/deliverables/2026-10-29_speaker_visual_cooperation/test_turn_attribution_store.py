import bootstrap
import importlib.util,json,sqlite3
import pytest
from common.conversation_store import ConversationStore
from common.profile_memory import ProfileConversationStore
from common.timeline_conversations import TimelineConversationStore
from common.speaker_turns import record
from test_helpers import CID,meta,complete,voice

def source_rows(path):
    with sqlite3.connect(path) as db:
        return {table:db.execute('SELECT * FROM '+table+' ORDER BY 1').fetchall() for table in
          ('conversations','turns','conversation_facts','recall_exclusions')}

def begin(store,owner=None,cid=CID,**kwargs):
    owner=owner or meta();store.begin(cid,owner,'公开测试输入','公开测试输入',**kwargs);return owner

def test_upgrade_adds_only_separate_table_and_preserves_original_rows(tmp_path):
    spec=importlib.util.spec_from_file_location('legacy_store',bootstrap.A/'common/conversation_store.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    path=tmp_path/'store.sqlite3';old=module.ConversationStore(path);begin(old)
    before=source_rows(path);new=ConversationStore(path)
    assert source_rows(path)==before
    new.attribution_pending(meta(),CID);new.attribution_merge(meta(),CID,complete(meta()))
    assert source_rows(path)==before
    assert new.attribution_for_turn(meta(),CID)['voice']['candidate_id']=='voice-one'

def test_exact_owner_and_cid_are_required_for_write_and_read(tmp_path):
    store=ConversationStore(tmp_path/'store.sqlite3');begin(store);store.attribution_pending(meta(),CID)
    for foreign in (dict(meta(),capture_id='different'),dict(meta(),generation=2),dict(meta(),pcm_sha256='f'*64)):
        with pytest.raises(ValueError):store.attribution_merge(foreign,CID,complete(foreign))
        with pytest.raises(ValueError):store.attribution_cancel(foreign,CID)
        with pytest.raises(ValueError):store.attribution_for_turn(foreign,CID)
    with pytest.raises(ValueError):store.attribution_merge(meta(),'b'*32,complete(meta(),'b'*32))

def test_cancelled_old_result_never_relabels_the_next_turn(tmp_path):
    store=ConversationStore(tmp_path/'store.sqlite3');a=begin(store);store.attribution_pending(a,CID)
    store.attribution_cancel(a,CID);b=begin(store,meta(2));store.attribution_pending(b,CID)
    assert not store.attribution_merge(a,CID,complete(a))
    assert store.attribution_for_turn(a,CID)['status']=='CANCELLED'
    assert store.attribution_for_turn(b,CID)['voice'] is None
    assert store.attribution_for_turn(b,CID)['status']=='PENDING'

def test_late_result_can_fill_original_played_turn_without_changing_ack(tmp_path):
    store=TimelineConversationStore(tmp_path/'store.sqlite3');owner=begin(store);store.attribution_pending(owner,CID)
    store.generated(owner,'公开回复',24000,'e'*64);assert store.played(owner,24000,'e'*64)
    before=source_rows(store.path);assert store.attribution_merge(owner,CID,complete(owner))
    assert source_rows(store.path)==before
    assert store.records(CID)[0]['status']=='played'

def test_memory_revision_and_forget_hide_or_cancel_obsolete_attribution(tmp_path):
    store=ConversationStore(tmp_path/'store.sqlite3');owner=begin(store);store.attribution_pending(owner,CID)
    other=begin(store,meta(2));store.memory_command(other,'清空本次对话记忆')
    assert store.attribution_merge(owner,CID,complete(owner))
    assert store.attribution_for_turn(owner,CID)['reason']=='MEMORY_REVISION_CHANGED'
    assert store.attribution_records(CID)==[]

def test_profile_inheritance_requires_original_authorized_scope(tmp_path):
    store=TimelineConversationStore(tmp_path/'store.sqlite3');pid=store.create_profile('公开测试档案',consent=True)
    owner=begin(store,profile=pid)
    with pytest.raises(PermissionError):store.attribution_pending(owner,CID)
    store.attribution_pending(owner,CID,profile=pid)
    with pytest.raises(PermissionError):store.attribution_for_turn(owner,CID)
    with pytest.raises(PermissionError):store.attribution_merge(owner,CID,complete(owner))
    assert store.attribution_merge(owner,CID,complete(owner),profile=pid)
    assert store.attribution_records(CID,profile=pid)[0]['personal_memory_allowed'] is False
    assert store.profiles()==[{'id':pid,'name':'公开测试档案'}]
    assert store.facts(CID,profile=pid)==[]

def test_schema_rejects_profile_claim_extra_private_fields_and_unstable_voice(tmp_path):
    store=ConversationStore(tmp_path/'store.sqlite3');begin(store);store.attribution_pending(meta(),CID)
    good=complete(meta())
    for invalid in (dict(good,personal_memory_allowed=True),dict(good,embedding=[1,0]),
                    dict(good,voice=dict(voice(),state='CANDIDATE_STABLE',consecutive_distinct=1)),
                    dict(good,voice=dict(voice(),field_calibrated=False))):
        with pytest.raises(ValueError):store.attribution_merge(meta(),CID,invalid)

def test_pending_retry_does_not_reset_terminal_and_anonymous_turns_still_record(tmp_path):
    store=ProfileConversationStore(tmp_path/'store.sqlite3');owner=begin(store)
    store.attribution_pending(owner,CID);store.attribution_merge(owner,CID,record(owner,CID,status='UNAVAILABLE',reason='NO_MODEL'))
    again=store.attribution_pending(owner,CID)
    assert again['status']=='UNAVAILABLE' and again['voice'] is None
    assert store.records(CID)[0]['user']=='公开测试输入'
