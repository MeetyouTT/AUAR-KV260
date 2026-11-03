"""Reconcile project progress from read-only evidence; no board operations."""
import datetime
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent;OUT=HERE.parent
board=json.loads((HERE/'LIVE_BOARD_READONLY.json').read_text(encoding='utf-8'))
models=json.loads((HERE/'LIVE_MODELS_READONLY.json').read_text(encoding='utf-8'))
latency=json.loads((OUT/'dialogue_latency_20261101/TWO_TURN_LATENCY.json').read_text(encoding='utf-8'))
memory=json.loads((OUT/'video_demo_readiness_20261101/MEMORY_CURRENT_READONLY.json').read_text(encoding='utf-8'))['board_result']
assert board['component_pins_consistent_at_snapshot'] and board['component_count']==380
assert models['ok'] and models['tts_ready'] and models['llm_residency']['llm_resident']
assert latency['completed_turns']==2 and latency['both_full_playback_receipts_committed']
assert memory['quick_check_ok']
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
coord={'schema':'aura-user-requested-chat-responsibilities-1','updated_utc':now,
    'axis_thread':{'thread_id':'01a19b64-8194-70e3-806b-03fa9a283918','host_id':'local',
        'title':'转轴跟随｜左侧停点优化','status':'active',
        'responsibility':'唯一板卡转轴操作、原跟随停点优化、转轴候选测试与发布、实体反馈',
        'handoff':'AXIS_CHAT_HANDOFF_20261102.txt','result_authority':'AXIS_CURRENT_HANDOFF.json'},
    'original_chat':{'responsibility':'整体工程梳理、模型/语音/视觉/身份/记忆的进程与证据汇总；不操作转轴',
        'board_actions_allowed_for_this_progress_audit':'read-only metadata only'},
    'global_document_writer':'original chat','axis_chat_writes_global_docs':False}
