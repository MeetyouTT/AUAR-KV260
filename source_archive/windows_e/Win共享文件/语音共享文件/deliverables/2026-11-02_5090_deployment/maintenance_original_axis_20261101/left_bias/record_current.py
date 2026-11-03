"""Record restored original following and the selected left-biased stop target."""
import datetime
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
MAINT=HERE.parent;OUT=MAINT.parent;PROJECT=OUT.parent.parent;SHARED=PROJECT.parent
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
apply=json.loads((HERE/'applied.json').read_text(encoding='utf-8'))
live=json.loads((HERE/'LIVE_TARGET45_01.json').read_text(encoding='utf-8'))['samples'][-1]
trial=json.loads((MAINT/'ui_follow_final.json').read_text(encoding='utf-8'))
gui=json.loads((MAINT/'gui_original_axis_final_observed.json').read_text(encoding='utf-8'))['board_result']
camera=json.loads((MAINT/'camera_restore_audit/RESTORED_CAMERA_AUDIT.json').read_text(encoding='utf-8'))['board_result']
assert apply['status']=='ORIGINAL_FOLLOW_TARGET45_SELECTED_STOPPED'
assert live['original_report']['effective_target']==.45
assert trial['ui_stopped_ready'] and trial['result']['visual_center_completions']==17
backup=HERE/'current_handoff_before';assert not backup.exists();backup.mkdir()
def write_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def backup_file(path):
    if path.exists():shutil.copy2(path,backup/(str(len(list(backup.iterdir())))+'-'+path.name))

path=OUT/'DEPLOYMENT_CURRENT.json';backup_file(path);v=json.loads(path.read_text(encoding='utf-8'))
v.update(updated_utc=now,phase='GUI_ORIGINAL_FOLLOW_RESTORED_LEFT_TARGET45_ACTIVE',
    startup_sha256=apply['startup_after_sha256'],gui_configuration_sha256='fc98455a5586cc4f1896f5472ec9b204bd7ff2b0c5be2798ba5cab1788b9b959',
    selected_binding_sha256='9ab2533d2c3000d61095f54de2e8199f53461ac085e2f58230ab36149be6af1f',
    selected_binding_source_count=25,selected_binding_current_owner_valid=True,readback_rebind_pending_after_camera_restore=False,
    camera_owner=camera['camera_owner'],camera_service_active=True,camera_restore_audit='maintenance_original_axis_20261101/camera_restore_audit/RESTORED_CAMERA_AUDIT.json',
    gui_software_ready=True,gui_service_active=True,gui_owners=gui['owners'],gui_state='running',
    gui_receipt='maintenance_original_axis_20261101/gui_original_axis_final_observed.json',
    latest_service_observation='maintenance_original_axis_20261101/left_bias/LIVE_TARGET45_01.json',
    current_ui_page=live['page'],physical_page_visibility='USER_CONFIRMED_ROLE_MAIN_PAGE_AND_CORRECT_PHYSICAL_FACE_FOLLOW',
    wide_platform_execution_ready=True,current_boot_motion_authorized=True,
    user_confirmed_motor_power_disconnected=False,user_reported_motor_power_connected=True,
    original_axis_controller_unchanged=False,original_axis_control_algorithm_unchanged=True,
    original_axis_source_change='one optional target-center-ratio argument on original entry; 24 other files byte-identical',
    axis_controller_root=apply['controller_root'],axis_controller_manifest_sha256=apply['controller_manifest_sha256'],
    axis_face_configuration_sha256=apply['face_config_sha256'],
    axis_current_following=live['following'],axis_current_pulse_us=live['pulse_us'],
    axis_physical_direction_user_confirmed=True,axis_original_follow_user_confirmed=True,
    axis_user_observation_quote='方向正确，能够跟随',
    axis_original_follow_trial={'receipt':'maintenance_original_axis_20261101/ui_follow_final.json',
        'duration_s':trial['result']['elapsed_s'],'commands_accepted':trial['result']['commands_accepted'],
        'visual_center_completions':17,'stop_confirmed':True,'target_during_this_trial':.5},
    axis_stop_target={'screen_ratio':.45,'white_line_ratio':.5,'tolerance_ratio':.03,'band':[.42,.48],
        'runtime_setting_verified':True,'new_position_user_acceptance':'PENDING',
        'receipt':'maintenance_original_axis_20261101/left_bias/LIVE_TARGET45_01.json'},
    identity_query_component_sha256='85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809',
    measured_latency_report='dialogue_latency_20261101/TWO_TURN_LATENCY.json')
v['identity_query_fix'].update(applied=True,runtime_validation_pending=False,
    runtime_scope='patched production source loaded in current GUI; speaker and camera identity services ready; actual KNOWN/voice binding pending')
v['memory_status']['scope']='Historical aggregates before maintenance; the current GUI and worker have since restarted'
v['remaining']=['user acceptance of new white-line-left stop target',
    'known-person and personal-memory association acceptance','persistent NTP and cold-boot recovery']
write_json(path,v)
path=OUT/'CONNECTION_CONTEXT.json';backup_file(path);c=json.loads(path.read_text(encoding='utf-8'))
c.update(updated_utc=now,gui_software_ready=True,gui_supervisor=gui['owners']['supervisor'],gui_gtk=gui['owners']['gtk'],
    current_boot_motion_explicitly_authorized=True,user_reported_axis_powered=True,
    user_confirmed_installation_unchanged=True,user_confirmed_correct_follow_direction=True,
    current_startup_sha256=apply['startup_after_sha256'],current_camera_owner=camera['camera_owner'])
