import json
import sqlite3
import threading

import pytest

from board.runtime.board_dialogue import BoardDialogueController, StaleGeneration
from board.runtime.board_dialogue_client import InferenceHttpClient
from board.runtime.board_memory_policy import (BoardContextBuilder, BoardMemoryCommands,
                                               BoardSummaryClient, ContextLimitError, message_cost)
from board.visual_timeline import VisualTimelineCollector
from common.board_memory import BoardMemoryStore, BoardMemoryWorker
from common.model_inference_wire import Owner, audio_payload, make_response
from common.profile_access import ProfileAccess
from tools.model_inference_host import InferenceHost, make_server


SCOPE = {'kind':'conversation','id':'PRIVATE_SCOPE'}
REPLY = '好的，先列书单。'
SUMMARY = '小林计划周五买3本书，尚未购买；助手已完整建议先列书单。'


class Clock:
    value = 1000.
    def __call__(self):
        return self.value


class Client:
    def __init__(self):
        self.calls = []
        self.fail_tts = False
        self.summary_hook = None
        self.semantic = {'summary': SUMMARY, 'keywords':['书单']}

    def request(self, kind, payload, **options):
        self.calls.append(json.loads(json.dumps(payload)))
        owner = Owner.from_dict(payload)
        if kind == 'llm':
            if payload['task'] == 'summary':
                if self.summary_hook:
                    self.summary_hook()
                text = json.dumps(self.semantic, ensure_ascii=False)
            else:
                text = json.dumps(dict(reply_text=REPLY, emotion='friendly', avatar_action=''))
            return make_response(owner, result={'text':text})
        if self.fail_tts:
            raise OSError('synthetic TTS failed')
        return make_response(owner, result={'audio':audio_payload(b'\x01\x00' * 480)})

    def cancel(self, owner):
        return None


def controller(store, client):
    prompt = '你是汐蓝，按原有三字段JSON自然回答。'
    return BoardDialogueController(store, client, board_boot_id='public-boot', system_prompt=prompt,
                                   command_handler=BoardMemoryCommands(store),
                                   context_builder=BoardContextBuilder(prompt))


def prepare(control, text, generation):
    return control.prepare_text(text, scope=SCOPE, session_id='session', generation=generation,
                                budget_ms=2000)


def acknowledge(control, plan):
    return control.acknowledge(plan, playback_token=plan.playback_token,
                               sha256=plan.sha256, samples=plan.samples)


def test_explicit_write_and_forget_survive_failed_tts(tmp_path):
    store, client = BoardMemoryStore(tmp_path/'synthetic.sqlite3'), Client()
    control = controller(store, client)
    client.fail_tts = True
    with pytest.raises(OSError):
        prepare(control, '记住：项目是海风', 1)
    assert store.context(SCOPE)['facts'][0]['value'] == '海风'
    assert all(call.get('task') != 'dialogue' for call in client.calls)
    with pytest.raises(OSError):
        prepare(control, '忘记项目', 2)
    assert store.context(SCOPE)['facts'] == []


def test_commands_can_play_their_confirmed_result_and_late_ack_cannot_resurrect(tmp_path):
    store, client = BoardMemoryStore(tmp_path/'synthetic.sqlite3'), Client()
    control = controller(store, client)
    old = prepare(control, '记住：项目是海风', 1)
    new = prepare(control, '把我的项目改成朝露', 2)
    with pytest.raises(StaleGeneration):
        acknowledge(control, old)
    acknowledge(control, new)
    assert store.context(SCOPE)['facts'][0]['value'] == '朝露'
    assert control.idle


def test_context_reuses_one_continuity_summary_and_history_is_opt_in():
    builder = BoardContextBuilder('原有人设。')
    context = dict(messages=[{'role':'user','content':'上一轮'}, {'role':'assistant','content':'上一回答'}],
                   facts=[], summaries=[{'start_utc':1,'end_utc':2,'text':'前面讨论过书单。'}])
    messages = builder(context, '接着说')
    assert messages[0]['content'] == '原有人设。'
    assert sum('前面讨论过书单' in m['content'] for m in messages) == 1
    assert builder.metrics['history_requested'] is False
    assert message_cost(messages, 120) <= 2048
    messages = builder(context, '过去呢', [{'source':'timeline_summary','text':'明确检索结果'}])
    assert any('明确检索结果' in m['content'] for m in messages)
    assert builder.metrics['history_items'] == 1


