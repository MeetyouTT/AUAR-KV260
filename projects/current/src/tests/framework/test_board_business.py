"""Board assembly, local authorization, capture leases; synthetic, no devices/ML."""
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import struct
import sys
import threading
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from board.runtime.board_business import (
    BoardBusinessConfig, BoardBusinessRuntime, LocalProfileSelections, LocalIdentityReplies,
    board_entry_policy, create_board_business_runtime,
)
from board.runtime.audio.board_capture import BoardFrontendPool, BoardAutomaticCapture, BoardBargeCapture
from common.board_memory import BoardMemoryStore
from common.conversation_selection import ConversationSelection
from common.model_inference_wire import Owner, make_response, audio_payload
from common.profile_access import ProfileAccess


class Clock:
    def __init__(self): self.now = 10.
    def __call__(self): return self.now


class Timeline:
    boot_id = 'test-boot'
    def __init__(self): self.good = True; self.known = True
    def event_time(self):
        if not self.known: raise RuntimeError('uninitialized')
        return 1793400000.
    def safe_for_compaction(self): return self.good
    def compaction_guard(self): return nullcontext()
    def quality_snapshot(self): return {'status': 'verified' if self.good else 'degraded'}


class Client:
    host, port = '192.168.50.1', 8797
    def __init__(self): self.calls = []; self.samples = 0
    def request(self, kind, payload, **kwargs):
        self.calls.append((kind, payload))
        text = json.dumps(dict(reply_text='我在听，慢慢说吧。', emotion='friendly', avatar_action=''), ensure_ascii=False)
        return make_response(Owner.from_dict(payload), result=(dict(text=text) if kind == 'llm' else
            dict(audio=audio_payload(b'\x01\x00' * 2400, 24000))))
    def cancel(self, owner): pass
    def sample_health_date(self, timeline, **kwargs): self.samples += 1; timeline.known = True; return {'verified': True}


class Asr:
    model_sha256 = 'a' * 64
    def __init__(self, text='今天聊点什么'): self.text = text
    def transcribe(self, pcm, **kwargs): return self.text


def runtime(tmp_path, **kwargs):
    clock, timeline, client = Clock(), Timeline(), Client()
    captured = SimpleNamespace(idle=True)
    value = BoardBusinessRuntime(BoardBusinessConfig(str(tmp_path/'private'), (1793300000., 1793500000.)),
        'test-boot', asr=Asr(), system_prompt='只输出三字段JSON的原人设。',
        conversation_selection=ConversationSelection(tmp_path/'conversation.json'),
        timeline=timeline, client=client, clock=clock, capture_idle=lambda: captured.idle, **kwargs)
    return value, clock, timeline, client, captured


def clip():
    pcm = struct.pack('<h', 1000) * 3200
    return SimpleNamespace(capture_id='clip-1', audio=SimpleNamespace(sample_count=3200), pcm=pcm)


def drain(jobs):
    result = []
    while True:
        value = jobs.poll()
        if value is None: return result
        result.append(value)


def test_factory_keeps_all_business_and_receipt_on_board(tmp_path):
    bundle, clock, timeline, client, capture = runtime(tmp_path)
    assert not bundle.started and client.calls == [] and bundle.jobs.thread is None
    assert bundle.store.clock == timeline.event_time
    bundle.jobs.select_conversation(resume=False)
    meta = bundle.jobs.submit(clip())
    assert not bundle.idle()
    assert bundle.jobs.run_next()
    values = drain(bundle.jobs)
    complete = next(item['network_complete'] for item in values if 'network_complete' in item)
    assert [kind for kind, _ in client.calls] == ['llm', 'tts']
    assert 'profile' not in json.dumps(client.calls, ensure_ascii=False)
    assert bundle.store.context({'kind': 'conversation', 'id': bundle.jobs.conversation_selection.active})['messages'][-1]['role'] == 'user'
    bundle.jobs.acknowledge(meta, complete)
    bundle.jobs.drain_actions()
    assert bundle.jobs.last_ack['committed'] and bundle.idle()
    capture.idle = False
    assert not bundle.idle()
    capture.idle = True; timeline.good = False
    assert not bundle.idle()
    bundle.close()


def test_start_requires_initial_clock_and_date_sampling_is_explicit(tmp_path):
    bundle, _, timeline, client, _ = runtime(tmp_path)
    timeline.known = False
    with pytest.raises(RuntimeError, match='uninitialized'): bundle.start()
    assert not bundle.started and client.samples == 0
    bundle.initialize_clock(timeout=1.)
    assert client.samples == 1
    bundle.start(); assert bundle.started
    bundle.close()


