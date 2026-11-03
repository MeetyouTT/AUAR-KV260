"""Record the authorized live 0.80 trial; preserve all earlier failed-human evidence."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];ANALYSIS=ROOT.parent/'语言模型分析'
existing=HERE/'threshold_080_verification_summary.json'
if existing.exists() and json.loads(existing.read_text(encoding='utf-8')).get('actual_user_enrollment_passed') is True:
    raise SystemExit('Retaining successful real-user enrollment; do not overwrite it with the earlier empty-library pending snapshot.')
read=lambda name:json.loads((HERE/name).read_text(encoding='utf-8'))
a=read('threshold_080_activation.json');v=read('threshold_080_current_verification.json');u=read('threshold_080_ui_recovery.json')
assert a['status']=='THRESHOLD_080_LOADED_AWAITING_REAL_USER_TRIAL'
assert v['threshold']==.8 and v['database']=={'identities':0,'templates':0,'revision':13}
assert v['automatic']['can_start'] and u['automatic_can_start']
summary={'client_date':'2026-10-19','status':'THRESHOLD_080_READY_AWAITING_REAL_USER_TRIAL',
 'explicit_user_authorization':'用户同意下一轮试0.80，随后要求继续',
 'threshold':.8,'previous_threshold':.85,'ambiguity_margin':.1,
 'threshold_origin':'user_authorized_experimental_cosine_0.80_not_field_calibrated',
 'boundary_margin_and_real_public_model_preflight_passed':a['preflight_passed'],
 'registered_count':0,'template_count':0,'database_revision':13,'database_preserved_during_threshold_reload':True,
 'single_reference_template_policy_unchanged':True,'selection_minimum_ms':15000,'heldout_frames':5,
 'consecutive_heldout_validation_unchanged':True,'quality_filters_unchanged':True,'original_anchor_policy_unchanged':True,
 'backend':'WINDOWS_CPU_SFACE_ORT','active_sources_verified':v['active_source_count'],
 'runtime':v['source_runtime'],'active_identity_config':v['active_identity_config'],
 'database_backup_created':False,'current_boot_id':v['current_boot_id'],'current_camera_pid':v['current_camera_pid'],
 'boot_changed_since_initial_activation':v['boot_changed_since_original_activation'],
 'original_pc_models_restored_after_reboot':True,'ui_reloaded_after_pc_recovery':u['ui_restarted'],
 'start_conversation_available':v['automatic']['can_start'],
 'actual_user_enrollment_passed':None,'actual_board_listening_passed':None,'departure_return_recognition_passed':None,
 'different_person_test_passed':None,'field_accuracy_calibrated':False,
 'photos_accessed':False,'templates_exported':False,'full_frames_exported':False,
 'rollback_config_only_backup':a['backup']}
(HERE/'threshold_080_verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'threshold_080_listening.json').write_text(json.dumps({'status':'AWAITING_NEW_REAL_USER_080_TRIAL',
 'actual_user_enrollment_passed':None,'actual_board_listening_passed':None,
 'departure_return_recognition_passed':None,'different_person_test_passed':None},indent=2),encoding='utf-8')
report=f'''# 0.80人脸匹配试用已加载

2026-10-19用户同意下一轮试0.80并要求继续。活动匹配阈值已由0.85改为0.80，本地开发配置同步；旧保留0.85的要求在此次明确授权范围内被更新。0.1身份间隔、至少15秒自然视频选样、最多24份RAM候选、一个实际代表特征、5份连续独立新帧验证、原始锚点核对和明确姓名/登记确认均保持。

## 已核实结果

- 新门槛的真实匹配器边界：0.7999拒绝、0.80及0.8001通过；分差不足0.1仍拒绝/歧义。采样usable门槛与匹配器同用0.80。
- 使用固定公开Lena图片，板卡YuNet/对齐→Windows同一SFace CPU→板端临时库，完整开头确认、自动取样验证/保存、重新识别及失脸清除通过。逻辑时钟顺序驱动，不注入姿态/质量，不接触用户身份库；这不是新真人登记成功。
- 最初对话未停止时，闲置保护拒绝切换且没有改配置；对话停止后切换完成。仅相机身份服务为加载门槛重启，22份活动源与人体DPU/ByteTrack配置保持，原身份库0条/模板0份、修订13及哈希不变。
- 随后设备重新启动，已重新核对活动配置仍0.80/0.1，身份库仍空、权限{v['database_mode']}，活动22份源码一致。当前相机PID {v['current_camera_pid']}，boot `{v['current_boot_id']}`；这些是当前快照，后续应动态读取。
- 设备重启后电脑8791/8792未运行，已按原启动器恢复Paraformer、原27B/IQ4_XS及OmniVoice16与SFace CPU。界面先于电脑服务启动，首次获取提示资源失败，故在对话停止状态下重载原界面，恢复feedback_ready和开始对话按钮；未修改业务源码或音频/模型参数。
- 当前开始对话可用，自动对话仍未开启。未代替用户录音/发起真人登记，未在玩偶播放测试音。

## 使用步骤

点击开始对话，说“帮我登记身份，我叫……”；听到复述后说“确认登记”。从空库登记新身份，不需要“确认更新登记”。慢慢自然转头，听到“看向镜头，稍停几秒”后看回镜头等待结果，末尾不用再次确认。

0.80在前次保留24帧上可通过分数条件，但不同人对照及新真人登记、离场重返尚未验收。不能称为最终校准阈值或稳定识别完成。用户下一次反馈应结合新会话实际COMMITTED、分数与库修订判断。

## 活动路径、证据与回退

活动UI/相机源码仍 `{v['source_runtime']}`，身份配置 `{v['active_identity_config']}`；有效配置副本 `effective_config_080/board_identity.json`，本地配置 `aura/config/board_identity.json`。同一配置内的threshold同时用于库内识别、登记新帧验证及换轨原始锚点核对，原0.1分差保持。

本次回退只需在对话停止时恢复配置备份 `{a['backup']}/board_identity.before.json` 并重新加载相机服务，即回到0.85。备份只含配置，不含用户数据库/模板；不得恢复已删除身份。原较早阈值提案脚本仍属历史，不能运行其中的0.363提案代替本次0.80。

证据：`threshold_080_activation.json`、`threshold_080_preflight.log`、`threshold_080_current_verification.json`、`threshold_080_ui_recovery.json`、`threshold_080_verification_summary.json`。以前0.85失败/离线比较、全部删除记录分别保留，未修改为成功。未保存现场照片/视频或导出姓名/模板，大语言模型数据仍D盘。
'''
(HERE/'THRESHOLD_080.md').write_text(report,encoding='utf-8')
marker='<!-- threshold-080-active-20261019 -->'
block=marker+f'\n- 2026-10-19用户已同意“下一轮先试0.80”并要求继续，活动及本地board_identity阈值0.85→0.80，0.1间隔/15秒选样/最多24RAM/单实际代表模板/连续5独立新帧/固定原始锚点及授权不变。此新授权覆盖下方旧保留0.85/0.80未部署表述。真实匹配器边界/分差及公开Lena临时库完整自动登记识别失脸预检通过；22份活动源码及DPU/ByteTrack/音频模型配置保持，库当前0身份/0模板/修订13。活动runtime仍 `{v["source_runtime"]}`，当前相机PID {v["current_camera_pid"]}但后续应动态读取。设备随后重启已复核0.80持久生效；原PC8791/8792按原启动器恢复，空闲重载UI以重新取得反馈提示，开始对话可用。真人0.80登记/听音/重返及不同人误认尚待验证，不能当已校准。最新证据 `deliverables/2026-10-19_threshold_calibration/THRESHOLD_080.md`、`threshold_080_verification_summary.json` 优先于旧0.85快照。回退仅恢复本次配置备份并加载相机，不恢复已删身份；LLM数据D盘。\n<!-- /threshold-080-active-20261019 -->\n\n'
path=ROOT/'AGENTS.md';raw=path.read_text(encoding='utf-8')
if marker not in raw:path.write_text(block+raw,encoding='utf-8')
note='> **2026-10-19 0.80试用已生效：** 用户同意后，活动/本地人脸匹配阈值改0.80，保留0.1分差和5份连续新帧验证。公开模型/边界预检通过，当前库仍空（修订13）；设备重启后已复核配置并恢复原电脑语音/人脸服务，开始对话可用。真人登记和重返仍待验证。[本轮加载与回退](deliverables/2026-10-19_threshold_calibration/THRESHOLD_080.md)。\n\n'
path=ROOT/'README.md';raw=path.read_text(encoding='utf-8')
if not raw.startswith('> **2026-10-19 0.80试用已生效：**'):path.write_text(note+raw,encoding='utf-8')
path=HERE/'README.md';raw=path.read_text(encoding='utf-8')
note='> 后续用户已同意试用0.80，现已加载；此前下方“仍0.85/未部署”为离线分析时点。身份库仍空、修订13。[最新0.80加载与回退](THRESHOLD_080.md)。\n\n'
if not raw.startswith('> 后续用户已同意试用0.80'):path.write_text(note+raw,encoding='utf-8')
path=HERE/'verification_summary.json';old=json.loads(path.read_text(encoding='utf-8'))
old.update(subsequent_user_authorized_trial_threshold=.8,subsequent_trial_deployed=True,
 latest_trial_evidence=str(HERE/'threshold_080_verification_summary.json'))
path.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
analysis='人脸0.80试用加载_20261019.md';(ANALYSIS/analysis).write_text(report+'\n完整证据：`'+str(HERE)+'`。\n',encoding='utf-8')
path=ANALYSIS/'README.md';raw=path.read_text(encoding='utf-8')
entry=f'## 最新：0.80试用已加载\n\n[本轮加载与验证]({analysis})：用户同意后已改0.80，保留0.1分差及连续5新帧；边界/公开模型预检通过，库0条/修订13，重启后配置与原语音/人脸服务已恢复核实。真人本轮登记和重返尚待验证。\n\n'
if analysis not in raw:raw=raw.replace('# 语言模型分析统一入口\n','# 语言模型分析统一入口\n\n'+entry,1)
path.write_text(raw,encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
