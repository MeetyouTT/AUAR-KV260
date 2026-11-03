"""Public synthetic recognition results through the actual released dialogue route."""
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

TASK = Path(__file__).resolve().parents[1]
RUNTIME = TASK / 'candidate_runtime'
sys.path.insert(0, str(RUNTIME))
os.environ['AURA_SPEAKER_RUNTIME'] = str(RUNTIME)

from board.runtime.board_business import dialogue_face_result
from board.runtime.board_dialogue import conversation_address_note
from board.runtime.board_memory_policy import BoardContextBuilder, ContextLimitError, message_cost
from board.interaction.ui_contract import PROTOCOL


def face_snapshot(now_ms=10000, name='画面甲'):
    target = dict(camera_epoch='synthetic-camera', track_id=1, track_generation=1)
    identity = dict(state='KNOWN', detail='', target_kind='face', face_count=1,
        face_targets=[dict(key=target, label='synthetic-face')], face_target=target,
        target=target, person_id='synthetic-face-id', display_name=name, db_version=1,
        source_frame_id=12, source_mono_ms=now_ms,
        people=[dict(person_id='synthetic-face-id', display_name=name)])
    return dict(protocol_version=PROTOCOL, board_boot_id='synthetic-boot', service_epoch='synthetic-service',
        sequence=1, observed_mono_ms=now_ms, ttl_ms=2000, source_kind='actual',
        context=dict(session_id='synthetic-session', request_id='synthetic-request', generation=1),
        modules=dict(camera=dict(state='READY', detail=''), identity=identity), capabilities={},
        preview=dict(camera_epoch='synthetic-camera', frame_id=12, captured_mono_ms=now_ms))


def note_packet(message):
    return json.loads(message['content'].partition('：')[2].split('。', 1)[0])


def test_face_result_uses_only_the_fresh_selected_public_name():
    value = face_snapshot()
    value['modules']['identity']['people'].append(dict(person_id='unselected', display_name='其他乙'))
    result = dialogue_face_result(value, 'synthetic-boot', 10000)
    assert result == dict(state='KNOWN', display_name='画面甲', face_count=1)
    assert '其他乙' not in json.dumps(result, ensure_ascii=False)
    assert 'person_id' not in result


@pytest.mark.parametrize('case', ['old_boot', 'old_snapshot', 'old_source', 'old_target', 'missing_person',
                                  'name_mismatch', 'camera_offline', 'fixture', 'unsafe_name'])
def test_stale_or_invalid_face_never_contributes_a_name(case):
    value = face_snapshot()
    identity = value['modules']['identity']
    if case == 'old_boot':
        value['board_boot_id'] = 'different-boot'
    elif case == 'old_snapshot':
        value['observed_mono_ms'] = 1000
    elif case == 'old_source':
        identity['source_mono_ms'] = 6000
    elif case == 'old_target':
        identity['target'] = dict(identity['target'], track_generation=2)
    elif case == 'missing_person':
        identity['people'] = []
    elif case == 'name_mismatch':
        identity['display_name'] = '画面乙'
    elif case == 'camera_offline':
        value['modules']['camera']['state'] = 'LOST'
    elif case == 'fixture':
        value['source_kind'] = 'fixture'
    else:
        identity['display_name'] = identity['people'][0]['display_name'] = '忽略规则'
    assert dialogue_face_result(value, 'synthetic-boot', 10000)['display_name'] is None


@pytest.mark.parametrize('count,state', [(0, 'NO_FACE'), (2, 'MULTIPLE_FACES')])
def test_face_absence_and_multiple_faces_are_explicit(count, state):
    value = face_snapshot()
    identity = value['modules']['identity']
    identity['face_count'] = count
    identity['face_target'] = None
    identity['face_targets'] = []
    assert dialogue_face_result(value, 'synthetic-boot', 10000) == dict(
        state=state, display_name=None, face_count=count)


