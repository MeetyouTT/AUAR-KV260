"""Publish verified facts, preserving initial failures and pending human hearing."""
import json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
d=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
v=json.loads((HERE/'active_verification.json').read_text(encoding='utf-8'))
smoke=json.loads((HERE/'smoke.json').read_text(encoding='utf-8'))
display=json.loads((HERE/'display_activity_check.json').read_text(encoding='utf-8'))
listening=json.loads((HERE/'listening.json').read_text(encoding='utf-8'))
assert d['status']=='UI_ONLY_DEPLOYED' and v['status']=='ACTIVE_UI_VERIFIED' and smoke['passed']
assert display['passed'] and display['runtime']==c['runtime']
hearing=listening.get('human_hearing_verified') is True and listening.get('user_confirmed_heard_turns')==2
observation=json.loads((HERE/'passive_live_observation.json').read_text(encoding='utf-8'))
acks={row['last_playback_ack']['request_id'] for row in observation['rows']
      if row.get('last_playback_ack') and row['last_playback_ack'].get('committed')}
summary={'status':'DEPLOYED_TWO_TURN_HUMAN_HEARING_PASSED' if hearing else 'DEPLOYED_HUMAN_HEARING_PENDING','date':'2026-10-20','runtime':c['runtime'],
 'windows_tests_passed':int(re.search(r'(\d+) passed',(HERE/'tests_pc.log').read_text(encoding='utf-8')).group(1)),
 'board_tests_passed':int(re.search(r'(\d+) passed',(HERE/'tests_log.log').read_text(encoding='utf-8')).group(1)),
 'windows_linux_only_tests_skipped':1,'windows_avatar_tests_unavailable':7,
 'windows_avatar_test_limitation':'Current Windows voice runtime lacks cv2; seven avatar-worker tests passed in the complete board run. Initial Windows failures are retained in tests_pc_merged_missing_opencv.log.',
 'full_hidden_gtk_initialization_passed':True,'active_source_verified':True,
 'same_track_turning_allowed_after_initial_frontal_gate':True,'detection_gap_maximum_ms_from_actual_source':1000,
 'explicit_pause_persisted':True,'shutdown_preserves_user_choice':True,
 'diagnostic_counters_enabled':True,'camera_unit_and_pid_unchanged':v['camera_unchanged'],
 'source_runtime':c['source_runtime'],'animation_performance_version_preserved':True,
 'accepted_reply_finishes_despite_visual_loss':True,'visual_revalidated_before_next_listen':True,
 'display_wake_on_conversation_activity':True,'real_x11_wake_checked':True,
 'desktop_idle_policy_unchanged':True,'preference_path':d['preference_path'],
 'monitor_was_enabled_before':d['monitor_was_enabled_before'],'monitor_choice_source':d['monitor_choice_source'],
 'camera_pid_snapshot':v['camera_pid'],'identity_database_unchanged':True,'identity_threshold_preserved':d['identity_threshold'],
 'monitor_enabled_at_deployment':d['monitor_enabled_preserved'],'pc_model_services_restarted':False,
 'first_live_attempt_failed':True,'screen_text_seen_by_user':True,
 'earlier_two_software_playback_acks_observed':True,'human_hearing_verified':hearing,
 'confirmed_acoustic_root_cause':False,'new_live_acceptance':'PASSED_TWO_TURN_HEARING' if hearing else 'PENDING',
 'latest_user_feedback':listening['latest_live_feedback'],'user_confirmed_heard_turns':listening.get('user_confirmed_heard_turns',0),
 'recovery_observed_committed_ack_count':len(acks),'passive_observation_does_not_prove_hearing':True,
 'previous_trial_feedback':listening['pre_recovery_live_feedback'],'previous_trial_result':'FAILED',
 'black_screen_root_cause':'X11 DPMS OFF after 600 seconds; UI process was running',
 'screen_recovery_confirmed_by_user':listening['display_recovery_user_confirmed'],
 'speaker_binding_verified':False,'voice_barge_in':False,'full_duplex':False,
 'television_or_bystander_rejection_verified':False,'latency_optimization_performed':False,
 'initial_deployment_failure_retained':'initial_failed_deployment.json',
 'initial_deployment_failure_cause':'Symlinked Python modules imported the previous common package; fixed by copying unchanged Python sources inside the candidate'}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
listening['recovery_candidate']=c['runtime']
(HERE/'listening.json').write_text(json.dumps(listening,ensure_ascii=False,indent=2),encoding='utf-8')
root_summary=HERE.parent/'verification_summary.json'
history=HERE.parent/'initial_verification_summary.json'
if not history.exists():history.write_bytes(root_summary.read_bytes())
root_summary.write_text(json.dumps(dict(summary,latest_evidence='resume-20261020/verification_summary.json',
 initial_evidence='initial_verification_summary.json',first_live_feedback='listening.json'),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
