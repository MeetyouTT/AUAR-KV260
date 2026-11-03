"""Record verified deployment facts and keep earlier user feedback as history."""
import json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
read=lambda name:json.loads((HERE/name).read_text(encoding='utf-8-sig'))
write=lambda path,value:path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
c=read('candidate.json');d=read('deployment.json');v=read('source_verification.json');p=read('preflight.json')
probe=read('voice_host_probe.json')
assert d['status']=='NATURAL_ENROLLMENT_DEPLOYED_AWAITING_REAL_USER_VALIDATION'
assert c['tests_passed'] and c['preflight_passed'] and all(p[k] for k in ('real_models_passed','bootstrap_passed','widget_passed'))
assert len(v['active_sources'])==17 and all(v['preserved'].values())
assert v['pc_health']['identity_voice_enrollment']['sampling_guidance_version']==2
assert probe['status']=='PASS_REAL_NATURAL_ENROLLMENT_ASR_TTS_RELAY_AND_ORIGINAL_27B_CHAT'
pc_count=int(re.search(r'(\d+) passed', (HERE/'tests_pc.log').read_text(encoding='utf-8-sig')).group(1))
linux_count=int(re.search(r'Ran (\d+) tests', (HERE/'tests_board.log').read_text(encoding='utf-8')).group(1))
c.update(activated=True,deployment_status=d['status']);write(HERE/'candidate.json',c)
summary={'client_date':'2026-10-19','status':d['status'],'active_runtime':c['runtime'],
    'pc_tests_passed':pc_count,'linux_tests_passed':linux_count,'active_sources_verified':17,
    'real_public_models_passed':True,'fixture_uses_logical_capture_clock':True,'fixture_pose_quality_injected':False,
    'real_asr_omnivoice_three_phase_relay_and_original_27b_passed':True,
    'gtk_synthetic_natural_progress_checked':True,'selection_window_minimum_ms':15000,'selection_minimum_frames':10,
    'ram_pool_maximum_frames':24,'heldout_consecutive_eligible_frames':5,'threshold':.85,'ambiguity_margin':.1,
    'threshold_changed':False,'selected_template_is_one_observed_vector':True,'failed_validation_retains_candidate':True,
    'new_track_requires_fixed_original_anchor_point85_and_gallery_margin':True,
    'confirmation_frame_dip_retains_ready_window_without_writing':True,
    'missing_face_immediately_hides_identity_and_preview':True,
    'database_revision_before':d['database_revision_before'],'database_revision_after':d['database_revision_after'],
    'database_hash_unchanged':not d['identity_database_modified'],'registered_count':d['enrolled_count'],
    'body_audio_model_config_preserved':v['preserved'],'llm_weights_remain_outside_shared_directory':True,
    'photos_exported':False,'templates_exported':False,'names_exported':False,'video_saved':False,
    'actual_user_natural_sampling_passed':None,'actual_board_listening_passed':None,'departure_return_recognition_passed':None,
    'previous_version_field_feedback':'field_feedback_iteration1.json',
    'previous_version_reached_confirm_update_name':True,
    'previous_version_confirmation_failed_and_later_detection_loss_reported':True,
    'limits':['Public image testing is not a real-user angle/lighting accuracy test.',
              'No guarantee all head angles meet unchanged 0.85 threshold.',
              'No liveness, active-speaker binding or personal long-term chat memory.']}
write(HERE/'verification_summary.json',summary)
write(HERE/'listening.json',{'client_date':'2026-10-19','version':'natural-motion',
    'actual_user_natural_sampling_passed':None,'actual_board_listening_passed':None,'departure_return_recognition_passed':None})
old=HERE.parent/'2026-10-19_multiframe_enrollment'
feedback='用户反馈：稍微动一下就识别不了，固定姿势采样太困难；要求慢慢自然转头，由系统从一段视频里自动选样。'
previous=json.loads((old/'verification_summary.json').read_text(encoding='utf-8-sig'))
previous.update(status='SUPERSEDED_AFTER_USER_REPORTED_FIXED_POSE_SAMPLING_DIFFICULTY',
    real_user_feedback=feedback,actual_user_sampling_passed=False,superseded_by=str(HERE/'verification_summary.json'))
previous['limits'][0]='Real user reported fixed-pose sampling difficulty; successful enrollment and re-entry were not verified.'
write(old/'verification_summary.json',previous)
listening=json.loads((old/'listening.json').read_text(encoding='utf-8-sig'))
listening.update(new_sampling_user_feedback=feedback,actual_user_sampling_passed=False)
write(old/'listening.json',listening)
block=('> **2026-10-19 自然转头自动选样已部署：** 看着镜头慢慢自然转头，系统从至少15秒画面中自动选清晰人脸，'
       '取消固定左右姿势；最多24份RAM候选，后续5份独立画面仍须逐份达到0.85及0.1间隔。'
       '失脸保留窗口，新轨迹先与固定起始人脸核对0.85及身份间隔；确认时一帧不合格保留选样，明确确认后才写身份库。'
       f'PC{pc_count}项、Linux{linux_count}项、真实模型/语音HTTP预检通过；'
       '部署库仍5条/修订8，真人自然转头、听音和重返识别待验证。'
       '[本轮状态与回退](deliverables/2026-10-19_natural_face_enrollment/README.md)。\n\n')