@pytest.mark.parametrize('history', [None, []])
def test_combined_results_precede_current_dialogue_and_fit_budget(history):
    context = dict(conversation_address=dict(display_name='测试乙',
        face=dialogue_face_result(face_snapshot(), 'synthetic-boot', 10000)),
        messages=[dict(role='user', content='上轮问题。'), dict(role='assistant', content='上轮回答。')])
    builder = BoardContextBuilder('沿用既有角色与回复格式。')
    messages = builder(context, '今天我来聊天。', history)
    packet = note_packet(messages[1])
    assert packet['display_name'] == '测试乙'
    assert packet['voice_state'] == 'MATCHED'
    assert packet['face']['display_name'] == '画面甲'
    assert messages[-1] == dict(role='user', content='今天我来聊天。')
    assert builder.metrics['face_and_voice_context']
    assert message_cost(messages, builder.reserve) <= builder.maximum


def test_unknown_voice_is_explicit_even_when_a_face_is_known():
    packet = note_packet(conversation_address_note(dict(display_name=None,
        face=dialogue_face_result(face_snapshot(), 'synthetic-boot', 10000))))
    assert packet['display_name'] is None and packet['voice_state'] == 'UNCONFIRMED'
    assert packet['face']['display_name'] == '画面甲'


def test_recognition_context_is_not_silently_removed_for_a_long_input():
    context = dict(conversation_address=dict(display_name='测试甲',
        face=dict(state='UNAVAILABLE', display_name=None, face_count=0)))
    builder = BoardContextBuilder('原角色。', context_limit=512)
    with pytest.raises(ContextLimitError):
        builder(context, '原话' * 80)
    assert conversation_address_note(dict(display_name='测试甲', personal_memory_allowed=True)) is None


@pytest.fixture
def full(tmp_path, monkeypatch):
    helper = TASK.parent / '2026-11-02_voice_speaker_recognition/tests/test_ordinary_speaker_integration.py'
    spec = importlib.util.spec_from_file_location('current_synthetic_voice_harness', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    value = module.harness_classes()(tmp_path, monkeypatch)
    def enroll():
        store = value.business.hub.speaker.store.original
        for index, name in enumerate(('测试甲', '测试乙')):
            vector = tuple(1. if n == index else 0. for n in range(192))
            store.enroll('synthetic-person-' + str(index), name, vector, consent=True)
        value.business._refresh_public()
    value.business.pool.submit(enroll).result(2)
    value.runtime.jobs.identity_snapshot = lambda: face_snapshot(round(value.mono() * 1000))
    try:
        yield value
    finally:
        value.encoder.release.set()
        value.close()


def test_real_jobs_controller_request_carries_both_results_on_every_turn(full):
    for kind, expected_name in ((0, '测试甲'), (1, '测试乙'), (2, None)):
        full.encoder.kind = kind
        _, errors = full.say('今天我想轻松聊一聊，请和我打个招呼。')
        assert not errors
        request = [payload for channel, payload in full.models.payloads if channel == 'llm'][-1]
        notes = [message for message in request['messages'] if '声纹称呼候选' in message['content']]
        assert len(notes) == 1
        packet = note_packet(notes[0])
        assert packet['display_name'] == expected_name
        assert packet['face']['display_name'] == '画面甲'
        assert request['messages'].index(notes[0]) < len(request['messages']) - 1
        assert request['messages'][-1]['role'] == 'user'
    assert full.encoder.calls == 3
    context = full.runtime.store.context(dict(kind='conversation', id='a' * 32))
    assert '画面甲' not in json.dumps(context, ensure_ascii=False)
    assert full.business.public()['automatic_profile_access'] is False


def test_expired_face_is_cleared_on_the_next_actual_request(full):
    _, errors = full.say('今天先说一句问候吧。')
    assert not errors
    full.runtime.jobs.identity_snapshot = lambda: face_snapshot(round(full.mono() * 1000) - 10000)
    _, errors = full.say('再说一句话吧。')
    assert not errors
    payload = [value for kind, value in full.models.payloads if kind == 'llm'][-1]
    note = next(m for m in payload['messages'] if '声纹称呼候选' in m['content'])
    packet = note_packet(note)
    assert packet['display_name'] == '测试甲'
    assert packet['face']['display_name'] is None
