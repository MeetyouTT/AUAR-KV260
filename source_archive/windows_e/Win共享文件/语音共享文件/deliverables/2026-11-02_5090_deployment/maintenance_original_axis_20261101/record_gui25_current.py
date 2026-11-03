"""Record completed normal restore receipts; no device operations."""
import datetime
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
receipt_name = 'maintenance_original_axis_20261101/gui_ready25_observed_01.json'
proof = json.loads((OUT / receipt_name).read_text(encoding='utf-8'))['board_result']
assert proof['status'] == 'GUI_SOFTWARE_READY_PAUSED_OLD_AXIS_CONTEXT_LOCKED'
assert len(proof['checks']) == 16 and all(proof['checks'].values())
applied = json.loads((HERE / 'gui_binding25_applied.json').read_text(encoding='utf-8'))['board_result']
assert applied['startup_after_sha256'] == proof['startup_sha256']
now = datetime.datetime.now(datetime.timezone.utc).isoformat()

def save_existing(path, value, backup_name):
    backup = HERE / backup_name
    assert not backup.exists()
    shutil.copy2(path, backup)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

path = OUT / 'DEPLOYMENT_CURRENT.json'
current = json.loads(path.read_text(encoding='utf-8'))
assert current['startup_sha256'] == applied['startup_before_sha256']
current.update(updated_utc=now,
    phase='GUI_RESTORED_ORIGINAL_WIDE_ACTIVE_AXIS_PHYSICAL_ACCEPTANCE_PENDING',
    startup_sha256=proof['startup_sha256'],
    gui_configuration_sha256=proof['ui_config_sha256'],
    selected_binding_sha256=proof['selected_binding_sha256'],
    selected_binding_source_count=25,
    selected_binding_current_owner_valid=True,
    readback_rebind_pending_after_camera_restore=False,
    selected_binding_receipt='maintenance_original_axis_20261101/gui_binding25_applied.json',
    gui_receipt=receipt_name, gui_software_ready=True,
    gui_service_active=True, gui_owners=proof['owners'],
    gui_state='main_page_ready_listening_paused_original_axis_old_context_locked',
    camera_owner=applied['camera_owner'], camera_service_active=True,
    latest_service_observation=receipt_name,
    saved_listening_enabled=False,
    wide_platform_execution_ready=True,
    current_boot_axis_physical_acceptance_passed=False,
    current_boot_axis_reference_and_direction_verified=False,
    current_boot_axis_follow_verified=False,
    axis_gui_state='FAULT_OLD_CONTEXT', axis_automatic_following=False,
    axis_motion_output_requested=False,
    user_reported_motor_power='DISCONNECTED',
    full_five_component_trial_ready=False,
    full_three_minute_integrated_demo_ready=False,
    physical_page_visibility='PREVIOUSLY_USER_CONFIRMED_CURRENT_RESTORE_SOFTWARE_ONLY',
    physical_page_observed_after_current_restore=False,
    remaining=[
        'fresh full original camera checkpoint restoration audit',
        'current-boot physical reference, observed direction and original axis-follow acceptance',
        'known-person identification and corresponding personal-memory association acceptance',
        'physical speech/avatar synchronisation and continuous three-minute integrated rehearsal',
        'persistent NTP and cold-boot recovery'])
current['identity_query_fix'].update(runtime_validation_pending=True,
    code_loaded_by_current_gui=True,
    loaded_component_sha256=current['identity_query_component_sha256'],
    new_human_identity_query_pending=True)
save_existing(path, current, 'deployment_current.before_gui25_current.json')

path = OUT / 'CONNECTION_CONTEXT.json'
context = json.loads(path.read_text(encoding='utf-8'))
context.update(updated_utc=now, gui_software_ready=True,
    gui_supervisor=proof['owners']['supervisor'], gui_gtk=proof['owners']['gtk'],
    camera_owner=applied['camera_owner'],
    user_reported_axis_powered=False,
    user_reported_motor_power='DISCONNECTED',
    current_boot_axis_physical_acceptance_passed=False,
    gui_receipt=receipt_name,
    physical_role_main_page_user_confirmed_before_current_restore=True,
    physical_role_main_page_user_confirmed=False)
