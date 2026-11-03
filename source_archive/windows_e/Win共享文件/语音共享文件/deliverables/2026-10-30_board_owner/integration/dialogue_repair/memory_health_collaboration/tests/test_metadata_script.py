"""Exercise production-shaped metadata reader on a fully synthetic fixture."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3

from common.board_memory import BoardMemoryStore

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('synthetic_board_metadata', HERE/'board_readonly_metadata.py')
metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata)


def layout(tmp_path):
    root = tmp_path/'public-production'
    (root/'startup').mkdir(parents=True)
    (root/'startup/config.json').write_text('{}', encoding='utf-8')
    for name in metadata.SOURCE_FILES:
        target = root/'runtime/aura'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('# public synthetic source\n', encoding='utf-8')
    return root


def test_fixed_field_reader_locates_runtime_and_keeps_db_unchanged(tmp_path):
    root = layout(tmp_path)
    now = [1000.]
    database = tmp_path/'synthetic.sqlite3'
    store = BoardMemoryStore(database, clock=lambda: now[0])
    store.append_event(dict(kind='conversation', id='SYNTHETIC_PRIVATE_SCOPE'),
        'SYNTHETIC_PRIVATE_EVENT', 'user_said', 'SYNTHETIC_PRIVATE_TEXT')
    now[0] = 1400.
    task = store.prepare_compaction()
    store.fail_compaction(task['task_id'], task['lease_token'], 'model_failed')
    def state():
        return dict(reply='SYNTHETIC_PRIVATE_TEXT', board_business=dict(
            memory=dict(running=True, completed=0, discarded=3, error='operation_failed',
                retry_backoff=dict(failure_streak=3, last_failure_code='model_failed', last_delay_seconds=12),
                summary_diagnostics=dict(state='failed', stage='semantic_json', code='candidate_rejected',
                    error_class='JSONDecodeError', private='SYNTHETIC_PRIVATE_TOKEN')),
            retention=dict(enabled=True),
            clock=dict(utc_lower_bound=1400., safe_for_compaction=True, verified_age_seconds=4., uncertainty_seconds=1.)))
    before = database.read_bytes()
    result = metadata.diagnose(root, database, state_loader=state)
    assert database.read_bytes() == before
    assert result['diagnostic_status'] == 'metadata_read_complete'
    assert all(result['source_sha256'].values())
    assert result['store']['backlog_events'] == 1
    assert result['store']['oldest_backlog_age_seconds'] == 400
    assert result['store']['unlinked_missing_valid_bodies'] == 0
    assert result['store']['compacted_bodies_remaining'] == 0
    assert result['latest_16_task_counts'] == [dict(state='failed', error_code='model_failed', count=1)]
    assert result['retry']['last_failure_code'] == 'model_failed'
    assert result['missing_body_classification']['total'] == result['missing_body_classification']['unexplained'] == 0
    assert result['summary_diagnostics']['stage'] == 'semantic_json'
    assert 'SYNTHETIC_PRIVATE' not in json.dumps(result)
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT COUNT(*) FROM bm_bodies').fetchone()[0] == 1


def test_version_mismatch_exits_before_state_or_database_read(tmp_path):
    root = layout(tmp_path)
    def forbidden():
        raise AssertionError('Must not read old version state')
    result = metadata.diagnose(root, tmp_path/'nonexistent.sqlite3', expected_sha='a'*64, state_loader=forbidden)
    assert result['diagnostic_status'] == 'version_changed_repin_before_read'
    assert result['expected_startup_matches'] is False


def test_known_valid_bodyless_command_requires_migration_and_current_fact_proof(tmp_path):
    from common.timeline_conversations import TimelineConversationStore
    from tests.framework.test_board_memory_migration import command, migrate
    source = TimelineConversationStore(tmp_path/'synthetic-legacy.sqlite3')
    command(source, 1, '记住：项目是海风')
    target = BoardMemoryStore(tmp_path/'synthetic-target.sqlite3', clock=lambda: 2000.)
    migrate(source, target)
    with sqlite3.connect(target.path) as db:
        result = metadata.missing_body_metadata(db)
        assert result['total'] == result['migrated_excluded_command_with_current_fact'] == 1
        assert result['unexplained'] == 0
        assert target.context(dict(kind='conversation', id='a'*32))['facts'][0]['value'] == '海风'
        # An omitted explicit privacy marker cannot be assumed legitimate.
        db.execute('DELETE FROM bm_migration_exclusions')
        result = metadata.missing_body_metadata(db)
        assert result['total'] == result['unexplained'] == 1
        assert result['migrated_excluded_command_with_current_fact'] == 0
