"""Record only observed deployment/tests; keep human enrollment pending."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];ANALYSIS=ROOT.parent/'语言模型分析'
existing=HERE/'verification_summary.json'
if existing.exists() and json.loads(existing.read_text(encoding='utf-8')).get('actual_user_registration_passed') is False:
    raise SystemExit('Retaining real-user failure evidence; do not replace it with preflight-only pending status.')
read=lambda name:json.loads((HERE/name).read_text(encoding='utf-8-sig'))
c,d,p,v,probe,coexist,obs=[read(n) for n in ('candidate.json','deployment.json','preflight.json',
 'source_verification.json','feature_probe.json','coexistence.json','live_observation.json')]
assert d['status']=='WINDOWS_FACE_FEATURES_DEPLOYED_AWAITING_REAL_USER_VALIDATION'
assert all(p[k] for k in ('real_models_passed','bootstrap_passed','widget_passed'))
assert coexist['status']=='PASS_REAL_ORIGINAL_VOICE_AND_CPU_FEATURE_COEXISTENCE'
assert len(v['active_sources'])==22 and all(v['preserved'].values())
report={'client_date':'2026-10-19','status':'DEPLOYED_PREFLIGHT_PASS_REAL_USER_PENDING',
 'active_runtime':c['runtime'],'pc_tests_passed':74,'linux_tests_passed':188,
 'active_sources_verified':22,'backend':'WINDOWS_CPU_SFACE_ORT','model_unchanged':True,
 'public_cross_backend_cosine_min':probe['cross_backend_cosine_min'],
 'public_wired_feature_median_ms':probe['wired_median_ms'],
 'public_wired_feature_max_ms':probe['wired_max_ms'],
 'voice_cpu_coexistence_passed':True,'voice_cpu_coexistence_busy_samples':coexist['while_voice_busy'],
 'combined_request_and_name':True,'upfront_explicit_confirmation':True,
 'replacement_requires_explicit_update':True,'automatic_validation_cue_without_response':True,
 'automatic_save_after_heldout_validation':True,'final_spoken_confirmation_required':False,
 'threshold':.85,'ambiguity_margin':.1,'threshold_changed':False,
 'selection_minimum_ms':15000,'ram_maximum_candidates':24,'heldout_frames':5,
 'sampling_failure_numeric_diagnostics':True,'database_hash_unchanged_during_deployment':True,
 'database_revision_before':d['database_revision_before'],'database_revision_after':d['database_revision_after'],
 'registered_count':d['enrolled_count'],'preserved_source_config':v['preserved'],
 'actual_user_registration_passed':None,'actual_board_listening_passed':None,
 'departure_return_recognition_passed':None,'previous_simple_version_human_result':'FAILED_TIMEOUT_COLLECT10_VALIDATE0',
 'user_clarification':'等待验证时一直在慢慢转头',
 'live_observation_known_samples':obs['known_samples'],'live_observation_samples':len(obs['samples']),
 'live_observation_face_target_samples':obs['face_target_samples'],
 'live_observation_is_not_enrollment_acceptance':True,
 'images_persisted':False,'full_frames_transferred_to_feature_service':False,'templates_exported':False,
 'gpu_used_for_sface':False,'rollback_backup':d['backup'],
 'limits':['Same-model CPU offload changes latency, not same-frame recognition accuracy.',
           'Public single-image tests cannot establish human pose robustness at 0.85.',
           'No liveness or verified speaker-to-face binding.']}
(HERE/'verification_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'listening.json').write_text(json.dumps({'status':'AWAITING_NEW_REAL_USER_FEEDBACK',
 'actual_user_registration_passed':None,'actual_board_listening_passed':None,
 'previous_feedback':'验证不通过；等待验证时一直在慢慢转头'},ensure_ascii=False,indent=2),encoding='utf-8')
readme=f'''# Windows CPU人脸特征与自动验证提示

2026-10-19已部署，真人登记/听音/重返仍待新一轮反馈。上一版真人结果是选样达到10份、验证未完成并超时，用户确认验证时一直慢慢转头；不能把本轮公开素材通过当作真人修复验收。

## 当前流程

点击开始对话，说“帮我登记身份，我叫原来的称呼”。开头复述后明确确认一次；已有同名称呼需“确认更新登记”。之后看着镜头自然慢转头，至少15秒内自动挑选清晰人脸。选样后自动播“清晰人脸已选好。请自然看向镜头，稍停几秒，我再确认一下。”不需要回答或点击，后续五份新合格帧达到原0.85和0.1身份间隔才自动保存，只有匹配COMMITTED回执才播成功。

修复了简化版连这句验证提示也抑制的问题；开头确认、最后自动验证/保存的授权和采样token约束保持。

## 计算路径

板卡YuNet找脸、五点对齐、112×112裁剪与质量筛选 → 既有有线LAN8792的独立CPU特征接口 → 同一固定SHA的SFace、ORT CPU → 板端归一化、身份比对/采样/授权/SQLite保存。人体YOLOX-Nano/ByteTrack、DPU/FPGA、相机和声音播放配置保持；原Paraformer、27B/IQ4_XS、OmniVoice16、五项延迟选项保持。

只发送当前112×112人脸PNG，单次最多64KiB，不发送全身/全幅图，不落盘或记录照片/视频/向量。请求与结果绑定权重版本、图像SHA、相机、轨迹代次、源帧/采集时间和随机请求；650ms超时、回复错配或目标/库变化一律拒用，没有弱匹配回退。电脑端独立非排队锁，不与长语音请求共用推理锁。

采样仍最多24份RAM候选，选择一个实际观测代表向量、五份独立连续验证，未新增多模板、均值特征或放宽角度/质量/匹配条件。特征快了不等于同帧分数提高；严格0.85下的真人角度鲁棒性仍需验证。

## 验证与数据

- Windows74项、Linux188项通过；Windows真实模型和真实HTTP检查在Windows运行，板卡不安装Windows主机依赖。首次错误地把该测试列入板端的日志保留为 `tests_initial_host_import_error.log`。
- 固定公开Lena真实板卡YuNet→Windows SFace→临时库完整自动登记、识别、失脸清除，以及隐藏GTK人脸窗口通过。使用逻辑时钟顺序驱动，不注入质量或姿态，不接触用户库。
- 公开人脸有线请求16次中位{probe['wired_median_ms']:.2f}ms，最大{probe['wired_max_ms']:.2f}ms；板卡同模型单次{probe['board_single_local_ms']:.2f}ms。跨后端余弦{probe['cross_backend_cosine_min']:.15f}。这是小样本特征处理测量，不是整机识别/语音延迟承诺。
- 真实ASR/原27B/OmniVoice16 HTTP与独立CPU特征同时运行通过；语音busy期间{coexist['while_voice_busy']}次特征成功。登记回复为合成板端测试信号，不是真人登记；未在玩偶播放测试音。
- 部署库仍{d['enrolled_count']}条、修订{d['database_revision_after']}且哈希未变；权限0600。22份活动源码哈希及相机/人体跟踪/音频配置核对通过。
- RAM健康状态增加质量跳帧、轨迹恢复拒绝、验证分数/间隔拒绝、最佳连续通过数与最近24帧分数；失败后保留数值统计，不保留照片、模板或称呼。
- 最后20秒只读观察{len(obs['samples'])}次，有人脸目标{obs['face_target_samples']}次、KNOWN {obs['known_samples']}次，采样未启动。目标仍有短暂丢失，不能把加载/提速称为真人识别成功；观察的实际姿态不确定。

证据：`tests_pc.log`、`tests_board.log`、`preflight.json`、`real_models.log`、`feature_probe.json`、`voice_host_probe.json`、`coexistence.json`、`deployment.json`、`live_observation.json`、`source_verification.json`、`verification_summary.json`。源码ZIP只含小型源码/有效配置，不包含模型、环境、数据库、录音或现场照片。

## 活动路径与回退

- UI/相机：`{c['runtime']}`。
- 当前备份：`{d['backup']}`。结束对话后运行本目录 `rollback.py` 恢复切换前的板端单位，不删除或恢复用户身份库。
- 第一次CPU切换前的纯板端SFace回退备份在 `initial_cpu_deployment.json` 的backup字段。若需要直接恢复纯板端路径，使用该文件对应备份；当前rollback恢复到第一次CPU版。
- 8792原语音服务已空闲重载；回退板端后新增特征接口不再接收板端图像。原PC源码备份在 `before`；旧模型及历史归档保留。

之前的[失败诊断](../2026-10-19_validation_diagnosis/README.md)保留。个人持久聊天记忆、活体检测和说话者人脸绑定未在本轮实现。LLM权重与Ollama数据仍D盘。
'''
(HERE/'README.md').write_text(readme,encoding='utf-8')
analysis='身份验证失败与CPU提速_20261019.md'
(ANALYSIS/analysis).write_text(readme+'\n完整证据目录：`'+str(HERE)+'`。\n',encoding='utf-8')
latest='''<!-- windows-face-features-20261019 -->
> **2026-10-19 人脸特征CPU提速与验证提示已部署：** 同一SFace转Windows CPU，板卡仍独立找脸/裁脸/比对/存库，只有112×112人脸走有线LAN。公开素材往返中位约18ms、两端输出一致；Windows74项/Linux188项及真实模型、原语音共存预检通过。补回选样后自动“看向镜头稍停”提示，无需回答或末尾确认。0.85/0.1及原DPU/ByteTrack/27B/OmniVoice16保持，库5条/修订8未变。上一版真人验证已失败，当前真人登记与重返仍待验收。[本轮状态与回退](deliverables/2026-10-19_windows_face_features/README.md)。
<!-- /windows-face-features-20261019 -->

'''
file=ROOT/'README.md';raw=file.read_text(encoding='utf-8');raw=raw.replace('真人简化流程待验证','真人反馈验证失败，采样达到10份后超时')
if '<!-- windows-face-features-20261019 -->' not in raw:file.write_text(latest+raw,encoding='utf-8')
block=f'''<!-- windows-face-features-20261019 -->
- 2026-10-19当前活动UI/相机 `{c['runtime']}`，PC8792同一SFace/ORT CPU特征就绪，板卡只发送瞬时112×112对齐脸，不保存/传全幅或导出模板。原0.85/0.1、单实际代表模板/后5份独立验证、固定锚点/源帧和授权约束保持，网络650ms超时或上下文错配拒用。Windows74/Linux188、公开真实模型临时库、语音CPU共存、22份活动源及配置校验通过，库5条/修订8哈希未变；公开往返中位18ms，不当真人精度证明。用户上一版简化登记明确验证失败，collect10/validate0后超时，并确认“一直在慢慢转头”；新版本补回一次自动sample_validate提示看向镜头稍停，不要再说正式流程完全没有中间提示，但无需用户回答或最后确认。失败RAM新增分数/间隔/质量/恢复诊断。真人本版登记、听音、离场重返仍待验证。最新证据和回退 `deliverables/2026-10-19_windows_face_features/README.md`、失败诊断 `deliverables/2026-10-19_validation_diagnosis/README.md` 优先于下方旧路径与待验收表述。原视觉DPU/ByteTrack、原27B/ASR/OmniVoice16及参数保持；LLM数据仍D盘。
<!-- /windows-face-features-20261019 -->

'''
file=ROOT/'AGENTS.md';raw=file.read_text(encoding='utf-8')
raw=raw.replace('真人简化登记/听音/重返仍待验证','真人简化登记已反馈验证失败（collect10/validate0超时），听音/重返未验收')
if '<!-- windows-face-features-20261019 -->' not in raw:file.write_text(block+raw,encoding='utf-8')
file=ANALYSIS/'README.md';raw=file.read_text(encoding='utf-8')
entry=f'## 最新：人脸验证失败与Windows CPU提速\n\n[失败诊断与本轮部署]({analysis})：上一版真人验证超时且一直慢转头；已接入同一SFace CPU后端并补回自动看镜头提示，保留0.85，真人本版结果待验收。\n\n'
if analysis not in raw:raw=raw.replace('# 语言模型分析统一入口\n','# 语言模型分析统一入口\n\n'+entry,1)
raw=raw.replace('PC109项、Linux183项及真实模型/语音预检通过，0.85保持，真人流程待验证。','PC109项、Linux183项及预检通过，0.85保持；真人随后反馈验证失败，collect10/validate0后超时。')
file.write_text(raw,encoding='utf-8')
old=ROOT/'deliverables/2026-10-19_simple_face_enrollment/README.md'
raw=old.read_text(encoding='utf-8');note='> 真人后续结果：验证未通过，collect10/validate0后超时。用户表示一直慢慢转头。当前后续部署和证据见[CPU提速与自动验证提示](../2026-10-19_windows_face_features/README.md)。\n\n'
if not raw.startswith('> 真人后续结果：'):old.write_text(note+raw,encoding='utf-8')
feedback=ROOT/'deliverables/2026-10-19_validation_diagnosis/feedback.json';f=json.loads(feedback.read_text(encoding='utf-8'))
f['user_validation_motion']='一直在慢慢转头';feedback.write_text(json.dumps(f,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
