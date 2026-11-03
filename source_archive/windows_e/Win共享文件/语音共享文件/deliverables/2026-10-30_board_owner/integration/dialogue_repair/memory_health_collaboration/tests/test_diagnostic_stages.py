"""Missing telemetry must not be replaced by payload-bearing error strings."""
import json
import sqlite3

import pytest

from common.board_memory import BoardMemoryStore
from common.board_memory_backoff import BoardMemoryBackoffWorker
from common.model_inference_wire import Owner, make_response
from board.runtime.board_memory_policy import BoardSummaryClient


class Client:
    def __init__(self, text):
        self.text = text

    def request(self, kind, payload, **kwargs):
        return make_response(Owner.from_dict(payload), result=dict(text=self.text))

    def cancel(self, owner):
        pass


@pytest.mark.parametrize('text,stage', [
    ('SYNTHETIC_PRIVATE_RESPONSE', 'semantic_json'),
    ('{"summary":"公开","keywords":["公开"],"unknown":"SYNTHETIC_PRIVATE_RESPONSE"}', 'semantic_shape'),
    ('{"summary":"公开","keywords":[]}', 'semantic_bounds'),
    ('{"summary":"公开","keywords":["公开","公开"]}', 'semantic_bounds'),
    ('{"summary":"公开","keywords":["公开"]}', 'full_source_validation'),
])
def test_candidate_rejection_keeps_body_and_reports_only_static_stage(tmp_path, text, stage):
    now = [1000.]
    store = BoardMemoryStore(tmp_path/'synthetic-reject.sqlite3', clock=lambda: now[0])
    store.append_event(dict(kind='conversation', id='synthetic-scope'), 'synthetic-event', 'user_said',
        '公开数字42不得遗漏。', metadata=dict(numbers=[42]))
    now[0] = 1400.
    summary = BoardSummaryClient(Client(text), board_boot_id='synthetic-boot')
    worker = BoardMemoryBackoffWorker(store, summary, idle=lambda: True)
    assert not worker.step()
    assert worker.error == 'candidate_rejected'
    report = worker.health()['summary_diagnostics']
    assert report['stage'] == stage
    assert report['state'] == 'failed' and report['code'] == 'candidate_rejected'
    assert 'SYNTHETIC_PRIVATE_RESPONSE' not in json.dumps(worker.health())
    assert store.health()['active_bodies'] == 1
    assert store.health()['valid_summaries'] == 0


def test_success_clears_diagnostics_and_processes_backlog_after_failure(tmp_path):
    now = [1000.]
    store = BoardMemoryStore(tmp_path/'synthetic-recover.sqlite3', clock=lambda: now[0])
    store.append_event(dict(kind='conversation', id='synthetic-scope'), 'synthetic-event', 'user_said',
        '公开数字42不得遗漏。', metadata=dict(numbers=[42]))
    now[0] = 1400.
    client = Client('{"summary":"公开","keywords":["公开"]}')
    summary = BoardSummaryClient(client, board_boot_id='synthetic-boot')
    retry_time = [1.]
    worker = BoardMemoryBackoffWorker(store, summary, idle=lambda: True, retry_clock=lambda: retry_time[0])
    assert not worker.step()
    assert store.health()['backlog_events'] == 1
    assert worker.health()['summary_diagnostics']['stage'] == 'full_source_validation'
    client.text = '{"summary":"公开数字42不得遗漏。","keywords":["公开"]}'
    retry_time[0] += 3
    assert worker.step()
    assert store.health()['backlog_events'] == store.health()['active_bodies'] == 0
    assert store.health()['valid_summaries'] == 1
    assert worker.health()['summary_diagnostics'] == dict(state='complete', stage='complete', code='none', error_class='none')
    assert worker.health()['retry_backoff']['failure_streak'] == 0
    with sqlite3.connect(store.path) as db:
        assert db.execute('SELECT text FROM bm_bodies').fetchall() == []
