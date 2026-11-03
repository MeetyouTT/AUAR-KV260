"""Same-owner retries and cancellation at actual sole-worker/transaction seams."""
import threading
import importlib.util
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest

from board.runtime.board_speaker_business import BoardSpeakerBusiness
from tests.framework.test_board_business import Clock
from tests.framework.test_board_speaker_business import Encoder,MODEL,quality,capture,BOOT

QUESTION='你已经帮我把声纹登记保存成功了吗？'
HERE=Path(__file__).resolve().parents[1]


def make(tmp_path):
    clock=Clock()
    service=BoardSpeakerBusiness.create(tmp_path/'synthetic-only',encoder_factory=Encoder,
        board_boot_id=BOOT,quality=quality,expected_model_id=MODEL,anonymous_config={'enabled':True},
        wall_clock=lambda:1793400000.,clock=clock,data_origin='synthetic')
    return service,clock


def call(service,n,text,**kwargs):
    meta,raw=capture(n)
    return service.turn(meta,text,raw,**kwargs)


def samples(service):
    call(service,1,'登记我的声纹，我叫测试甲')
    for n in (2,3,4):call(service,n,'第'+str(n)+'段公开合成句子')


def inspect(service):
    return service.pool.submit(lambda:dict(people=len(service.hub.speaker.store.people()),
        revision=service.hub.speaker.store.revision,receipts=len(getattr(service.hub.speaker,'save_receipts',{})))).result(2)


@pytest.mark.parametrize('invalidator',['ttl61','speaker_revision'])
def test_real_business_same_rid_status_retry_rechecks_ttl_and_speaker_revision(tmp_path,invalidator):
    service,clock=make(tmp_path)
    try:
        samples(service);call(service,5,'确认保存声纹')
        meta,raw=capture(6)
        assert '已收到声纹保存提交回执' in service.turn(meta,QUESTION,raw)
        if invalidator=='ttl61':clock.now+=61
        else:
            def bump_public_fixture_revision():
                store=service.hub.speaker.store
                with store.db:store.db.execute("UPDATE metadata SET value=value+1 WHERE key='revision'")
            service.pool.submit(bump_public_fixture_revision).result(2)
        answer=service.turn(meta,QUESTION,raw)  # EXACT same rid/meta/text/PCM.
        assert '没有可核对' in answer and '不能判断' in answer
        assert '未保存' not in answer and inspect(service)['people']==1
    finally:assert service.close()


def test_original_write_retry_idempotency_and_fingerprint_refusal_survive(tmp_path):
    service,_=make(tmp_path)
    try:
        samples(service);meta,raw=capture(5)
        first=service.turn(meta,'确认保存声纹',raw);before=inspect(service)
        assert service.turn(meta,'确认保存声纹',raw)==first
        assert inspect(service)==before
        qmeta,qraw=capture(6)
        service.turn(qmeta,QUESTION,qraw)
        with pytest.raises(ValueError,match='reused with different input'):
            service.turn(qmeta,'声纹现在可用吗',qraw)
        assert inspect(service)['people']==1
    finally:assert service.close()


@pytest.mark.parametrize('seam',['before_commit','after_commit_before_post_current','after_post_current_before_adoption'])
def test_original_transaction_facts_and_cancelled_receipts_stay_separate(tmp_path,monkeypatch,seam):
    service,_=make(tmp_path);cancel=threading.Event()
    try:
        samples(service)
        store=service.hub.speaker.store;original_enroll=store.enroll
        if seam=='before_commit':
            def enroll(*args,**kwargs):raise ValueError('Synthetic original transaction failure')
            monkeypatch.setattr(store,'enroll',enroll)
        elif seam=='after_commit_before_post_current':
            def enroll(*args,**kwargs):
                result=original_enroll(*args,**kwargs)
                cancel.set()  # Original SQLite transaction has already returned.
                return result
            monkeypatch.setattr(store,'enroll',enroll)
        else:
            original_run=service._run
            def run_then_cancel(job,operation):
                result=original_run(job,operation)
                if job['meta']['generation']==5:cancel.set()
                return result
            monkeypatch.setattr(service,'_run',run_then_cancel)
        expected=ValueError if seam=='before_commit' else InterruptedError
        with pytest.raises(expected):call(service,5,'确认保存声纹',cancel_event=cancel)
        facts=inspect(service)  # FIFO worker barrier also completes metadata cleanup.
        assert facts['people']==(0 if seam=='before_commit' else 1)
        assert facts['receipts']==0
        answer=call(service,6,QUESTION)
        assert '已收到声纹保存提交回执' not in answer
        if seam!='before_commit':
            assert '不能判断' in answer and '未保存' not in answer
    finally:assert service.close()


