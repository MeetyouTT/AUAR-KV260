"""Archive only reviewed source and metadata receipts for the current repair."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INTEGRATION = HERE.parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    receipts = {
        'installed': INTEGRATION / 'listening_entry_fix/actual_automatic-listening-v5-half-duplex.json',
        'ready': INTEGRATION / 'production_business_acceptance/actual_ready.json',
        'control': INTEGRATION / 'listening_entry_fix/actual_control_semantics.json',
        'live': INTEGRATION / 'listening_entry_fix/actual_live_listening.json',
    }
    installed = read(receipts['installed'])
    live, control, ready = (read(receipts[name]) for name in ('live', 'control', 'ready'))
    pin = installed['startup_sha256']
    assert live['startup_sha256'] == control['startup_sha256'] == pin
    assert live['continuous_capture_passed'] and live['priority_scope_passed']
    assert control['cancel_rearm_passed'] and control['pause_closed_microphone']
    assert ready['main_pid'] == control['main_pid']
    assert all(s['listening']['conversation_mode'] == 'half_duplex'
               and s['listening']['voice_barge_in'] is False
               and s['listening']['wake_word_required'] is False for s in live['samples'])
    evidence = {}
    for name, path in receipts.items():
        raw = path.read_bytes()
        target = HERE / ('actual_' + name + '.json')
        target.write_bytes(raw)
        evidence[name] = dict(path=target.name, sha256=hashlib.sha256(raw).hexdigest())
    status = dict(status='HALF_DUPLEX_DEPLOYED_HUMAN_SMOOTH_PLAYBACK_UNVERIFIED',
        startup_sha256=pin, source_manifest_sha256=installed['source_manifest_sha256'],
        component_pins=installed['component_pins'], board_boot_id=live['board_boot_id'],
        main_pid=ready['main_pid'], gtk_pid=control['gtk_pid'], camera_pid=live['camera_pid'],
        entry_mode='direct_speech', wake_word_required=False, conversation_mode='half_duplex',
        automatic_listening=True, barge_in=False, echo_reference_stream=False,
        pause_resume_verified=True, cancel_rearm_verified=True, continuous_capture_verified=True,
        source_tests=dict(passed=22, subtests_passed=3),
        operator_report_before_repair='stuttering_audio', prior_cumulative_underrun_packets=840,
        actual_conversation_after_repair_verified=False, smooth_audio_after_repair_verified=False,
        full_physical_dialogue_acceptance=False, original_capture_queue_frames=8,
        per_packet_memory_authority_check_preserved=True, model_or_voice_changed=False,
        private_data_replayed=False, diagnostic_transcript_or_pcm_archived=False, evidence=evidence)
    observation=HERE/'half_duplex_after_operator.json'
    if observation.exists():
        row=read(observation)
        assert row['startup_sha256']==pin
        status.update(status='HALF_DUPLEX_DEPLOYED_STUTTER_REPRODUCED_GUARD_BOTTLENECK',
            latest_operator_feedback='still_stuttering_corrects_earlier_positive_selection',
            smooth_audio_after_repair_verified=False, observed_audio_packets=row['stream_diagnostics']['audio_packets'],
            producer_diagnostics=row['producer_diagnostics'], consumer_diagnostics=row['stream_diagnostics'],
            cumulative_underrun_packets_after_repair=row['audio_output']['underrun_packets'],
            complete_playback_ack=row['last_ack']['committed'],
            capture_overflow_observed_after_approximately_237_seconds=True,
            capture_automatic_recovery_observed=True)
        status['evidence']['spoken_round']={'path':observation.name,
            'sha256':hashlib.sha256(observation.read_bytes()).hexdigest()}
    (HERE/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=status['status'],startup_sha256=pin,receipts_saved=len(evidence))))


if __name__ == '__main__':
    main()
