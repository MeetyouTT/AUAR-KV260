"""Structured fake model replies only; synthetic SQLite, no HTTP/model calls."""
import json
import sqlite3

import pytest

from common.board_memory import BoardMemoryStore
from common.board_memory_backoff import BoardMemoryBackoffWorker
from board.runtime.board_memory_policy import BoardSummaryClient
from common.model_inference_wire import Owner, make_response


class Client:
    def __init__(self, code):
        self.code = code
        self.calls = 0

    def request(self, kind, payload, **kwargs):
        self.calls += 1
        return make_response(Owner.from_dict(payload), error=self.code, retryable=True)

    def cancel(self, owner):
        pass


@pytest.mark.parametrize('code,expected,streak', [
    ('preempted', 'cancelled', 0),
    ('foreground_busy', 'cancelled', 0),
    ('superseded', 'cancelled', 0),
    ('cancelled', 'cancelled', 0),
    ('deadline_exceeded', 'deadline_exceeded', 1),
    ('backend_failed', 'model_failed', 1),
])
def test_structured_reply_classification_preserves_sources(tmp_path, code, expected, streak):
    now = [1000.]
    store = BoardMemoryStore(tmp_path/'synthetic-wire-error.sqlite3', clock=lambda: now[0])
    store.append_event(dict(kind='conversation', id='synthetic-scope'), 'synthetic-event', 'user_said', '公开的合成记录。')
    now[0] += 301
    client = Client(code)
    summary = BoardSummaryClient(client, board_boot_id='synthetic-boot')
    worker = BoardMemoryBackoffWorker(store, summary, idle=lambda: True)
    assert worker.step() is False
    assert client.calls == 1
    assert worker.error == expected
    assert worker.health()['retry_backoff']['failure_streak'] == streak
    with sqlite3.connect(store.path) as db:
        assert db.execute('SELECT COUNT(*) FROM bm_bodies').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM bm_summaries').fetchone()[0] == 0
    if hasattr(summary, 'failure_metadata'):
        assert summary.failure_metadata()['code'] == code


def test_unknown_server_error_code_is_never_exported_verbatim(tmp_path):
    now = [1000.]
    store = BoardMemoryStore(tmp_path/'synthetic-unknown.sqlite3', clock=lambda: now[0])
    store.append_event(dict(kind='conversation', id='synthetic-scope'), 'synthetic-event', 'user_said', '公开记录。')
    now[0] += 301
    summary = BoardSummaryClient(Client('SYNTHETIC_PRIVATE_TOKEN'), board_boot_id='synthetic-boot')
    worker = BoardMemoryBackoffWorker(store, summary, idle=lambda: True)
    assert not worker.step()
    assert worker.error == 'model_failed'
    if hasattr(summary, 'failure_metadata'):
        assert 'SYNTHETIC_PRIVATE_TOKEN' not in json.dumps(summary.failure_metadata())
