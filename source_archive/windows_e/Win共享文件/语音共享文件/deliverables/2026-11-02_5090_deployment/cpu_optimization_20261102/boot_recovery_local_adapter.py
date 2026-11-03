"""Local planning only. No transport, service calls, original loader or writes.

Returned objects are unverified candidates, never Native authorization receipts.
The original implementations referenced by BOOT_RECOVERY_INTERFACE.json remain
responsible for all live checks, normal stop, Native archive/restore and commit.
"""
import copy


class RequiredMetadata(ValueError):
    pass


def require(value, message):
    if not value:
        raise RequiredMetadata(message)


def plan_flow(observation):
    """Validate orchestration choices, without validating observation truth."""
    require(observation.get('schema') == 'aura-boot-interface-observation-1', 'observation schema required')
    require(observation.get('board_boot_id'), 'actual board boot required')
    require(type(observation.get('camera_running')) is bool, 'camera running state required')
    require(observation.get('observation_provenance_required') is True, 'fresh provenance must remain required')
    result = {'status': 'OFFLINE_CONTROL_FLOW_PLAN_ONLY', 'production_execution_allowed': False,
              'native_validation_passed': False, 'proof_created': False, 'steps': []}
    if observation['camera_running']:
        require(observation.get('camera_owner'), 'actual current owner required')
        result.update(route='maintenance_running_camera', steps=[
            'obtain_idle_exclusive_handoff', 'normal_gui_stop_by_original_owner',
            'collect_pre_stop_closures_bounds_and_history_provenance',
            'normal_stop_current_owner.default_readonly_dry_run',
            'normal_stop_current_owner.explicit_stop_once',
            'wait_for_normal_stop_and_new_final', 'validate_fresh_final_history_readonly',
            'original_same_boot_preflight_attach_once',
            'observe_actual_new_owner_and_run_config', 'original_selected_binding_verify',
            'caller_reviewed_selected_UI_startup_CAS', 'original_GUI_start_and_READY_checks'])
        return result
    require(observation.get('no_live_camera_owner_confirmed') is True, 'unit and process evidence required')
    require(observation.get('checkpoint_pin') and observation.get('checkpoint_source_boot'), 'original pinned checkpoint and source boot required')
    if observation['checkpoint_source_boot'] == observation['board_boot_id']:
        require(observation.get('same_boot_normal_stop_and_full_history_proof_available') is True,
                'same-boot no-owner resume needs actual prior stop/full-history evidence')
        require(observation.get('same_boot_seed_consumed') is False, 'same-boot final must be unconsumed')
        route = 'no_owner_same_boot_sealed_resume'
        first = ['validate_existing_actual_same_boot_stop_and_full_history_evidence']
    else:
        require(observation.get('allow_new_kernel_boot') is True, 'original new-kernel opt-in required')
        require(observation.get('current_kernel_domain_consumed') is False,
                'a consumed new-kernel domain cannot be initialized again')
        route = 'cold_no_camera_owner_new_kernel'
        first = ['original_preflight_routes_to_load_new_boot_checkpoint',
                 'original_attach_performs_commit_new_boot_then_restore_adopt_once']
    result.update(route=route, steps=['obtain_exclusive_boot_start_handoff',
        'verify_no_camera_GUI_Native_owners_and_current_platform'] + first + [
        'observe_actual_started_owner_and_run_config', 'original_selected_binding_verify',
        'caller_reviewed_selected_UI_startup_CAS', 'original_GUI_start_and_READY_checks'])
    return result


def after_stop(result):
    """Control-flow gate only; does not produce or validate a Native receipt."""
    require(result.get('status') == 'CAMERA_STOPPED_NEW_FINAL_PRESENT',
            'pending, failed, missing or unknown stop result: observe; do not retry or start')
    require(result.get('normal_stop_submitted_once') is True and result.get('forced_action') is False,
            'original single normal stop required')
    require(result.get('fresh_checkpoint'), 'fresh final pin required')
    return {'next': 'validate_fresh_final_history_readonly', 'native_validation_passed': False,
            'production_execution_allowed': False}


def propose_rebind(before, actual, observed_source_sha256, approved_changed_sources):
    """Pure metadata projection; original live _verify must still accept it.

    No source, config, startup, gallery, checkpoint or receipt is read/written.
    Caller must supply actual source observations and explicitly reviewed deltas.
    """
    require(isinstance(before.get('source_sha256'), dict), 'current selected source map required')
    needed = {'board_boot_id', 'camera_pid', 'camera_start_ticks',
              'camera_cmdline_sha256', 'camera_config', 'observation_provenance_pin'}
    require(set(actual) == needed and actual['observation_provenance_pin'], 'fresh actual owner/config provenance required')
    require(type(actual['camera_pid']) is int and actual['camera_pid'] > 0, 'actual PID required')
    require(isinstance(actual['camera_start_ticks'], str) and actual['camera_start_ticks'].isdigit(), 'actual birth required')
    require(isinstance(approved_changed_sources, dict), 'explicit approved delta map required')
    expected_paths = set(before['source_sha256']) | set(approved_changed_sources) | {actual['camera_config']}
    require(set(observed_source_sha256) == expected_paths, 'complete source observations, including historical paths, required')
    for path, old in before['source_sha256'].items():
        expected = approved_changed_sources.get(path, old)
        require(observed_source_sha256[path] == expected, 'unapproved changed or missing historical source')
    for path, new in approved_changed_sources.items():
        require(observed_source_sha256[path] == new, 'approved delta differs from observation')
    candidate = copy.deepcopy(before)
    for key in needed - {'observation_provenance_pin'}:
        candidate[key] = actual[key]
    candidate['source_sha256'] = copy.deepcopy(observed_source_sha256)
    return {'status': 'REBIND_CANDIDATE_REQUIRES_ORIGINAL_LIVE_VERIFY', 'candidate': candidate,
            'source_count': len(candidate['source_sha256']),
            'observation_provenance_pin': copy.deepcopy(actual['observation_provenance_pin']),
            'original_metadata_verify_passed': False, 'production_apply_allowed': False,
            'native_proof_created': False}
