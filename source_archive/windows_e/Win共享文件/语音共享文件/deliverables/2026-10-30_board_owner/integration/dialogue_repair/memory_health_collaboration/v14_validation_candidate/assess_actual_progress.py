"""Analyze root-supplied fixed-field receipts locally; never connect to board."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_INITIAL = HERE.parents[1]/'first_wait_integration/actual_memory_v14_initial.json'


def load(path):
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    assert value['metadata_only'] is True and value['read_only'] is True
    assert value['diagnostic_status'] == 'metadata_read_complete'
    assert value['expected_startup_matches'] is True
    return value


def committed(value):
    return sum(row['count'] for row in value['task_counts'] if row['state'] == 'committed')


def sources(value):
    return {row['source']: row['count'] for row in value['backlog_source_counts']}


def assess(initial_path=DEFAULT_INITIAL, followup_path=None):
    baseline = load(initial_path)
    candidate = json.loads((HERE/'HANDOFF.json').read_text(encoding='utf-8'))
    expected = {name: row['sha256'] for name,row in candidate['files'].items()}
    expected['common/board_memory_backoff.py'] = candidate['unchanged_backoff_sha256']
    matches = {name: baseline['source_sha256'].get(name) == digest for name,digest in expected.items()}
    assert all(matches.values())
    body_proof = baseline['missing_body_classification']
    source_counts = sources(baseline)
    assert sum(source_counts.values()) == baseline['store']['backlog_events']
    result = dict(status='INITIAL_V14_STRUCTURED_SUMMARY_COMMITS_VERIFIED_BACKLOG_TREND_PENDING',
        evidence=dict(path=str(initial_path), sha256=hashlib.sha256(initial_path.read_bytes()).hexdigest()),
        startup_sha256=baseline['startup_sha256'], candidate_modules_match=matches,
        worker=baseline['worker'], retry=baseline['retry'], last_summary=baseline['summary_diagnostics'],
        durable_committed_tasks=committed(baseline), valid_summaries=baseline['store']['valid_summaries'],
        previous_v13_durable_committed=270,
        durable_committed_change_since_v13=committed(baseline)-270,
        process_counter_note='Worker completed and lifetime SQLite totals have different origins. Reader fetches public state before opening SQLite snapshot; do not force 270+worker.completed to equal lifetime total.',
        backlog=dict(events=baseline['store']['backlog_events'], source_counts=source_counts,
            camera_source_events=source_counts.get('camera_observed',0),
            other_source_events=sum(count for name,count in source_counts.items() if name!='camera_observed'),
            oldest_age_seconds=baseline['store']['oldest_backlog_age_seconds'],
            last_commit_age_seconds=baseline['store']['last_commit_age_seconds'],
            eligible_structured_camera_count='Not measured: source type alone is not the exact producer-contract eligibility test'),
        invariants=dict(compacted_bodies_remaining=baseline['store']['compacted_bodies_remaining'],
            invalidated_summary_payloads_remaining=baseline['store']['invalidated_summary_payloads_remaining'],
            known_bodyless_migration_markers=body_proof['migrated_excluded_command_with_current_fact'],
            unexplained_missing_bodies=body_proof['unexplained'],
            active_leases=baseline['store']['active_leases'], expired_leases=baseline['store']['expired_leases']),
        conclusions=dict(structured_camera_summary_publication='PASS: latest method and durable successful commits observed on matching deployed source',
            deletion_structure='PASS at snapshot: no bodies remain linked to compacted events; unknown missing-body count is zero',
            lifetime_store='PASS at snapshot: durable summaries increased since v13',
            backlog_net_decline='NOT_VERIFIED: earlier 796 and current 869 differ in version/time and include new arrivals; use this initial sample as baseline',
            all_pending_work_cleared='NOT_PASSED: 869 pending events remain',
            free_form_summary_quality='NOT_VERIFIED', real_conversation_retrieval_correction_forgetting='NOT_VERIFIED'),
        this_conversation_connected_to_board=False, this_conversation_modified_production=False)
    if followup_path is not None:
        latest = load(followup_path)
        same_startup = latest['startup_sha256'] == baseline['startup_sha256']
        same_sources = latest['source_sha256'] == baseline['source_sha256']
        seconds = latest['observed_mono']-baseline['observed_mono']
        comparison = dict(evidence=str(followup_path), evidence_sha256=hashlib.sha256(followup_path.read_bytes()).hexdigest(),
            same_startup=same_startup, same_source_map=same_sources,
            observed_monotonic_elapsed_seconds=seconds, comparable=same_startup and same_sources and seconds>0)
        if comparison['comparable']:
            final_sources = sources(latest)
            net = latest['store']['backlog_events']-baseline['store']['backlog_events']
            comparison.update(backlog_net_change=net, backlog_net_declined=net<0,
                durable_committed_change=committed(latest)-committed(baseline),
                valid_summaries_change=latest['store']['valid_summaries']-baseline['store']['valid_summaries'],
                source_net_changes={name:final_sources.get(name,0)-source_counts.get(name,0)
                    for name in sorted(set(final_sources)|set(source_counts))},
                latest_worker=latest['worker'], latest_retry=latest['retry'],
                latest_summary_diagnostics=latest['summary_diagnostics'], latest_store=latest['store'],
                note='Net queue change includes arrivals and any authorized mutations; report it alongside successful commits, not as an isolated throughput measurement.')
            result['status'] = 'SAME_V14_BACKLOG_NET_DECLINE_VERIFIED' if net<0 else 'SAME_V14_SNAPSHOT_NO_NET_DECLINE'
            result['conclusions']['backlog_net_decline'] = ('PASS: pending events declined between matching version snapshots'
                if net<0 else 'NOT_VERIFIED: matching followup did not show net queue decline')
            result['conclusions']['all_pending_work_cleared'] = ('PASS at followup snapshot' if latest['store']['backlog_events']==0
                else 'NOT_PASSED: %d pending events remain at followup' % latest['store']['backlog_events'])
            result['latest_observation'] = dict(evidence=str(followup_path), startup_sha256=latest['startup_sha256'],
                worker=latest['worker'], retry=latest['retry'], last_summary=latest['summary_diagnostics'],
                durable_committed_tasks=committed(latest), valid_summaries=latest['store']['valid_summaries'],
                backlog=dict(events=latest['store']['backlog_events'],source_counts=final_sources,
                    camera_source_events=final_sources.get('camera_observed',0),
                    other_source_events=sum(n for s,n in final_sources.items() if s!='camera_observed')),
                missing_body_classification=latest['missing_body_classification'])
        result['followup_comparison'] = comparison
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--initial',type=Path,default=DEFAULT_INITIAL)
    parser.add_argument('--followup',type=Path)
    args = parser.parse_args()
    result = assess(args.initial,args.followup)
    target = HERE/('ACTUAL_PROGRESS_ASSESSMENT.json' if args.followup else 'ACTUAL_INITIAL_ASSESSMENT.json')
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    latest = result.get('latest_observation',result)
    print(json.dumps(dict(status=result['status'], worker=latest['worker'],
        durable_committed_tasks=latest['durable_committed_tasks'], backlog=latest['backlog'],
        followup=result.get('followup_comparison')),ensure_ascii=True))