def test_clock_refresh_uses_existing_worker_before_step_and_never_idle(tmp_path):
    bundle, clock, timeline, client, capture = runtime(tmp_path)
    clock.now += 601.
    assert bundle.idle() and client.samples == 0
    capture.idle = False
    assert bundle.memory_worker.before_step(lambda: False) is False and client.samples == 0
    capture.idle = True
    assert bundle.memory_worker.before_step(lambda: False) is True and client.samples == 1
    assert bundle.memory_worker.before_step(lambda: False) is None and client.samples == 1
    bundle.close()


def test_clock_refresh_failure_is_bounded_backed_off_and_preserves_pending_data(tmp_path):
    bundle, clock, timeline, client, capture = runtime(tmp_path)
    scope = {'kind':'conversation', 'id':'a'*32}
    bundle.store.append_event(scope, 'old-event', 'device_event', '没有完成的公开测试事件')
    clock.now += 601.
    calls = []
    def fail(timeline, **kwargs):
        calls.append(kwargs)
        assert kwargs['deadline'] == clock() + 1.
        raise TimeoutError('fixture')
    client.sample_health_date = fail
    assert bundle.memory_worker.step() is False and len(calls) == 1
    assert bundle.memory_worker.step() is False and len(calls) == 1
    assert bundle.store.history(scope)[0]['text'] == '没有完成的公开测试事件'
    assert bundle.clock_refresh_error == 'TimeoutError'
    bundle.close()


def test_local_profile_selection_requires_same_process_authenticated_grant(tmp_path):
    clock = Clock(); access = ProfileAccess('a'*64, clock=clock)
    profiles = LocalProfileSelections(access, 'test-boot', lambda pid: None, wall_clock=lambda: 1793400000.)
    with pytest.raises(PermissionError): profiles.issue('b'*32, 'f'*64)
    wire = profiles.issue('b'*32, 'a'*64)
    selected = profiles.resolve(wire, 'test-boot')
    assert selected['scope']['kind'] == 'profile'
    with pytest.raises(PermissionError): profiles.resolve(wire, 'another-boot')
    forged = dict(wire, profile_id='c'*32)
    with pytest.raises(PermissionError): profiles.resolve(forged, 'test-boot')
    profiles.release(selected)
    with pytest.raises(PermissionError): profiles.resolve(wire, 'test-boot')
    profiles.close()


def test_factory_local_profile_new_context_uses_explicit_partition(tmp_path):
    access = ProfileAccess('a'*64)
    bundle, _, _, client, _ = runtime(tmp_path, profile_access=access)
    pid = bundle.store.create_profile('测试用户', consent=True)
    wire = bundle.profiles.issue(pid, 'a'*64)
    bundle.jobs.select_profile(wire)
    original = bundle.jobs.profile_selection['conversation_id']
    bundle.jobs.submit(clip()); bundle.jobs.run_next(); drain(bundle.jobs)
    bundle.jobs.cancel(); bundle.jobs.drain_actions()
    changed = bundle.jobs.select_conversation(resume=False)
    assert changed != original
    # Current facts remain authorized across conversations, recent text does not.
    scope = bundle.jobs.profile_selection['scope']
    assert bundle.store.context(scope, context_source_id='conversation:'+changed)['messages'] == []
    assert bundle.store.context(scope, context_source_id='conversation:'+original)['messages']
    bundle.close()
    assert not access.grants


def test_same_process_profile_control_has_a_real_local_selection_entry(tmp_path):
    from tools.board_profile_dialog import select_local_profile
    access = ProfileAccess('a'*64)
    bundle, _, _, _, _ = runtime(tmp_path, profile_access=access)
    with pytest.raises(PermissionError):
        select_local_profile(bundle, operator_key='f'*64, name='不得创建', consent=True)
    assert bundle.store.profiles() == []
    with pytest.raises(PermissionError):
        select_local_profile(bundle, operator_key='a'*64, name='尚未同意', consent=False)
    result = select_local_profile(bundle, operator_key='a'*64, name='本地测试', consent=True)
    assert result['mode'] == 'personal'
    assert bundle.jobs.profile_selection['scope']['id'] == result['profile_id']
    bundle.jobs.select_profile(None); bundle.jobs.drain_actions()
    select_local_profile(bundle, operator_key='a'*64, profile_id=result['profile_id'])
    assert bundle.jobs.profile_selection is not None
    bundle.close()


