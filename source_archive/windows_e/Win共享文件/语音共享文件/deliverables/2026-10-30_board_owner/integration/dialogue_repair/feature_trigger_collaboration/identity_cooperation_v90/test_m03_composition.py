"""Opt-in local composition smoke; frozen M03 sources are never edited."""
from pathlib import Path

from test_identity_cooperation import Harness


def test_actual_combined_factory_keeps_M03_preview_confirmation_and_source_closure(tmp_path):
    import board.runtime.board_business as business
    assert 'combined_with_frozen_M03' in str(Path(business.__file__))
    h = Harness(tmp_path)
    try:
        h.say('雪妃，记住：项目是公开海风')
        scope = dict(kind='conversation',id=h.bundle.jobs.conversation_selection.active)
        assert h.bundle.store.context(scope)['facts'][0]['value'] == '公开海风'
        spoken, _ = h.say('雪妃，删除今天的对话记录')
        assert '拟删除' in spoken and '确认删除记录' in spoken
        assert h.bundle.store.context(scope)['facts'][0]['value'] == '公开海风'
        spoken, _ = h.say('雪妃，确认删除记录')
        assert '已按预览删除' in spoken
        assert h.bundle.store.context(scope)['facts'] == []
        assert all('公开海风' not in row['text'] for row in h.bundle.store.history(scope))
        assert not h.bundle.access.grants
    finally:
        h.close()
