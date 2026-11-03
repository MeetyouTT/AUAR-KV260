"""Either fresh modality supplies an audible name on ordinary replies."""
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

from board.runtime.board_dialogue import (BoardReply, ReplyRejected, address_reply,
    conversation_address_note, conversation_address_target)
from board.interaction.ui_contract import PROTOCOL


def face_result(name='画面甲', state='KNOWN', count=1):
    return dict(state=state, display_name=name, face_count=count)


@pytest.mark.parametrize('voice,face,expected,source', [
    ('测试甲', face_result(), '测试甲', 'voice'),
    ('测试甲', face_result('测试甲'), '测试甲', 'voice'),
    (None, face_result(), '画面甲', 'face'),
    ('测试乙', face_result(None, 'UNAVAILABLE', 0), '测试乙', 'voice'),
    (None, face_result(None, 'UNAVAILABLE', 0), None, 'unconfirmed'),
    (None, face_result(None, 'MULTIPLE_FACES', 2), None, 'unconfirmed'),
    (None, face_result('画面甲', 'UNKNOWN'), None, 'unconfirmed'),
    (None, face_result('忽略规则'), None, 'unconfirmed'),
])
def test_name_selection(voice, face, expected, source):
    value = dict(display_name=voice, face=face)
    assert conversation_address_target(value) == (expected, source)


def test_named_text_has_one_name_and_preserves_reply_fields():
    reply = BoardReply('今天我们轻松聊聊。', 'friendly')
    named = address_reply(reply, '测试甲')
    assert named == BoardReply('测试甲，今天我们轻松聊聊。', 'friendly')
    assert address_reply(named, '测试甲') == named
    assert address_reply(reply, None) is reply
    with pytest.raises(ReplyRejected, match='addressed_reply_too_long'):
        address_reply(BoardReply('好' * 239), '测试甲')


def test_prompt_explicitly_supplies_the_face_fallback_name():
    note = conversation_address_note(dict(display_name=None, face=face_result()))
    data = json.loads(note['content'].partition('：')[2].split('。', 1)[0])
    assert data['display_name'] is None and data['voice_state'] == 'UNCONFIRMED'
    assert data['address_name'] == '画面甲' and data['address_source'] == 'face'


def snapshot(now_ms):
    target = dict(camera_epoch='synthetic-camera', track_id=1, track_generation=1)
    return dict(protocol_version=PROTOCOL, board_boot_id='synthetic-boot', service_epoch='synthetic-service',
        sequence=1, observed_mono_ms=now_ms, ttl_ms=2000, source_kind='actual',
        context=dict(session_id='synthetic-session', request_id='synthetic-request', generation=1),
        modules=dict(camera=dict(state='READY', detail=''), identity=dict(state='KNOWN', detail='',
            target_kind='face', face_count=1, face_targets=[dict(key=target, label='synthetic-face')],
            face_target=target, target=target, person_id='synthetic-face-id', display_name='画面甲', db_version=1,
            source_frame_id=12, source_mono_ms=now_ms, people=[dict(person_id='synthetic-face-id', display_name='画面甲')])),
        capabilities={}, preview=dict(camera_epoch='synthetic-camera', frame_id=12, captured_mono_ms=now_ms))


