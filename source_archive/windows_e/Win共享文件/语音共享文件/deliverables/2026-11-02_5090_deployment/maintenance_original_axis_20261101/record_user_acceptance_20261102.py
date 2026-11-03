"""Close axis acceptance from explicit human feedback. Local documents only."""
import copy
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;D=HERE.parent
OUT=HERE/'user_acceptance_20261102';OUT.mkdir(exist_ok=True)
current_path=D/'AXIS_CURRENT_HANDOFF.json';old=current_path.read_bytes();current=json.loads(old)
backup=OUT/'AXIS_CURRENT_HANDOFF.before_human_acceptance.json'
assert not backup.exists();backup.write_bytes(old)
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
quote='转轴测试是没问题的没有一顿一顿，人脸与声纹关联不用做'
acceptance=dict(schema='aura-axis-human-acceptance-1',recorded_host_utc=stamp,
    source_type='Explicit human feedback relayed by original primary chat',
    source_chat='01a1994e-f547-74e1-903d-3591021d67c8',human_quote_exact=quote,
    status='PASS_BY_EXPLICIT_USER_FEEDBACK',physical_follow_accepted=True,no_stuttering_accepted=True,
    right_turn_stutter_issue='CLOSED_USER_ACCEPTED',further_parameter_tuning='CLOSED_NOT_REQUESTED',
    repeated_axis_acceptance_testing='CLOSED_DO_NOT_REPEAT_FOR_CLOSEOUT',
    face_voice_association='REMOVED_FROM_SCOPE_BY_USER',
    implementation_and_parameters='RETAIN_EXISTING',
    runtime_boot_id_proven_by_feedback=None,runtime_source_pin_proven_by_feedback=None,register_readback_proven_by_feedback=None,
    action_scope=dict(local_handoff_update_only=True,board_queries=0,ssh_calls=0,axis_commands=0,
        service_restart=0,dfx=0,initialization_or_recentering=0,implementation_parameter_changes=0),
    independent_boot_recovery='Separate work; original serial ownership and fresh actual-state prerequisites remain. No automatic initialization, recenter, DFX or repeated tuning follows from this acceptance.')
