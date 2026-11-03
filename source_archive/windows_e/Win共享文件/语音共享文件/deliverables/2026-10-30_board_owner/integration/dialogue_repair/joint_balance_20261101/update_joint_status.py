"""Update only the main chat's local status from saved evidence and reviews."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
path = HERE / 'joint_balance_status.json'
data = json.loads(path.read_text(encoding='utf-8'))
data['status'] = 'CURRENT_JOINT_TRIAL_SET_COMPLETE_CAPTIONS_AUDIO_AND_RECENT_MEMORY_USER_CONFIRMED'
data['report'] = str(HERE / '优化与验收进度.md')
review_path = HERE / 'ROOT_SUBTITLE_REVIEW.json'
review = json.loads(review_path.read_text(encoding='utf-8'))
data['subtitle_candidate'] = dict(status='DEPLOYED_PUBLIC_ARM_AND_LIVE_CAPTIONS_AUDIO_PASSED',
    before_sha256=review['before_sha256'], after_sha256=review['after_sha256'],
    source=str(HERE / 'subtitle_repair/after/tools/production_memory_presentation.py'),
    public_tests_passed=review['public_regressions'],
    unchanged_hot_paths=review['unchanged_hot_paths'],
    root_review_sha256=hashlib.sha256(review_path.read_bytes()).hexdigest(),
    deployed=True, live_display_verified=True)
data['live_checks'] = dict(introduction_user_audio_continuous=True,
    introduction_user_wait_acceptable=True, visual_count_user_correct=True,
    visual_audio_user_complete=True, memory_recall='USER_CONFIRMED_WARM_WATER_AFTER_THREE_DIALOGUE_TURNS',
    memory_recall_scope='Current dialogue continuity; not an over-five-minute summary retrieval proof.',
    subtitle_display='USER_CONFIRMED_BOTH_COLUMNS_VISIBLE_AND_COMPLETE_AUDIO_ON_RETEST',
    all_functionality_accepted=False, acoustic_first_sound_measured=False)
project = HERE.parents[4]
jp = project/'deliverables/2026-10-31_visual_axis_maintenance/reviews/joint_performance_20261101'
ready_path = jp/'evidence/subtitle_receipt_forward_ready_1793536079425576200.json'
ready_bytes = ready_path.read_bytes()
ready = json.loads(ready_bytes)['result']
serial = json.loads((HERE/'SERIAL_SUBTITLE_OPERATOR_REVIEW.json').read_text(encoding='utf-8'))
assert ready['status'] == 'PRODUCTION_BOARD_BUSINESS_READY'
assert ready['startup_sha256'] == serial['new_startup_sha256']
assert ready['source_manifest_sha256'] == serial['new_manifest_sha256']
data.update(current_startup_sha256=ready['startup_sha256'],
    current_manifest_sha256=ready['source_manifest_sha256'],
    current_spec_sha256=serial['new_spec_sha256'],
    current_source_sha256=serial['candidate_source_sha256'],
    current_supervisor_pid=ready['main_pid'], current_gtk_pid=ready['gtk_pid'],
    current_component_count=380)
data['subtitle_candidate'].update(public_arm_tests_passed=19,
    public_arm_projection_tests_passed=10, randomized_public_cases=500,
    public_arm_python='3.9.9', public_arm_machine='aarch64',
    public_arm_evidence_sha256=serial['arm_evidence_sha256'],
    normal_ready_receipt=str(ready_path),
    normal_ready_sha256=hashlib.sha256(ready_bytes).hexdigest())
data['passive_postcheck']['measured_startup_sha256'] = '71c28c2d4a15585a0370790c9be62ab5c1d975d0ac70626613429d355e83bb87'
data['passive_postcheck']['repeated_after_subtitle_repair'] = False
caption_dir = jp/'evidence/live_trial_1793536566480481000'
data['caption_live_trial'] = str(caption_dir)
paused_bytes = (caption_dir/'FINAL_PAUSED.json').read_bytes()
paused = json.loads(paused_bytes)
proof, state = paused['proof'], paused['proof']['state']
assert proof['startup_sha256'] == ready['startup_sha256']
assert proof['manifest_sha256'] == ready['source_manifest_sha256']
assert proof['all_component_bytes_match'] is True and proof['component_pins'] == 380
assert proof['original_controller_unchanged'] is True
assert state['listening_state'] == 'PAUSED' and state['listening_enabled'] is False
assert state['microphone_open'] is False and state['playing'] is False
assert state['following'] is False and state['readback']['flags'] == 0
assert proof['owners']['camera']['pid'] == 430894
assert proof['owners']['supervisor']['pid'] == ready['main_pid']
assert proof['owners']['gtk']['pid'] == ready['gtk_pid']
result_bytes = (caption_dir/'RESULT.json').read_bytes()
result = json.loads(result_bytes)
feedback_bytes = (caption_dir/'USER_FEEDBACK.json').read_bytes()
feedback = json.loads(feedback_bytes)
assert feedback['both_subtitle_columns_user_visible'] is True
assert feedback['audio_complete_user_confirmed'] is True
complete = [r for r in result['terminal_events'] if r.get('kind') == 'complete' and r.get('status') == 'ONE_NEW_TURN_COMPLETE']
assert len(complete) == 1 and complete[0]['request_token'] == feedback['request_token']
rows = [json.loads(line) for line in (caption_dir/'metadata.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
samples = [r for r in rows if r.get('kind') == 'sample']
assert samples and any(r.get('ack_committed') is True and r.get('ack_request_token') == feedback['request_token'] for r in samples)
assert any(r['caption_metadata']['showing'] is True for r in samples)
assert all(r['caption_metadata']['api_reply_empty'] is True and r['caption_metadata']['api_transcript_empty'] is True for r in samples)
assert all(r['runtime_faults']['count'] == 0 for r in samples)
assert paused['renderer_worker_fault_count'] == 0
data['last_observed_device_state'] = state
data['last_observed_device_state_reference'] = dict(path=str(caption_dir/'FINAL_PAUSED.json'),
    sha256=hashlib.sha256(paused_bytes).hexdigest())
data['caption_acceptance'] = dict(request_token=feedback['request_token'],
    observed_complete_ack=True, both_columns_user_confirmed=True, audio_complete_user_confirmed=True,
    caption_showing_observed=True, api_reply_and_transcript_empty_all_samples=True,
    samples=len(samples), runtime_faults=0, renderer_worker_faults=0,
    result_sha256=hashlib.sha256(result_bytes).hexdigest(), feedback_sha256=hashlib.sha256(feedback_bytes).hexdigest(),
    original_failed_caption_trial_preserved=str(jp/'evidence/live_trial_1793536079510966000'),
    no_acoustic_measurement_or_long_duration_acceptance=True)
data['live_checks']['current_joint_trial_set_passed'] = True
path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(status=data['status'], current_startup_sha256=data['current_startup_sha256'],
    subtitle_candidate_sha256=data['subtitle_candidate']['after_sha256']), ensure_ascii=False))
