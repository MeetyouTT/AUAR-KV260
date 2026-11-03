import datetime,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
raw=json.loads((HERE/'AXIS_PREFLIGHT_ACTUAL.json').read_bytes())
ready=json.loads((HERE/'AXIS_ACCEPTANCE_READY.json').read_bytes())
assert ready['preflight_complete'] and ready['exclusive_preflight_window_released']
assert ready['this_stage_actions']['axis_commands']==0 and not ready['start_action_executed']
value=dict(schema='aura-axis-device-returned-before-protected-stop-1',recorded_host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='ALL_AXIS_PREFLIGHT_CALLS_COMPLETED_DEVICE_RETURNED_TO_ROOT_CPU',
    one_shot_remote_completed_host_utc=raw['host_completed_utc'],
    completed_evidence='Strict SSH call returned normally; one-shot remote Python emitted final JSON; no detached observer, controller or background task launched.',
    persistent_observer_started=False,persistent_observer_running=False,new_follow_process_started=False,
    preflight_HTTP_connections_closed=True,preflight_commands_completed=True,
    board_queries_after_preflight_completion=0,axis_commands=0,DFX_or_initialization_or_motion=0,
    device_and_GUI_slot_released=True,current_phase_owner='Identity root / CPU for original protected normal GUI-camera stop and genuine fresh-final/full-history validation',
    identity_root_thread='01a19ad7-5865-7c60-82fa-605d17aea70f',main_thread='01a1994e-f547-74e1-903d-3591021d67c8',
    next_axis_phase='Only after CPU_STOP_AND_FINAL_READY plus explicit phase handoff: original client remove/load and original ID_STOP_ONLY. No BIND/REFERENCE/ARM/COMMIT/recenter/motion.',
    start_gate_status='NOT_EXECUTED; global180s T0 not issued',
    accepted_controller_and_parameters_preserved=True,latest_d667_identity_cores_preserved=True,
    extra_UI_source_full_export='Deferred; no extra board read during returned root/CPU phase',
    readiness_file=str(HERE/'AXIS_ACCEPTANCE_READY.json'),window_release=str(HERE/'AXIS_PREFLIGHT_WINDOW_RELEASE.json'))
p=HERE/'AXIS_DEVICE_RETURNED_TO_ROOT_CPU.json';assert not p.exists();p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
release_path=HERE/'AXIS_PREFLIGHT_WINDOW_RELEASE.json';release=json.loads(release_path.read_bytes())
release.update(all_axis_preflight_calls_exited=True,persistent_observers_running=False,
    explicit_device_return_receipt=str(p),current_phase_owner=value['current_phase_owner'])
release_path.write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=value['status'],receipt=str(p),axis_commands=0,more_board_queries=False),ensure_ascii=False))
