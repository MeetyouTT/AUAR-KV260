"""Cross-module continuity and revocation regressions found during integration."""
import pytest
from contextlib import contextmanager
import sqlite3

from board.runtime.board_memory_policy import BoardContextBuilder, BoardSummaryClient
from common.board_memory import BoardMemoryStore, BoardMemoryWorker, StaleTurn, ScopeDenied
from common.profile_access import ProfileAccess
from common.device_policy import MODEL_HINT
from tools.dialogue_host_ollama import fast_system_prompt
from tests.framework.test_board_memory import Clock, SCOPE
from tests.framework.test_board_memory_completion import FragmentClient


def test_compacted_long_turn_fits_next_turn_with_the_real_accepted_persona(tmp_path):
    clock = Clock()
    store = BoardMemoryStore(tmp_path / 'public-continuity.sqlite3', clock=clock)
    store.append_event(SCOPE, 'long-public-input', 'user_said', '普通背景，' * 1400)
    clock.advance(301)
    builder = BoardContextBuilder(fast_system_prompt() + MODEL_HINT)
    capacity = min(768, builder.continuity_capacity())
    assert capacity >= 64
    client = BoardSummaryClient(FragmentClient(), board_boot_id='public-boot',
                               final_summary_max_utf8_bytes=capacity)
    assert BoardMemoryWorker(store, client, idle=lambda: True).step()
    assert store.health()['active_bodies'] == 0
    builder(store.context(SCOPE), '继续聊刚才的内容。')
    assert builder.metrics['continuity_summary']
    assert builder.metrics['budget_upper_bound'] <= 2048
    assert client.metrics['final_summary_utf8_bytes'] <= capacity


def test_local_sequence_liveness_is_revoked_by_scope_clear_and_generation(tmp_path):
    clock = Clock()
    store = BoardMemoryStore(tmp_path / 'public-local-sequence.sqlite3', clock=clock)
    store.begin_turn(SCOPE, 'guide', '公开登记流程测试', generation=2)
    assert store.check_turn_current('guide', generation=2)
    with pytest.raises(StaleTurn):
        store.check_turn_current('guide', generation=1)
    store.clear(SCOPE, operation_id='clear-public-test')
    with pytest.raises(StaleTurn):
        store.check_turn_current('guide', generation=2)


def test_local_sequence_rechecks_the_same_live_profile_grant(tmp_path):
    clock = Clock(); access = ProfileAccess('a' * 64, clock=clock)
    store = BoardMemoryStore(tmp_path / 'public-profile-guide.sqlite3', clock=clock, profile_access=access)
    pid = store.create_profile('公开合成档案', consent=True)
    meta = dict(board_boot_id='public-boot', session_id='public-session')
    _, grant = access.issue(pid, meta)
    store.begin_turn(dict(kind='profile', id=pid, grant=grant), 'guide', '公开测试', generation=1)
    assert store.check_turn_current('guide', generation=1)
    access.revoke(meta)
    with pytest.raises((ScopeDenied, PermissionError)):
        store.check_turn_current('guide', generation=1)


def test_before_step_can_refresh_clock_without_a_quality_lease_or_sqlite_lock(tmp_path):
    clock = Clock(); store = BoardMemoryStore(tmp_path/'public-maintenance.sqlite3', clock=clock)
    store.append_event(SCOPE, 'public', 'user_said', '公开内容')
    clock.advance(301)
    guarded = []; order = []
    @contextmanager
    def guard():
        guarded.append(True)
        try:
            yield
        finally:
            guarded.pop()
    def maintenance(cancelled):
        assert not guarded and not cancelled()
        with sqlite3.connect(store.path, timeout=.01, isolation_level=None) as db:
            db.execute('BEGIN IMMEDIATE'); db.rollback()
        order.append('refresh')
        return False  # New capture could have preempted maintenance.
    def no_model(*_):
        raise AssertionError('Maintenance declined this idle step')
    worker = BoardMemoryWorker(store, no_model, idle=lambda: True,
                               compaction_guard_factory=guard, before_step=maintenance)
    assert worker.step() is False and order == ['refresh']
    assert store.health()['active_bodies'] == 1
    worker.stop.set()
    assert worker.step() is False and order == ['refresh']


def test_normalized_device_query_is_labelled_and_cannot_be_misattributed_as_a_private_user_quote(tmp_path):
    clock = Clock(); store = BoardMemoryStore(tmp_path/'public-device-query.sqlite3', clock=clock)
    device = dict(kind='device', id='public-camera')
    meta = dict(claims=[dict(field='input_representation', value='normalized_visual_query')])
    store.begin_turn(device, 'query', '设备查询意图（规范化）：查询公开人数。', generation=1,
                     metadata=meta, input_source='device_event')
    assert store.history(device)[0]['source'] == 'device_event'
    assert store.context(device)['messages'] == []
    with pytest.raises(ValueError):
        store.begin_turn(device, 'unlabelled', '规范意图', input_source='device_event')
    with pytest.raises(ScopeDenied):
        store.begin_turn(SCOPE, 'private-scope', '规范意图', metadata=meta, input_source='device_event')
