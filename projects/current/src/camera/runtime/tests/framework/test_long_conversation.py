"""Durability, isolation, playback evidence and bounded long-context recall."""
import hashlib
import io
import json
from pathlib import Path
import threading
from unittest.mock import MagicMock, patch

import pytest

from common.conversation_store import ConversationStore
from common.conversation_selection import ConversationSelection
from common.conversation_context import build_context, request_cost
from tools.board_model_host import ModelHost
from tools.voice_channel_source import channel_frames
from common.voice_channel import read_frame
from tests.framework.test_voice_channel import owner
from tests.framework import test_voice_channel as voice_fixture

CID = 'a' * 32
DIGEST = hashlib.sha256(b'audio').hexdigest()


def make_store(tmp_path):
    return ConversationStore(tmp_path / 'conversations.sqlite3')


def add(store, index, text, *, cid=CID, played=True):
    meta = owner('turn%d' % index, index)
    store.begin(cid, meta, text, text)
    store.generated(meta, '回答%d。' % index, 480, DIGEST)
    if played:
        store.played(meta, 480, DIGEST)
    return meta


def test_restart_keeps_input_but_never_recalls_unplayed_assistant(tmp_path):
    store = make_store(tmp_path)
    add(store, 1, '我的项目叫海风。')
    add(store, 2, '第二个问题', played=False)
    restored = make_store(tmp_path)
    records = restored.records(CID)
    history, metrics = build_context('same-27b', records, '继续')
    assert any(row['content'] == '第二个问题' for row in history)
    assert not any(row['role'] == 'assistant' and row['content'] == '回答2。' for row in history)
    assert restored.health()['turns'] == 2


def test_mismatched_ack_and_cancel_do_not_authorize_generated_text(tmp_path):
    store = make_store(tmp_path)
    meta = add(store, 1, '请解释', played=False)
    with pytest.raises(ValueError):
        store.played(meta, 479, DIGEST)
    store.failed(meta)
    with pytest.raises(ValueError):
        store.played(meta, 480, DIGEST)
    history, _ = build_context('same-27b', store.records(CID), '继续')
    assert history == [{'role': 'user', 'content': '请解释'}]


def test_ack_is_idempotent_and_request_reuse_is_rejected(tmp_path):
    store = make_store(tmp_path)
    meta = add(store, 1, '你好')
    assert store.played(meta, 480, DIGEST) is False
    with pytest.raises(ValueError):
        store.begin(CID, meta, '改写的输入', '改写的输入')
    assert store.health()['turns'] == 1


def test_conversations_do_not_cross_and_current_turn_is_excluded(tmp_path):
    store = make_store(tmp_path)
    meta = add(store, 1, '这属于另一段会话', cid='b' * 32)
    add(store, 2, '这是当前问题')
    assert store.records(CID, exclude='turn2') == []
    assert len(store.records('b' * 32)) == 1
    with pytest.raises(ValueError):
        store.records('../escape')


def test_fifty_rounds_retrieve_source_and_keep_request_within_budget(tmp_path):
    store = make_store(tmp_path)
    add(store, 1, '请记住，我的项目叫海风。')
    for index in range(2, 51):
        add(store, index, '聊聊第%d天的天气和散步。' % index)
    history, metrics = build_context('same-27b', store.records(CID), '我的项目叫什么？')
    assert '海风' in json.dumps(history, ensure_ascii=False)
    assert metrics['source_turns'] == [1]
    assert metrics['archive_turns'] == 50
    assert metrics['budget_upper_bound'] <= metrics['context_limit']
    assert len(history) < 100


def test_correction_has_later_source_and_is_not_silently_replaced_by_old_fact(tmp_path):
    store = make_store(tmp_path)
    add(store, 1, '我叫小林。')
    add(store, 2, '纠正一下，叫我小周。')
    for index in range(3, 20):
        add(store, index, '今天散步很舒服。')
    history, metrics = build_context('same-27b', store.records(CID), '我叫什么名字？')
    text = json.dumps(history, ensure_ascii=False)
    assert '小周' in text and text.index('小林') < text.index('小周')
    assert metrics['source_turns'] == [1, 2]
    from tools.dialogue_stream import stream_body
    assert '更正以较新的原话为准' in stream_body('same-27b', history, '我叫什么名字？')['messages'][0]['content']


@pytest.mark.parametrize('reasoning', [False, True])
def test_oversize_current_input_is_rejected_instead_of_silent_truncation(reasoning):
    with pytest.raises(ValueError, match='context budget'):
        build_context('same-27b', [], '中文' * 2000, reasoning=reasoning)


def test_selection_requires_explicit_resume_and_new_is_isolated(tmp_path):
    path = tmp_path / 'selection.json'
    first = ConversationSelection(path)
    with pytest.raises(ValueError):
        first.select(True)
    cid = first.select(False)
    restored = ConversationSelection(path)
    assert restored.saved == cid and restored.active is None
    assert restored.select(True) == cid
    assert restored.select(False) != cid
    assert len(list(tmp_path.glob('*.tmp-*'))) == 0


def host(tmp_path):
    model = ModelHost.__new__(ModelHost)
    model.meta_lock = threading.Lock()
    model.histories = {}; model.wire_histories = {}; model.preference_memories = {}
    model.pending_streams = {}; model.latest_generations = {}; model.conversation_turns = {}
    model.conversations = make_store(tmp_path)
    return model


def test_model_host_persists_only_valid_playback_and_retries_ack(tmp_path):
    model = host(tmp_path)
    meta = owner()
    model.register_stream(meta)
    model.begin_conversation(meta, CID, '你好', '你好')
    model.complete_stream(meta, '你好', '你好呀。', 480, DIGEST)
    ack = {'context': meta, 'voice_sample_count': 480, 'pcm_sha256': DIGEST}
    assert model.acknowledge_stream(ack) == model.acknowledge_stream(ack) == {'committed': True}
    assert model.conversations.records(CID)[0]['status'] == 'played'
    assert model.histories == {} and model.preference_memories == {}


