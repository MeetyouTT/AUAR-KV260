import hashlib
import importlib.util
import json
from pathlib import Path

from common.board_memory import BoardMemoryStore


HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('metadata_reader_v14', HERE/'board_readonly_metadata_v14.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def test_static_reasons_and_attempt_buckets_never_export_body_or_unknown_values(tmp_path):
    root = tmp_path/'synthetic-root'
    (root/'startup').mkdir(parents=True)
    (root/'startup/config.json').write_text('{}', encoding='utf-8')
    for relative in reader.SOURCE_FILES:
        path = root/'runtime/aura'/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# synthetic\n', encoding='utf-8')
    clock = [1000.]
    store = BoardMemoryStore(tmp_path/'synthetic.sqlite3', clock=lambda: clock[0])
    store.append_event(dict(kind='conversation',id='SYNTHETIC_PRIVATE_ID'), 'SYNTHETIC_PRIVATE_EVENT',
        'user_said', 'SYNTHETIC_PRIVATE_BODY')
    clock[0] = 1400.
    task = store.prepare_compaction()
    store.fail_compaction(task['task_id'], task['lease_token'], 'candidate_rejected')
    state = dict(board_business=dict(clock=dict(utc_lower_bound=1400.,safe_for_compaction=True),
        memory=dict(summary_diagnostics=dict(state='failed',stage='full_source_validation',
            code='candidate_rejected',error_class='CandidateRejected',
            rejection_reasons=['protected_number_missing_or_changed','SYNTHETIC_PRIVATE_REASON']))))
    before = Path(store.path).read_bytes()
    result = reader.diagnose(root, Path(store.path), state_loader=lambda: state)
    assert Path(store.path).read_bytes() == before
    assert result['summary_diagnostics']['rejection_reasons'] == ['protected_number_missing_or_changed']
    assert result['backlog_source_counts'] == [dict(source='user_said', count=1)]
    assert result['task_attempt_buckets'] == [dict(state='failed',error_code='candidate_rejected',attempts_bucket='1',count=1)]
    assert 'SYNTHETIC_PRIVATE' not in json.dumps(result)