acceptance_path=OUT/'USER_ACCEPTANCE.json';acceptance_path.write_text(json.dumps(acceptance,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
observed_keys=('boot_id','owners','follow_processes','startup_sha256','face_config_sha256',
    'latest_observation_utc','latest_observed_following','latest_observed_pan_state','latest_observed_readback',
    'ui_page','last_report','last_report_status','last_report_result','runtime_fault_count',
    'current_boot_stop_verified','current_platform','binding_compatibility','pan_component_pins','current_zone_sha256','current_face_readback')
historical={k:copy.deepcopy(current.get(k)) for k in observed_keys if k in current}
historical.update(scope='Historical axis-chat observation only; not an assertion of current hardware condition or current physical failure.',
    superseded_for_physical_acceptance_by=str(acceptance_path))
retained_targets=copy.deepcopy(current['targets']);retained_recovery=copy.deepcopy(current['recovery_stability'])
current.update(status='USER_ACCEPTED_AXIS_FOLLOW_AND_NO_STUTTER_IMPLEMENTATION_RETAINED',updated_utc=stamp,
    human_acceptance=acceptance,human_acceptance_record=str(acceptance_path),
    last_axis_chat_board_snapshot_historical=historical,
    runtime_state_currently_verified=False,current_runtime_status='NOT_QUERIED_FOR_HUMAN_ACCEPTANCE_CLOSEOUT',
    boot_id=None,owners=[],follow_processes=None,startup_sha256=None,face_config_sha256=None,
    latest_observation_utc=None,latest_observed_following=None,latest_observed_pan_state=None,latest_observed_readback=None,
    ui_page=None,last_report=None,last_report_status='NO_NEW_TELEMETRY_FOR_HUMAN_ACCEPTANCE',last_report_result=None,
    runtime_fault_count=None,current_boot_stop_verified=None,current_platform=None,binding_compatibility=None,
    pan_component_pins=None,current_zone_sha256=None,current_face_readback=None,
    current_release_basis='Last recorded selected original stable150 implementation, retained without change; no fresh runtime/source verification this update.',
    issue_status=dict(axis_physical_follow='PASS_USER_ACCEPTED',right_turn_stutter='CLOSED_USER_ACCEPTED',
        continued_parameter_tuning='CLOSED',repeated_acceptance_retests='CLOSED',face_voice_association='OUT_OF_SCOPE_USER_CANCELLED'),
    boot_recovery_scope=dict(status='INDEPENDENT_WORK',thread='01a19ca4-6c68-70f2-a9a0-af51dfda6bc6',
        serial_handoff_required=True,actual_current_state_and_native_protection_required=True,
        no_automatic_initialization_recentering_dfx=True,no_retest_for_axis_closeout=True),
    next_action='Axis physical-follow and stuttering acceptance are closed by explicit user feedback. Retain current implementation/parameters; do not tune, move, query or retest for closeout. Separate persistent boot recovery may proceed only under its own explicit serial handoff and actual-current-state checks.',
    rollback='No rollback or parameter change requested; preserve existing implementation and parameters.')
current['previous_user_feedback_historical']=copy.deepcopy(current['latest_user_feedback'])
current['latest_user_feedback']=dict(original=quote,new_version_observation='PASS_BY_EXPLICIT_USER_FEEDBACK',
    physical_follow_accepted=True,no_stuttering_accepted=True,face_voice_association_requested=False,source_chat=acceptance['source_chat'])
current['cause_evidence']['scope']='Historical analysis of the earlier stuttering complaint, now closed by later explicit human acceptance. Do not present old interruptions as current physical failure.'
current['validation']['initial_runtime_observation_historical_only']=current['validation'].get('field_result')
current['validation']['field_result']='PASS_BY_EXPLICIT_USER_FEEDBACK: physical follow works and no stuttering. Numeric test/old runtime observations remain historical; no new boot/source/register proof inferred.'
current['validation']['human_physical_follow_acceptance']='PASS'
current['validation']['human_no_stuttering_acceptance']='PASS'
current['validation']['new_hardware_test_or_register_readback_performed']=False
current['preserved']['scope']='Historical release preservation evidence; this update changes only local handoffs and acceptance status.'
current['coordination_freeze'].update(axis_publication=True,follow_start=True,current_turn_axis_commands=0,
    already_stopped_readonly=None,current_boot_register_readback=None,
    resume_condition='No resumption for tuning or acceptance closeout. Only a separate explicitly coordinated persistent-boot-recovery task with fresh current-state/owner evidence may require original actions.')
current['acceptance_update_scope']='No new board observations. Historical benchmark/FAULT/null snapshot cannot be used to deny the newer explicit human acceptance.'
assert current['targets']==retained_targets and current['recovery_stability']==retained_recovery
assert current['current_release']=='/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-stable150-35d5e154'
assert current['controller_manifest_sha256']=='9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9'
tmp=current_path.with_name('.'+current_path.name+'.accepted.tmp')
tmp.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(current_path)
note='''转轴人类验收收口（2026-11-02）

用户最新原话：“转轴测试是没问题的没有一顿一顿，人脸与声纹关联不用做”。来源为原主窗口01a1994e-f547-74e1-903d-3591021d67c8转达的人类明确反馈。

结论：转轴实物跟随验收通过；一顿一顿/右转顿挫问题已由用户确认通过并关闭。继续调参和为收口反复复测的待办均关闭。人脸与声纹关联按用户要求不做，整体范围由主窗口同步。

保留现有原Ubuntu实现与参数：control-10282601-left40-right45-stable150-35d5e154，manifest9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9；左停点.40、右.45、容差.03、恢复稳定门限150ms，原TTL和硬件4us/20ms保持。此次没有改程序、固件或参数。

本次仅更新AXIS_CURRENT_HANDOFF和本地交接：0 SSH、0板端查询、0轴命令、0服务重启、0DFX、0初始化/回中。人类验收不冒充新鲜boot、source pin、MMIO或寄存器STOP证明；没有补造flags0/lease0。

此前a6d benchmark/FAULT/null及903c STOP均按原时点留档，不能据此断言用户最新实体测试仍故障。AXIS_CURRENT_HANDOFF已将这些板端观测归入明确标时的历史快照，当前硬件状态写明本次未查询。

持久开机恢复是独立工作，保持原串行维护权交接和Native保护链，按届时现役实际状态执行。人类验收收口不会自动触发重复初始化、回中、DFX、运动或重新调参。开机恢复分支目标仍先是可核验UI与轴输出关闭。
'''
(OUT/'USER_ACCEPTANCE_HANDOFF.txt').write_text(note,encoding='utf-8')
release_dir=HERE/'left_stop40_20261102/recovery_stability_20261102_v3'
result_path=release_dir/'CURRENT_RESULT.txt'
if result_path.exists():
    prior=result_path.read_bytes();(OUT/'CURRENT_RESULT.before_human_acceptance.txt').write_bytes(prior)
    result_path.write_text(note+'\n以下为历史交付记录，包含当时待验状态；当前人类验收以以上最新结论为准。\n\n'+prior.decode('utf-8'),encoding='utf-8')
state_path=release_dir/'DELIVERY_STATE.json'
if state_path.exists():
    prior=state_path.read_bytes();(OUT/'DELIVERY_STATE.before_human_acceptance.json').write_bytes(prior)
    state=json.loads(prior);state.update(status='USER_ACCEPTED_AXIS_FOLLOW_AND_NO_STUTTER',
        physical_acceptance='PASS_BY_EXPLICIT_USER_FEEDBACK',acceptance_record=str(acceptance_path),
        no_new_hardware_observation=True,parameters_changed=False)
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=current['status'],acceptance=str(acceptance_path),handoff=str(current_path),
    left_target=current['targets']['left'],right_target=current['targets']['right'],rearm_stability_ms=current['recovery_stability']['minimum_ms'],
    issue_status=current['issue_status'],board_queries=0,board_actions=0,
    no_new_register_or_boot_proof=True,source_or_parameter_changes=False),ensure_ascii=False,indent=2))