def test_voice_first_continuation_does_not_start_requiring_a_face():
    check = board_entry_policy('voice_first', 'test-boot', None, now_ms=lambda: 1000)
    assert check({'board_boot_id': 'test-boot'}, None, '等等，我还没说完', is_current=lambda: True)
    assert not check({'board_boot_id': 'other'}, None, '等等', is_current=lambda: True)
    assert not check({'board_boot_id': 'test-boot'}, None, '等等', is_current=lambda: False)
    with pytest.raises(ValueError): board_entry_policy('visual', 'test-boot', None, now_ms=lambda: 1000)


class FakeGate:
    def __init__(self):
        self.lock = threading.Lock(); self.closed = False; self.error = ''
        self.denoiser = self.vad = SimpleNamespace(reset=lambda: None)
        self.started = threading.Event(); self.finish = threading.Event()
    def __call__(self, frame):
        with self.lock:
            self.started.set(); self.finish.wait(2)
            return True
    def close(self): self.closed = True
    def public(self): return {'closed': self.closed}


def test_local_frontend_is_preloaded_once_and_does_not_reuse_inflight_state():
    gate = FakeGate(); pool = BoardFrontendPool(gate)
    first = pool.acquire(); errors = []
    def work():
        try: first([0]*320)
        except Exception as exc: errors.append(exc)
    thread = threading.Thread(target=work); thread.start()
    assert gate.started.wait(1)
    first.close()
    with pytest.raises(RuntimeError): pool.acquire()
    gate.finish.set(); thread.join(1)
    assert not thread.is_alive() and isinstance(errors[0], InterruptedError)
    second = pool.acquire(); assert second.pool.gate is gate
    second.close(); pool.close()
    with pytest.raises(RuntimeError): pool.acquire()


def test_local_capture_configuration_never_selects_remote_frontend():
    for capture_type, args in ((BoardAutomaticCapture, (lambda: False,)), (BoardBargeCapture, (object(),))):
        with pytest.raises(ValueError, match='legacy network frontend'):
            capture_type(*args, frontend_factory=lambda: None, audio_frontend={'enabled': True})


def test_local_handler_is_not_called_before_scope_authorization(tmp_path):
    bundle, _, _, client, _ = runtime(tmp_path)
    called = []
    with pytest.raises(PermissionError):
        bundle.controller.prepare_local_reply('你还认识我吗', lambda: called.append(True),
            scope={'kind': 'profile', 'id': 'f'*32}, session_id='s', generation=1, budget_ms=3000)
    assert not called and not client.calls
    bundle.close()


def test_local_reply_uses_tts_and_full_ack_without_llm(tmp_path):
    from board.runtime.board_dialogue import BoardReply
    bundle, _, _, client, _ = runtime(tmp_path)
    plan = bundle.controller.prepare_local_reply('测试本地提示', lambda: BoardReply('这是本地验证提示。'),
        scope={'kind': 'conversation', 'id': 'c'*32}, session_id='s', generation=1, budget_ms=3000)
    assert [kind for kind, _ in client.calls] == ['tts']
    assert not bundle.controller.idle
    bundle.controller.acknowledge(plan, playback_token=plan.playback_token, sha256=plan.sha256, samples=plan.samples)
    assert bundle.controller.idle
    bundle.close()


def test_device_answer_has_same_scope_sources_and_no_fabricated_user_quote(tmp_path):
    from board.runtime.board_dialogue import SourcedBoardReply
    bundle, _, _, client, _ = runtime(tmp_path)
    scope = {'kind':'device', 'id':'board-camera'}
    bundle.store.append_event(scope, 'camera-source', 'camera_observed', '稳定检测到2个人。')
    plan = bundle.controller.prepare_local_reply('设备查询意图（规范化）：当前人数',
        lambda: SourcedBoardReply('目前稳定检测到2个人。', source_event_ids=('camera-source',)),
        scope=scope, session_id='device-query', generation=1, budget_ms=3000,
        topic='视觉查询答复', input_source='device_event',
        metadata={'claims':[{'field':'input_representation','value':'normalized_visual_query'}]})
    bundle.controller.acknowledge(plan, playback_token=plan.playback_token, sha256=plan.sha256, samples=plan.samples)
    rows = bundle.store.history(scope)
    assert not any(row['source'] == 'user_said' for row in rows)
    bundle.store.forget(scope, event_ids=('camera-source',))
    assert not any(row['text'] == '目前稳定检测到2个人。' for row in bundle.store.history(scope))
    assert [kind for kind, _ in client.calls] == ['tts']
    bundle.close()