root_readme=ROOT/'README.md';raw=root_readme.read_text(encoding='utf-8-sig')
raw=re.sub(r'^> \*\*2026-10-19 自然转头自动选样已部署：.*?\n\n','',raw,count=1,flags=re.S)
root_readme.write_text(block+raw,encoding='utf-8')
agents=ROOT/'AGENTS.md';raw=agents.read_text(encoding='utf-8-sig')
instruction=('\n<!-- natural-face-enrollment-20261019 -->\n'
    '- 2026-10-19用户反馈固定左右姿势采样困难，要求自然慢转头、从视频自动筛查。已部署自然选样版：UI/相机`'+c['runtime']+'`，'
    'PC8792已重载，`identity_voice_enrollment.sampling_guidance_version=2`。至少15秒选样、至少10份合格帧、RAM最多24份，'
    '无左右姿势配额，选一个实际代表向量，后5份连续合格新帧逐份0.85且比其他身份高0.1；分数失败重置验证进度而保留选样，不绕过门槛。'
    '失脸立即隐藏身份/预览并暂停，选样窗口继续等待；新轨迹须以新合格SFace向量核对固定起始锚点>=0.85且比其他身份高0.1，才能绑定继续，锚点不滚动。'
    '同相机/服务/库版本和采样token必须保持；多人、相机/服务换代、库变动、超时禁止保存。确认时帧不合格或写入明确拒绝保留ready窗口并重新请求确认，不弱化写库条件。'
    '修复脸框裁剪边界关联，预测位移限制仅作用于人脸IoU，原人体DPU/ByteTrack和音频/模型参数保持。'
    f'明确确认前不写库，已有称呼更新仍需“确认更新登记”。PC{pc_count}项、Linux{linux_count}项、公开素材真实模型（无姿态标签注入，逻辑时钟顺序驱动）及真实OmniVoice16三段HTTP通过；'
    '仅预检，非真人听音/自然转头/重返验收。部署前后库5条/修订8且哈希不变。失败原因保留在健康状态RAM，不导出现场照片、模板或称呼。'
    '最新入口`deliverables/2026-10-19_natural_face_enrollment/README.md`和`verification_summary.json`，优先于下方固定姿势版本路径；'
    '后者真人反馈已补为采样困难，不再描述为完全没有用户反馈。LLM数据仍D盘。\n'
    '<!-- /natural-face-enrollment-20261019 -->\n')
if '<!-- natural-face-enrollment-20261019 -->' in raw:
    raw=re.sub(r'<!-- natural-face-enrollment-20261019 -->.*?<!-- /natural-face-enrollment-20261019 -->',
               lambda _:instruction.strip(),raw,count=1,flags=re.S)
else:raw=raw.replace('# 本项目工作约定','# 本项目工作约定\n'+instruction,1)
agents.write_text(raw,encoding='utf-8')
analysis=ROOT.parent/'语言模型分析'
report=('# 自然转头视频自动选样实施（2026-10-19）\n\n'
    '用户要求慢慢自然转头，由系统自己从一段视频挑选清晰人脸。新版已部署到`'+c['runtime']+'`。'
    '取消固定左右角度配额，至少15秒收集至少10份合格画面，最多在RAM保留24份候选；选实际代表特征后，'
    '再以5份后续合格新画面逐份验证0.85及0.1身份间隔。验证波动保留选样，只重新累计验证。'
    '失脸立即隐藏身份结果和预览，保留选样窗口；新轨迹须以合格新SFace特征匹配固定起始锚点0.85及0.1间隔后才能继续，锚点不滚动。'
    '多人/服务相机换代/库变化禁止继续。最后确认遇到帧波动保留选样并请求重新确认。\n\n'
    f'PC{pc_count}项、Linux{linux_count}项、公开图片真实YuNet/SFace及真实ASR/OmniVoice16三段提示和原27B聊天HTTP预检通过；'
    '公开图片使用逻辑时钟顺序驱动，没有注入姿态/质量标签，不能代替真人角度测试。部署身份库仍5条/修订8且哈希保持。'
    '真人自然转头、听音、离场重返仍待验证。仍为单模板识别，不能保证任意角度超过0.85。\n\n'
    '[完整流程、证据、限制和回退](../语音共享文件/deliverables/2026-10-19_natural_face_enrollment/README.md)。'
    '板端沿用CPU人脸模型，Win继续原语音模型；人体DPU/ByteTrack和所有LLM/ASR/TTS模型参数保持。'
    '不保存视频或默认导出照片，LLM权重/Ollama数据仍在D盘。\n')
(analysis/'自然转头视频选样实施_20261019.md').write_text(report,encoding='utf-8')
index=analysis/'README.md';raw=index.read_text(encoding='utf-8-sig')
entry=('## 最新：自然转头视频自动选样\n\n[自然转头视频选样实施](自然转头视频选样实施_20261019.md)：'
    f'已替代固定左右姿势流程，从至少15秒视频画面自动选清晰人脸，保留0.85和明确确认。PC{pc_count}项、Linux{linux_count}项及真实模型/语音HTTP预检通过；'
    '部署库5条/修订8未变，真人自然转头和重返识别待验证。\n\n')
raw=re.sub(r'## 最新：自然转头视频自动选样\n.*?(?=\n## |\Z)','',raw,count=1,flags=re.S)
index.write_text(raw.replace('# 语言模型分析统一入口\n','# 语言模型分析统一入口\n\n'+entry,1),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
