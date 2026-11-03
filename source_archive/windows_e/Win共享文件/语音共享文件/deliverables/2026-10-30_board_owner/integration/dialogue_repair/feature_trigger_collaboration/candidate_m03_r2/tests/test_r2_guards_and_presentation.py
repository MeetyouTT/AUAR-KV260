"""Public temporary SQLite/RAM only; original controller and UI lifecycle.
No model, real grant, microphone, camera, speaker, GUI or network is accessed.
"""
from contextlib import contextmanager
from datetime import datetime
import importlib.util
from pathlib import Path
import threading
from types import SimpleNamespace as NS
from zoneinfo import ZoneInfo

import pytest

from board.runtime.board_dialogue import SourcedBoardReply, StaleGeneration
from board.runtime.history_delete import calendar_day
from common.board_memory import ScopeDenied, StaleTurn
from common.profile_access import ProfileAccess
from tools import production_memory_presentation as presentation

H=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('m03_r2_original_public_fixture',H/'review_m03_win_inference/test_delete_boundaries.py')
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
TEXT='公开旧显示及关联值标记'


@pytest.fixture
def r():
    value=original.DeleteBoundaryReview(methodName='runTest');value.setUp()
    try:yield value
    finally:value.doCleanups()


def seed(r):
    r.append('public-target',r.now-60.)
    r.store.correct(r.scope,'项目',TEXT,source_event_ids=('public-target',))


def pending(r):return next(iter(r.handler.pending.values())).copy()


def control_say(r,text,*,cancel=None,current=lambda:True):
    r.generation+=1
    meta=dict(board_boot_id='public-review-boot',session_id='public-review-session',
        generation=r.generation,request_id='public-command-'+str(r.generation))
    job=NS(scope=r.scope,deadline=r.mono()+30.,meta=meta)
    return r.handler(text,job=job,controller=r.controller,is_current=current,
        cancel_event=cancel or threading.Event())


@pytest.mark.parametrize('day,hours',[('2026-03-08',23),('2026-11-01',25),('2026-10-31',24)])
def test_full_local_day_keeps_dst_length_and_next_midnight_exclusive(r,day,hours):
    interval=calendar_day(day,now=r.now,zone='America/Los_Angeles')
    assert interval['end']-interval['start']==hours*3600
    r.append('outside-before',interval['start']-.001)
    r.append('inside-start',interval['start'])
    r.append('inside-end',interval['end']-.001)
    r.append('outside-end',interval['end'])
    r.say('删除'+day+'的对话记录');r.say('确认删除记录')
    assert r.state('inside-start')==r.state('inside-end')=='forgotten'
    assert r.state('outside-before')==r.state('outside-end')=='valid'


def test_fact_cosource_value_and_its_derived_summary_are_both_removed(r):
    from tests.framework.test_board_memory import candidate
    seed(r)
    # Make both public sources older than five minutes without advancing mono;
    # compaction uses trusted synthetic UTC and remains a separate original API.
    r.timeline.utc+=301.;r.now=r.timeline.utc
    kinds=set()
    # The original store deliberately leases one exact topic at a time; user
    # roots and memory commands therefore form separate public summary tasks.
    for _ in range(2):
        task=r.store.prepare_compaction(max_events=8)
        assert task
        kinds.update(s['source'] for s in task['sources'])
        text='公开日期边界测试内容。项目是'+TEXT+'。'
        assert r.store.commit_compaction(task['task_id'],task['lease_token'],candidate(task,text))['committed']
    assert 'memory_command' in kinds and 'user_said' in kinds
    assert r.store.history(r.scope,search=TEXT)
    r.say('删除今天的对话记录');r.say('确认删除记录')
    assert r.state('public-target')=='forgotten' and r.store.context(r.scope)['facts']==[]
    # Search is deliberately lexical OR, so a new management reply saying
    # "关联记忆" may match some terms without retaining the deleted value.
    assert all(TEXT not in row['text'] for row in r.store.history(r.scope,search=TEXT))
    assert r.store.health()['valid_summaries']==0
    with r.store._db() as db:
        assert db.execute("SELECT count(*) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.source='memory_command' AND e.state='valid'").fetchone()[0]==0
        assert db.execute("SELECT count(*) FROM bm_summary_keywords").fetchone()[0]==0


def test_expiry_immediately_before_commit_rolls_back_written_bodies_facts_and_receipt(r,monkeypatch):
    seed(r);r.say('删除今天的对话记录');r.mono.now+=59.9
    original_save=r.store._save_operation
    notifications=[];r.store.notify_history_delete_committed=lambda **kwargs:notifications.append(kwargs)
    def save_then_expire(*args,**kwargs):
        original_save(*args,**kwargs)
        r.mono.now+=.2
    monkeypatch.setattr(r.store,'_save_operation',save_then_expire)
    reply=r.say('确认删除记录')
    assert '已过期，没有删除' in reply and r.state('public-target')=='valid'
    assert r.store.context(r.scope)['facts'][0]['value']==TEXT and notifications==[]
    with r.store._db() as db:
        assert db.execute("SELECT count(*) FROM bm_operations WHERE kind='transcript_delete'").fetchone()[0]==0


