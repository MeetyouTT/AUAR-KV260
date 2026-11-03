"""Focused v14 review with public synthetic SQLite and no model client."""
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

import pytest

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parent / 'memory_health_collaboration/v14_validation_candidate'
sys.path.insert(0, str(HERE.parents[4] / 'aura'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


import common
memory = load('common.board_memory', CANDIDATE / 'after/common/board_memory.py')
common.board_memory = memory
load('common.board_memory_backoff', CANDIDATE / 'before/common/board_memory_backoff.py')
policy = load('board.runtime.board_memory_policy', CANDIDATE / 'after/board/runtime/board_memory_policy.py')


class NoModel:
    def request(self, *args, **kwargs): raise AssertionError('No inference is permitted')
    def cancel(self, owner): raise AssertionError('No inference owner exists')


def fixture(tmp_path):
    now = [1000.]
    store = memory.BoardMemoryStore(tmp_path / 'public-camera.sqlite3', clock=lambda: now[0])
    scope = dict(kind='device', id='public-camera')
    # The insertion order differs from recording time; all metadata is public.
    for count, frame, recorded in ((2, 11, 1001.), (7, 13, 1003.), (0, 12, 1002.)):
        now[0] = recorded
        text = '摄像头视野内稳定检测到%d个人体目标。' % count if count else '摄像头视野内当前未检测到人体目标。'
        store.append_event(scope, 'public-frame-' + str(frame), 'camera_observed', text, topic='视觉',
            metadata=dict(evidence='visual_observation', numbers=[count], speaker_known=False,
                source_id='a' * 64, time_basis='board_camera_health_source_bound', occurred_utc=recorded,
                claims=[dict(field='event_kind', value='person_count_observed' if count else 'no_person_detected'),
                        dict(field='people_count', value=count), dict(field='source_frame_id', value=frame),
                        dict(field='source_kind', value='actual')]))
    now[0] = 1400.
    task = store.prepare_compaction(max_events=8)
    assert len(task['sources']) == 3
    summary = policy.BoardSummaryClient(NoModel(), board_boot_id='public-boot')
    return store, scope, task, summary


def test_all_sources_order_refs_claims_survive_atomic_structured_publication(tmp_path):
    store, scope, task, summary = fixture(tmp_path)
    original_refs = {(s['event_id'], s['revision']) for s in task['sources']}
    original_claims = copy.deepcopy(task['required_claims'])
    task['sources'].reverse()
    value = summary(task, lambda: False)
    assert value['summary'] == '相机观察：人体目标采样计数依次为2、0、7。0仅表示该采样未检出人体。'
    assert {(r['event_id'], r['revision']) for r in value['source_refs']} == original_refs
    assert value['claims'] == original_claims
    assert summary.metrics['complete_source_coverage'] and summary.metrics['model_calls'] == 0
    saved = store.commit_compaction(task['task_id'], task['lease_token'], value)
    assert saved['committed']
    with sqlite3.connect(store.path) as db:
        assert db.execute('SELECT COUNT(*) FROM bm_bodies').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM bm_summary_sources').fetchone()[0] == 3
        assert db.execute('SELECT COUNT(*) FROM bm_events WHERE state=?', ('valid',)).fetchone()[0] == 3
        assert json.loads(db.execute('SELECT claims FROM bm_summaries').fetchone()[0]) == original_claims


@pytest.mark.parametrize('key,value', [('names', ['SYNTHETIC_PRIVATE_NAME']), ('negated', True), ('status', 'planned')])
def test_additional_protected_metadata_declines_local_projection(tmp_path, key, value):
    store, scope, task, summary = fixture(tmp_path)
    eligible = copy.deepcopy(task['sources'])
    eligible[1]['metadata'][key] = value
    assert summary._structured_camera_summary(task, eligible) is None
    assert store.health()['active_bodies'] == 3


def test_mixed_user_source_is_not_dropped_to_make_camera_only_summary(tmp_path):
    store, scope, task, summary = fixture(tmp_path)
    eligible = copy.deepcopy(task['sources'])
    eligible[1]['source'] = 'user_said'
    assert summary._structured_camera_summary(task, eligible) is None
    assert len(eligible) == 3 and store.health()['active_bodies'] == 3


def test_over_capacity_declines_instead_of_omitting_sources_or_truncating(tmp_path):
    store, scope, task, summary = fixture(tmp_path)
    summary.final_maximum = 64
    assert summary._structured_camera_summary(task, task['sources']) is None
    assert store.health()['active_bodies'] == 3 and store.health()['valid_summaries'] == 0


@pytest.mark.parametrize('field,value', [('people_count', True), ('source_frame_id', True)])
def test_boolean_values_cannot_impersonate_typed_integer_claims(tmp_path, field, value):
    _, _, task, summary = fixture(tmp_path)
    eligible = copy.deepcopy(task['sources'])
    for claim in eligible[0]['metadata']['claims']:
        if claim['field'] == field: claim['value'] = value
    assert summary._structured_camera_summary(task, eligible) is None