def test_current_input_is_not_silently_truncated():
    builder = BoardContextBuilder('原有人设。')
    with pytest.raises(ContextLimitError):
        builder({'messages':[], 'facts':[], 'summaries':[]}, '不能截断否定' * 1000)


def test_character_address_understanding_keeps_raw_asr_in_memory(tmp_path):
    store, client = BoardMemoryStore(tmp_path/'synthetic.sqlite3'), Client()
    control = controller(store, client)
    prepare(control, '西兰，你好', 1)
    request = next(call for call in client.calls if call.get('task') == 'dialogue')
    assert request['messages'][-1] == {'role':'user','content':'汐蓝，你好'}
    assert not any(message['content'] == '西兰，你好' for message in request['messages'][:-1])
    assert store.context(SCOPE)['messages'][-1]['content'] == '西兰，你好'
    builder = BoardContextBuilder('原有人设。')
    literal = '我的朋友叫西兰，不要改名字。'
    assert builder({'messages':[]}, literal)[-1]['content'] == literal


@pytest.mark.parametrize('text', ['西蓝，记住：项目是海风', '西蓝：记住：项目是海风'])
def test_addressed_explicit_commands_still_write_on_board_with_raw_sources(tmp_path, text):
    store, client = BoardMemoryStore(tmp_path/'synthetic.sqlite3'), Client()
    control = controller(store, client)
    plan = prepare(control, text, 1)
    assert store.context(SCOPE)['facts'][0]['value'] == '海风'
    assert store.context(SCOPE)['messages'][-1]['content'] == text
    assert not any(call.get('task') == 'dialogue' for call in client.calls)
    acknowledge(control, plan)
    denied = prepare(control, '西蓝，查看我的长期记忆', 2)
    assert '授权个人档案' in denied.reply.text


def test_clear_command_removes_old_memory_and_can_ack_its_success(tmp_path):
    store, client = BoardMemoryStore(tmp_path/'synthetic.sqlite3'), Client()
    control = controller(store, client)
    old = prepare(control, '记住：项目是海风', 1)
    acknowledge(control, old)
    cleared = prepare(control, '清空本次对话记忆', 2)
    assert '已清空' in cleared.reply.text
    assert store.context(SCOPE)['facts'] == []
    assert all('海风' not in row.get('text', '') for row in store.history(SCOPE))
    acknowledge(control, cleared)
    assert store.context(SCOPE)['messages'][-1]['role'] == 'assistant'
    assert control.idle


def test_conversation_limited_command_cannot_mutate_personal_scope(tmp_path):
    access = ProfileAccess('9' * 64)
    _, grant = access.issue('a' * 32, {'board_boot_id':'public-boot', 'session_id':'session'})
    personal = {'kind':'profile', 'id':'a' * 32, 'grant':grant}
    store = BoardMemoryStore(tmp_path/'synthetic.sqlite3', profile_access=access)
    store.correct(personal, '项目', '原项目', operation_id='original-personal-value')
    client = Client()
    control = controller(store, client)
    for generation, text in enumerate(('记住本次对话：项目是海风', '清空本次对话记忆'), 1):
        plan = control.prepare_text(text, scope=personal, session_id='session', generation=generation,
                                    budget_ms=2000)
        assert '切换到普通对话' in plan.reply.text
        acknowledge(control, plan)
        assert store.context(personal)['facts'][0]['value'] == '原项目'
    assert not any(call.get('task') == 'dialogue' for call in client.calls)


def test_current_fact_direct_answer_survives_full_context_and_is_forgotten(tmp_path):
    store, client = BoardMemoryStore(tmp_path/'synthetic.sqlite3'), Client()
    control = controller(store, client)
    acknowledge(control, prepare(control, '记住：项目是海风', 1))
    store.begin_turn(SCOPE, 'unrelated-long-turn', '无关的近期话题' * 200, generation=1)
    store.interrupt('unrelated-long-turn', generation=1)
    answer = prepare(control, '我的项目是什么？', 2)
    assert '海风' in answer.reply.text
    acknowledge(control, answer)
    assert not any(call.get('task') == 'dialogue' for call in client.calls)
    prepare(control, '忘记项目', 3)
    assert all('海风' not in row.get('text', '') for row in store.history(SCOPE))


def test_explicit_history_has_priority_over_unrelated_recent_turn_and_empty_is_not_absence():
    builder = BoardContextBuilder('原有人设。')
    context = dict(messages=[dict(role='user', content='无关话题' * 130)], facts=[], summaries=[])
    messages = builder(context, '昨天说了什么', [dict(source='timeline_summary', text='昨天讨论过书单。')])
    assert any('昨天讨论过书单' in message['content'] for message in messages)
    assert builder.metrics['history_items'] == 1
    empty = builder(context, '昨天说了什么', [])
    assert any('不代表事情没有发生' in message['content'] for message in empty)
    assert builder.metrics['history_requested'] and builder.metrics['history_items'] == 0


