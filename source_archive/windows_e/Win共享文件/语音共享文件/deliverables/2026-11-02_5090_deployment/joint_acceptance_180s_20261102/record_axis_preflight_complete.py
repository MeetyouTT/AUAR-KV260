import datetime
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;D=HERE.parent
p=HERE/'AXIS_ACCEPTANCE_READY.json';raw=p.read_bytes();ready=json.loads(raw)
actual=json.loads((HERE/'AXIS_PREFLIGHT_ACTUAL.json').read_bytes());v=actual['board_result']
assert not ready['can_participate'] and ready['this_stage_actions']['axis_commands']==0
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
(HERE/'AXIS_ACCEPTANCE_READY.before_completion.json').write_bytes(raw)
grant=ready.pop('owners')
ready['handoff_expected_owners']={k:grant[k] for k in ('gui_owner','gtk_owner','camera_owner')}
ready['owners']=v['owners']
ready['gui_and_gtk_owner_exactly_checked_against_handoff']=True
ready['preflight_complete']=True;ready['board_calls_completed_at_host_utc']=stamp
ready['exclusive_preflight_window_released']=True
ready['released_to_identity_root_thread']='01a19ad7-5865-7c60-82fa-605d17aea70f'
ready['root_gui_preparation_slot_available']=True
ready['further_axis_board_queries_or_actions_scheduled']=False
ready['start_gate_can_override_blockers']=False
ready['minimum_recovery_dependencies']=[
    'Root coordinates actual motor-power isolation confirmation before any required original wide DFX; current user handoff states motor power connected. No repeated question from axis chat.',
    'Separate authorized platform maintenance handoff: normal GUI/camera release and genuine current-owner final checkpoint with original complete history/counter/consumption validation; no seed/counter/marker fabrication.',
    'Original client wide restore only if actual platform needs it; actual firmware/overlay/VART/ZOCL and fresh context plus original ID_STOP_ONLY proof, followed by minimal current-boot binding transaction preserving latest d667/identity/accepted axis code.',
    'Fresh READY/followfalse/flags0/lease0 and effective source/no-conflict evidence, then main START_GATE for the new180s acceptance. No tuning or automatic reference/calibration/recenter.'
]
layout=ready['face_position_overlay_metadata']
layout['source_declared_hint_geometry']=dict(x=92,y=78,width=400,height=30)
layout['geometry_basis']='Freshly hashed editor source line67; not an external screen/frame measurement'
layout['actual_x11_geometry_observed']='geometry' in layout
layout['actual_window_title_exported']=False
p.write_text(json.dumps(ready,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
release=dict(schema='aura-axis-preflight-window-release-1',host_utc=stamp,
    status='PREFLIGHT_COMPLETE_AXIS_BLOCKED_GUI_SLOT_RELEASED_TO_IDENTITY_ROOT',
    ready_file=str(p),can_participate=False,board_queries_complete=True,axis_commands=0,
    GUI_camera_DFX_source_changes=0,exclusive_preflight_window_released=True,
    released_to_thread='01a19ad7-5865-7c60-82fa-605d17aea70f',
    main_coordinator='01a1994e-f547-74e1-903d-3591021d67c8',
    next_action='Root coordinates actual platform/guard recovery dependency or updates acceptance participation. Axis chat performs no more board calls until a new explicit phase handoff.',
    prior_axis_physical_acceptance='PASS; not reopened')
(HERE/'AXIS_PREFLIGHT_WINDOW_RELEASE.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
current_path=D/'AXIS_CURRENT_HANDOFF.json';old=current_path.read_bytes()
(HERE/'AXIS_CURRENT_HANDOFF.before_180s_preflight.json').write_bytes(old);current=json.loads(old)
current.update(status='JOINT_180S_PREFLIGHT_BLOCKED_CURRENT_PLATFORM_PENDING_ROOT_RECOVERY',updated_utc=stamp,
    current_runtime_status='ACTUAL_PREFLIGHT_BENCHMARK_PAN_GUARD_FAULT_NO_REGISTER_READBACK',runtime_state_currently_verified=True,
    boot_id=v['boot_id'],startup_sha256=v['startup_sha256_after'],owners=v['owners'],follow_processes=v['follow_processes'],
    face_config_sha256=v['pan_component_pins']['config/pan_face.local.json']['actual_sha256'],
    latest_observation_utc=actual['host_completed_utc'],latest_observed_following=False,
    latest_observed_pan_state='FAULT',latest_observed_readback=None,ui_page=v['gui']['ui_page'],
    runtime_fault_count=v['gui']['runtime_fault_count'],current_boot_stop_verified=False,
    current_platform=v['platform'],binding_compatibility=v['compatibility'],
    pan_component_pins={k:r['actual_sha256'] for k,r in v['pan_component_pins'].items()},
    current_zone_sha256=v['zone']['sha256'],current_face_readback=v['selected_face_readback'],
    joint_180s_acceptance=dict(user_authorized=True,readiness=str(p),window_release=str(HERE/'AXIS_PREFLIGHT_WINDOW_RELEASE.json'),
        can_participate=False,START_GATE_required=True,START_GATE_cannot_override_blockers=True,
        preflight_complete=True,board_calls_released=True,axis_commands_this_stage=0,
        motor_power_connected_per_user=True,root_asks_all_field_questions=True),
    next_action='Preflight complete; return GUI preparation slot to identity root. Current platform/old-boot bindings prevent original follow. Await separately coordinated recovery dependencies or fresh phase handoff; no DFX, service restart, reference, recenter, tuning or follow start under this preflight grant.')
current['coordination_freeze'].update(axis_publication=True,follow_start=True,current_turn_axis_commands=0,
    already_stopped_readonly=False,current_boot_register_readback=None,
    resume_condition='New180s functional acceptance requested, but actual preflight blocked. Root coordinates recovery separately; after fresh READY/source/STOP proof wait main START_GATE.',
    exclusive_axis_preflight_window='COMPLETED_RELEASED_TO_IDENTITY_ROOT')
assert current['human_acceptance']['physical_follow_accepted'] is True
assert current['issue_status']['right_turn_stutter']=='CLOSED_USER_ACCEPTED'
tmp=current_path.with_name('.'+current_path.name+'.joint180.tmp');tmp.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(current_path)
print(json.dumps(dict(status=ready['status'],can_participate=False,preflight_complete=True,GUI_slot_released=True,
    ready_file=str(p),release_file=str(HERE/'AXIS_PREFLIGHT_WINDOW_RELEASE.json'),
    observed_host_utc=ready['observed_host_utc'],axis_commands=0,layout=layout),ensure_ascii=False,indent=2))
