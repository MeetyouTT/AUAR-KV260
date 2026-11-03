"""Exact-pinned Store, synthetic SQLite only; no hardware/model/real archive."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import sqlite3
import sys

import pytest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[5]
sys.path.insert(0,str(ROOT/'aura'))
from common.profile_access import ProfileAccess

FILE=HERE.parent/'after/common/board_memory.py'
spec=importlib.util.spec_from_file_location('common.prepared_memory_candidate',FILE)
memory=importlib.util.module_from_spec(spec);sys.modules[spec.name]=memory;spec.loader.exec_module(memory)
SCOPE={'kind':'conversation','id':'public-conversation'}
DIGEST=hashlib.sha256(b'public-pcm').hexdigest()


def make(tmp_path,**options):
    return memory.BoardMemoryStore(tmp_path/'synthetic.sqlite3',clock=lambda:1000.,**options)


def prepared(store,*,scope=SCOPE,name='public-turn',sources=()):
    store.begin_turn(scope,name,'公开合成请求。',generation=1)
    return store.generated(name,'第一句公开回答。第二句尚未完成。',generation=1,
                           source_event_ids=sources,provenance_complete=True)


def bind(store,name='public-turn'):
    store.bind_audio_receipt(name,generation=1,playback_token='public-token',sha256=DIGEST,samples=240)


def test_exact_base_has_only_new_read_method_and_no_other_ast_changes():
    before=HERE.parents[1]/'source_before/common/board_memory.py'
    assert hashlib.sha256(before.read_bytes()).hexdigest()=='19dabc48425ed711af17fc56929a0198067217c52593e157db23b8724ddffde3'
    old,new=ast.parse(before.read_bytes()),ast.parse(FILE.read_bytes())
    cls=next(n for n in new.body if isinstance(n,ast.ClassDef) and n.name=='BoardMemoryStore')
    additions=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='check_prepared_turn_current']
    assert len(additions)==1
    cls.body.remove(additions[0])
    assert ast.dump(old)==ast.dump(new)


def test_prepared_check_is_read_only_and_accepts_bound_or_unbound_pending(tmp_path):
    store=make(tmp_path);prepared(store)
    before=Path(store.path).read_bytes()
    for _ in range(3):assert store.check_prepared_turn_current('public-turn',generation=1) is True
    assert Path(store.path).read_bytes()==before
    # The local cue API retains its original stricter generating-only state.
    with pytest.raises(memory.StaleTurn):store.check_turn_current('public-turn',generation=1)
    bind(store)
    assert store.check_prepared_turn_current('public-turn',generation=1) is True
    assert not any(r['role']=='assistant' for r in store.context(SCOPE)['messages'])


@pytest.mark.parametrize('state',['generating','played','interrupted','wrong_generation'])
def test_only_original_awaiting_generation_is_authorized(tmp_path,state):
    store=make(tmp_path)
    if state=='generating':store.begin_turn(SCOPE,'public-turn','公开输入',generation=1)
    else:
        prepared(store);bind(store)
        if state=='played':store.ack_played('public-turn',generation=1,playback_token='public-token',sha256=DIGEST,samples=240)
        elif state=='interrupted':store.interrupt('public-turn',generation=1)
    with pytest.raises(memory.StaleTurn):
        store.check_prepared_turn_current('public-turn',generation=2 if state=='wrong_generation' else 1)


@pytest.mark.parametrize('operation',['forget','correct','clear'])
def test_second_store_invalidation_blocks_later_audio_and_full_ack(tmp_path,operation):
    store=make(tmp_path)
    store.append_event(SCOPE,'public-source','user_said','项目还没有完成。')
    store.correct(SCOPE,'项目','尚未完成',source_event_ids=['public-source'])
    prepared(store,sources=['public-source']);bind(store)
    other=memory.BoardMemoryStore(store.path,clock=lambda:1001.)
    if operation=='forget':other.forget(SCOPE,event_ids=['public-source'])
    elif operation=='correct':other.correct(SCOPE,'项目','已经重新确认')
    else:other.clear(SCOPE)
    with pytest.raises((memory.StaleTurn,memory.ScopeDenied)):
        store.check_prepared_turn_current('public-turn',generation=1)
    with pytest.raises((memory.StaleTurn,memory.ScopeDenied)):
        store.ack_played('public-turn',generation=1,playback_token='public-token',sha256=DIGEST,samples=240)
    assert not any(r['role']=='assistant' for r in store.context(SCOPE)['messages'])


@pytest.mark.parametrize('mutation',['invalid_dependency','foreign_dependency','missing_user_ref','assistant_state','assistant_playback','assistant_turn'])
def test_check_validates_all_recorded_dependencies_and_exact_assistant(tmp_path,mutation):
    store=make(tmp_path)
    store.append_event(SCOPE,'public-source','user_said','公开旧资料。')
    store.append_event({'kind':'conversation','id':'other-public-scope'},'other-event','user_said','另一公开范围。')
    receipt=prepared(store,sources=['public-source'])
    # Deliberate fixture corruption isolates source checks from the normal
    # invalidator, which already revokes the pending turn atomically.
    with sqlite3.connect(store.path) as db:
        if mutation=='invalid_dependency':db.execute("UPDATE bm_events SET state='corrected' WHERE event_id='public-source'")
        elif mutation=='foreign_dependency':db.execute("UPDATE bm_events SET scope_id='other-public-scope' WHERE event_id='public-source'")
        elif mutation=='missing_user_ref':db.execute('DELETE FROM bm_event_dependencies WHERE event_id=? AND source_event_id=?',(receipt['assistant_event_id'],receipt['user_event_id']))
        elif mutation=='assistant_state':db.execute("UPDATE bm_events SET state='forgotten' WHERE event_id=?",(receipt['assistant_event_id'],))
        elif mutation=='assistant_playback':db.execute("UPDATE bm_events SET playback='incomplete' WHERE event_id=?",(receipt['assistant_event_id'],))
        else:db.execute("UPDATE bm_events SET turn_id='other-turn' WHERE event_id=?",(receipt['assistant_event_id'],))
    with pytest.raises((memory.StaleTurn,memory.ScopeDenied)):
        store.check_prepared_turn_current('public-turn',generation=1)


def test_profile_revocation_and_reopen_do_not_authorize_pending_audio(tmp_path):
    access=ProfileAccess('a'*64,clock=lambda:10.)
    actor={'board_boot_id':'public-boot','session_id':'public-session'}
    _,grant=access.issue('b'*32,actor)
    store=make(tmp_path,profile_access=access)
    scope={'kind':'profile','id':'b'*32,'grant':grant}
    prepared(store,scope=scope)
    assert store.check_prepared_turn_current('public-turn',generation=1)
    reopened=memory.BoardMemoryStore(store.path,clock=lambda:1001.,profile_access=access)
    with pytest.raises(PermissionError):reopened.check_prepared_turn_current('public-turn',generation=1)
    access.revoke(actor)
    with pytest.raises(PermissionError):store.check_prepared_turn_current('public-turn',generation=1)


def test_clear_operation_keeps_its_own_new_confirmation_but_revokes_old_turn(tmp_path):
    store=make(tmp_path);prepared(store)
    store.begin_turn(SCOPE,'clear-command','清空本次对话记忆。',generation=2)
    store.clear(SCOPE,operation_turn_id='clear-command')
    store.generated('clear-command','已清空本次对话记忆。',generation=2)
    assert store.check_prepared_turn_current('clear-command',generation=2)
    with pytest.raises(memory.StaleTurn):store.check_prepared_turn_current('public-turn',generation=1)


def test_expanded_summary_dependencies_remain_valid_after_body_cleanup(tmp_path):
    now=[1000.]
    store=memory.BoardMemoryStore(tmp_path/'summary.sqlite3',clock=lambda:now[0])
    store.append_event(SCOPE,'summary-source','user_said','公开事件记录。')
    now[0]=1400.
    task=store.prepare_compaction()
    candidate=dict(schema_version=1,scope=task['scope'],topic=task['topic'],start_utc=task['start_utc'],end_utc=task['end_utc'],
        source_refs=[dict(event_id=r['event_id'],revision=r['revision']) for r in task['sources'] if r['include_in_summary']],
        summary='公开事件记录。',keywords=['公开','事件'],claims=task['required_claims'])
    saved=store.commit_compaction(task['task_id'],task['lease_token'],candidate)
    assert saved['committed']
    with sqlite3.connect(store.path) as db:assert db.execute("SELECT 1 FROM bm_bodies WHERE event_id='summary-source'").fetchone() is None
    store.begin_turn(SCOPE,'public-turn','过去记录了什么？',generation=1)
    store.generated('public-turn','记录了公开事件。',generation=1,summary_ids=[saved['summary_id']],provenance_complete=True)
    assert store.check_prepared_turn_current('public-turn',generation=1)
    store.forget(SCOPE,event_ids=['summary-source'])
    with pytest.raises((memory.StaleTurn,memory.ScopeDenied)):
        store.check_prepared_turn_current('public-turn',generation=1)