write_json(path,c)
path=OUT/'PARALLEL_WORK.json';backup_file(path);p=json.loads(path.read_text(encoding='utf-8'))
p.update(updated_utc=now,current_phase=v['phase'],board_current_boot_motion_authorized=True,
    remaining_platform_execution_ready=True,root_is_only_board_writer=True)
p['tasks'] += [
    {'agent':'/root/axis_follow_restore','status':'completed','result':'original 25-file path, original rated release and mirror/white-line target reviewed; root restored and user confirmed correct physical following'},
    {'agent':'/root/identity_runtime_verify','status':'completed','result':'identity v2 deployed and bound to actual restored camera; exact clock sampler and intermittent network tail diagnosed'}]
write_json(path,p)
report='''转轴原方案恢复及左偏停点更新（洛杉矶 2026-11-02）

用户已现场确认原人脸跟随“方向正确，能够跟随”。原UI轮次运行109.352秒，386次接收命令、40段、17次视觉居中完成，显式STOP后flags=0、lease=0；这轮目标仍为0.5。

按用户随后要求，当前停止目标设为镜像画面0.45，原白线保持0.5，容差0.03，因此目标带[0.42,0.48]整体位于白线左侧。两侧共用此目标；实际停止受真实帧、容差、跨越和过期保护影响，不宣称机械停点精确20像素。

沿用原控制算法、固件、driver、速度、行程与源时效。仅在原run入口加一个可选target-center-ratio参数（默认仍0.5）并传给原EdgeConfig；另24项字节不变。旧25项目录与旧STOP回执保留。GUI实时读取新配置，没有重启GUI、相机或模型。

纯参数/双向停止检查6组及7个非法值通过；原入口其余AST不变。运行回读确认0.45/0.03，GUI故障0。新停点尚待用户现场确认，不将原方向验收当作新停点验收。

当前主GUI supervisor97308、GTK97312，相机79866，同boot903cfade-b93c-48fa-804e-379be1967313；实际指纹和新startup以DEPLOYMENT_CURRENT.json为准。原相机exact seed c6c8…与18层archive已完整验证。

两轮对话旧实测：ASR1.093/1.395秒，LLM1.940/1.833秒，TTS0.766/0.838秒。主要等待为完整LLM回复，其次ASR；不把软件SPEAKING当声学首声。
身份查询/声纹登记串扰v2已随现行GUI加载；真人KNOWN、声纹标定及个人私库协同仍待验。
GUI曾两次被原1秒时钟采样门槛拒绝；独立HTTP观测证实间歇3秒以上长尾，随后原门槛正常启动通过，60次并行health最大236.5ms。没有放宽时钟保护。
'''
(HERE/'CURRENT_RESULT.txt').write_text(report,encoding='utf-8')
handoff=OUT/'HANDOFF.txt';backup_file(handoff)
handoff.write_text(report+'\n以下为各阶段保留记录，当前以DEPLOYMENT_CURRENT.json为准。\n\n'+handoff.read_text(encoding='utf-8'),encoding='utf-8')
prefix='''<!-- 5090-local-deployment-20261102 -->
5090接续更新（洛杉矶2026-11-02）：Windows原27B IQ4_XS/OmniVoice16及LAN已验收，端点192.168.50.1:8797，仅板192.168.50.2可推理，权重仍D:/AIModels。板端原wide联合固件已恢复，原相机从封存final精确恢复；真实相机79866，GUI97308/97312，同boot903cfade-b93c-48fa-804e-379be1967313。身份查询串扰v2已加载，选用25pin绑定、380组件匹配。用户已现场确认原跟随方向正确并能跟随；原UI一轮17次视觉居中完成并核STOP。随后按用户要求将双向停止目标改为白线左侧0.45（容差0.03），白线仍0.5；仅原入口增加可选目标参数，另24文件不变，旧版本保留，新停点待用户确认。当前startup ff7c0599d8b719b66dadee193553b937027de72867f266e1cb443320a9b5dc4e，跟随按现役UI状态核验。最新事实统一读语音共享文件/deliverables/2026-11-02_5090_deployment/DEPLOYMENT_CURRENT.json；最新详述maintenance_original_axis_20261101/left_bias/CURRENT_RESULT.txt。聆听保存false，模型未换，冷启动/持久NTP/真人KNOWN尚未最终验收。冻结STATUS/READY_LOCAL和下方旧PID/startup/benchmark段落仅为原时点历史；勿重放旧运动或恢复脚本。
<!-- /5090-local-deployment-20261102 -->'''
for path in (SHARED/'AGENTS.md',SHARED/'README.md',PROJECT/'AGENTS.md',PROJECT/'README.md'):
    if not path.exists():continue
    backup_file(path);text=path.read_text(encoding='utf-8')
    start='<!-- 5090-local-deployment-20261102 -->';end='<!-- /5090-local-deployment-20261102 -->'
    if start in text:
        a=text.index(start);b=text.index(end,a)+len(end);text=text[:a]+prefix+text[b:]
    else:text=prefix+'\n\n'+text
    path.write_text(text,encoding='utf-8')
print(json.dumps({'phase':v['phase'],'startup_sha256':v['startup_sha256'],'current_file':str(OUT/'DEPLOYMENT_CURRENT.json'),'backup_files':len(list(backup.iterdir()))}))
