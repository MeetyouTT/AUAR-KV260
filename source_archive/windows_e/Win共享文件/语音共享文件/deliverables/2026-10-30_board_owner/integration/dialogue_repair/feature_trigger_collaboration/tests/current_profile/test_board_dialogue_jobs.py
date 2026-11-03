"""Light synthetic job/stream/receipt tests; no devices, sockets or ML imports.

No GPU/ARM/service/model work. ASR/model classes below are injected fixtures.
"""
import copy
from dataclasses import replace
import hashlib
from pathlib import Path
import struct
import sys
import threading
from types import SimpleNamespace
import uuid

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from board.runtime.audio.board_dialogue_jobs import BoardCapabilityNotReady, BoardDialogueJobs, PlaybackPayload
from board.runtime.board_dialogue import AudioChunk, BoardReply, PlaybackPlan, StaleGeneration
from common.model_inference_wire import Owner
from common.voice_channel import ChannelState


class Clock:
    def __init__(self): self.now = 10.
    def __call__(self): return self.now


class Asr:
    def __init__(self, text='今天有点累', clock=None):
        self.text, self.clock, self.calls, self.hook = text, clock, [], None
        self.model_sha256 = 'a' * 64
    def transcribe(self, pcm, **kwargs):
        self.calls.append((pcm, kwargs))
        if self.hook: self.hook()
        if self.clock: self.clock.now += .1
        return self.text


class Controller:
    board_boot_id = 'synthetic-boot'
    def __init__(self, asr, *, rate=24000, samples=2400):
        self.asr, self.rate, self.samples = asr, rate, samples
        self.command_handler = object()
        self.context_builder = object()
        self.calls, self.cancelled, self.acks = [], [], []
        self.plans = {}
        self.hook = None
        self.preemptions = 0
        self.store = SimpleNamespace(preempt_compaction=self._preempt)
    def _preempt(self):
        self.preemptions += 1
    def prepare_text(self, text, **kwargs):
        self.calls.append((text, kwargs))
        if self.hook: self.hook()
        pcm = b'\x01\x00' * self.samples
        owner = Owner(uuid.uuid4().hex, self.board_boot_id, kwargs['session_id'], kwargs['generation'])
        plan = PlaybackPlan(self.board_boot_id, kwargs['session_id'], kwargs['generation'], kwargs['turn_id'],
            uuid.uuid4().hex, BoardReply('我会陪你聊聊。', 'friendly'),
            (AudioChunk(owner, '我会陪你聊聊。', pcm, self.rate),), hashlib.sha256(pcm).hexdigest(),
            self.samples, self.rate)
        self.plans[plan.turn_id] = plan
        return plan
    def cancel(self, session_id, *, generation):
        self.cancelled.append((session_id, generation)); return True
    def acknowledge(self, plan, **kwargs):
        assert kwargs == dict(playback_token=plan.playback_token, sha256=plan.sha256, samples=plan.samples, complete=True)
        self.acks.append((plan, kwargs)); return {'status': 'played'}


def clip(capture='synthetic-capture'):
    pcm = struct.pack('<h', 1000) * 3200
    return SimpleNamespace(capture_id=capture, audio=SimpleNamespace(sample_count=3200), pcm=pcm)


def setup(*, text='今天有点累', rate=24000, **kwargs):
    clock = Clock(); asr = Asr(text, clock); controller = Controller(asr, rate=rate)
    invalidations = []
    job = BoardDialogueJobs(controller,
        dict(enabled=True, host='192.168.50.1', port=8808, timeout_ms=30000), 'synthetic-boot',
        scope_provider=lambda meta: {'kind': 'conversation', 'id': 'a' * 32},
        playback_invalidator=lambda reason, owner: invalidations.append((reason, owner)),
        clock=clock, wall_clock=lambda: 1793376000., start_worker=False, **kwargs)
    return job, controller, asr, clock, invalidations


def collect(job):
    values = []
    while True:
        value = job.poll()
        if value is None: return values
        values.append(value)


def prepare(job, capture='synthetic-capture'):
    meta = job.submit(clip(capture)); assert job.run_next()
    return meta, collect(job)


def completion(values):
    return next(v['network_complete'] for v in values if 'network_complete' in v)