(OUT/'CHAT_COORDINATION.json').write_text(json.dumps(coord,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rows=[
    {'module':'本机模型与LAN','status':'实测通过、当前健康','evidence':['LIVE_MODELS_READONLY.json','../parallel_lan/LAN_PUBLIC_BOARD_READY.json'],
        'facts':'原27B IQ4_XS与OmniVoice16；模型驻留，TTS就绪；板卡LAN推理链路已验收'},
    {'module':'板端业务/角色UI','status':'当前运行正常','evidence':['LIVE_BOARD_READONLY.json'],
        'facts':'GUI/相机/边界editor均运行；380组件一致；角色准备完成、业务写者持有、故障0；当前在视觉页，聆听暂停'},
    {'module':'视觉感知','status':'运行就绪、有实际人脸输入及跟随证据','evidence':['LIVE_BOARD_READONLY.json','../maintenance_original_axis_20261101/ui_follow_final.json'],
        'facts':'相机采集和检测持续，身份服务ready，无采集错误；不等同本人KNOWN已验收'},
    {'module':'基础语音对话','status':'两轮真人完整播放通过','evidence':['../dialogue_latency_20261101/TWO_TURN_LATENCY.json'],
        'facts':'两轮均有匹配完整播放回执；软件观测录音结束至SPEAKING约5.04/5.29秒；非声学首声'},
    {'module':'转轴跟随','status':'基础方向/跟随用户已确认；新左停点优化在独立对话进行','evidence':['../AXIS_CHAT_HANDOFF_20261102.txt'],
        'facts':'原UI基线109.352秒、386接受命令、17次视觉完成并STOP；新左0.40/右0.45候选31项测试通过，发布与新实体反馈由转轴对话负责'},
    {'module':'身份与语言协同','status':'修复已部署；真人完整链待验','evidence':['../identity_dialogue_review/REVIEW_VERDICT.json','../identity_dialogue_review/runtime_after25/RUNTIME_MINIMAL_01.json'],
        'facts':'修复身份查询被声纹登记误采样；当前身份/声纹服务就绪；本人KNOWN、声纹绑定和个人权限调用未完成本轮实测'},
    {'module':'记忆','status':'已落在板端、原摘要链运行；个人记忆/长时召回待验','evidence':['../video_demo_readiness_20261101/MEMORY_CURRENT_READONLY.json','LIVE_BOARD_READONLY.json'],
        'facts':'07:20只读快照767轮、3391有效摘要、1项待处理正文、quick_check通过；08:36当前GUI累计完成86项，不能跨进程相减'},
    {'module':'开机恢复与稳定性','status':'尚未最终验收','evidence':['LIVE_BOARD_READONLY.json','../identity_dialogue_review/runtime_after25/ORIGINAL_SAMPLER_VS_PLAIN_01.json'],
        'facts':'当前业务时钟锚定可用，但系统NTP未同步；有网络健康请求秒级长尾；下一次冷启动能自动恢复wide/相机绑定/GUI/轴尚未验收'},
]
progress={'schema':'aura-project-progress-1','updated_utc':now,'client_date':'2026-11-02','timezone':'America/Los_Angeles',
    'live_board_observed_utc':board['utc'],'live_models_observed_utc':models['observed_utc'],
    'overall':'基础链路已跑通；完整身份个人记忆协同、最终停点、冷启动恢复仍待验收',
    'full_five_component_human_acceptance_complete':False,'axis_thread':coord['axis_thread'],'modules':rows,
    'measured_latency_ms':latency['means_ms'],
    'next_sequence':['独立转轴对话完成新左停点实物确认',
        '同一轮验证视觉目标、本人KNOWN、声纹/会话关联、个人记忆权限与正常回复完整播放',
        '根据两轮已测数据先检查完整LLM回复交付和ASR，再定位网络长尾',
        '保存后做一次有现场观察的冷启动与自动恢复验收'],
    'audit_actions':{'board_commands_sent':False,'database_opened':False,'models_restarted':False,'private_content_exported':False}}
(HERE/'PROJECT_PROGRESS.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
backup=HERE/'global_state_before_reconcile';assert not backup.exists();backup.mkdir()
p=OUT/'DEPLOYMENT_CURRENT.json';shutil.copy2(p,backup/p.name);v=json.loads(p.read_text(encoding='utf-8'))
legacy_keys=('axis_gui_state','axis_automatic_following','axis_motion_output_requested','user_reported_motor_power',
             'current_boot_axis_physical_acceptance_passed','current_boot_axis_reference_and_direction_verified','current_boot_axis_follow_verified')
v['archived_axis_fields_before_project_reconciliation']={k:v.get(k) for k in legacy_keys}
v.update(updated_utc=now,project_progress='project_progress_20261102/PROJECT_PROGRESS.json',
    latest_project_observation='project_progress_20261102/LIVE_BOARD_READONLY.json',
    latest_project_observation_utc=board['utc'],axis_work_owner='dedicated_user_chat',
    axis_chat_thread_id=coord['axis_thread']['thread_id'],axis_chat_title=coord['axis_thread']['title'],
    axis_live_detail_authority='AXIS_CURRENT_HANDOFF.json (maintained by dedicated chat; use when present)',
    axis_gui_state=board['axis_snapshot_only']['state'],axis_automatic_following=board['axis_snapshot_only']['following'],
    user_reported_motor_power='CONNECTED',user_reported_motor_power_connected=True,
    current_boot_axis_follow_verified=True,
    current_boot_axis_follow_verified_scope='Original direction/following baseline confirmed by user; latest asymmetric stop position not yet accepted',
    current_boot_axis_physical_acceptance_passed=False,
    current_boot_axis_physical_acceptance_scope='Final stop-position tuning pending; baseline physical motion and correct direction already demonstrated',
    current_boot_axis_reference_and_direction_verified=True,
    current_boot_axis_reference_and_direction_scope='Current stopped command reference and original observed direction; no measured mechanical zero or waveform qualification',
    mechanical_zero_calibrated=False,
    physical_page_observed_after_current_restore=True,
    persistent_ntp_synchronized=board['persistent_ntp_synchronized'],
    gui_software_ready=True,gui_service_active=True,camera_service_active=True,
    model_current_health_receipt='project_progress_20261102/LIVE_MODELS_READONLY.json',
    current_runtime_memory={'observed_utc':board['utc'],'gui_supervisor':board['units']['aura-avatar-ui.service']['owner'],**board['business']['memory']})
v['memory_status']['scope']='Historical read-only aggregate snapshot at07:20UTC; current process counters are separate in current_runtime_memory'
v['remaining']=['dedicated axis chat: final left-stop-position acceptance',
    'same-turn known-person, voice binding and personal-memory permission acceptance',
    'end-to-end latency and intermittent network tail improvement',
    'persistent NTP and cold-boot automatic recovery acceptance']
p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=OUT/'PARALLEL_WORK.json';shutil.copy2(p,backup/p.name);v=json.loads(p.read_text(encoding='utf-8'))
v.update(updated_utc=now,main_responsibility=coord['original_chat']['responsibility'],
    board_axis_write_owner='chat:'+coord['axis_thread']['thread_id'],current_phase='PROJECT_BASELINE_READY_AXIS_REFINEMENT_DEDICATED_CHAT',
    chat_coordination='CHAT_COORDINATION.json')
p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary='''项目进程梳理（洛杉矶2026-11-02）

转轴已交给新对话“转轴跟随｜左侧停点优化”，ID01a19b64-8194-70e3-806b-03fa9a283918。原窗口负责整体项目进程和全局文档；不再发转轴动作，避免两个窗口竞争。

已完成并有实测证据：本机原27B IQ4_XS+OmniVoice16、LAN板卡推理；板端角色UI及原wide视觉平台恢复；两轮真人完整语音对话；原人脸跟随方向/动作由用户现场确认。08:36只读核验GUI/相机/editor均运行，380组件一致，故障0，身份/声纹服务ready。

转轴当前工作：用户明确是“左边转完后偏右”，前两次挪触发线没有解决停止位置。新对话已完成左0.40/右0.45候选的15项专项+16项原硬件slew回归，共31项通过；正在沿原事务发布，新实体停点尚待用户确认。该进度不等同全部实物验收通过。

对话延迟：两轮ASR1.093/1.395秒、完整LLM RPC1.940/1.833秒、TTS0.766/0.838秒。录音结束至软件SPEAKING约5.04/5.29秒；主生成等待为完整LLM回复，其次ASR。软件状态不代表扬声器物理首声，累计guard时间不可整项重复相加。

身份/语言：身份整句查询误进声纹样本的串扰已修复并加载。服务ready不等于本人KNOWN或已授权个人私库；本轮已登记人的视觉重识别、声纹/会话关联与个人记忆完整对话仍缺实物验收。

记忆：权威业务在板端。07:20只读聚合767轮/3391有效摘要/1待处理正文、quick_check通过；08:36新GUI进程memory.completed=86、discarded=0。不能把不同进程完成计数相减，也不能把profile数0误报成人脸库为空。个人权限联动及长时召回待验。

稳定性：业务时间锚定可用，系统持久NTP未同步。独立健康请求出现过3秒级长尾，原1秒时钟guard曾两次阻止UI启动，之后正常通过；不宣布问题已消失。整机下一次断电上电后自动恢复wide、相机来源绑定、GUI和轴的流程尚未验收。

后续顺序：先让转轴专用对话收齐新停点反馈；再在同一轮做视觉/本人KNOWN/声纹关联/个人记忆权限/完整语音播放的联合验收；之后按实测定位LLM交付、ASR和网络长尾，最后验证一次冷启动恢复。
实际证据和字段范围见project_progress_20261102/PROJECT_PROGRESS.json。全局状态中旧FAULT_OLD_CONTEXT、motor DISCONNECTED等过时字段已归档并按最新证据纠正，转轴细节后续以独立对话AXIS_CURRENT_HANDOFF.json为准。
'''
(HERE/'PROJECT_PROGRESS.txt').write_text(summary,encoding='utf-8')
p=OUT/'HANDOFF.txt';shutil.copy2(p,backup/p.name);p.write_text(summary+'\n以下为原阶段保留记录。\n\n'+p.read_text(encoding='utf-8'),encoding='utf-8')
project=OUT.parent.parent;shared=project.parent
note='项目职责已拆分：转轴专用对话“转轴跟随｜左侧停点优化”（01a19b64-8194-70e3-806b-03fa9a283918）持唯一转轴写权；原对话继续整体进程梳理。全局进度以deliverables/2026-11-02_5090_deployment/project_progress_20261102/PROJECT_PROGRESS.json及CHAT_COORDINATION.json为准，下面各次调参段落按其时间理解；最新转轴版本/实体反馈以专用对话AXIS_CURRENT_HANDOFF.json为准。\n'
for i,p in enumerate((shared/'AGENTS.md',shared/'README.md',project/'AGENTS.md',project/'README.md')):
    shutil.copy2(p,backup/(str(i)+'-'+p.name));text=p.read_text(encoding='utf-8')
    marker='<!-- 5090-project-progress-chat-split-20261102 -->';end='<!-- /5090-project-progress-chat-split-20261102 -->'
    assert marker not in text
    p.write_text(marker+'\n'+note+end+'\n\n'+text,encoding='utf-8')
print(json.dumps({'progress':str(HERE/'PROJECT_PROGRESS.txt'),'modules':len(rows),
    'axis_chat':coord['axis_thread']['thread_id'],'board_changes':False}))