def test_model_summary_has_no_authority_over_scope_or_provenance(tmp_path):
    clock, client = Clock(), Client()
    store = BoardMemoryStore(tmp_path/'synthetic.sqlite3', clock=clock)
    control = controller(store, client)
    plan = prepare(control, '小林计划周五买3本书，尚未购买。', 1)
    assert not any(m['role'] == 'assistant' for m in store.context(SCOPE)['messages'])
    acknowledge(control, plan)
    clock.value += 301
    summarize = BoardSummaryClient(client, board_boot_id='public-boot')
    worker = BoardMemoryWorker(store, summarize, idle=lambda:control.idle, max_events=2)
    assert worker.step()
    assert store.health()['active_bodies'] == 0
    blocks = store.history(SCOPE)
    assert len(blocks) == 1 and blocks[0]['text'] == SUMMARY
    sent = next(c for c in client.calls if c.get('task') == 'summary')
    serialized = json.dumps(sent)
    assert 'PRIVATE_SCOPE' not in serialized and 'lease_token' not in serialized
    assert blocks[0]['source_refs']
    client.semantic = dict(client.semantic, scope={'kind':'device','id':'invented'})
    clock.value += 1
    store.append_event(SCOPE, 'next', 'user_said', '小林计划周五买3本书，尚未购买。')
    clock.value += 301
    assert worker.step() is False
    assert store.health()['active_bodies'] == 1


def test_new_input_during_model_summary_keeps_source_bodies(tmp_path):
    clock, client = Clock(), Client()
    store = BoardMemoryStore(tmp_path/'synthetic.sqlite3', clock=clock)
    store.append_event(SCOPE, 'old', 'user_said', '小林计划周五买3本书，尚未购买。')
    clock.value += 301
    client.summary_hook = lambda:store.begin_turn(SCOPE, 'fresh', '新的问题', generation=2)
    worker = BoardMemoryWorker(store, BoardSummaryClient(client, board_boot_id='public-boot'), idle=lambda:True)
    assert worker.step() is False
    assert store.health()['valid_summaries'] == 0
    assert store.health()['active_bodies'] == 2


def test_visual_adapter_writes_to_the_real_board_store(tmp_path):
    store = BoardMemoryStore(tmp_path/'synthetic.sqlite3')
    scope = {'kind':'device','id':'synthetic-device'}
    collector = VisualTimelineCollector('boot', store.append_event, scope)
    for frame, stamp in [(1,1000),(2,1300),(3,1600)]:
        health = dict(board_boot_id='boot', service_epoch='camera-service', camera_epoch='camera',
                      role='DPU_YOLOX_PERSON_PREVIEW', detector={'count_kind':'people'},
                      observation_frame_id=frame, people_count=1, observation_age_ms=10,
                      capture_age_ms=5, camera_error='', detector_error='',
                      timestamp_kind='appsink_dequeue_monotonic')
        collector.ingest_health(health, requested_mono_ms=stamp, received_mono_ms=stamp+10)
    events = store.history(scope)
    assert len(events) == 1 and events[0]['source'] == 'camera_observed'
    assert events[0]['metadata']['evidence'] == 'visual_observation'


def test_real_http_controller_memory_and_full_ack(tmp_path):
    class Backend:
        def llm(self, payload, **options):
            return {'text':json.dumps(dict(reply_text=REPLY,emotion='friendly',avatar_action=''))}
        def tts(self, payload, **options):
            return {'audio':audio_payload(b'\x02\x00' * 480)}
        def close(self):
            pass
    models = InferenceHost(Backend())
    server = make_server(('127.0.0.1',0), models)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        store = BoardMemoryStore(tmp_path/'synthetic.sqlite3')
        control = controller(store, InferenceHttpClient('127.0.0.1',server.server_address[1]))
        plan = prepare(control, '公开的集成测试', 1)
        assert plan.samples == 480 and plan.pcm == b'\x02\x00' * 480
        assert not any(m['role'] == 'assistant' for m in store.context(SCOPE)['messages'])
        acknowledge(control, plan)
        assert any(m['role'] == 'assistant' for m in store.context(SCOPE)['messages'])
        assert not list(tmp_path.glob('*.wav'))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        models.close()