def test_existing_stream_contract_and_verified_local_ack():
    job, controller, asr, clock, invalidated = setup()
    meta, values = prepare(job)
    state = ChannelState(meta)
    for value in values:
        if 'channel_event' in value: state.accept(value['channel_event'], value['pcm'])
    assert state.ended and state.samples == 2400
    kinds = [v['channel_event']['kind'] for v in values if 'channel_event' in v]
    assert kinds[:4] == ['start', 'transcript', 'text', 'control'] and kinds[-1] == 'end'
    assert [v['channel_event']['start_sample'] for v in values if v.get('channel_event', {}).get('kind') == 'audio'] == [0, 480, 960, 1440, 1920]
    assert controller.acks == []
    result = completion(values); job.acknowledge(meta, result)
    assert controller.acks == []  # Store/network cleanup is off the audio owner.
    job.drain_actions()
    assert len(controller.acks) == 1 and job.last_ack['committed']
    assert job.public()['pending'] is False
    assert asr.calls[0][1]['deadline'] == 40.
    assert controller.calls[0][1]['budget_ms'] <= 29900
    assert invalidated[-1][0] == 'playback_token_changed'


@pytest.mark.parametrize('field,value', [('sample_count', 1), ('pcm_sha256', '0' * 64), ('playback_token', 'wrong')])
def test_receipt_tampering_cannot_write_played(field, value):
    job, controller, *_ = setup(); meta, values = prepare(job)
    result = dict(completion(values)); result[field] = value
    with pytest.raises((StaleGeneration, ValueError)): job.acknowledge(meta, result)
    job.drain_actions(); assert controller.acks == []


def test_cancel_new_generation_and_queued_ack_are_invalidated():
    job, controller, *_ = setup(); old, values = prepare(job)
    result = completion(values); job.acknowledge(old, result)
    job.cancel(); job.drain_actions()
    assert controller.acks == [] and controller.cancelled
    with pytest.raises(StaleGeneration): job.acknowledge(old, result)
    new, values = prepare(job, 'new-capture')
    assert new['generation'] > old['generation']
    with pytest.raises(StaleGeneration):
        job.playback_clock(old, playback_token=result['playback_token'], position_seconds=.05)


def test_only_latest_waiting_capture_is_recognized():
    job, controller, asr, *_ = setup()
    old = job.submit(clip('old-capture')); new = job.submit(clip('new-capture'))
    assert new['generation'] > old['generation'] and job.run_next()
    assert len(asr.calls) == 1 and controller.calls[0][1]['turn_id'] == new['request_id']
    assert all(v['context']['capture_id'] == 'new-capture' for v in collect(job))


def test_new_board_job_preempts_summary_before_asr_and_holds_idle_until_ack():
    job, controller, asr, *_ = setup()
    assert job.idle
    def during_asr():
        assert controller.preemptions == 1 and not job.idle
    asr.hook = during_asr
    meta = job.submit(clip()); assert not job.idle
    job.run_next(); values = collect(job); assert not job.idle
    job.acknowledge(meta, completion(values)); assert not job.idle
    job.drain_actions(); assert job.idle


def test_cancel_during_asr_drops_text_before_model():
    job, controller, asr, *_ = setup(); asr.hook = job.cancel
    prepare(job)
    assert controller.calls == [] and collect(job) == []
    job.drain_actions()


def test_original_deadline_includes_board_asr_and_queueing():
    job, controller, asr, clock, *_ = setup()
    job.submit(clip()); clock.now = 41.
    assert job.run_next()
    assert not asr.calls and not controller.calls
    assert collect(job)[0]['error'] == 'TimeoutError'


def test_non24k_plan_fails_closed_and_keeps_native_receipt():
    job, controller, *_ = setup(rate=48000)
    meta, values = prepare(job)
    assert values[-1]['error'] == 'board_handler_not_ready:native_rate_playback_bridge'
    assert not any('network_complete' in v for v in values)
    plan = controller.plans[meta['request_id']]
    assert plan.sample_rate == 48000 and plan.samples == 2400
    job.drain_actions(); assert controller.cancelled and not controller.acks


