"""Public invented dialogue only; no existing private databases or recordings."""
import ast
from pathlib import Path
import sqlite3

import pytest

from board.runtime.board_memory_policy import BoardContextBuilder, message_cost
from common.board_memory import BoardMemoryStore
from common.character_profile import selected_profile

SCOPE = {'kind': 'conversation', 'id': 'public-five-turn-check'}
ADDRESS = {'display_name': '测试员', 'face': {'state': 'NO_FACE', 'display_name': None, 'face_count': 0}}
UTTERANCES = ['我养的小猫叫团团，它最喜欢蓝色。', '今天天气很好，陪我轻松聊聊。',
              '我准备下午去公园散步。', '走路累了可以怎么放松？']


class Clock:
    value = 1000.
    def __call__(self):
        return self.value


def played(store, clock, i, text, *, source='conversation:public-video'):
    name = 'public-turn-' + str(i)
    store.begin_turn(SCOPE, name, text, generation=i, metadata={'source_id': source})
    clock.value += 1
    store.generated(name, '好的，我们接着聊。', generation=i)
    store.bind_audio_receipt(name, generation=i, playback_token=name, sha256='a'*64, samples=240)
    store.ack_played(name, generation=i, playback_token=name, sha256='a'*64, samples=240)
    clock.value += 1


def builder():
    return BoardContextBuilder(selected_profile().persona_full_prompt, context_limit=4096)


def context(*, reply='好的，我们接着聊。'):
    return {'messages': [m for u in UTTERANCES for m in
            ({'role': 'user', 'content': u}, {'role': 'assistant', 'content': reply})],
            'facts': [], 'summaries': [], 'conversation_address': ADDRESS}


def test_fifth_request_includes_four_complete_prior_turns_and_recognition():
    b = builder()
    out = b(context(), '第一轮我告诉你的宠物名字和喜欢的颜色是什么？')
    assert all({'role': 'user', 'content': u} in out for u in UTTERANCES)
    assert sum(m['role'] == 'assistant' for m in out) == 4
    assert b.metrics['five_turn_window_complete'] and b.metrics['prior_user_turns_included'] == 4
    assert b.metrics['face_and_voice_context'] and message_cost(out, 120) <= 4096


def test_facts_and_old_summaries_cannot_displace_first_turn():
    c = context()
    c['facts'] = [{'key': '项目', 'value': '海风'*300}]
    c['summaries'] = [{'end_utc': 1, 'text': '更早的事情'*300}]
    b = builder(); out = b(c, '请回忆最开始的话。')
    assert all({'role': 'user', 'content': u} in out for u in UTTERANCES)
    assert b.metrics['five_turn_window_complete'] and message_cost(out, 120) <= 4096


def test_long_assistant_answers_preserve_all_four_user_originals():
    b = builder(); out = b(context(reply='很长的回答。'*300), '最初的小猫叫什么？')
    assert all({'role': 'user', 'content': u} in out for u in UTTERANCES)
    assert b.metrics['five_turn_window_complete'] and message_cost(out, 120) <= 4096


def test_raw_five_turns_survive_age_and_store_reopen(tmp_path):
    clock = Clock(); path = tmp_path/'public.sqlite3'
    store = BoardMemoryStore(path, clock=clock, data_origin='board')
    for i in range(1, 6):
        played(store, clock, i, UTTERANCES[(i-1)%4])
    clock.value += 1800
    assert store.prepare_compaction() is None
    store = BoardMemoryStore(path, clock=clock, data_origin='board')
    out = store.context(SCOPE, context_source_id='conversation:public-video')
    assert len(out['messages']) == 10 and out['messages'][0]['content'] == UTTERANCES[0]
    assert store.prepare_compaction() is None


def test_sixth_completed_turn_allows_only_oldest_raw_turn_to_compact(tmp_path):
    clock = Clock(); store = BoardMemoryStore(tmp_path/'public.sqlite3', clock=clock, data_origin='board')
    for i in range(1, 7):
        played(store, clock, i, '公开测试句'+str(i))
    clock.value += 301
    prepared = store.prepare_compaction()
    assert prepared
    with sqlite3.connect(store.path) as db:
        turns = {db.execute('SELECT turn_id FROM bm_events WHERE event_id=?', (r['event_id'],)).fetchone()[0]
                 for r in prepared['sources']}
    assert turns == {'public-turn-1'}


def test_pending_fifth_keeps_first_available_and_active_turn_blocks_compaction(tmp_path):
    clock = Clock(); store = BoardMemoryStore(tmp_path/'public.sqlite3', clock=clock, data_origin='board')
    for i, text in enumerate(UTTERANCES, 1):
        played(store, clock, i, text)
    store.begin_turn(SCOPE, 'public-turn-5', '第一轮的小猫叫什么？', generation=5,
                     metadata={'source_id': 'conversation:public-video'})
    clock.value += 301
    c = store.context(SCOPE, context_source_id='conversation:public-video'); c['conversation_address'] = ADDRESS
    b = builder(); out = b(c, '第一轮的小猫叫什么？')
    assert {'role': 'user', 'content': UTTERANCES[0]} in out
    assert b.metrics['prior_user_turns_included'] == 4 and store.prepare_compaction() is None


def test_conversation_partition_does_not_import_another_conversation(tmp_path):
    clock = Clock(); store = BoardMemoryStore(tmp_path/'public.sqlite3', clock=clock, data_origin='board')
    played(store, clock, 1, UTTERANCES[0])
    played(store, clock, 2, '另一段对话只谈散步。', source='conversation:other')
    c = store.context(SCOPE, context_source_id='conversation:other')
    assert len(c['messages']) == 2 and all('团团' not in m['content'] for m in c['messages'])
    clock.value += 301
    assert store.prepare_compaction() is None  # each source has its own retention window


def test_board_factory_selects_expanded_context_without_changing_synthetic_defaults():
    root = Path(__file__).resolve().parents[1]
    text = (root/'candidate_runtime/board/runtime/board_business.py').read_text(encoding='utf-8')
    assert "context_limit=4096 if config.data_origin == 'board' else 2048" in text
    assert BoardContextBuilder('原有人设。').maximum == 2048


def test_model_preload_and_every_request_share_4096_context():
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root/'host_candidate/model_inference_host.py').read_bytes())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'LocalModelBackend')
    preload = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_preload_llm_request')
    call = next(n for n in ast.walk(preload) if isinstance(n, ast.Call) and any(k.arg == 'options' for k in n.keywords))
    assert ast.literal_eval(next(k.value for k in call.keywords if k.arg == 'options')) == {'num_ctx': 4096}
    ollama = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_ollama')
    assert any(isinstance(n, ast.Assign) and ast.unparse(n.targets[0]) == "body['options']['num_ctx']"
               and ast.literal_eval(n.value) == 4096 for n in ast.walk(ollama) if isinstance(n, ast.Assign))
