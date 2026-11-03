"""Pronunciation tolerance must preserve literal words and the raw ASR trace."""
import io
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest

from common.spoken_input import prepare_spoken_input, SPEECH_INPUT_HINT
from common.voice_channel import read_frame
from tools.dialogue_host_ollama import fast_system_prompt
from tools.voice_channel_source import channel_frames
from tests.framework import test_voice_channel as voice_fixture
from tests.framework.test_voice_channel import owner


@pytest.mark.parametrize('raw,expected', [
    ('你好西兰今天过得怎么样', '你好汐蓝今天过得怎么样'),
    ('你好，西蓝！陪我聊聊', '你好，汐蓝！陪我聊聊'),
    ('嗨溪蓝你在吗', '嗨汐蓝你在吗'),
    ('希蓝帮我想想', '汐蓝帮我想想'),
    ('夕蓝，你好', '汐蓝，你好'),
    ('汐兰', '汐蓝'),
    ('西兰在吗', '汐蓝在吗'),
    ('你好西兰今天不是很开心', '你好汐蓝今天不是很开心'),
    ('你好西兰记住十五不是五十', '你好汐蓝记住十五不是五十'),
])
def test_only_known_character_vocatives_are_interpreted(raw, expected):
    result = prepare_spoken_input(raw)
    assert result['raw_text'] == raw and result['text'] == expected
    assert len(result['adjustments']) == 1
    edit = result['adjustments'][0]
    assert raw[:edit['start']] + edit['to'] + raw[edit['end']:] == expected
    assert prepare_spoken_input(expected)['text'] == expected


@pytest.mark.parametrize('raw', [
    '我喜欢西兰花', '你好西兰花好吃吗', '西兰花怎么炒',
    '我朋友叫西兰', '西兰今天请客', '西兰是我同学',
    '你好西兰先生', '西兰学校在哪里',
    '我叫西兰不是汐蓝', '你好西兰我说的不是汐蓝',
    '你好西兰这两个字怎么写', '你好西兰别改我的原话',
    '你好汐蓝今天怎么样', '十五还是五十我没说清',
    '我不想去不是我想去', '我今天有点内陪我聊聊', '',
])
def test_other_words_names_numbers_and_negations_stay_literal(raw):
    result = prepare_spoken_input(raw)
    assert result == {'raw_text': raw, 'text': raw, 'adjustments': []}


def test_stream_keeps_raw_transcript_but_uses_interpreted_context_and_history():
    helper = voice_fixture.VoiceChannelTests()
    with tempfile.TemporaryDirectory() as folder:
        models = helper.fixture_models(Path(folder))
        models.latency_options = {'reply_first': True, 'early_sentence': True, 'coalesce_chat': True}
        received = {}
        def factory(host, model, history, text, timeout, **options):
            received['model_text'] = text
            return helper.fake_stream()
        models.complete_stream = lambda meta, user, *args: received.update(history_user=user)
        frames = list(channel_frames(models, owner(), '你好西兰今天怎么样', 4,
                                    model='fixture', host='fixture', stream_factory=factory, feedback=True))
        headers = [read_frame(io.BytesIO(frame))[0] for frame in frames]
        transcript = next(row for row in headers if row['kind'] == 'transcript')
        assert transcript['text'] == '你好西兰今天怎么样'
        assert transcript['input_adjustments'][0]['from'] == '西兰'
        assert received == {'model_text': '你好汐蓝今天怎么样', 'history_user': '你好汐蓝今天怎么样'}
        assert headers[-1]['kind'] == 'end' and headers[-1]['clauses'] == 1
        assert headers[-1]['timing']['input_adjustments'] == transcript['input_adjustments']
        assert not any(row['kind'] == 'thinking' for row in headers)


def test_uncertain_speech_guidance_preserves_key_information_and_prompt_budget():
    prompt = fast_system_prompt()
    assert SPEECH_INPUT_HINT in prompt
    assert '关键信息拿不准时简短确认' in prompt
    assert '姓名、数字、否定含义不擅改' in prompt
    assert '提到别人姓名不改变自己的身份' in prompt
    assert '通常一两句，最多48个中文字' in prompt


def test_complete_wav_route_uses_same_name_interpretation_and_history():
    from tools.board_model_host import ModelHost
    with tempfile.TemporaryDirectory() as folder:
        models = voice_fixture.VoiceChannelTests().fixture_models(Path(folder))
        models.root = Path(folder)
        generate = models.voice.generate
        models.voice.generate = lambda text: dict(generate(text), duration_seconds=.1, generation_seconds=.01)
        expected = {'reply_text': '你好呀，今天想聊什么？', 'emotion': 'friendly', 'avatar_action': ''}
        with patch('tools.board_model_host.dialogue.build_response', return_value=expected) as llm:
            result = ModelHost.answer(models, owner(), '你好西兰今天怎么样')
        assert llm.call_args.args[0]['transcript'] == '你好汐蓝今天怎么样'
        assert result['reply_text'] == expected['reply_text']
        history = models.histories[(owner()['board_boot_id'], owner()['session_id'])]
        assert history[0]['content'] == '你好汐蓝今天怎么样'
