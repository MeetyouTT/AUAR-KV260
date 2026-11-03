import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
handoff_path=HERE/'AXIS_COORDINATION_HANDOFF.json'
raw=handoff_path.read_bytes();receipt=json.loads(raw)
assert receipt['status']=='AXIS_STOP_CONFIRMED_FROZEN_FOR_CPU_OPTIMIZATION'
after=receipt['after'];rb=after['readback']
assert after['state']=='READY' and after['following'] is False
assert rb['flags']==0 and rb['lease_left_ms']==0 and rb['reason']==0
assert not receipt['follow_processes_after'] and receipt['axis_command_count']==0
assert receipt['already_stopped_readonly'] and receipt['original_stopped_receipt']['referenced_report_sha_matches']
# Preserve the raw SSH return; normalize only human-readable labels locally.
(HERE/'AXIS_COORDINATION_HANDOFF.raw_ssh.json').write_bytes(raw)
receipt['authorization']['scope']='授权本次优化与复测的双向协调'
receipt['retest_plan']='After coordinated publication, dedicated axis chat alone owns bounded original-UI follow start and STOP; CPU owner read-only samples two real dialogue rounds plus 60-120 seconds of follow.'
handoff_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
current_path=HERE.parent/'AXIS_CURRENT_HANDOFF.json';old=current_path.read_bytes()
(HERE/'AXIS_CURRENT_HANDOFF.before_cpu_freeze.json').write_bytes(old)
current=json.loads(old)
current.update(status='AXIS_STOP_CONFIRMED_FROZEN_FOR_CPU_OPTIMIZATION',updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    startup_sha256=receipt['startup_sha256'],face_config_sha256=receipt['face_config_sha256'],
    controller_manifest_sha256=receipt['controller_manifest_sha256'],current_release=receipt['controller_root'],
    boot_id=receipt['boot_id'],owners=receipt['owners'],follow_processes=receipt['follow_processes_after'],
    latest_observation_utc=receipt['utc'],latest_observed_following=False,latest_observed_pan_state='READY',
    latest_observed_readback=rb,ui_page=after['ui_page'],runtime_fault_count=after['runtime_fault_count'],
    last_report=receipt['last_report']['path'],last_report_status=receipt['last_report']['status'],
    last_report_result=receipt['last_report']['result'],
    coordination_freeze=dict(axis_publication=True,follow_start=True,
        optimization_chat='01a19b1a-6a07-7781-8af9-aacacb1c8ca4',
        handoff=str(handoff_path),handoff_sha256=hashlib.sha256(handoff_path.read_bytes()).hexdigest(),
        current_turn_axis_commands=0,already_stopped_readonly=True,
        cpu_owner_may_restart_gui_and_camera=True,preserve_latest_pan_bytes_and_pins=True,
        resume_condition='Explicit bilateral coordination after CPU publication and fresh owner/pin verification'),
    next_action='Freeze axis publication and follow start. Await optimization chat coordination after camera/GTK publication. Dedicated axis chat retains sole bounded follow start/STOP responsibility for combined retest.')
current['validation']['later_stop_receipt_observation']=dict(utc=receipt['utc'],
    commands_accepted=receipt['last_report']['result']['commands_accepted'],
    visual_center_completions=receipt['last_report']['result']['visual_center_completions'],
    elapsed_s=receipt['last_report']['result']['elapsed_s'],
    physical_jitter_acceptance='Not established by numeric stop receipt')
tmp=current_path.with_name('.'+current_path.name+'.freeze.tmp')
tmp.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(current_path)
print(json.dumps(dict(utc=receipt['utc'],status=receipt['status'],following=False,flags=rb['flags'],lease_left_ms=rb['lease_left_ms'],
    pulse_us=rb['width_us'],axis_commands_this_turn=receipt['axis_command_count'],owners=receipt['owners'],
    startup_sha256=receipt['startup_sha256'],pan_pins={k:v['actual_sha256'] for k,v in receipt['pan_component_pins'].items()},
    stop_receipt_sha_matches=True,coordination_handoff=str(handoff_path),latest_handoff=str(current_path)),ensure_ascii=False,indent=2))
