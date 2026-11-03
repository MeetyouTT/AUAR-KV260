import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;NEW=HERE/'recovery_stability_20261102_v3';DELIVERY=HERE.parents[1]
def read(name):return json.loads((NEW/name).read_text(encoding='utf-8'))
live=read('FINAL_LIVE.json');release=read('APPLIED.json');tests=read('PURE_TESTS.json');board=read('PURE_TESTS_BOARD_PY39.json')
assert tests['status']==board['status']=='PASS' and tests['tests_run']==board['tests']['tests_run']==42
assert live['startup_sha256']==release['startup_after_sha256'] and live['following'] is True
assert live['components_verified']==380 and live['selected_files_verified']==25
assert live['report_result']['rearm_stability_ms']==150 and live['runtime_fault_count']==0
review=read('INDEPENDENT_REVIEW.json')
for r in review['records']:
    assert hashlib.sha256((NEW/'candidate'/r['file']).read_bytes()).hexdigest()==r['after']
current=dict(schema='aura-axis-dedicated-chat-handoff-2',updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    operator='Dedicated axis chat; sole board axis writer. Original project chat read-only.',
    status='STABLE150_DEPLOYED_ORIGINAL_UI_RUNNING_FIELD_MOTION_ACCEPTANCE_PENDING',
    current_release=live['controller_root'],startup_sha256=live['startup_sha256'],face_config_sha256=live['face_config_sha256'],
    controller_manifest_sha256=live['controller_manifest_sha256'],boot_id=live['boot_id'],owners=live['owners'],
    follow_processes=live['follow_processes'],latest_observation_utc=live['utc'],latest_observed_following=live['following'],
    latest_observed_pan_state=live['pan_state'],latest_observed_readback=live['current_readback'],ui_page=live['ui_page'],
    last_report=live['report'],last_report_status=live['report_status'],last_report_result=live['report_result'],
    runtime_fault_count=live['runtime_fault_count'],
    targets=dict(left=.4,right=.45,tolerance=.03,left_stop_band=[.37,.43],right_stop_band=[.42,.48],
        left_trigger=.05,right_camera_trigger=.8064720153808593,white_line=.5,trigger_settings_changed=False),
    recovery_stability=dict(enabled=True,minimum_ms=150,minimum_distinct_admitted_images=3,
        requires_source_and_wall_time_span=True,requires_new_detection_anchor=True,duplicate_frames_do_not_count=True,
        invalid_gap_resets_progress=True,normal_first_start_unchanged=True,normal_visual_completion_unchanged=True,
        immediate_protective_stop_preserved=True,image_ttl_ms=250,detection_anchor_ttl_ms=500,
        previous_authority_lease_velocity_reference_not_restored=True,post_arm_frame_required=True),
    latest_user_feedback=dict(original='Right turn jitters; left turn normal (original typo interpreted).',
        clarified='Stops briefly and then continues.',new_version_observation='PENDING'),
    cause_evidence=dict(previous_run_s=24.293,normal_completions=8,interrupted_segments=5,
        interruptions=dict(SOURCE_UNCONFIRMED=2,SOURCE_HORIZON_ENDED=1,CONTROL_TICK_LATE=1,SOURCE_SUBMISSION_EXPIRED=1),
        rearm_gaps_ms=[170,319,189,73,71],same_segment_endpoint_reversals_observed=0,
        sparse_width_samples=dict(PWM_INCREASE=95,PWM_DECREASE=33,opposite_steps=0),
        user_view_direction_to_pwm_mapping='NOT_ESTABLISHED',
        supported_conclusion='Repeated protective stop/rearm matches reported stuttering; exact upstream scheduling/face-loss cause and mechanics not proven.'),
    validation=dict(windows_python310=dict(passed=42,failed=0,skipped=0),board_python39=dict(passed=42,failed=0,skipped=0),
        original_hardware_slew_tests=16,left_episode_tests=15,rearm_gate_tests=11,components_verified=380,selected_files_verified=25,
        original_baseline_changed_files=3,unchanged_files=22,hardware_slew_session_native_libs_unchanged=True,
        actual_new_report_and_arguments_verified=True,
        actual_new_version_accepted_commands=live['report_result']['commands_accepted'],
        actual_new_version_visual_completions=live['report_result']['visual_center_completions'],
        actual_new_version_rearm_gate_passes=live['report_result']['rearm_stability_passes'],
        field_result='No motion accepted in the saved final observation; source recovery gate was exercised during prearm without PWM. Do not count this as jitter or stop-position acceptance.'),
    preserved=dict(gui_pid=True,camera_pid=True,models=True,firmware=True,native_recovery_seed_counters_marker=True,
        zone_settings_sha256=live['zone_settings_sha256'],global_project_docs_not_written=True),
    transaction_root=release['transaction_root'],
    evidence=dict(delivery_directory=str(NEW),source_review=str(NEW/'INDEPENDENT_REVIEW.json'),
        windows_tests=str(NEW/'PURE_TESTS.json'),board_tests=str(NEW/'PURE_TESTS_BOARD_PY39.json'),
        publication=str(NEW/'APPLIED.json'),ui_start=str(NEW/'UI_STARTED.json'),live=str(NEW/'FINAL_LIVE.json'),
        previous_jitter_analysis=str(HERE/'py39_fix/JITTER_ANALYSIS.json')),
    history=dict(first_candidate='Failed before output due to Python 3.9 float | None annotation; typing.Optional correction tested on board; failure preserved.',
        prior_left40_right45='py39_fix was deployed and actually exercised; latest selected release is stable150.'),
    next_action='User observes same right-turn movement. Read actual latest report fresh; compare stop/rearm counts and gate events. Do not re-toggle a running follower or assume user-view direction equals a PWM sign.',
    rollback='If field behavior is worse, use original pan_stop and verify READY/flags0/lease0, then compare-and-swap only this transaction startup.before.json and pan_face.before.json after fresh exact owner/boot/hash checks; v2 controller remains intact.',
    concurrency_boundary='Only axis delivery and AXIS_CURRENT_HANDOFF.json maintained here. Original chat owns AGENTS/README/global DEPLOYMENT_CURRENT reconciliation.')
