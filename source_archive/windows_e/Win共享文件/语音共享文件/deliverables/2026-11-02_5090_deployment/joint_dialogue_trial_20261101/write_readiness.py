"""Assemble the current read-only engineering assessment from actual evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
OUT=HERE.parent
now=datetime.datetime.now(datetime.timezone.utc)
platform=json.loads((HERE/'platform_live_01.json').read_text(encoding='utf-8'))['board_result']
perception=json.loads((HERE/'perception_review/PERCEPTION_VERDICT.json').read_text(encoding='utf-8'))
model=json.loads((HERE/'model_health_current.json').read_text(encoding='utf-8'))
dialogue=json.loads((HERE/'dialogue_review/current_source_receipt.json').read_text(encoding='utf-8'))['board_result']
assert platform['boot_id']==perception['board_boot_id']==dialogue['boot_id']
assert perception['component_files_verified']==dialogue['startup_component_count']==380
assert all(item['current_startup_pinned'] for item in dialogue['files'].values())
assert model['ok'] and model['tts_ready'] and model['voice_alive'] and not model['voice_error_present']
assert model['model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and model['num_step']==16
assert perception['identity_config_matches_latest_recorded_user_choice']
assert perception['effective_identity_policy']=={'threshold':0.5,'ambiguity_margin':0.1,'result_ttl_ms':3000}
assert platform['axis_ready_for_joint_trial'] is False
components={
    'vision':{'software_ready':True,'observation':'confirmed body target in3/3 samples; valid face target in1/3',
        'body_target_confirmed_samples':perception['visual_body_target_confirmed_samples'],
        'valid_face_samples':perception['valid_face_target_samples']},
    'doll_avatar':{'software_ready':True,'main_page':True,'visible_native_frames_advancing':True,
        'audio_output_software_ready':True,'runtime_faults':perception['gui_runtime_faults'],
        'current_trial_acoustic_playback_and_mouth_sync_accepted':False},
    'dialogue':{'model_backend_ready':True,'entry_mode':dialogue['configuration']['entry_mode'],
        'asr_variant':dialogue['configuration']['asr_variant'],'listening_currently_paused':True,
        'voice_first_guest_single_turn_can_be_tried':True,'current_human_end_to_end_turn_accepted':False,
        'source_of_business_and_persistence':'board'},
    'identity':{'model_chain_ready':True,'fresh_known_samples':perception['identity_fresh_known_samples'],
        'fresh_unknown_samples':perception['identity_fresh_unknown_samples'],
        'no_face_target_samples':perception['identity_no_face_target_samples'],
        'current_known_person_recognition_demonstrated':False,
        'same_capture_visual_context_is_bound_to_dialogue_job':True,
        'production_identity_query_and_enrollment_handlers_present':True,
        'face_match_is_private_profile_permission':False,
        'private_profile_permission_policy':'existing operator authorization and live boot/session-bound grant',
        'policy':perception['effective_identity_policy'],'policy_matches_latest_user_choice':True,
        'policy_authorization_source':'deliverables/2026-10-19_threshold_050/README.md',
        'gallery_empty_inferred':False},
    'axis':{'ready':False,'firmware':platform['firmware'],'state':platform['manual_pan']['state'],
        'readback_available':platform['manual_pan']['readback_available'],'following':False,
        'wide_candidate_installed_manifest_verified':True,'reviewed_real_platform_switch_backend_ready':False,
        'current_boot_position_direction_and_short_motion_accepted':False}}
evidence_paths=['platform_live_01.json','model_health_current.json',
    'perception_review/PERCEPTION_VERDICT.json','perception_review/perception_current_02.json',
    'perception_review/identity_policy_provenance_01.json','perception_review/PROVENANCE_NOTE.txt',
    'dialogue_review/current_source_receipt.json','dialogue_review/source_index.json']
evidence=[{'path':p,'sha256':hashlib.sha256((HERE/p).read_bytes()).hexdigest()} for p in evidence_paths]
result={'schema':'aura-five-component-dialogue-readiness-1','updated_utc':now.isoformat(),
    'board_boot_id':platform['boot_id'],'startup_sha256':perception['startup_sha256'],
    'full_five_component_trial_ready':False,'basic_guest_dialogue_trial_conditions_present':True,
    'actual_trial_executed':False,'human_audio_or_images_archived':False,
    'board_configuration_or_firmware_changed':False,'components':components,
    'blocking_full_acceptance':['axis platform remains benchmark with FAULT and no readback',
        'current observation has no demonstrated known-person recognition',
        'new-host human capture-to-complete-playback-and-mouth-sync turn not yet accepted'],
    'next_sequence':['complete and review the real wide-platform recovery transaction without losing Native counters',
        'restore current-boot platform and owner bindings, validate ID/STOP and physical reference/direction',
        'verify fresh known-person recognition with an already registered person in view',
        'run one human turn while visual/identity context, avatar/audio and separately enabled face-follow are observed',
        'accept full playback receipt and user observations, then pause listening and stop following'],
    'evidence':evidence}
target=HERE/'FULL_FLOW_READINESS.json'
assert not target.exists();target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
text='''五模块对话协作评估（洛杉矶2026-11-01）

当前不能宣称已具备包含真实转轴、已知身份确认的五模块全流程验收条件。
可以准备一次普通guest语音对话 + 视觉上下文 + 原玩偶音画的基本单轮试跑；本次只做了状态与源码检查，聆听仍暂停。

视觉：相机/检测继续推进，3次采样都有确认人体目标；人脸目标仅1次有效，其余2次无脸目标。
玩偶：主页面、原角色和可见动画正常，运行故障0，MCP01音频输出IDLE_READY；本轮尚未实际说话或验口型同步。
对话：原27B/OmniVoice16健康，权重驻留，板端ASR/业务路径及完整播放ACK接入存在；新主机公开LLM/TTS先前已通过，但不是一次真人整轮听音验收。
身份：模型链ready，采样为1次新鲜UNKNOWN、2次无脸目标，KNOWN=0；不能据此说已认出用户，也不能推断图库为空。
转轴：当前kv260-benchmark-b4096.bit.bin，manual_pan=FAULT、无读回、跟随false；安装了wide候选不等于当前已加载和验收。

实际协作关系
录音时的视觉快照与同一clip/meta/scope绑定进入同一对话job，并送入板端speaker analysis；身份查询/登记handler已由生产factory注入。
普通voice_first对话可按guest进行，已知人脸不自动成为个人档案权限。个人授权继续由原operator及同boot/session活grant约束，这是正常权限设计。
原回复进入音频播放、表情/口型/角色呈现，完整播放ACK控制回合收尾。真实人脸跟随由独立的视觉页按钮启动，不会因为开始聆听就自动启动。

身份参数核对
当前0.50、分差0.10、TTL3000ms符合最后明确用户选择。deliverables/2026-10-19_threshold_050/README.md记录“现在那就调成0.5”，明确更新旧0.80/0.85约定。
旧23pin、新24pin和当前相机运行选择使用同一身份配置SHA398ece6a4d5d81076c9a4f9f40a43e97cedd469e0b47e3a835e589a2255ca6e3，部署重绑定未改该值。
本次初始诊断沿用旧0.85的预期已更正，原失败观察保留；不将它列为当前参数不合规或通过改阈值解决UNKNOWN。

当前可用的基本单轮操作（不包含转轴验收）
1. 保持当前跟随关闭，在镜头前观察视觉与身份状态；未识别时按guest记录，不口头认领个人权限。
2. 在主页面点击“开始聆听”，等待原麦克风就绪提示后说一句公开测试问题，例如“你好，请简单介绍一下你自己”。
3. 观察一次录音/ASR、思考、回答播放，听音并看字幕/口型及角色动画；同时确认视觉仍推进。
4. 等原完整播放完成回执后，点击“暂停聆听”，确认PAUSED、mic=false、无播放。单纯取消当前轮可能500ms后重新聆听，不能替代暂停。
5. 在板端RAM比较同轮归属及ACK是否比开始前更新，只记录同轮匹配/新ACK/committed布尔、阶段耗时、样本校验结果、口型/帧数、视觉/身份枚举和听音反馈；不额外保存照片、声纹、模板或真实对话副本。

完整五模块试验前的顺序
先完成可审阅的真实平台恢复执行器，以原正常停服路径封存当前Native最终检查点；成套恢复wide、核本boot ID/STOP、机械参考与方向，再恢复相机与实际GUI绑定。
再让已登记的人在镜头前完成新鲜KNOWN验证；具备这些条件后，才启用本轮视觉跟随并进行一次真人对话、口型/音频和转轴的联合观察。
旧boot的PID、位置、STOP、方向或已消费检查点不代替本轮证据。当前没有为此次评估停止相机、切换PL、开启麦克风或发转轴动作。

当前总表：FULL_FLOW_READINESS.json；原始证据在perception_review、dialogue_review及platform_live_01.json。
'''
(HERE/'READINESS.txt').write_text(text,encoding='utf-8')

current_path=OUT/'DEPLOYMENT_CURRENT.json'
current=json.loads(current_path.read_text(encoding='utf-8'))
backup=HERE/'deployment_current.before_joint_assessment.json';assert not backup.exists();shutil.copy2(current_path,backup)
current.update(joint_dialogue_readiness='joint_dialogue_trial_20261101/FULL_FLOW_READINESS.json',
    full_five_component_trial_ready=False,basic_guest_dialogue_trial_conditions_present=True,
    known_identity_confirmed_in_current_observation=False,
    identity_policy=perception['effective_identity_policy'],identity_policy_matches_latest_user_choice=True,
    joint_assessment_updated_utc=now.isoformat())
if 'known-person recognition in current joint trial' not in current['remaining']:
    current['remaining'].append('known-person recognition in current joint trial')
current_path.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
handoff=OUT/'HANDOFF.txt'
shutil.copy2(handoff,HERE/'handoff.before_joint_assessment.txt')
prefix='''五模块协作评估补充（洛杉矶2026-11-01）：
当前基本guest语音/视觉上下文/角色音画具备试跑条件，尚未执行本次真人整轮；含转轴和已知身份的完整五模块暂不具备验收条件。
实时轴为benchmark/FAULT/无读回；视觉人体目标有效，但本次没有新鲜KNOWN身份。身份0.50/0.10/3000符合后来明确用户授权，并非本次部署改坏。
完整结论与操作路线：joint_dialogue_trial_20261101/READINESS.txt、FULL_FLOW_READINESS.json。页面/模型既有通过记录继续有效；本次未开麦、播放或运动。

'''
handoff.write_text(prefix+handoff.read_text(encoding='utf-8'),encoding='utf-8')
print(json.dumps({'full_five_component_trial_ready':False,'basic_trial_conditions_present':True,
    'report':str(HERE/'READINESS.txt'),'sources_verified':len(dialogue['files'])}))