@pytest.mark.parametrize('loss',['deadline','cancel','owner'])
def test_original_request_loss_after_write_acquisition_never_deletes(r,monkeypatch,loss):
    seed(r);r.say('删除今天的对话记录')
    cancel=threading.Event();state={'current':True};original_db=r.store._db;changed=[]
    @contextmanager
    def delayed(write=False):
        with original_db(write) as db:
            if write and not changed and db.execute("SELECT count(*) FROM bm_turns WHERE turn_id='public-command-2'").fetchone()[0]:
                changed.append(True)
                if loss=='deadline':r.mono.now+=30.1
                elif loss=='cancel':cancel.set()
                else:state['current']=False
            yield db
    monkeypatch.setattr(r.store,'_db',delayed)
    with pytest.raises(TimeoutError if loss=='deadline' else StaleGeneration):
        control_say(r,'确认删除记录',cancel=cancel,current=lambda:state['current'])
    assert changed and r.state('public-target')=='valid'
    assert r.store.context(r.scope)['facts'][0]['value']==TEXT


@pytest.mark.parametrize('loss',['deadline','cancel','owner'])
def test_original_request_loss_after_mutation_rolls_back_before_commit(r,monkeypatch,loss):
    seed(r);r.say('删除今天的对话记录')
    cancel=threading.Event();state={'current':True};save=r.store._save_operation
    notifications=[];r.store.notify_history_delete_committed=lambda **kwargs:notifications.append(kwargs)
    def saved_then_lost(*args,**kwargs):
        save(*args,**kwargs)
        if loss=='deadline':r.mono.now+=30.1
        elif loss=='cancel':cancel.set()
        else:state['current']=False
    monkeypatch.setattr(r.store,'_save_operation',saved_then_lost)
    with pytest.raises(TimeoutError if loss=='deadline' else StaleGeneration):
        control_say(r,'确认删除记录',cancel=cancel,current=lambda:state['current'])
    assert r.state('public-target')=='valid' and r.store.context(r.scope)['facts'][0]['value']==TEXT
    assert notifications==[]
    with r.store._db() as db:
        assert db.execute("SELECT count(*) FROM bm_operations WHERE kind='transcript_delete'").fetchone()[0]==0


def test_original_profile_grant_expiry_after_acquisition_is_rechecked(r,monkeypatch):
    # Explicit ORIGINAL grants for this public temporary test store only.
    # No production profile is selected or issued, and no automatic auth added.
    access=ProfileAccess('9'*64,clock=r.mono);access.authenticate('9'*64)
    _,grant=access.issue('a'*32,dict(board_boot_id='public-review-boot',session_id='public-review-session'),ttl=30)
    r.store.profile_access=access;r.scope=dict(kind='profile',id='a'*32,grant=grant)
    seed(r);r.say('删除个人今天的对话记录');r.mono.now+=29.9
    original_db=r.store._db;advanced=[]
    @contextmanager
    def delayed(write=False):
        with original_db(write) as db:
            if write and not advanced and db.execute("SELECT count(*) FROM bm_turns WHERE turn_id='public-command-2'").fetchone()[0]:
                r.mono.now+=.2;advanced.append(True)
            yield db
    monkeypatch.setattr(r.store,'_db',delayed)
    with pytest.raises(PermissionError):r.say('确认删除记录')
    assert advanced and r.state('public-target')=='valid'


class Bridge:
    def __init__(self):self.lock=threading.Lock();self.state=dict(reply=TEXT)
    def publish(self,state,frame):self.state=state


class Visual:
    def __init__(self):
        self.stream=None;self.pending=self.ready=self.audio_waiting=None
        self.reply=TEXT;self.turns=[];self.log=[];self.phase='IDLE'
        self.core=NS(reply_text=TEXT);self.output=NS(active=False,paused=False)
    def channel_event(self,header,pcm,owner,feedback_assets,requested_at):
        if header['kind']=='start':self.stream=dict(owner=owner)


class Recording:
    def __init__(self):self.controller=Visual();self.transcription=dict(state='ANSWERED',text=TEXT)
    def tick(self):return None
    def public(self):return dict(reply=self.controller.reply,local_transcription=dict(self.transcription))


def present(r):
    rec=Recording();jobs=NS(playback_invalidator=None,condition=threading.Condition(threading.RLock()),_active_job=None,active=None)
    jobs._current=lambda job:jobs._active_job is job and not job.cancelled.is_set()
    runtime=NS(config=NS(data_origin='board'),store=r.store,jobs=jobs,_foreground_idle=lambda:False)
    worker=NS(read=lambda:dict(state=dict(reply=TEXT,local_transcription=dict(text=TEXT))))
    stage=NS(board_business=NS(runtime=runtime),controller=worker,bridge=Bridge(),closed=False)
    life=presentation.bind_presentation(stage,rec,clock=r.mono)
    presentation.attach_presentation(stage)
    owner=dict(board_boot_id='public-review-boot',session_id='old-session',generation=1,request_id='old-display')
    for header in (dict(kind='start'),dict(kind='transcript',text=TEXT),dict(kind='text',text=TEXT)):
        rec.controller.channel_event(header,b'',owner,{},r.mono())
    return stage,rec,life,jobs,owner