def test_common_natural_status_questions_through_actual_paired_entry_do_not_add_voice_samples(tmp_path):
    from board.runtime.board_business import BoardBusinessConfig,BoardBusinessRuntime
    from common.conversation_selection import ConversationSelection
    from tests.framework.test_board_business import Timeline,Client,Asr,drain
    from tools.yuki_business_candidate import bind_runtime_pair
    path=HERE.parent.parent/'resume_yuki_business_candidate_v2/test_candidate_contracts.py'
    spec=importlib.util.spec_from_file_location('v3_real_pair_fixture',path)
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    pair,_,_=fixture.pair_ready();clock=Clock();timeline=Timeline();client=Client()
    timeline.boot_id=BOOT
    bundle=BoardBusinessRuntime(BoardBusinessConfig(str(tmp_path/'public-business'),
        (1793300000.,1793500000.)),BOOT,asr=Asr(),system_prompt=pair.selected_prompt,
        conversation_selection=ConversationSelection(tmp_path/'selection.json'),timeline=timeline,
        client=client,clock=clock,capture_idle=lambda:True,
        identity_snapshot=lambda:None,identity_command=lambda command:None)
    bind_runtime_pair(bundle,pair)
    service=BoardSpeakerBusiness.create(tmp_path/'public-speaker',encoder_factory=Encoder,
        board_boot_id=BOOT,quality=quality,expected_model_id=MODEL,anonymous_config={'enabled':True},
        wall_clock=timeline.event_time,clock=clock,data_origin='synthetic')
    bundle.attach_speaker_business(service);bundle.jobs.select_conversation(resume=False)
    def say(n,text):
        bundle.jobs.asr.text=text;pcm=struct.pack('<h',n*1000)*48000
        meta=bundle.jobs.submit(SimpleNamespace(capture_id='v3-paired-'+str(n),
            audio=SimpleNamespace(sample_count=48000),pcm=pcm))
        assert bundle.jobs.run_next()
        rows=drain(bundle.jobs)
        assert not any('error' in row for row in rows),rows
        spoken=''.join(row['channel_event']['text'] for row in rows
            if row.get('channel_event',{}).get('kind')=='text')
        complete=next(row['network_complete'] for row in rows if 'network_complete' in row)
        bundle.jobs.acknowledge(meta,complete);bundle.jobs.drain_actions()
        assert bundle.jobs.last_ack['committed']
        return spoken,meta
    try:
        say(1,'雪妃，登记我的声纹，我叫测试乙')
        for n,text in enumerate(('你有没有保存我的声纹？','你有没有帮我登记声纹',
                '你保存过我的声纹吗','我的声纹保存成功了吗'),2):
            answer,meta=say(n,text)
            assert '仍在采样' in answer
            def state():
                device=service.hub.speaker;row=device.sessions[device.key(meta)]
                return row['stage'],len(row['vectors']),len(row['hashes']),len(device.store.people())
            assert service.pool.submit(state).result(2)==('samples',0,0,0)
        assert not bundle.access.grants and all(kind=='tts' for kind,_ in client.calls)
    finally:bundle.close()
