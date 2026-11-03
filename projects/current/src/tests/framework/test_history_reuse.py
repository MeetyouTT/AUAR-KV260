"""Wire history remains private, bounded, aligned, and playback-confirmed."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
from unittest.mock import MagicMock, patch

import pytest

from common.voice_channel import read_frame
from tools.board_model_host import ModelHost
from tools.dialogue_stream import OllamaReplyStream, wire_history_within_budget
from tools.voice_channel_source import channel_frames
from tests.framework import test_voice_channel as fixture

DIGEST = hashlib.sha256(b'voice').hexdigest()


def host():
    model = ModelHost.__new__(ModelHost)
    model.meta_lock = threading.Lock()
    model.histories = {}; model.wire_histories = {}; model.pending_streams = {}; model.latest_generations = {}
    return model


def raw_reply(text):
    return json.dumps({'a': text, 'b': 'friendly', 'c': ''}, ensure_ascii=False, separators=(',', ':'))


def commit(model, index, *, raw=None, session=None, reuse=False):
    meta = fixture.owner('turn%d' % index, index)
    if session is not None: meta['session_id'] = session
    text = '回复%d' % index
    model.register_stream(meta)
    model.complete_stream(meta, '问题%d' % index, text, 480, DIGEST,
                          wire_reply=raw, reuse_previous_wire=reuse)
    model.acknowledge_stream({'context': meta, 'voice_sample_count': 480, 'pcm_sha256': DIGEST})
    return meta


def test_raw_json_only_commits_after_matching_full_playback_ack():
    model = host(); meta = fixture.owner()
    model.register_stream(meta)
    raw = ' \n' + raw_reply('你好呀。')
    model.complete_stream(meta, '你好', '你好呀。', 480, DIGEST, wire_reply=raw)
    assert model.histories == {} and model.wire_histories == {}
    with pytest.raises(ValueError):
        model.acknowledge_stream({'context': meta, 'voice_sample_count': 479, 'pcm_sha256': DIGEST})
    assert model.wire_histories == {}
    model.acknowledge_stream({'context': meta, 'voice_sample_count': 480, 'pcm_sha256': DIGEST})
    plain, wire = model.history_for_stream(meta)
    assert plain[-1]['content'] == '你好呀。' and wire[-1]['content'] == raw
    assert plain[0] == wire[0] == {'role': 'user', 'content': '你好'}


@pytest.mark.parametrize('raw', ['{"a":', raw_reply('不是这句话')])
def test_invalid_or_mismatched_raw_history_cannot_be_saved(raw):
    model = host(); meta = fixture.owner(); model.register_stream(meta)
    with pytest.raises(ValueError):
        model.complete_stream(meta, '你好', '你好呀。', 480, DIGEST, wire_reply=raw)
    assert model.pending_streams == {} and model.wire_histories == {}


def test_cancelled_generation_does_not_commit_semantic_or_wire_history():
    model = host(); meta = fixture.owner('cancelled', 1); model.register_stream(meta)
    model.complete_stream(meta, '你好', '你好呀。', 480, DIGEST, wire_reply=raw_reply('你好呀。'))
    model.register_stream(fixture.owner('new', 2))
    with pytest.raises(ValueError):
        model.acknowledge_stream({'context': meta, 'voice_sample_count': 480, 'pcm_sha256': DIGEST})
    assert model.histories == {} and model.wire_histories == {}


def test_both_representations_keep_the_same_four_round_window():
    model = host()
    for index in range(1, 6):
        meta = commit(model, index, raw=raw_reply('回复%d' % index), reuse=True)
    plain, wire = model.history_for_stream(meta)
    assert len(plain) == len(wire) == 8
    assert plain[0]['content'] == wire[0]['content'] == '问题2'
    for left, right in zip(plain, wire):
        assert left['role'] == right['role']
        assert left['content'] == (json.loads(right['content'])['a'] if right['role'] == 'assistant' else right['content'])


def test_session_eviction_also_removes_its_private_wire_copy():
    model = host()
    for index in range(33):
        commit(model, index, raw=raw_reply('回复%d' % index), session='session%d' % index)
    assert len(model.histories) == len(model.wire_histories) == 32
    assert set(model.histories) == set(model.wire_histories)
    assert ('test-boot', 'session0') not in model.wire_histories


def test_changed_canonical_history_falls_back_without_replacing_memory():
    model = host(); meta = commit(model, 1, raw=raw_reply('回复1'))
    key = (meta['board_boot_id'], meta['session_id'])
    model.histories[key][-1]['content'] = '其他入口更新了这句话'
    plain, wire = model.history_for_stream(meta)
    assert wire is None and plain[-1]['content'] == '其他入口更新了这句话'


def test_non_wire_turn_invalidates_cache_but_preserves_all_semantic_rounds():
    model = host(); meta = commit(model, 1, raw=raw_reply('回复1'))
    commit(model, 2)
    plain, wire = model.history_for_stream(meta)
    assert wire is None and len(plain) == 4 and plain[-1]['content'] == '回复2'


def test_conservative_budget_falls_back_before_truncating_history():
    short = [{'role': 'user', 'content': '记住小林喜欢绿色'},
             {'role': 'assistant', 'content': raw_reply('记住啦。')}]
    long = [dict(row) for row in short]
    long[-1]['content'] = ' ' * 3000 + long[-1]['content']
    assert wire_history_within_budget('same-27b', short, '我叫什么？')
    assert not wire_history_within_budget('same-27b', long, '我叫什么？')
    assert long[0] == short[0]  # The budget check never edits memory.


def test_stream_retains_exact_json_only_after_validated_completion():
    raw = ' \n' + raw_reply('你好呀。🐳')
    packets = [{'message': {'content': raw}, 'done': False}, {'message': {'content': ''}, 'done': True}]
    response = io.BytesIO(b''.join(json.dumps(row).encode() + b'\n' for row in packets))
    response.status = 200
    connection = MagicMock(); connection.getresponse.return_value = response
    with patch('tools.dialogue_stream.http.client.HTTPConnection', return_value=connection):
        stream = OllamaReplyStream('http://localhost', 'same-27b', [], '你好', 3, reply_first=True)
        assert stream.raw_reply is None
        events = list(stream)
    assert stream.raw_reply == raw
    assert events[-1][0] == 'complete' and events[-1][1]['reply_text'] == '你好呀。🐳'


@pytest.mark.parametrize('oversized', [False, True])
def test_pipeline_selects_confirmed_wire_or_full_plain_fallback(oversized):
    with tempfile.TemporaryDirectory() as folder:
        model = host()
        raw = (' ' * 3000 if oversized else '') + raw_reply('回复1')
        meta = commit(model, 1, raw=raw)
        voice = fixture.VoiceChannelTests().fixture_models(Path(folder)).voice
        model.voice = voice
        model.latency_options = {'reply_first': True, 'coalesce_chat': True, 'reuse_history': True}
        captured = {}
        class Stream:
            raw_reply = globals()['raw_reply']('我记得你喜欢绿色。')
            def __iter__(self):
                yield 'text', '我记得你喜欢绿色。'
                yield 'speech_ready', None
                yield 'complete', {'reply_text': '我记得你喜欢绿色。', 'emotion': 'friendly', 'avatar_action': ''}
            def cancel(self): pass
        def factory(host, name, history, text, timeout, **options):
            captured['history'] = history
            return Stream()
        current = fixture.owner('next', 2)
        packets = list(channel_frames(model, current, '我喜欢什么颜色', 4, model='same-27b', host='fixture',
                                     stream_factory=factory, feedback=True))
        end = read_frame(io.BytesIO(packets[-1]))[0]
        assert end['kind'] == 'end' and end['timing']['history_messages'] == 2
        assert end['timing']['history_format'] == ('plain' if oversized else 'exact_json')
        assert captured['history'][-1]['content'] == ('回复1' if oversized else raw)
        assert len(model.histories[(meta['board_boot_id'], meta['session_id'])]) == 2
        model.acknowledge_stream({'context': current, 'voice_sample_count': end['sample_count'], 'pcm_sha256': end['pcm_sha256']})
        plain, wire = model.history_for_stream(current)
        assert len(plain) == len(wire) == 4
        assert wire[1]['content'] == ('回复1' if oversized else raw)
