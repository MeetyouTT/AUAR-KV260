"""Real factory, synthetic model/encoder and public memories only."""
from pathlib import Path
import threading
import time

from common.board_memory import MemoryBusy
from test_identity_cooperation import Harness


def test_combined_factory_keeps_M03_preview_confirmation_and_source_closure(tmp_path):
    import board.runtime.board_business as business
    assert Path(business.__file__).resolve() == (
        Path(__file__).resolve().parent / 'after/board/runtime/board_business.py')
    h = Harness(tmp_path)
    try:
        h.say('雪妃，记住：项目是公开海风')
        scope = dict(kind='conversation', id=h.bundle.jobs.conversation_selection.active)
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


def test_real_factory_speaker_worker_retries_single_transient_evidence_write(tmp_path):
    h = Harness(tmp_path)
    original = h.bundle.store.append_event
    attempts = []
    saved = threading.Event()
    def append(*args, **kwargs):
        if args[1].startswith('speaker:'):
            attempts.append(args[1])
            if len(attempts) == 1:
                raise MemoryBusy('public_synthetic_contention')
            value = original(*args, **kwargs)
            saved.set()
            return value
        return original(*args, **kwargs)
    h.bundle.store.append_event = append
    try:
        h.say('公开测试今天天气')
        assert saved.wait(1.)
        assert len(attempts) == 2 and attempts[0] == attempts[1]
        with h.bundle.store._db() as db:
            assert db.execute('SELECT count(*) FROM bm_events WHERE event_id=?', (attempts[0],)).fetchone()[0] == 1
        assert h.bundle.speaker_business.health()['evidence_errors'] == 0
    finally:
        h.close()
