import json
import importlib.util
from pathlib import Path

import pytest

from board.runtime import board_dialogue as dialogue
from board.runtime.board_dialogue import BoardDialogueController, _Turn, conversation_address_target
from board.runtime.board_memory_policy import BoardContextBuilder, message_cost
from tests.framework.test_board_dialogue import Store, Models, Clock, ack


@pytest.fixture
def flag(tmp_path, monkeypatch):
    path = tmp_path/'thinking.json'
    monkeypatch.setattr(dialogue, 'THINKING_TEST_PATH', path)
    return path


def enable(path, **changes):
    value = dict(version=1, enabled=True, board_boot_id='synthetic-boot', num_predict=192)
    value.update(changes)
    path.write_text(json.dumps(value))


@pytest.mark.parametrize('kind', ['missing', 'bad_json', 'oversized', 'wrong_boot', 'disabled',
                                 'string_bool', 'wrong_cap', 'extra_key', 'bool_version'])
def test_invalid_or_absent_selection_keeps_normal_requests(flag, kind):
    if kind == 'bad_json': flag.write_text('{')
    elif kind == 'oversized': flag.write_text(' '*1025)
    elif kind == 'wrong_boot': enable(flag, board_boot_id='previous-boot')
    elif kind == 'disabled': enable(flag, enabled=False)
    elif kind == 'string_bool': enable(flag, enabled='true')
    elif kind == 'wrong_cap': enable(flag, num_predict=1024)
    elif kind == 'extra_key': enable(flag, extra=True)
    elif kind == 'bool_version': enable(flag, version=True)
    assert dialogue.dialogue_thinking_test_options('synthetic-boot') == {}


def test_selection_is_reversible_without_process_restart(flag):
    enable(flag)
    assert dialogue.dialogue_thinking_test_options('synthetic-boot') == dict(think=True, num_predict=192)
    flag.unlink()
    assert dialogue.dialogue_thinking_test_options('synthetic-boot') == {}


def test_context_reserves_thinking_space_and_keeps_complete_current_input(flag):
    builder = BoardContextBuilder('请保持原来的三字段JSON。')
    class ContextStore:
        def context(self, scope):
            return dict(messages=[dict(role='user', content='原记忆'*80),
                                  dict(role='assistant', content='完整回答'*80)], facts=[])
    controller = BoardDialogueController(ContextStore(), None, board_boot_id='synthetic-boot',
        system_prompt=builder.system_prompt, context_builder=builder)
    turn = _Turn('synthetic-session', 1, 'synthetic-turn', 99999999, {})
    turn.llm_options = dict(think=True, num_predict=192)
    text = '请计算58乘3，给我一句完整的回答。'
    messages = controller._messages(turn, text, None)
    assert message_cost(messages, 192) <= 2048
    assert text in messages[-1]['content']
    assert builder.reserve == 120
    assert not any(message['content'] == '原记忆'*80 for message in messages)


def test_only_remote_dialogue_uses_thinking_and_toggle_takes_effect_next_turn(flag):
    clock, store = Clock(), Store()
    models = Models(clock, reply='今天慢慢来，我会陪你。')
    builder = BoardContextBuilder('测试人设：只返回reply_text/emotion/avatar_action三字段JSON')
    controller = BoardDialogueController(store, models, board_boot_id='synthetic-boot',
        system_prompt=builder.system_prompt, context_builder=builder, clock=clock)
    enable(flag)
    for generation, enabled in ((1, True), (2, False)):
        if not enabled: flag.unlink()
        plan = controller.prepare_text('今天有点累', scope=dict(kind='conversation', id='synthetic-session'),
            session_id='synthetic-session', generation=generation, budget_ms=3000)
        request = next(payload for kind, payload, _ in reversed(models.calls) if kind == 'llm')
        assert request['options'] == (dict(think=True, num_predict=192) if enabled else {})
        assert controller.last_prepare_metrics['thinking_test_enabled'] == enabled
        assert all('options' not in payload for kind, payload, _ in models.calls if kind == 'tts')
        assert ack(controller, plan)['status'] == 'played'
    assert controller.idle


def test_current_named_reply_rule_is_preserved():
    assert conversation_address_target(dict(display_name='测试乙', face=dict(state='KNOWN',
        display_name='画面甲', face_count=1))) == ('测试乙', 'voice')


def test_longer_input_can_use_the_original_budget_without_chopping_data(flag):
    builder = BoardContextBuilder('x'*1550)
    class ContextStore:
        def context(self, scope): return dict(messages=[], facts=[])
    controller = BoardDialogueController(ContextStore(), None, board_boot_id='synthetic-boot',
        system_prompt=builder.system_prompt, context_builder=builder)
    turn = _Turn('synthetic-session', 1, 'synthetic-turn', 99999999, {})
    turn.llm_options = dict(think=True, num_predict=192)
    messages = controller._messages(turn, 'abc', None)
    assert messages[0]['content'] == 'x'*1550
    assert messages[-1]['content'] == 'abc'
    assert turn.llm_options == dict(think=True, num_predict=120)
    assert message_cost(messages, 120) <= 2048


def test_composed_jobs_send_thinking_with_the_existing_real_context_builder(flag, tmp_path, monkeypatch):
    helper = Path(__file__).resolve().parent.parent/'2026-11-02_voice_speaker_recognition/tests/test_ordinary_speaker_integration.py'
    spec = importlib.util.spec_from_file_location('synthetic_thinking_composition', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    full = module.harness_classes()(tmp_path, monkeypatch)
    try:
        # The composition uses this explicit synthetic boot identifier.
        enable(flag, board_boot_id=full.runtime.controller.board_boot_id)
        _, errors = full.say('今天有点累，陪我轻松聊一句。')
        assert not errors
        request = [payload for kind, payload in full.models.payloads if kind == 'llm'][-1]
        assert request['options'] == dict(think=True, num_predict=192)
        assert message_cost(request['messages'], 192) <= 2048
    finally:
        full.encoder.release.set()
        full.close()
