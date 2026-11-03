"""Archive matching deployment receipts and summarize metadata-only observations."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
INTEGRATION = REPAIR.parent
STARTUP = 'e9fca749489d1333e20c3df0fb0285086b1aaf938b2b7ffe8ee54e915928466d'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def evidence(path):
    return dict(path=path.relative_to(REPAIR).as_posix(),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def summarize(rows):
    assert len(rows) == 90
    first, last = rows[0], rows[-1]
    assert all(row['startup_sha256'] == STARTUP for row in rows)
    assert len({row['board_boot_id'] for row in rows}) == 1
    duration = last['observed_mono'] - first['observed_mono']
    counters = [row['safe_capture']['counters'] for row in rows]
    fronts = [row['capture_performance'] for row in rows]
    queues = [row['safe_capture']['input_queue'] for row in rows]
    constant = lambda values: len(set(values)) == 1 and values[0] is not None
    same_capture = all(constant([v.get(key) for v in fronts])
                       for key in ('worker_pid', 'worker_generation', 'microphone_pid'))
    counters_unchanged = all(constant([v.get(key) for v in counters])
                             for key in ('armed', 'submitted', 'speech_starts'))
    quiet = all(row['listening'].get('state') == 'WAITING_SPEECH'
                and row['listening'].get('microphone_open') is True
                and row['playing'] is False
                and row['safe_capture']['capture'].get('speech_active') is False
                for row in rows)
    no_failures = all(row['safe_capture'].get('error_code') == 'none'
                      and row['capture_performance'].get('capture_failures') == 0
                      and row['last_capture_failure']['error']['present'] is False
                      for row in rows)
    increasing = all(b.get('frames', 0) > a.get('frames', 0)
                     for a, b in zip(fronts, fronts[1:]))
    capacity_original = all(q.get('capacity_frames') == 8 for q in queues)
    passed = (duration > 237 and same_capture and counters_unchanged and quiet
              and no_failures and increasing and capacity_original)
    means = {}
    calls = fronts[-1].get('endpoint_feed_calls', 0) - fronts[0].get('endpoint_feed_calls', 0)
    if same_capture and increasing and calls > 0:
        for name in ('wall', 'cpu'):
            key = 'endpoint_feed_' + name + '_total_ms'
            means[name + '_mean_ms'] = round((fronts[-1][key] - fronts[0][key]) / calls, 4)
        means['calls_in_window'] = calls
    return dict(samples=len(rows), duration_seconds=round(duration, 3),
                bounded_quiet_capture_passed=passed,
                same_capture_worker_generation_and_microphone=same_capture,
                counters_unchanged=counters_unchanged, quiet_at_all_samples=quiet,
                zero_capture_failures=no_failures, frames_strictly_increasing=increasing,
                original_8_frame_capacity=capacity_original,
                queue_peak_frames=max(q.get('peak_frames', 0) for q in queues),
                max_observed_capture_failures=max(v.get('capture_failures', 0) for v in fronts),
                endpoint_feed=means,
                claim_scope='This sampled window only; not multi-hour stability, cold boot, or human playback acceptance')


def main():
    paths = dict(
        installed=INTEGRATION/'listening_entry_fix/actual_automatic-listening-v8-ui-budget.json',
        ready=INTEGRATION/'production_business_acceptance/actual_ready.json',
        live=INTEGRATION/'listening_entry_fix/actual_live_listening.json',
        control=INTEGRATION/'listening_entry_fix/actual_control_semantics.json')
    records = {key: read(path) for key, path in paths.items()}
    for key in ('installed', 'live', 'control'):
        assert records[key]['startup_sha256'] == STARTUP
    ready, live, control = (records[key] for key in ('ready', 'live', 'control'))
    assert ready['status'] == 'PRODUCTION_BOARD_BUSINESS_READY' and ready['guard_removed']
    assert ready['main_pid'] == control['main_pid'] == int(live['unit']['MainPID'])
    assert ready['gtk_pid'] == control['gtk_pid'] == live['gtk_pid']
    assert live['continuous_capture_passed'] and live['priority_scope_passed']
    assert all(control[key] for key in ('pause_preference_false_observed',
        'resume_preference_true_observed', 'cancel_rearm_passed', 'pause_closed_microphone',
        'pause_released_owned_arecord', 'model_worker_reused_on_rearm'))
    archived = {}
    for key, source in paths.items():
        target = HERE/('actual_' + key + '.json')
        if target.exists():
            assert target.read_bytes() == source.read_bytes()
        else:
            target.write_bytes(source.read_bytes())
        archived[key] = evidence(target)
    observation = REPAIR/'ui_budget_long_listening.json'
    long_capture = summarize(read(observation)['samples'])
    profile_path = REPAIR/'board_budget_quiet_v8.json'
    profile = read(profile_path)
    assert profile['startup_sha256'] == STARTUP
    process_cpu = {row['role'] if row['pid'] != live['gtk_pid'] else 'gtk_business': row['cpu_core_percent']
                   for row in profile['processes'] if row['role'] != 'worker' or row['pid'] == live['gtk_pid']}
    previous = read(REPAIR/'guard_session_candidate/STATUS.json')
    value = dict(
        status=('UI_BUDGET_DEPLOYED_BOUNDED_QUIET_CAPTURE_VERIFIED'
                if long_capture['bounded_quiet_capture_passed']
                else 'UI_BUDGET_DEPLOYED_CAPTURE_OBSERVATION_NEEDS_REVIEW'),
        updated_utc=datetime.now(timezone.utc).isoformat(),
        startup_sha256=STARTUP,
        source_manifest_sha256=records['installed']['source_manifest_sha256'],
        component_pins=records['installed']['component_pins'],
        main_pid=ready['main_pid'], gtk_pid=live['gtk_pid'],
        camera_pid=live['camera_pid'], board_boot_id=live['board_boot_id'],
        automatic_listening=True, wake_word_required=False, conversation_mode='half_duplex',
        controls_verified=True, short_capture_verified=True, bounded_quiet_capture=long_capture,
        latest_human_confirmation=dict(
            startup_sha256=previous['startup_sha256'],
            operator_feedback='continuous_and_complete',
            observed_confirmed_round=previous['observed_confirmed_round'],
            scope='One round on scoped-connection version v7, before this UI-only update'),
        performance_snapshot=dict(duration_seconds=profile['duration_seconds'],
            whole_board_busy_percent=profile['cpu']['cpu']['busy_percent'],
            process_cpu_percent_one_core_100=process_cpu,
            interpretation='No controlled A/B reduction of whole-board CPU established by this short sample'),
        tests=dict(ui_behavior=10, existing_presentation=19, presentation_subcases=3),
        full_physical_dialogue_acceptance=False, long_run_stability_verified=False,
        capture_diagnostics_installed=True, per_packet_fresh_authority_checks=True,
        private_data_replayed=False, diagnostic_text_or_pcm_saved=False,
        evidence=dict(**archived, long_capture=evidence(observation), performance=evidence(profile_path),
                      previous_human_confirmation=evidence(REPAIR/'guard_session_candidate/STATUS.json')))
    write(HERE/'STATUS.json', value)
    write(REPAIR/'STATUS.json', dict(value, detail='ui_budget_candidate/STATUS.json'))
    handoff = read(HERE/'HANDOFF.json')
    handoff['status'] = value['status']
    handoff['verified_deployment'] = evidence(HERE/'STATUS.json')
    handoff['performance_claim'] = value['performance_snapshot']['interpretation']
    write(HERE/'HANDOFF.json', handoff)
    print(json.dumps(dict(status=value['status'], capture=long_capture,
                          performance=value['performance_snapshot']), ensure_ascii=True))


if __name__ == '__main__':
    main()
