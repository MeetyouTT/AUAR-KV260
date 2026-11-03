"""Assess saved numeric evidence, with no live device or database access."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[5]
RET = PROJECT/'deliverables/2026-10-31_visual_axis_maintenance/reviews/summary_retention_acceptance_20261101'
paths = [RET/'evidence/target_probe_r3_baseline_1793539124765536800.json',
         RET/'evidence/target_probe_r3_after_natural_300s_1793539342593344500.json']
expected = ['edf8640513238d30c2cb2d06b4e8e971b2572c51ab84292928015dd44369a824',
            '307496a52a80319c69674c08f4e36e0b098c714ef2e1316cdb6f016f0c7a59a6']
reports = []
for path, digest in zip(paths, expected):
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest()==digest
    envelope = json.loads(data)
    assert envelope['probe_sha256']=='cbe23506be5c5a5864814537f8cb0770592803437358d31a8e3a9e072052ae6c'
    assert envelope['result']['probe_exit_code']==0
    report = envelope['result']['probe_result']
    assert report['status']=='TARGET_METADATA_COMPLETE'
    assert report['selected_conversation_matches_seed'] is True
    assert report['clock_safe_for_compaction'] is True
    assert report['seed_request_token']=='8db2358adf1cd749e621baaee14ec65a8b87ba50a042b8419a8dfa32c1e86f34'
    assert report['seed_full_playback_recorded'] is True
    reports.append(report)
before, after = reports
assert before['seed_scope_token']==after['seed_scope_token']
assert [e['body_rows'] for e in before['seed_events']]==[1,1]
assert [e['body_rows'] for e in after['seed_events']]==[0,0]
assert [e['event_token'] for e in before['seed_events']]==[e['event_token'] for e in after['seed_events']]
assert all(e['eligible_age_reached'] is False for e in before['seed_events'])
assert after['target_compaction_proven'] is True
assert after['seed_turn_closed_age_seconds']>=300
assert all(e['current_fact_source_links']==0 and e['valid_summary_link_count']==1 and e['committed_task_count']==1 for e in after['seed_events'])
assert after['seed_events'][0]['valid_summary_tokens']==after['seed_events'][1]['valid_summary_tokens']
result = dict(schema='aura-root-natural-retention-assessment-1', status='STORAGE_PASS_RECALL_PENDING',
    seed_request_token=after['seed_request_token'], seed_scope_token=after['seed_scope_token'],
    baseline_body_rows=[1,1], after_body_rows=[0,0],
    baseline_closed_age_seconds=before['seed_turn_closed_age_seconds'],
    after_closed_age_seconds=after['seed_turn_closed_age_seconds'],
    same_valid_direct_summary_for_both=True, committed_tasks=True, current_fact_links=0,
    clock_verified_for_age=True, forced_clock_or_compaction_or_deletion=False,
    only_saved_metadata_read_by_assessor=True, actual_prompt_retrieval_observed=False,
    evidence=[dict(path=str(path),sha256=sha) for path,sha in zip(paths,expected)])
(HERE/'RETENTION_RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