path=DELIVERY/'AXIS_CURRENT_HANDOFF.json'
if path.exists():(NEW/'AXIS_CURRENT_HANDOFF.before.json').write_bytes(path.read_bytes())
tmp=path.with_name('.'+path.name+'.axis.tmp');tmp.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
note='''本轮转轴交付（洛杉矶 2026-11-02；运行状态以 JSON UTC 原时点为准）

现役原 Ubuntu 控制程序已版本化发布 stable150。只改原入口/core/session 三文件，另22文件、hardware_slew_session.py及两原so保持。左停点0.40，右停点0.45，容差0.03；左触发0.05和原右触发0.806472保持。

用户确认右转表现为“停一下又继续转”。对应上一版24.293秒报告有8次正常完成、5次中途保护停止：UNCONFIRMED两次，HORIZON_ENDED、CONTROL_TICK_LATE、SUBMISSION_EXPIRED各一次；恢复170/319/189/73/71ms。保留命令未发现同段反向端点。稀疏宽度读回未发现方向内反向步进，不代替引脚波形或轴端测量；用户面对设备的右转尚未直接对应PWM增减。

保守修正：保护停止仍立即执行。只对中断后的重启增加150ms稳定门限，至少3张不同的原准入图像，图像时间和接收时间均须跨足150ms，并看到中断后更新的检测锚；重复/排队旧帧不能替代稳定时长，再失效重新计稳定进度。正常首次启动、正常居中完成、原250ms图像/500ms检测锚、源租约、ARM后真实帧与停止保护保持。

Windows Python3.10及真实板端Python3.9各42项通过，无失败跳过：15停点/恢复、16原hardware-slew、11稳定门限。380组件和25控制文件闭包回读通过。GUI97308/97312与相机79866保持；模型、固件和native恢复检查点/计数/marker未改。

已从原UI开启一次，新report确认left=.40/right=.45/stability=150，实际子进程201785，仍持续监视。保存的最后观测未有PWM运动命令（0 accepted、0 visual completions），仅在无PWM预ARM时发生两次稳定门限通过；当前脸在区域内、flags0、lease0、1480us。此证据证明加载和无运动恢复路径，不作为新抖动或停点的实体验收。新现场效果待用户同方式右转反馈。

首次候选的float | None注解在板端Python3.9导入失败，未输出；已用typing.Optional修正，失败与旧版本证据均保留。旧v2已实际运动，相关8次完成不能算stable150验收。

最新指纹与后续串行入口：上一级交付根 AXIS_CURRENT_HANDOFF.json。仅本对话操作板端转轴；原整体窗口只读。
'''
(NEW/'CURRENT_RESULT.txt').write_text(note,encoding='utf-8')
(NEW/'DELIVERY_STATE.json').write_text(json.dumps(dict(status=current['status'],handoff=str(path),
    handoff_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),files=[dict(file=r['file'],sha256=r['after']) for r in review['records']],
    physical_acceptance='PENDING',last_utc=live['utc']),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=current['status'],handoff=str(path),following=live['following'],
    runtime_fault_count=live['runtime_fault_count'],commands_accepted=live['report_result']['commands_accepted'],
    tests_each_runtime=42,components=380,selected=25)))
