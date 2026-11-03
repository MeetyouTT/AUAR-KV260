"""Record the verified display fix and bounded production observation."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
INTEGRATION = REPAIR.parent
STARTUP = '1129a2a7af2b401537710d1a67651c79961c1b10198f5625ae6802e7ac99fd77'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def proof(path):
    return dict(path=path.relative_to(REPAIR).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def write(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def main():
    sources = dict(installed=INTEGRATION/'listening_entry_fix/actual_automatic-listening-v10-null-status-fix.json',
        ready=INTEGRATION/'production_business_acceptance/actual_ready.json',
        live=INTEGRATION/'listening_entry_fix/actual_live_listening.json',
        control=INTEGRATION/'listening_entry_fix/actual_control_semantics.json')
    docs = {k: read(p) for k, p in sources.items()}
    assert all(docs[k]['startup_sha256'] == STARTUP for k in ('installed', 'live', 'control'))
    ready, live, control = (docs[k] for k in ('ready', 'live', 'control'))
    assert ready['status'] == 'PRODUCTION_BOARD_BUSINESS_READY' and ready['guard_removed']
    assert ready['gtk_pid'] == live['gtk_pid'] == control['gtk_pid']
    assert ready['main_pid'] == int(live['unit']['MainPID']) == control['main_pid']
    assert live['continuous_capture_passed'] and live['priority_scope_passed']
    assert all(control[k] for k in ('pause_preference_false_observed', 'resume_preference_true_observed',
        'cancel_rearm_passed', 'pause_closed_microphone', 'pause_released_owned_arecord', 'model_worker_reused_on_rearm'))
    evidence = {}
    for key, path in sources.items():
        target = HERE/('actual_' + key + '.json')
        if target.exists():
            assert target.read_bytes() == path.read_bytes()
        else:
            target.write_bytes(path.read_bytes())
        evidence[key] = proof(target)
    trace_path = REPAIR/'null_status_long_listening.json'
    rows = read(trace_path)['samples']
    assert len(rows) == 90 and all(row['startup_sha256'] == STARTUP for row in rows)
    assert len({row['board_boot_id'] for row in rows}) == 1
    duration = rows[-1]['observed_mono'] - rows[0]['observed_mono']
    fronts = [row['capture_performance'] for row in rows]
    counts = [row['safe_capture']['counters'] for row in rows]
    queues = [row['safe_capture']['input_queue'] for row in rows]
    same = lambda values: values[0] is not None and len(set(values)) == 1
    same_capture = all(same([v.get(k) for v in fronts]) for k in ('worker_pid', 'worker_generation', 'microphone_pid'))
    same_counts = all(same([v.get(k) for v in counts]) for k in ('armed', 'speech_starts', 'submitted'))
    quiet = all(row['playing'] is False and row['listening']['state'] == 'WAITING_SPEECH'
        and row['listening']['microphone_open'] is True
        and row['safe_capture']['capture'].get('speech_active') is False for row in rows)
    failure_counts = [v.get('capture_failures') for v in fronts]
    capture_ok = (same(failure_counts) and all(type(n) is int and n >= 0 for n in failure_counts)
        and all(row['safe_capture']['error_code'] == 'none' for row in rows))
    no_ui_faults = all(row['runtime_faults']['count'] == 0 for row in rows)
    advancing = all(b.get('frames', 0) > a.get('frames', 0) for a, b in zip(fronts, fronts[1:]))
    original_queue = all(q.get('capacity_frames') == 8 for q in queues)
    passed = duration > 237 and same_capture and same_counts and quiet and capture_ok and no_ui_faults and advancing and original_queue
    endpoint = {}
    calls = fronts[-1].get('endpoint_feed_calls', 0) - fronts[0].get('endpoint_feed_calls', 0)
    if same_capture and advancing and calls > 0:
        endpoint = {name + '_mean_ms': round((fronts[-1]['endpoint_feed_' + name + '_total_ms']
            - fronts[0]['endpoint_feed_' + name + '_total_ms'])/calls, 4) for name in ('wall', 'cpu')}
        endpoint['calls'] = calls
    window = dict(seconds=round(duration, 3), samples=len(rows), bounded_quiet_capture_passed=passed,
        same_capture=same_capture, capture_counters_unchanged=same_counts, quiet_at_all_samples=quiet,
        no_new_capture_failure_in_window=capture_ok, no_ui_faults=no_ui_faults,
        capture_failure_count_at_window_start=failure_counts[0],
        capture_failure_count_at_window_end=failure_counts[-1],
        prior_capture_failure_metadata=rows[0]['last_capture_failure'],
        frames_advancing=advancing, original_queue=original_queue,
        queue_peak_frames=max(q.get('peak_frames', 0) for q in queues), endpoint_feed=endpoint)
    for key, path in dict(observation=trace_path, fault_reproduction=REPAIR/'ui_runtime_fault_trace.json',
        previous_human_confirmation=REPAIR/'guard_session_candidate/STATUS.json',
        display_wake_verification=REPAIR/'display_idle_policy_restored.json',
        regression=HERE/'HANDOFF.json').items():
        evidence[key] = proof(path)
    value = dict(status='NULL_DISPLAY_STATUS_FIXED_BOUNDED_LISTENING_VERIFIED' if passed else 'NULL_DISPLAY_STATUS_FIXED_OBSERVATION_REQUIRES_REVIEW',
        updated_utc=datetime.now(timezone.utc).isoformat(), startup_sha256=STARTUP,
        source_manifest_sha256=docs['installed']['source_manifest_sha256'], component_pins=docs['installed']['component_pins'],
        main_pid=ready['main_pid'], gtk_pid=live['gtk_pid'], camera_pid=live['camera_pid'], board_boot_id=live['board_boot_id'],
        automatic_listening=True, wake_word_required=False, conversation_mode='half_duplex',
        controls_verified=True, short_capture_verified=True, observation=window,
        fixes=['Per-turn readonly connection reuse with fresh checks per packet',
               'Deduplicate unchanged display text',
               'Voice-first listening keeps display awake with existing five-second activity API',
               'Missing recording or latency metadata cannot cancel a dialogue through a formatting TypeError'],
        latest_human_confirmation=dict(revision='v7', feedback='continuous_and_complete',
            evidence='guard_session_candidate/STATUS.json', applies_to_this_display_fix=False),
        full_physical_dialogue_acceptance=False, multi_hour_stability_verified=False,
        controlled_whole_board_cpu_reduction_proven=False, private_data_replayed=False,
        diagnostic_text_or_pcm_saved=False, evidence=evidence, detail='runtime_status_fix_candidate/STATUS.json')
    write(HERE/'STATUS.json', value)
    write(REPAIR/'STATUS.json', value)
    print(json.dumps(dict(status=value['status'], observation=window), ensure_ascii=True))


if __name__ == '__main__':
    main()