save_existing(path, context, 'connection_context.before_gui25_current.json')

handoff = OUT / 'HANDOFF.txt'
assert not (HERE / 'handoff.before_gui25_current.txt').exists()
shutil.copy2(handoff, HERE / 'handoff.before_gui25_current.txt')
prefix = '''当前状态更新（洛杉矶2026-11-01 23:18软件观察）：
原wide平台及DPU相机已恢复，GUI正常启动一次并通过16项只读检查。相机79866；supervisor82126/GTK82130，完整birth/命令指纹见gui_ready25_observed_01.json。
startup 3f5e81ab…、UI fc98455a…、新选用readback 9ab2533d…，保留原24pins并追加当前run-config为25pins；380组件核验通过，默认14pin与旧24pin绑定均按历史保留。
主页面角色READY、原生动画帧和视觉帧持续推进、无运行故障，原业务写者/时钟已恢复，保存聆听false。身份查询/声纹登记干扰修复已由当前GUI加载，真人查询验收仍待做。
原ID_STOP通过但1500us只是复位寄存器值，不是实体中心。原转轴25文件未改；GUI转轴仍因旧context为FAULT、follow=false，无vsrv或/dev/mem映射、未请求运动。用户确认动力仍断开。
目前不能宣称3分钟全模块一体协同已验收：仍需本boot实体参考/方向/跟随、KNOWN身份及对应记忆验证、声画现场检查和一次连续排练。
以下较早维护/READY记录是历史过程，当前以DEPLOYMENT_CURRENT.json与本段指向回执为准。

'''
handoff.write_text(prefix + handoff.read_text(encoding='utf-8'), encoding='utf-8')

root = OUT.parent.parent
shared = root.parent
block = '''5090 本机部署接续更新（洛杉矶 2026-11-01）：当前统一读语音共享文件/deliverables/2026-11-02_5090_deployment/DEPLOYMENT_CURRENT.json。Windows原27B/OmniVoice模型推理服务为192.168.50.1:8797，板卡192.168.50.2；权重和Ollama数据位于共享目录外D:/AIModels。冻结STATUS/READY_LOCAL/source_manifest是历史回环验收。当前boot903cfade；原wide平台与DPU相机79866已恢复，GUI supervisor82126/GTK82130正常启动一次，380组件与25源绑定通过；startup 3f5e81abc20ce5169ac91ae302611cba8958175a6a2bdb615fd9b858353120d5，当前软件观察见maintenance_original_axis_20261101/gui_ready25_observed_01.json。角色main/READY、动画与视觉帧推进，聆听false。身份查询/声纹登记串扰修复已加载，真人验收待做。原转轴控制器25文件未改，ID_STOP通过；本boot实体参考、方向、跟随尚未验收，GUI保持旧context FAULT/follow=false，用户确认动力断开。KNOWN身份/个人记忆关联和3分钟整机演示尚待验证。勿重复安装下载、重启现役服务或重用旧PID/运动证据/检查点。'''
start = '<!-- 5090-local-deployment-20261102 -->'
end = '<!-- /5090-local-deployment-20261102 -->'
for index, target in enumerate((shared / 'AGENTS.md', root / 'AGENTS.md', shared / 'README.md')):
    if not target.is_file():
        continue
    original = target.read_text(encoding='utf-8')
    assert original.count(start) == 1 and original.count(end) == 1
    begin = original.index(start)
    finish = original.index(end, begin) + len(end)
    backup = HERE / ('entry_before_gui25_%d.txt' % index)
    assert not backup.exists()
    shutil.copy2(target, backup)
    target.write_text(original[:begin] + start + '\n' + block + '\n' + end + original[finish:], encoding='utf-8')

print(json.dumps({'phase': current['phase'], 'gui_software_ready': True,
    'full_three_minute_integrated_demo_ready': False, 'device_operations': False}))