def test_explicit_rate_bridge_has_distinct_played_and_native_receipts():
    def converter(plan):
        assert plan.sample_rate == 48000
        return PlaybackPayload(b'\x01\x00' * (plan.samples // 2), converter_id='reviewed-synthetic-half-rate')
    job, controller, *_ = setup(rate=48000, audio_converter=converter)
    meta, values = prepare(job); result = completion(values)
    assert result['sample_count'] == 1200 and result['source_receipt']['samples'] == 2400
    assert result['sample_rate'] == 24000 and result['source_receipt']['sample_rate'] == 48000
    assert job.playback_clock(meta, playback_token=result['playback_token'], position_seconds=.025)['audio_sample'] == 600
    job.acknowledge(meta, result); job.drain_actions()
    assert controller.acks[0][1]['samples'] == 2400


def test_lip_clock_is_sink_seconds_times_24000_and_owner_bound():
    job, *_ = setup(); meta, values = prepare(job); result = completion(values)
    clock = job.playback_clock(meta, playback_token=result['playback_token'], position_seconds=.05)
    assert clock['audio_sample'] == 1200
    with pytest.raises(StaleGeneration): job.playback_clock(meta, playback_token='wrong', position_seconds=.05)
    with pytest.raises(ValueError): job.playback_clock(meta, playback_token=result['playback_token'], position_seconds=float('nan'))
    job.close()
    with pytest.raises(StaleGeneration): job.playback_clock(meta, playback_token=result['playback_token'], position_seconds=.05)


@pytest.mark.parametrize('text,expected', [
    ('帮我登记身份', 'identity_enrollment'), ('雪妃，记住我', 'identity_enrollment'),
    ('你还认识我吗', 'identity_query'), ('确认登记', 'identity_enrollment'),
    ('帮我登记声纹', 'speaker_identity'), ('删除昨天的记录', 'history_delete_preview'),
    ('确认删除', 'history_delete_preview'), ('你看到了什么', 'structured_visual_query'),
    ('帮我计算58乘3', 'reasoning_dialogue'),
])
def test_missing_sensitive_board_handlers_never_fall_back_to_model(text, expected):
    job, controller, *_ = setup(text=text)
    _, values = prepare(job)
    assert values[-1]['error'] == 'board_handler_not_ready:' + expected
    assert not controller.calls


def test_explicit_memory_precedes_reasoning_and_retains_raw_alias():
    text = '雪妃，记住：价格是50+20'
    job, controller, *_ = setup(text=text)
    prepare(job)
    assert controller.calls[0][0] == text
    assert controller.calls[0][1]['history_query'] is None


def test_history_only_when_explicit_and_current_chat_stays_small():
    job, controller, *_ = setup(); prepare(job)
    assert controller.calls[0][1]['history_query'] is None
    job.cancel(); job.drain_actions(); job.asr.text = '回忆昨天我们聊了什么'
    prepare(job, 'history-capture')
    query = controller.calls[-1][1]['history_query']
    assert query is not None and set(query) == {'start', 'end', 'search', 'limit'}
    assert query['start'] < query['end'] and 'topic' not in query
    assert query['search'] is None


def test_explicit_historical_subject_is_sent_to_search_not_exact_topic():
    job, controller, *_ = setup(text='回忆昨天我们聊过海风项目什么')
    prepare(job)
    selected = controller.calls[-1][1]['history_query']
    assert selected['search'] == '海风项目' and 'topic' not in selected


def test_wake_alias_and_wake_only_follow_existing_audio_gate():
    job, controller, *_ = setup(text='雪妃')
    job.mark_wake_entry('synthetic-capture'); meta, values = prepare(job)
    assert values == [dict(wake_detected=True, wake_only=True, context=meta)]
    assert controller.calls == []
    job.asr.text = '雪妃，今天有点累'
    job.mark_wake_entry('new-capture'); _, values = prepare(job, 'new-capture')
    assert controller.calls[-1][0] == '今天有点累'
    assert any(v.get('wake_detected') and not v['wake_only'] for v in values)


def test_wake_requires_audio_and_rejects_unrelated_words():
    job, controller, *_ = setup(text='今天有点累')
    job.mark_wake_entry('synthetic-capture'); _, values = prepare(job)
    assert values[-1]['entry_rejected'] and not controller.calls
    silent = clip('silent-capture'); silent.pcm = bytes(len(silent.pcm))
    job.asr.text = '雪妃，陪我聊聊'; job.mark_wake_entry(silent.capture_id)
    job.submit(silent); job.run_next(); assert collect(job)[-1]['entry_rejected']


def test_visual_entry_and_profile_selection_are_explicitly_unavailable_without_local_grants():
    job, controller, *_ = setup()
    job.mark_visual_entry('synthetic-capture'); _, values = prepare(job)
    assert values[-1]['error'] == 'board_handler_not_ready:visual_entry_authorization'
    assert not controller.calls
    with pytest.raises(BoardCapabilityNotReady): job.select_profile({'access_token': 'a' * 64})
    assert job.profile_selection is None
    assert job.public()['drop_in_complete'] is False


def test_configuration_and_close_never_start_capture_or_legacy_business_transport():
    job, controller, *_ = setup()
    assert job.thread is None and job.action_thread is None
    with pytest.raises(BoardCapabilityNotReady): job.configure(dict(job.config, port=8792))
    job.configure(dict(job.config, timeout_ms=5000)); assert job.config['timeout_ms'] == 5000
    job.close(); job.close()
    with pytest.raises(ValueError): job.submit(clip())
    assert controller.calls == []


def test_live_profile_grants_remain_only_in_board_scope():
    released = []
    grant = object()
    def resolver(value, boot):
        return dict(scope=dict(kind='profile', id='b' * 32, grant=grant),
                    session_id='profile-session', conversation_id='c' * 32)
    job, controller, *_ = setup(profile_resolver=resolver, profile_release=released.append)
    job.select_profile({'mode': 'explicit-board-local'}); meta, values = prepare(job)
    assert controller.calls[0][1]['scope']['grant'] is grant
    assert 'grant' not in meta and 'profile_id' not in meta
    job.cancel(); job.drain_actions(); job.select_profile(None); job.drain_actions()
    assert released and job.profile_selection is None


def test_personal_new_conversation_changes_only_local_recent_context_partition():
    def resolver(value, boot):
        return dict(scope=dict(kind='profile',id='b'*32,grant=object()),
                    session_id='profile-session',conversation_id='c'*32)
    job, *_ = setup(profile_resolver=resolver,profile_release=lambda value:None)
    job.select_profile({'mode':'explicit-board-local'})
    grant = job.profile_selection['scope']['grant']
    cid = job.select_conversation(resume=False)
    assert cid != 'c'*32 and len(cid) == 32
    assert job.select_conversation(resume=True) == cid
    assert job.profile_selection['scope']['grant'] is grant
    _, _ = prepare(job)
    assert job.controller.calls[-1][1]['metadata']['source_id'] == 'conversation:' + cid
    job.close(); job.drain_actions()


def test_history_without_injected_trusted_clock_fails_closed():
    job, controller, *_ = setup(text='回忆昨天我们聊了什么')
    job.wall_clock = None
    _, values = prepare(job)
    assert values[-1]['error'] == 'board_handler_not_ready:trusted_history_clock'
    assert controller.calls == []


def test_real_board_store_memory_and_history_flow_without_legacy_services(tmp_path):
    import json
    from common.board_memory import BoardMemoryStore
    from common.model_inference_wire import make_response, audio_payload
    from board.runtime.board_dialogue import BoardDialogueController
    from board.runtime.board_memory_policy import BoardContextBuilder, BoardMemoryCommands
    class Store(BoardMemoryStore):
        def history_with_status(self, scope, **kwargs):
            self.history_calls.append((scope, kwargs))
            return super().history_with_status(scope, **kwargs)
    class Models:
        def __init__(self): self.calls = []
        def request(self, kind, payload, **kwargs):
            self.calls.append((kind, payload))
            result = (dict(text=json.dumps(dict(reply_text='我会陪你继续聊。', emotion='friendly', avatar_action='')))
                      if kind == 'llm' else dict(audio=audio_payload(b'\1\0' * 800)))
            return make_response(Owner.from_dict(payload), result=result)
        def cancel(self, owner): return None
    clock = Clock(); store = Store(tmp_path / 'synthetic.db', clock=lambda:1000.)
    store.history_calls = []; models = Models()
    raw = '雪妃，记住：项目是海风'; asr = Asr(raw, clock)
    builder = BoardContextBuilder('只返回原三字段JSON。')
    controller = BoardDialogueController(store, models, board_boot_id='synthetic-boot',
        system_prompt='只返回原三字段JSON。', asr=asr, clock=clock,
        command_handler=BoardMemoryCommands(store), context_builder=builder)
    scope = dict(kind='conversation', id='a' * 32)
    job = BoardDialogueJobs(controller,
        dict(enabled=True,host='192.168.50.1',port=8808,timeout_ms=30000), 'synthetic-boot',
        scope_provider=lambda meta:scope, clock=clock, wall_clock=lambda:1000., start_worker=False)
    meta, values = prepare(job)
    assert [kind for kind,_ in models.calls] == ['tts']
    assert store.context(scope)['facts'][0]['value'] == '海风'
    assert raw in [m['content'] for m in store.context(scope)['messages']]
    assert not any(m['role'] == 'assistant' for m in store.context(scope)['messages'])
    job.acknowledge(meta, completion(values)); job.drain_actions()
    assert any(m['role'] == 'assistant' for m in store.context(scope)['messages'])
    asr.text = '今天有点累'; meta, values = prepare(job, 'ordinary-capture')
    assert store.history_calls == []
    job.acknowledge(meta, completion(values)); job.drain_actions()
    asr.text = '回忆刚才我们聊了什么'; meta, values = prepare(job, 'history-capture')
    assert len(store.history_calls) == 1 and builder.metrics['history_requested']
    assert store.history_calls[0][0] == scope
    job.cancel(); job.drain_actions(); job.close()


def test_cancel_between_job_check_and_controller_registration_cannot_start_model(tmp_path):
    from common.board_memory import BoardMemoryStore
    from board.runtime.board_dialogue import BoardDialogueController
    entered = threading.Event(); release = threading.Event()
    class Models:
        def __init__(self): self.calls = []
        def request(self, *args, **kwargs): self.calls.append(args); raise AssertionError('Cancelled model request')
        def cancel(self, owner): return None
    def delayed_scope(scope, metadata):
        entered.set(); assert release.wait(2)
        return scope
    clock = Clock(); asr = Asr(clock=clock); models = Models()
    store = BoardMemoryStore(tmp_path / 'synthetic.db', clock=lambda:1000.)
    controller = BoardDialogueController(store,models,board_boot_id='synthetic-boot',
        system_prompt='synthetic',asr=asr,clock=clock,scope_resolver=delayed_scope)
    job = BoardDialogueJobs(controller,
        dict(enabled=True,host='192.168.50.1',port=8808,timeout_ms=30000),'synthetic-boot',
        scope_provider=lambda meta:dict(kind='conversation',id='a'*32),clock=clock,start_worker=False)
    meta = job.submit(clip()); thread = threading.Thread(target=job.run_next)
    thread.start(); assert entered.wait(2)
    job.cancel(); job.drain_actions()  # Controller has no registered owner yet.
    release.set(); thread.join(2); assert not thread.is_alive()
    assert models.calls == [] and controller.idle and collect(job) == []
    assert store.context({'kind':'conversation','id':'a'*32})['messages'] == []
    with pytest.raises(StaleGeneration):
        job.acknowledge(meta,dict(sample_count=1,pcm_sha256='a'*64,playback_token='stale'))
    job.close()


def test_external_cancel_while_transport_blocked_still_cancels_remote_owner(tmp_path):
    from common.board_memory import BoardMemoryStore
    from board.runtime.board_dialogue import BoardDialogueController
    entered = threading.Event(); release = threading.Event(); external = threading.Event()
    class Models:
        def __init__(self): self.cancelled = []
        def request(self, kind, payload, **kwargs):
            self.owner = Owner.from_dict(payload); entered.set(); assert release.wait(2)
            assert kwargs['cancelled']()
            raise InterruptedError('Synthetic blocked transport cancelled')
        def cancel(self, owner): self.cancelled.append(owner)
    models = Models(); store = BoardMemoryStore(tmp_path/'synthetic.db',clock=lambda:1000.)
    controller = BoardDialogueController(store,models,board_boot_id='synthetic-boot',system_prompt='synthetic')
    errors = []
    def prepare_blocked():
        try:
            controller.prepare_text('公开合成测试',scope={'kind':'conversation','id':'a'*32},
                session_id='synthetic-session',generation=1,budget_ms=30000,cancel_event=external)
        except Exception as exc: errors.append(exc)
    thread = threading.Thread(target=prepare_blocked); thread.start(); assert entered.wait(2)
    external.set(); release.set(); thread.join(2); assert not thread.is_alive()
    assert len(errors) == 1 and isinstance(errors[0],InterruptedError)
    assert models.cancelled == [models.owner] and controller.idle
    assert any(m['content']=='公开合成测试' for m in store.context({'kind':'conversation','id':'a'*32})['messages'])


def test_controller_failure_shared_event_still_delivers_current_error_frame(tmp_path):
    from common.board_memory import BoardMemoryStore
    from board.runtime.board_dialogue import BoardDialogueController
    class Models:
        def request(self,*args,**kwargs): raise TimeoutError('synthetic transport timeout')
        def cancel(self,owner): return None
    clock=Clock(); asr=Asr(clock=clock); store=BoardMemoryStore(tmp_path/'synthetic.db',clock=lambda:1000.)
    controller=BoardDialogueController(store,Models(),board_boot_id='synthetic-boot',
        system_prompt='synthetic',asr=asr,clock=clock)
    job=BoardDialogueJobs(controller,dict(enabled=True,host='192.168.50.1',port=8808,timeout_ms=30000),
        'synthetic-boot',scope_provider=lambda meta:dict(kind='conversation',id='a'*32),clock=clock,start_worker=False)
    _, values=prepare(job)
    assert values[-1]['error']=='TimeoutError' and job.public()['pending'] is False
    job.drain_actions(); job.close()
