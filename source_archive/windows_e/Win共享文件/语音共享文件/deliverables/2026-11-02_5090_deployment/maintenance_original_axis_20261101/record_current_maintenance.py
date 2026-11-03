import datetime
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent;OUT=HERE.parent
path=OUT/'DEPLOYMENT_CURRENT.json'
before=HERE/'deployment_current.before_original_axis_maintenance.json'
assert not before.exists();shutil.copy2(path,before)
value=json.loads(path.read_text(encoding='utf-8'))
value.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    phase='ORIGINAL_WIDE_LOADED_ID_STOP_PASS_CAMERA_RESTORING',
    gui_software_ready=False,gui_owners=None,gui_receipt=None,
    previous_accepted_gui_receipt='gui_start_and_verify.json',
    gui_state='normally_stopped_for_original_axis_maintenance',
    startup_sha256='0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f',
    identity_query_collaboration_patch_applied=True,
    identity_query_component_sha256='85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809',
    platform_firmware='aura-visual-servo-b4096-wide-v1.bit.bin',
    platform_readback='maintenance_original_axis_20261101/load_result_02.json',
    original_id_stop_passed=True,original_id_stop_receipt='maintenance_original_axis_20261101/camera_start_after_idstop.json',
    last_final_checkpoint_sha256='c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471',
    final_checkpoint_archive_chain_verified=18,
    selected_binding_current_owner_valid=False,readback_rebind_pending_after_camera_restore=True,
    user_confirmed_motor_power_disconnected=True,user_confirmed_installation_unchanged=True,
    user_can_observe_axis=True,user_confirmed_clear_space=True,
    original_axis_controller_unchanged=True,
    two_human_turns_playback_committed=True,
    measured_latency_report='dialogue_latency_20261101/TWO_TURN_LATENCY.json',
    camera_start_request='maintenance_original_axis_20261101/camera_start_after_idstop.json')
path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
handoff=OUT/'HANDOFF.txt';shutil.copy2(handoff,HERE/'handoff.before_original_axis_maintenance.txt')
prefix='''当前维护状态补充（洛杉矶2026-11-01）：
GUI已正常停止，身份查询/声纹登记串扰修复已应用，当前startup0f2a319a…；380组件核验通过。
相机1333已正常退出，新final c6c8baab…原reader及18层archive、全部观察下界通过并按原字节封存。
板端原client各执行一次remove/load，实际overlay/render/ZOCL及wide固件/VART读回通过；原ID_STOP_ONLY通过，ARM/COMMIT/BIND/REFERENCE均false。
已唯一请求原相机恢复，正在验证新owner/计数/消费审计；旧1333 GUI readback待按真实新owner重建，暂勿用旧绑定启动GUI。
用户已确认安装未动、可观察且空间足，转轴动力已单独断开。后续沿原25文件控制器，不写替代跟随算法。
两轮真人对话均有新完整播放回执：ASR1.093/1.395s，LLM1.940/1.833s，TTS0.766/0.838s；worker到首PCM入队4.328/4.591s。详见dialogue_latency_20261101/LATENCY_REPORT.txt。
当前真实阶段以DEPLOYMENT_CURRENT.json及maintenance_original_axis_20261101为准，下面先前页面READY是历史通过记录。

'''
handoff.write_text(prefix+handoff.read_text(encoding='utf-8'),encoding='utf-8')
print(json.dumps({'phase':value['phase'],'current':str(path)}))