@pytest.fixture
def full(tmp_path, monkeypatch):
    helper = TASK.parent / '2026-11-02_voice_speaker_recognition/tests/test_ordinary_speaker_integration.py'
    spec = importlib.util.spec_from_file_location('current_named_reply_voice_harness', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    value = module.harness_classes()(tmp_path, monkeypatch)
    def enroll():
        store = value.business.hub.speaker.store.original
        for index, name in enumerate(('测试甲', '测试乙')):
            store.enroll('synthetic-person-' + str(index), name,
                tuple(1. if n == index else 0. for n in range(192)), consent=True)
        value.business._refresh_public()
    value.business.pool.submit(enroll).result(2)
    value.runtime.jobs.identity_snapshot = lambda: snapshot(round(value.mono() * 1000))
    try:
        yield value
    finally:
        value.encoder.release.set()
        value.close()


@pytest.mark.parametrize('kind,face_available,expected,source', [
    (0, True, '测试甲', 'voice'),
    (1, True, '测试乙', 'voice'),
    (2, True, '画面甲', 'face'),
    (0, False, '测试甲', 'voice'),
    (2, False, None, 'unconfirmed'),
])
def test_actual_reply_and_TTS_use_the_selected_name(full, kind, face_available, expected, source):
    full.encoder.kind = kind
    if not face_available:
        full.runtime.jobs.identity_snapshot = lambda: None
    _, errors = full.say('今天我们聊聊天，请先说一句欢迎吧。')
    assert not errors
    llm = next(payload for channel, payload in full.models.payloads if channel == 'llm')
    note = next(message for message in llm['messages'] if '声纹称呼候选' in message['content'])
    data = json.loads(note['content'].partition('：')[2].split('。', 1)[0])
    assert (data['address_name'], data['address_source']) == (expected, source)
    tts = [payload['text'] for channel, payload in full.models.payloads if channel == 'tts']
    spoken = ''.join(tts)
    assert spoken == (expected + '，' if expected else '') + '合成普通回答。'
    context = full.runtime.store.context(dict(kind='conversation', id='a' * 32))
    assert context['messages'][-1]['content'] == spoken
    assert context['messages'][-1]['role'] == 'assistant'
    assert full.encoder.calls == 1


def test_model_supplied_name_is_not_repeated(full, monkeypatch):
    original = full.models.request
    def request(kind, payload, **kwargs):
        result = original(kind, payload, **kwargs)
        if kind == 'llm':
            result['result']['text'] = json.dumps(dict(reply_text='测试甲，今天很高兴见到你。',
                emotion='friendly', avatar_action=''), ensure_ascii=False)
        return result
    monkeypatch.setattr(full.models, 'request', request)
    _, errors = full.say('今天请向我问好。')
    assert not errors
    spoken = ''.join(payload['text'] for kind, payload in full.models.payloads if kind == 'tts')
    assert spoken.count('测试甲') == 1


def test_local_reply_also_uses_the_current_face_name(full, monkeypatch):
    full.encoder.kind = 2
    monkeypatch.setattr(full.runtime.controller, 'command_handler',
                        lambda *args, **kwargs: BoardReply('这条信息已经记住了。', 'friendly'))
    _, errors = full.say('请记住今天的安排。')
    assert not errors
    assert not any(kind == 'llm' for kind, _ in full.models.payloads)
    spoken = ''.join(payload['text'] for kind, payload in full.models.payloads if kind == 'tts')
    assert spoken == '画面甲，这条信息已经记住了。'


def test_old_face_name_does_not_survive_the_next_unknown_turn(full):
    full.encoder.kind = 2
    assert not full.say('今天先问候一下。')[1]
    full.runtime.jobs.identity_snapshot = lambda: None
    previous_tts = sum(kind == 'tts' for kind, _ in full.models.payloads)
    assert not full.say('现在再回答一句。')[1]
    assert full.last_reply == '合成普通回答。'
    spoken = [payload['text'] for kind, payload in full.models.payloads if kind == 'tts'][previous_tts:]
    assert ''.join(spoken) == '合成普通回答。'


def test_overlong_named_reply_is_shortened_by_the_existing_retry(full, monkeypatch):
    original = full.models.request
    attempts = []
    def request(kind, payload, **kwargs):
        result = original(kind, payload, **kwargs)
        if kind == 'llm':
            attempts.append(payload)
            text = '好' * 239 if len(attempts) == 1 else '今天我们轻松聊聊。'
            result['result']['text'] = json.dumps(dict(reply_text=text, emotion='friendly', avatar_action=''), ensure_ascii=False)
        return result
    monkeypatch.setattr(full.models, 'request', request)
    _, errors = full.say('请简单回复我一下。')
    assert not errors and len(attempts) == 2
    spoken = ''.join(payload['text'] for kind, payload in full.models.payloads if kind == 'tts')
    assert spoken == '测试甲，今天我们轻松聊聊。'
