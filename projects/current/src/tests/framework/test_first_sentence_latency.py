"""Earlier meaningful speech without cutting short replies or committing history."""
import io
import tempfile
import threading
from pathlib import Path

from common.voice_channel import ChannelState, read_frame
from tests.framework import test_voice_channel as fixtures
from tools.voice_channel_source import FirstSentenceBuffer, channel_frames


def test_sentence_buffer_keeps_short_greetings_commas_quotes_and_numbers_intact():
    buffer = FirstSentenceBuffer()
    fragments = ['你好呀！', '预算是3.14元，', '书名叫《星海！》', '这件事我们明天一起完成。', '最后再聊聊其他事。']
    emitted = []
    for fragment in fragments:
        emitted.extend(buffer.feed(fragment))
    assert len(emitted) == 1
    assert emitted[0] == ''.join(fragments[:-1])
    assert ''.join(emitted + buffer.finish()) == ''.join(fragments)


def test_sentence_buffer_emits_only_one_lead_and_preserves_every_character():
    text = '今天你已经认真完成了不少事情。接下来我们可以慢慢聊聊明天的安排。'
    buffer = FirstSentenceBuffer()
    emitted = []
    for char in text:
        emitted.extend(buffer.feed(char))
    assert emitted == ['今天你已经认真完成了不少事情。']
    assert ''.join(emitted + buffer.finish()) == text


def test_ascii_quoted_sentence_does_not_release_inside_a_title():
    buffer = FirstSentenceBuffer()
    assert buffer.feed('这本书的名字叫"今天你已经努力了！') == []
    assert buffer.feed('别放弃"，我们可以明天一起读。') == ['这本书的名字叫"今天你已经努力了！别放弃"，我们可以明天一起读。']


def test_earlier_tts_and_full_remainder_preserve_wire_text_and_uncommitted_history():
    first = '今天你已经认真完成了不少事情。'
    second = '接下来我们可以慢慢聊聊明天的安排。'
    with tempfile.TemporaryDirectory() as directory:
        models = fixtures.VoiceChannelTests().fixture_models(Path(directory))
        models.latency_options = {'coalesce_chat': True, 'first_sentence_chat': True}
        generated = threading.Event()
        original = models.voice.generate
        def voice(text):
            result = original(text)
            generated.set()
            return result
        models.voice.generate = voice
        class Stream:
            def __iter__(self):
                yield 'text', first
                assert generated.wait(2), 'TTS must start before the remaining answer is available'
                yield 'text', second
                yield 'speech_ready', None
                yield 'complete', {'reply_text': first+second, 'emotion': 'friendly', 'avatar_action': ''}
            def cancel(self): pass
        packets = channel_frames(models, fixtures.owner(), '聊聊今天', 4, model='fixture', host='fixture',
                                 stream_factory=lambda *a: Stream())
        state = ChannelState(fixtures.owner())
        headers = []
        for packet in packets:
            header, pcm = read_frame(io.BytesIO(packet))
            state.accept(header, pcm)
            headers.append(header)
        assert models.voice.calls == [first, second]
        assert state.ended and state.text == first+second
        assert headers[-1]['clauses'] == 2 and models.histories == {}
        assert next(i for i, h in enumerate(headers) if h['kind'] == 'audio') < next(
            i for i, h in enumerate(headers) if h.get('text') == second)


def test_short_reply_stays_one_continuous_tts_call():
    text = '你好呀！今天过得怎么样？'
    with tempfile.TemporaryDirectory() as directory:
        models = fixtures.VoiceChannelTests().fixture_models(Path(directory))
        models.latency_options = {'coalesce_chat': True, 'first_sentence_chat': True}
        class Stream:
            def __iter__(self):
                yield 'text', text
                yield 'speech_ready', None
                yield 'complete', {'reply_text': text, 'emotion': 'friendly', 'avatar_action': ''}
            def cancel(self): pass
        headers = [read_frame(io.BytesIO(p))[0] for p in channel_frames(models, fixtures.owner(), '你好', 4,
            model='fixture', host='fixture', stream_factory=lambda *a: Stream())]
        assert models.voice.calls == [text]
        assert headers[-1]['kind'] == 'end' and headers[-1]['clauses'] == 1
