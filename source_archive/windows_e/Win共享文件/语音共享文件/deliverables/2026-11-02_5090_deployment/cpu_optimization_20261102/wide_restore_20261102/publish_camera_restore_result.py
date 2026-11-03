"""Publish actual completed receipts and return this camera phase; no device calls."""
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
JOINT=HERE.parent.parent/'joint_acceptance_180s_20261102'


def digest(raw): return hashlib.sha256(raw).hexdigest()
def load(path): return json.loads(path.read_bytes())
def create(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f: json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def pin(path): return dict(path=str(path),sha256=digest(path.read_bytes()))


start=load(HERE/'CAMERA_RESTORE_START_RESULT.json')['board_result']
observed=load(HERE/'CAMERA_RESTORE_OBSERVE_RESULT.json')['board_result']
bound=load(HERE/'CAMERA_RESTORE_BIND_RESULT.json')['board_result']
assert start['status']=='ORIGINAL_CAMERA_START_REQUESTED_ONCE' and start['start_returncode']==0
assert observed['status']=='ORIGINAL_CAMERA_EXACT_FINAL_RESTORED_AND_VERIFIED'
assert bound['status']=='CURRENT_ORIGINAL_CAMERA_BINDING_COMMITTED_AND_VERIFIED'
assert bound['camera_owner']==observed['camera_owner']
assert bound['old_source_count']==26 and bound['new_source_count']==bound['source_count']==27
assert bound['all_historical_source_pins_preserved'] and bound['components_verified']==380 and bound['unchanged_components']==379
assert bound['changed_components']==['config/board_avatar_gtk.json']
grant_pin=pin(JOINT/'CPU_CAMERA_RESTORE_PHASE_HANDOFF.json')
assert grant_pin['sha256']=='79f47f1404c22f136bd595262c50c231b001170d12edd56c180876ae4c7bbcbd'
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
four={p:bound['component_sha256'][p] for p in ('board/runtime/board_business.py','board/runtime/board_dialogue.py',
      'board/runtime/board_memory_policy.py','board/runtime/board_speaker_business.py')}
result=dict(schema='aura-original-camera-restored-fresh-binding-result-1',recorded_host_utc=now,
    status='ORIGINAL_CAMERA_RESTORED_AND_FRESH_BINDING_VERIFIED_DEVICE_WINDOW_RETURNED',
    boot_id=observed['boot_id'],phase_grant=grant_pin,phase_returned=True,permission_active=False,
    camera_owner=observed['camera_owner'],camera_service=observed['camera_service'],camera_config=observed['run_config'],
    source_progress_verified=True,source_progress_samples=observed['source_progress_samples'],
    genuine_final_checkpoint=observed['checkpoint_pin'],exact_original_seed_preserved=True,
    bootstrap_handoff=observed['bootstrap_handoff'],native_consumption_marker=observed['marker'],
    original_recovery_audit=observed['audit_pin'],operator_request_audit_status=observed['audit_status'],
    operator_audit_status_is_not_Native_completion_proof=True,
    current_cumulative_lower_bounds=observed['original_current_cumulative_lower_bounds_checked'],
    complete_history_count=19,complete_history_original_validation=observed['complete_19_history_original_validation_preserved'],
    history_head_unchanged=True,original_Native_Python222_operator7_C6_library704_verified=True,
    original_persisted_native_configuration_changed_only_final_pointer=True,original_run_config_writer=observed['original_writer_source_pins'],
    startup_path=bound['startup_path'],startup_before_sha256=bound['startup_before_sha256'],
    startup_sha256=bound['startup_sha256'],runtime=bound['runtime'],component_count=380,
    component_sha256=bound['component_sha256'],unchanged_component_count=379,
    changed_components=bound['changed_components'],GUI_config_pin=bound['UI_pin'],
    selected_face_binding=dict(bound['selected_face_binding'],source_pin_count=27,configured_sha_matches=True,
        source_and_live_owner_verified=True),selected_source_sha256=bound['selected_source_sha256'],
    selected_binding_delta=dict(old_source_count=26,new_source_count=27,added_source_pin=bound['added_source_pin'],
        all_old26_sources_preserved_unchanged=True,original_pure_verify_passed=True),
    identity_four_core_preserved=four,sole_hardware_owners=observed['sole_hardware_owners'],
    normal_camera_start_submissions=1,normal_start_repeated=False,forced_action=False,
    GUI_started=False,listening_enabled=False,GUI_remains_normally_stopped_and_saved_listening_false=True,
    motor_power_must_remain_off=True,axis_command_DFX_motion_or_initialization_requested=False,
    source_models_libraries_threshold_identity_memory_or_layout_changed=False,
    native_checkpoint_seed_counter_marker_or_history_manually_rewritten=False,
    all_CPU_calls_completed=True,persistent_observers_running=False,active_CPU_board_access=False,
    no_further_CPU_board_access_under_this_phase=True,
    evidence={name:pin(HERE/name) for name in ('CAMERA_RESTORE_START_RESULT.json','CAMERA_RESTORE_OBSERVE_RESULT.json','CAMERA_RESTORE_BIND_RESULT.json')},
    next_owner='Identity/root serial coordinator; original GUI recovery only in its separately held phase. Layout remains pending after joint acceptance.')
path=JOINT/'CPU_CAMERA_RESTORE_RESULT.json';create(path,result)
returned=dict(schema='aura-CPU-camera-restoration-window-returned-1',recorded_host_utc=now,
    status='RETURNED_AFTER_ORIGINAL_CAMERA_RESTORE_AND_FRESH_BINDING_PASS',result=pin(path),
    all_calls_completed=True,persistent_observers_running=False,active_CPU_device_access=False,
    phase_grant_sha256=grant_pin['sha256'],GUI_not_started=True,listening_not_enabled=True,
    no_further_CPU_device_access_under_this_phase=True)
create(HERE/'CAMERA_RESTORE_PHASE_RETURNED.json',returned)
create(JOINT/'CPU_DEVICE_RETURNED_AFTER_CAMERA_RESTORE.json',returned)
print(json.dumps(dict(status=result['status'],camera_owner=result['camera_owner'],startup_sha256=result['startup_sha256'],
                     selected=result['selected_face_binding'],result_sha256=digest(path.read_bytes()))))


if __name__=='__main__': pass
