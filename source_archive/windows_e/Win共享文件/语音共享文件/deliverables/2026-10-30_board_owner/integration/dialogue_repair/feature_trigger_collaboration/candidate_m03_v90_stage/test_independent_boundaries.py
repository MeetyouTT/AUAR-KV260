"""Extra public-only scope/dependency cases absent from the original four."""
from datetime import datetime
import importlib.util
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from common.profile_access import ProfileAccess


FEATURE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    'independent_public_m03_fixture',
    FEATURE / 'review_m03_win_inference/test_delete_boundaries.py',
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


@pytest.fixture
def public_store():
    value = fixture.DeleteBoundaryReview(methodName='runTest')
    value.setUp()
    try:
        yield value
    finally:
        value.doCleanups()


def test_same_fact_revision_other_user_cosource_outside_day_survives(public_store):
    r = public_store
    midnight = datetime(2026, 10, 31, tzinfo=ZoneInfo('America/Los_Angeles')).timestamp()
    r.append('public-yesterday-root', midnight - 10.)
    r.append('public-today-cosource', midnight + 10.)
    r.store.correct(r.scope, '项目', '公开同版关联值', source_event_ids=(
        'public-yesterday-root', 'public-today-cosource',
    ))
    r.say('删除昨天的对话记录')
    r.say('确认删除记录')
    assert r.state('public-yesterday-root') == 'forgotten'
    assert r.state('public-today-cosource') == 'valid'
    assert r.store.context(r.scope)['facts'] == []
    assert all('公开同版关联值' not in row['text'] for row in r.store.history(r.scope))
    with r.store._db() as db:
        assert db.execute('SELECT count(*) FROM bm_bodies WHERE event_id=?',
                          ('public-today-cosource',)).fetchone()[0] == 1


def test_new_fact_link_after_preview_invalidates_unchanged_root_set(public_store):
    r = public_store
    r.append('public-unchanged-root', r.now - 60.)
    r.say('删除今天的对话记录')
    r.store.correct(r.scope, '新项目', '公开预览后关联值', source_event_ids=('public-unchanged-root',))
    reply = r.say('确认删除记录')
    assert '已变化，没有删除' in reply
    assert r.state('public-unchanged-root') == 'valid'
    assert r.store.context(r.scope)['facts'][0]['value'] == '公开预览后关联值'


def test_profile_revocation_after_mutation_rolls_back_before_commit(public_store, monkeypatch):
    r = public_store
    access = ProfileAccess('7' * 64, clock=r.mono)
    access.authenticate('7' * 64)
    actor = {'board_boot_id': 'public-review-boot', 'session_id': 'public-review-session'}
    _, grant = access.issue('b' * 32, actor)
    r.store.profile_access = access
    r.scope = {'kind': 'profile', 'id': 'b' * 32, 'grant': grant}
    r.append('public-revocation-target', r.now - 60.)
    r.say('删除个人今天的对话记录')
    original_save = r.store._save_operation
    notifications = []
    r.store.notify_history_delete_committed = lambda **kwargs: notifications.append(kwargs)

    def revoke_after_write(*args, **kwargs):
        original_save(*args, **kwargs)
        access.revoke(actor)

    monkeypatch.setattr(r.store, '_save_operation', revoke_after_write)
    with pytest.raises(PermissionError):
        r.say('确认删除记录')
    assert r.state('public-revocation-target') == 'valid'
    assert notifications == []
    with r.store._db() as db:
        assert db.execute("SELECT count(*) FROM bm_operations WHERE kind='transcript_delete'").fetchone()[0] == 0
