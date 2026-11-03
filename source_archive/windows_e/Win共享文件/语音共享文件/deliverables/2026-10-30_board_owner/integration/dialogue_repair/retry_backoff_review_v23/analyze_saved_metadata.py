"""Only saved sanitized metadata and a SHA-matched archived retry wrapper."""
import hashlib
import json
from pathlib import Path

REPAIR = Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-10-30_board_owner\integration\dialogue_repair')
OUTPUT = Path(__file__).resolve().parent


def read_json(path):
    data = path.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def main():
    live_path = REPAIR / 'progress_followup_20261031/v23_live_observe_1793514697378584800.json'
    features_path = REPAIR / 'progress_followup_20261031/v23_failed_source_features_1793514848527022800.json'
    mapping_path = REPAIR / 'release_v23_memory_summary_candidate/memory_summary_evidence/source_mapping.json'
    live, live_sha = read_json(live_path)
    features, features_sha = read_json(features_path)
    mapping, mapping_sha = read_json(mapping_path)
    assert live_sha == 'b9ff2af933d66e50a9c7dd474a82916953c6104f9ef1780178147cd4a7e8fde4'
    assert features_sha == '318d81a78bdbdcef063df02b55ac243dbe4f54376e5554a32dd003bee7472549'
    assert live['startup_sha256'] == mapping['startup_sha256']
    index, _ = read_json(REPAIR / 'jpeg_demand_review_v20/SOURCE_AUDIT.json')
    source = next(row for row in index['files'] if row['component'] == 'common/board_memory_backoff.py')
    source_sha = hashlib.sha256(Path(source['path']).read_bytes()).hexdigest()
    assert source_sha == mapping['component_pins']['common/board_memory_backoff.py']

    samples = live['samples']
    start = samples[0]['observed_mono']
    events = []
    previous_key = None
    resets = []
    for sample in samples:
        memory = sample['memory_reason']
        worker, retry, summary = memory['worker'], memory['retry'], memory['summary']
        key = (worker['completed'], worker['discarded'], retry['failure_streak'], retry['last_delay_seconds'])
        if key != previous_key:
            event = dict(observed_offset_seconds=sample['observed_mono'] - start,
                completed=worker['completed'], discarded=worker['discarded'],
                failure_streak=retry['failure_streak'], last_delay_seconds=retry['last_delay_seconds'],
                summary_stage=summary['stage'], summary_state=summary['state'],
                summary_method=summary.get('method'), rejection_reasons=summary.get('rejection_reasons', []))
            if previous_key and worker['completed'] > previous_key[0] and retry['failure_streak'] == 0 and previous_key[2] > 0:
                resets.append(event)
            events.append(event)
            previous_key = key
    after_resets = []
    for reset in resets:
        failure = next((event for event in events if event['observed_offset_seconds'] > reset['observed_offset_seconds']
                        and event['discarded'] > reset['discarded']), None)
        if failure:
            after_resets.append(dict(success_observed_offset_seconds=reset['observed_offset_seconds'],
                next_failure_observed_offset_seconds=failure['observed_offset_seconds'],
                observed_sample_time_difference_seconds=failure['observed_offset_seconds'] - reset['observed_offset_seconds'],
                next_failure_streak=failure['failure_streak'], next_failure_delay_seconds=failure['last_delay_seconds']))
    rows = features['rows']
    first = samples[0]['memory_reason']['worker']
    last = samples[-1]['memory_reason']['worker']
    result = dict(schema='aura.v23-global-retry-reset-review.v1',
        status='GLOBAL_RESET_CONFIRMED_SAME_BATCH_FREQUENCY_AND_RESOURCE_EFFECT_UNPROVEN',
        startup_sha256=live['startup_sha256'],
        evidence=dict(live_file=str(live_path), live_sha256=live_sha, features_file=str(features_path),
            features_sha256=features_sha, source_mapping_sha256=mapping_sha,
            archived_backoff_path=source['path'], archived_backoff_sha256=source_sha),
        observation=dict(samples=len(samples), duration_seconds=samples[-1]['observed_mono']-start,
            maximum_sampling_gap_seconds=max(b['observed_mono']-a['observed_mono'] for a,b in zip(samples,samples[1:])),
            completed_delta=last['completed']-first['completed'], discarded_delta=last['discarded']-first['discarded'],
            observed_success_resets=len(resets), state_transitions=events, failure_after_reset=after_resets,
            all_samples_paused=all(s['listening']['enabled'] is False and s['listening']['microphone_open'] is False for s in samples)),
        failed_source_features=dict(failed_task_rows=len(rows), attempts_min=min(x['attempts'] for x in rows),
            attempts_max=max(x['attempts'] for x in rows), recorded_attempts_sum=sum(x['attempts'] for x in rows),
            bytes_per_batch_min=min(x['source_utf8_bytes'] for x in rows), bytes_per_batch_max=max(x['source_utf8_bytes'] for x in rows),
            sources_per_batch_min=min(x['sources'] for x in rows), sources_per_batch_max=max(x['sources'] for x in rows),
            all_sources_user_said=all(x['source_kinds']['user_said']==x['sources'] for x in rows)),
        established=['The pinned wrapper has one global retry state and resets it on any committed batch.',
            'Three observed successful commits reset streak to0; the next observed failure in each case starts at delay3.',
            'The final failure without an intervening observed success advances the streak from1to2 and delay from3to6.'],
        not_established=['The observations contain no batch identifiers or per-batch attempt timestamps, so a reset cannot be linked to one of the12failed rows.',
            'The cumulative180recorded attempts are not180LLM requests in this63second window.',
            'Observed event sample differences are not exact task admission, retry waiting or model inference times.',
            'Neither successful nor failed compaction count proves an LLM call.',
            'No CPU, GPU, cache-hit or actual dialogue-latency effect was measured.',
            'The current v23 Store selection implementation was not opened or modified in this review.'],
        recommendations=['Keep semantic guards unchanged while root diagnoses negation handling.',
            'Consider batch-scoped validation-failure cooldown keyed by stable sources/revisions and policy version, distinct from global backend-error backoff.',
            'Unrelated successful batches must not clear a deferred batch; source revision/policy change or success of that batch can clear its own state.',
            'Skip deferred batches before leasing so healthy work can progress; avoid re-leasing and discarding every3seconds.',
            'First obtain board-local numeric prior-attempt age for the selected batch. If a12batch rotation already exceeds60seconds, a60second per-batch cooldown alone may have no effect.',
            'Keep quiet30seconds and foreground preemption as separate scheduling protections; they do not remove repeated failures during long PAUSED idle.'],
        model_requests_sent=False, device_connections_opened=False, product_sources_modified=False,
        publisher_opened_or_executed=False, real_memory_database_opened=False, private_content_or_ids_exported=False)
    (OUTPUT / 'ANALYSIS.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(status=result['status'], samples=len(samples), completed_delta=last['completed']-first['completed'],
        discarded_delta=last['discarded']-first['discarded'], observed_resets=len(resets), after_reset=after_resets)))


if __name__ == '__main__':
    main()