def test_real_production_hook_runs_after_db_and_grant_exit_blocks_old_display_and_preserves_confirmation(r):
    access=ProfileAccess('9'*64,clock=r.mono);access.authenticate('9'*64)
    _,grant=access.issue('a'*32,dict(board_boot_id='public-review-boot',session_id='public-review-session'))
    r.store.profile_access=access;r.scope=dict(kind='profile',id='a'*32,grant=grant)
    seed(r);stage,rec,life,jobs,old=present(r)
    assert rec.public()['reply']==TEXT
    r.say('删除个人今天的对话记录');saved=pending(r)
    confirmation=dict(board_boot_id='public-review-boot',session_id='public-review-session',generation=2,request_id='public-command-2')
    jobs._active_job=NS(meta=confirmation,cancelled=threading.Event());jobs.active=confirmation['request_id']
    hook=r.store.notify_history_delete_committed;checks=[]
    def notify(**kwargs):
        # A SECOND writer can acquire: outer delete transaction has committed.
        with r.store._db(True) as db:
            assert db.execute("SELECT state FROM bm_events WHERE event_id='public-target'").fetchone()[0]=='forgotten'
        released=[]
        def other_thread():
            got=access.lock.acquire(timeout=.3);released.append(got)
            if got:access.lock.release()
        thread=threading.Thread(target=other_thread);thread.start();thread.join(.5)
        assert not thread.is_alive() and released==[True]
        checks.append(True);hook(**kwargs)
    r.store.notify_history_delete_committed=notify
    reply=r.say('确认删除记录')
    assert '已按预览删除' in reply and checks==[True] and life.invalidations==1
    assert rec.public()['reply']=='' and stage.bridge.state['reply']==''
    assert stage.controller.read()['state']['reply']==''
    # Queued old display headers cannot revive a forgotten source.
    rec.controller.channel_event(dict(kind='start'),b'',old,{},10.)
    rec.controller.channel_event(dict(kind='text',text=TEXT),b'',old,{},10.)
    assert rec.public()['reply']==''
    # Only the SAME committed command may show a new confirmation. Raw input
    # from even that command remains masked by the production lifecycle.
    rec.controller.channel_event(dict(kind='start'),b'',confirmation,{},10.)
    rec.controller.channel_event(dict(kind='transcript',text=TEXT),b'',confirmation,{},10.)
    rec.controller.channel_event(dict(kind='text',text=reply),b'',confirmation,{},10.)
    assert rec.public()['reply']==reply and rec.public()['local_transcription']['text']==''
    # Exact original idempotent receipt performs no second delete or repaint.
    result=r.handler._confirm(r.scope,start=saved['start'],end=saved['end'],fingerprint=saved['fingerprint'],
        operation_id='history-delete:public-command-2',operation_turn_id='public-command-2',
        preview_turn_id=saved['preview_turn_id'],validate_live=lambda:(_ for _ in ()).throw(AssertionError('cached delete reran')))
    assert result['status']=='deleted' and checks==[True] and life.invalidations==1


def test_rollback_never_notifies_bound_production_presentation(r,monkeypatch):
    seed(r);stage,rec,life,jobs,old=present(r);r.say('删除今天的对话记录')
    save=r.store._save_operation
    def fail_after_write(*args,**kwargs):save(*args,**kwargs);raise RuntimeError('public forced rollback')
    monkeypatch.setattr(r.store,'_save_operation',fail_after_write)
    with pytest.raises(RuntimeError,match='public forced rollback'):r.say('确认删除记录')
    assert r.state('public-target')=='valid' and life.invalidations==0 and rec.public()['reply']==TEXT


def test_deleted_source_rejects_cached_prepared_guard_and_original_late_full_ack(r):
    seed(r)
    old=r.controller.prepare_local_reply('公开旧请求',lambda:SourcedBoardReply('公开旧回复',source_event_ids=('public-target',)),
        scope=r.scope,session_id='old-session',generation=1,budget_ms=30000,turn_id='old-queued-turn')
    with r.store.prepared_turn_checker(old.turn_id,generation=1) as check:
        assert check()
        r.say('删除今天的对话记录');r.say('确认删除记录')
        assert r.state('public-target')=='forgotten'
        with pytest.raises((ScopeDenied,StaleTurn)):check()
    with pytest.raises((ScopeDenied,StaleTurn,StaleGeneration)):
        r.controller.acknowledge(old,playback_token=old.playback_token,sha256=old.sha256,samples=old.samples)
    assert r.state('public-target')=='forgotten'