def test_new_generation_invalidates_old_pending_receipt(tmp_path):
    model = host(tmp_path)
    meta = owner('old', 1)
    model.register_stream(meta); model.begin_conversation(meta, CID, '旧问题', '旧问题')
    model.complete_stream(meta, '旧问题', '旧回答', 480, DIGEST)
    model.register_stream(owner('new', 2))
    with pytest.raises(ValueError):
        model.acknowledge_stream({'context': meta, 'voice_sample_count': 480, 'pcm_sha256': DIGEST})
    assert model.conversations.records(CID)[0]['status'] == 'interrupted'


def test_full_pipeline_restores_fifty_round_context_without_legacy_cache(tmp_path):
    model = host(tmp_path)
    for index in range(1, 51):
        add(model.conversations, index, '请记住项目叫海风。' if index == 1 else '今天散步。')
    model.voice = voice_fixture.VoiceChannelTests().fixture_models(tmp_path).voice
    model.latency_options = {'reply_first': True, 'reuse_history': True, 'coalesce_chat': True}
    captured = {}
    class Stream:
        def __iter__(self):
            yield 'text', '你的项目叫海风。'
            yield 'speech_ready', None
            yield 'complete', {'reply_text': '你的项目叫海风。', 'emotion': 'friendly', 'avatar_action': ''}
        def cancel(self): pass
    def factory(host, name, history, text, timeout, **options):
        captured['history'] = history
        return Stream()
    meta = owner('fresh', 100)
    packets = list(channel_frames(model, meta, '项目叫什么？', 5, model='same-27b', host='fixture',
                                 stream_factory=factory, conversation=CID))
    end = read_frame(io.BytesIO(packets[-1]))[0]
    assert end['kind'] == 'end'
    assert '海风' in json.dumps(captured['history'], ensure_ascii=False)
    assert end['timing']['conversation_context']['archive_turns'] == 50
    assert model.conversations.records(CID)[-1]['status'] == 'generated'
    model.acknowledge_stream({'context': meta, 'voice_sample_count': end['sample_count'],
                              'pcm_sha256': end['pcm_sha256']})
    assert model.conversations.records(CID)[-1]['status'] == 'played'


def test_http_conversation_header_survives_new_transport_session(tmp_path):
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    from board.runtime.audio.voice_channel import VoiceChannel
    model = host(tmp_path)
    model.lock = threading.Lock()
    model.voice = voice_fixture.VoiceChannelTests().fixture_models(tmp_path).voice
    model.latency_options = {}
    class Engine:
        model_id = 'TEST_ONLY'
        def transcribe(self, pcm): return '我喜欢绿色'
    server = AsrServer(('127.0.0.1', 0), Engine(), handler=ModelHandler)
    server.models = model
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    original = channel_frames
    seen = []
    def source(*args, **kwargs):
        seen.append(kwargs.get('conversation'))
        return original(*args, **kwargs, stream_factory=voice_fixture.VoiceChannelTests.fake_stream)
    channel = VoiceChannel('127.0.0.1', server.server_port)
    with patch('tools.voice_channel_source.channel_frames', source):
        thread.start()
        try:
            for index in range(2):
                meta = dict(owner('http%d' % index, 1), board_boot_id='boot%d' % index,
                            session_id='session%d' % index)
                result = channel.exchange(meta, voice_fixture.PCM, lambda header, pcm: None, conversation=CID)
                model.acknowledge_stream({'context': meta, 'voice_sample_count': result['sample_count'],
                                          'pcm_sha256': result['pcm_sha256']})
            assert seen == [CID, CID]
            assert len(model.conversations.records(CID)) == 2
        finally:
            channel.close(); server.shutdown(); server.server_close(); thread.join(2)


@pytest.mark.parametrize('choice,resume,starts', [('YES', True, True), ('NO', False, True), ('CANCEL', None, False)])
def test_ui_selection_precedes_start_and_cancel_never_opens_microphone(choice, resume, starts):
    from types import SimpleNamespace
    from tools.board_avatar_gtk import BoardAvatarStage
    stage = object.__new__(BoardAvatarStage)
    stage.window = object()
    stage.controller = MagicMock()
    stage.controller.public.return_value = {'automatic_conversation': {'enabled': False}}
    stage.services = MagicMock()
    stage.services.read.return_value = {'snapshot': {'modules': {}}}
    stage.transcriber = MagicMock()
    stage.transcriber.conversation_selection = SimpleNamespace(saved=CID)
    responses = SimpleNamespace(YES=1, NO=2, CANCEL=3)
    stage.Gtk = MagicMock(); stage.Gtk.ResponseType = responses
    stage.Gtk.Dialog.return_value.run.return_value = getattr(responses, choice)
    BoardAvatarStage.command(stage, {'type': 'conversation_toggle'})
    assert stage.controller.conversation_start.called is starts
    if starts:
        stage.transcriber.select_conversation.assert_called_once_with(resume=resume)
    else:
        stage.transcriber.select_conversation.assert_not_called()


def test_selection_change_is_rejected_while_worker_has_active_request(tmp_path):
    from board.runtime.audio.channel_jobs import ChannelConversationJobs
    jobs = object.__new__(ChannelConversationJobs)
    jobs.condition = threading.Condition(); jobs.closed = False; jobs.waiting = None; jobs.active = 'active'
    jobs.conversation_selection = ConversationSelection(tmp_path/'selection.json')
    with pytest.raises(ValueError):
        jobs.select_conversation(resume=False)
    assert jobs.conversation_selection.active is None
