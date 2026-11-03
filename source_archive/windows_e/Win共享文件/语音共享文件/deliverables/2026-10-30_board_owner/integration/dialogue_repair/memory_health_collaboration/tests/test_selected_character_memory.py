"""Current selected character, raw ASR and command permissions stay exact."""
import pytest
from board.runtime.character import CHARACTER_NAME
from board.runtime.board_memory_policy import BoardContextBuilder
from common.board_memory import BoardMemoryStore
from tests.framework.test_board_memory_policy import Client, controller, prepare, acknowledge, SCOPE


def test_selected_character_and_unrelated_names_keep_raw_text(tmp_path):
    assert CHARACTER_NAME == '雪妃'
    store, client = BoardMemoryStore(tmp_path/'synthetic-character.sqlite3'), Client()
    control = controller(store, client)
    raw = CHARACTER_NAME + '，你好'
    prepare(control, raw, 1)
    request = next(call for call in client.calls if call.get('task') == 'dialogue')
    assert request['messages'][-1] == dict(role='user', content=raw)
    assert store.context(SCOPE)['messages'][-1]['content'] == raw
    builder = BoardContextBuilder('公开的人设。')
    literal = '我的朋友叫西兰，不要改名字。'
    assert builder({'messages': []}, literal)[-1]['content'] == literal


@pytest.mark.parametrize('separator', ['，', '：'])
def test_current_addressed_commands_commit_on_board_and_keep_scope_permissions(tmp_path, separator):
    text = CHARACTER_NAME + separator + '记住：项目是海风'
    store, client = BoardMemoryStore(tmp_path/'synthetic-command.sqlite3'), Client()
    control = controller(store, client)
    plan = prepare(control, text, 1)
    assert store.context(SCOPE)['facts'][0]['value'] == '海风'
    assert store.context(SCOPE)['messages'][-1]['content'] == text
    assert not any(call.get('task') == 'dialogue' for call in client.calls)
    acknowledge(control, plan)
    denied = prepare(control, CHARACTER_NAME+'，查看我的长期记忆', 2)
    assert '授权个人档案' in denied.reply.text