def test_sourced_local_answer_cannot_smuggle_device_provenance_into_private_conversation(tmp_path):
    from board.runtime.board_dialogue import SourcedBoardReply
    bundle, _, _, client, _ = runtime(tmp_path)
    bundle.store.append_event({'kind':'device','id':'board-camera'}, 'device-only', 'camera_observed', '稳定检测到2个人。')
    with pytest.raises(PermissionError):
        bundle.controller.prepare_local_reply('现在几个人',
            lambda: SourcedBoardReply('有2个人。', source_event_ids=('device-only',)),
            scope={'kind':'conversation','id':'a'*32}, session_id='s', generation=1, budget_ms=3000)
    assert not client.calls
    bundle.close()


def test_composed_speaker_router_keeps_a_bare_name_as_ordinary_dialogue(tmp_path):
    bundle, clock, timeline, client, _ = runtime(tmp_path,
        identity_snapshot=lambda: None, identity_command=lambda command: None)
    class Business:
        boot, data_origin, config = 'test-boot', 'synthetic', {'enabled':True}
        wall_clock = timeline.event_time
        def __init__(self): self.clock = clock; self.closed = False
        def public(self): return {'active':False}
        def health(self): return {'queued_or_active':0}
        def route(self, meta, text, pcm, **kwargs):
            return dict(version=1,context=meta,binding_request=None,analysis_mode='TRACKER',
                decision=dict(route='ordinary',reply=None,attempt_id=None,board_text=None,
                              reason='SELF_NAME_HINT_NOT_ENROLLMENT_CONSENT',skip_legacy_device_command=False,
                              unified_saved=False,personal_memory_allowed=False))
        def turn(self, meta, text, pcm, **kwargs): return None
        def submit_analysis(self, *args, **kwargs): return None
        def reset(self): pass
        def close(self): self.closed = True; return True
    business = Business(); bundle.attach_speaker_business(business)
    bundle.jobs.asr.text = '我叫小林'
    bundle.jobs.select_conversation(resume=False)
    bundle.jobs.submit(clip()); bundle.jobs.run_next(); values = drain(bundle.jobs)
    assert any('network_complete' in value for value in values)
    assert [kind for kind, _ in client.calls] == ['llm', 'tts']
    context = bundle.store.context({'kind':'conversation','id':bundle.jobs.conversation_selection.active})
    assert [row['content'] for row in context['messages'] if row['role']=='user'] == ['我叫小林']
    bundle.close(); assert business.closed


def test_original_three_sample_speaker_workflow_through_jobs_and_one_player_ack(tmp_path):
    from board.runtime.board_speaker_business import BoardSpeakerBusiness
    from tests.framework.test_board_speaker_business import Encoder, MODEL, quality
    bundle, clock, timeline, client, _ = runtime(tmp_path,
        identity_snapshot=lambda: None, identity_command=lambda command: None)
    encoder = Encoder()
    business = BoardSpeakerBusiness.create(tmp_path/'speaker-synthetic', encoder_factory=lambda: encoder,
        board_boot_id='test-boot', quality=quality, expected_model_id=MODEL,
        anonymous_config={'enabled':True}, wall_clock=timeline.event_time, clock=clock, data_origin='synthetic')
    bundle.attach_speaker_business(business)
    bundle.jobs.select_conversation(resume=False)
    for index, text in enumerate(('登记我的声纹，我叫小林', '我今天看了书', '我正在准备午饭',
                                  '我晚上准备散步', '确认保存声纹'), 1):
        bundle.jobs.asr.text = text
        pcm = struct.pack('<h', index * 1000) * 48000
        value = SimpleNamespace(capture_id='public-capture-'+str(index),
                                audio=SimpleNamespace(sample_count=48000), pcm=pcm)
        meta = bundle.jobs.submit(value); assert bundle.jobs.run_next()
        output = drain(bundle.jobs)
        complete = next(item['network_complete'] for item in output if 'network_complete' in item)
        bundle.jobs.acknowledge(meta, complete); bundle.jobs.drain_actions()
        assert bundle.jobs.last_ack['committed']
        if index < 5:
            assert business.pool.submit(lambda: len(business.hub.speaker.store.people())).result(1.) == 0
    assert business.pool.submit(lambda: len(business.hub.speaker.store.people())).result(1.) == 1
    assert all(kind == 'tts' for kind, _ in client.calls)
    assert not business.public()['speaker_calibrated'] and not bundle.access.grants
    bundle.close()


def test_board_mode_cannot_bypass_board_kernel_lock_on_windows(tmp_path):
    import os
    if os.name != 'nt': pytest.skip('Windows rejection path')
    config = BoardBusinessConfig(str(tmp_path/'board'), (1793300000., 1793500000.), data_origin='board')
    with pytest.raises(RuntimeError, match='POSIX'):
        create_board_business_runtime(config, 'test-boot')
    assert not (tmp_path/'board').exists()
