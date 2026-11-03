"""Record successful real enrollment separately from pending spoken identity test."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];ANALYSIS=ROOT.parent/'语言模型分析'
read=lambda n:json.loads((HERE/n).read_text(encoding='utf-8-sig'))
c,d,p,v,q,initial,obs=[read(n) for n in ('candidate.json','deployment.json','preflight.json','source_verification.json',
 'voice_host_probe.json','initial_diagnosis.json','live_observation.json')]
assert d['status']=='SPOKEN_IDENTITY_QUERY_DEPLOYED_AWAITING_REAL_USER'
assert d['database_hash_unchanged'] and d['camera_pid_preserved']
assert all(p[k] for k in ('real_models_passed','bootstrap_passed','widget_passed'))
assert q['status']=='PASS_REAL_ASR_ORIGINAL_TTS_BOARD_QUERY_REPLIES'
assert initial['last_operation']=={'action':'identity_enroll','state':'COMMITTED','db_version':14}
summary={'client_date':'2026-10-19','status':'SPOKEN_CURRENT_FACE_QUERY_DEPLOYED_REAL_USER_QUERY_PENDING',
 'actual_user_080_enrollment_passed':True,'actual_enrollment_committed_revision':14,
 'user_report':'认证成功了但是问我是谁不知道',
 'actual_spoken_identity_query_passed':None,'actual_new_query_listening_passed':None,
 'departure_return_recognition_passed':None,'different_person_test_passed':None,
 'pc_tests_passed':107,'linux_tests_passed':199,'new_query_tests_passed':13,
 'public_real_model_enroll_query_and_loss_passed':True,'real_asr_tts_relay_passed':True,
 'real_asr_question_intent_recording_passed':None,
 'ui_runtime':c['runtime'],'camera_runtime_preserved':c['source_runtime'],
 'pc_query_version':1,'client_query_capability':'current-face-v1','query_scope':'fresh_current_face',
 'exact_direct_question_intents_only':True,'llm_receives_camera_identity':False,
 'spoken_name_enters_normal_chat_history':False,'query_can_write_identity_database':False,
 'speaker_identity_verified':False,'liveness_implemented':False,
 'capture_current_target_and_revision_checked':True,'maximum_face_result_age_ms':3000,
 'unknown_lost_multiple_stale_faces_never_use_last_enrollment_name':True,
 'threshold':.8,'ambiguity_margin':.1,'threshold_changed':False,
 'database_before':d['database_before'],'database_after':d['database_after'],
 'database_hash_unchanged':True,'active_sources_verified':len(v['active_sources']),
 'camera_service_restarted':False,'preserved_source_config':d['preserved_source_config'],
 'initial_known_samples':initial['known_samples'],'post_deploy_known_samples':obs['known_samples'],
 'post_deploy_observation_samples':len(obs['samples']),
 'post_deploy_observation_not_human_query_acceptance':True,
 'photos_exported':False,'templates_exported':False,'names_exported_in_evidence':False,
 'rollback_backup':d['backup']}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'listening.json').write_text(json.dumps({'status':'AWAITING_REAL_USER_SPOKEN_IDENTITY_QUERY',
 'actual_user_080_enrollment_passed':True,'actual_spoken_identity_query_passed':None,
 'actual_new_query_listening_passed':None,'previous_user_feedback':'登记成功，但问我是谁不知道'},ensure_ascii=False,indent=2),encoding='utf-8')
text=f'''# “我是谁”接入当前人脸识别结果

2026-10-19用户报告0.80下登记成功，但问“我是谁”时不知道。板端已核实真实身份写入COMMITTED、库1身份/1模板/修订14，软件记录registered音频完整；无需重新登记。此前0.85的失败记录、旧库清空回执保留。

## 原因和当前行为

此前只有身份登记口令进入板端身份流程；“我是谁”走原27B普通聊天，摄像头的身份结果未接入该回答，登记台词又不会进入聊天记忆，因此模型无法从登记过程得到称呼。这是未接通的查询功能，不应归结为登记没有保存。

新增客户端明确声明 `X-Aura-Identity-Query: current-face-v1`，并在已有身份协议下只对直接问句“我是谁”“我叫什么名字”“你认识我吗”等走板端查询。普通聊天与旧客户端保持原路由。查询通过已有当前录音context/token和原OmniVoice16合成，27B不参与身份推断，不把姓名答复写入普通聊天历史，不增加额外ASR/LLM模型。

查询核对录音开始与ASR返回时的真实相机/服务、单张人脸、同轨迹代次、同身份库修订；当前识别必须KNOWN、结果属于当前人脸、源帧不超过3秒且匹配库中同ID称呼。结果过期、换轨/服务、多人、失脸、UNKNOWN、库变动或取消都不报旧名字。登记进行中只提示等待，不取消/授权/保存任何登记。来源仍是相机识别，没有说话者声纹/活体绑定，所以回答明确为“镜头前识别到的是某某”。这不是在证明说话者本人身份。

## 两个独立问题

初次诊断时10次当前相机采样均UNKNOWN；没有照片或姿态证据可判定当时用户是否正对镜头。新增路由不能提高同帧SFace分数，0.80和0.1间隔保持。当时识别不通过时，新回答仍应明确“现在还没有认出镜头前的人”，而不是把刚登记的名字当作当前人。相机识别稳定性与语音查询是否接通要分别验收。

## 验证和部署

- Windows107项通过；新查询13项复测通过。Linux199项通过，覆盖旧登记/自动语音/DPU跟踪约束及新查询的失效边界。
- 固定公开Lena、真实板端YuNet/对齐→Windows同SFace CPU、临时SQLite，完整登记→KNOWN→查询称呼→失脸不报姓名通过；逻辑时钟顺序驱动，不注入质量或姿态，不访问用户库。公开单图不能代替真人鲁棒性。
- 真实历史PCM经过原ASR/HTTP和原OmniVoice16，known/unknown/失脸三种合成板端查询回复通过。不是用户实际“我是谁”录音或板端听音；真实问句路由由可控转写的HTTP测试验证。
- PC8792空闲重载查询支持；只切换UI，原相机PID保持，0.80/0.1、DPU/ByteTrack、相机和音频配置不变。库部署前后1条/修订14、哈希不变。25份候选UI源码哈希已核对；相机仍运行旧目录，没有误称整套相机源码都已切换。
- 最后只读观测{len(obs['samples'])}次，KNOWN {obs['known_samples']}次。这不是一次真人问句验收。

## 使用与状态

点“开始对话”，一个人正对镜头稍停，说“汐蓝，我是谁？”；有有效匹配才回答称呼。身份仍保留，不需要重复登记。真人新查询、听音、离场重返和不同人误认均待后续反馈；原普通聊天长期个人记忆仍未实现。

活动UI `{c['runtime']}`；相机保持 `{c['source_runtime']}`。配置副本见 `effective_config/`，没有复制模型、用户数据库、模板、现场照片或录音到源码包。LLM数据仍D盘。

证据：`initial_diagnosis.json`、`tests_pc.log`、`tests_board.log`、`preflight.json`、`real_models.log`、`voice_host_probe.json`、`deployment.json`、`source_verification.json`、`live_observation.json`、`verification_summary.json`、`verified_source.zip`。

回退：结束对话后运行 `rollback.py`，仅恢复旧UI单位，不恢复/删除身份库、不改相机和阈值。旧客户端不会声明查询能力，新增PC接口保持兼容；如需PC源回退，改前源码在本目录before，需空闲重载8792。UI备份 `{d['backup']}`。
'''
(HERE/'README.md').write_text(text,encoding='utf-8')
marker='<!-- spoken-identity-query-20261019 -->'
block=marker+f'\n- 2026-10-19用户0.80真人登记已成功，板端确认COMMITTED，当前1身份/1模板/修订14，不能再称空库或登记待验证；用户“我是谁”不知道，根因为普通聊天没有接摄像头结果。已部署只读直接问句查询：UI `{c["runtime"]}`，相机仍 `{c["source_runtime"]}`/PID动态读取，PC8792 query_version1，客户端另声明current-face-v1，旧客户端/普通聊天原路由。查询核对录音开始/当前真实服务、单张同人脸轨迹、库修订及3秒内KNOWN源，库中ID和称呼一致才报“镜头前识别到的是名字”；UNKNOWN/多人/失脸/过期/变代/取消不取旧名，不发数据库动作，不把姓名进入普通聊天历史，未实现说话者绑定或个人长期记忆。初始10次相机均UNKNOWN，路由修复不证明识别稳定性。PC107、新查询13复测、Linux199、公开真实模型临时库查询/失脸及真实ASR/TTS合成查询回复通过，25份UI源哈希和相机/DPU/音频保留核对，库1/14哈希不变。真人新问句/听音/重返仍待验证。最新证据 `deliverables/2026-10-19_spoken_identity_query/README.md`、`verification_summary.json` 优先于旧空库/查询未实现表述；0.80/0.1及原语音模型保持，LLM数据D盘。\n<!-- /spoken-identity-query-20261019 -->\n\n'
path=ROOT/'AGENTS.md';raw=path.read_text(encoding='utf-8')
if marker not in raw:path.write_text(block+raw,encoding='utf-8')
note='> **2026-10-19 登记成功并接入“我是谁”：** 真人0.80登记COMMITTED，当前1条/修订14。新查询读取当前有效人脸身份，报“镜头前识别到的是某某”；没认出/多人/过期不报旧名。PC107/Linux199及公开模型/语音预检通过，只切UI，相机/阈值/库保持；真人新查询和重返仍待验证。[本轮状态与回退](deliverables/2026-10-19_spoken_identity_query/README.md)。\n\n'
path=ROOT/'README.md';raw=path.read_text(encoding='utf-8')
if not raw.startswith('> **2026-10-19 登记成功并接入“我是谁”：**'):path.write_text(note+raw,encoding='utf-8')
for name in ('threshold_080_verification_summary.json','threshold_080_listening.json'):
 path=ROOT/'deliverables/2026-10-19_threshold_calibration'/name;value=json.loads(path.read_text(encoding='utf-8'))
 value.update(status='REAL_USER_080_ENROLLMENT_PASSED_SPOKEN_QUERY_FOLLOWUP',actual_user_enrollment_passed=True,
  actual_board_listening_passed=None,registered_audio_complete=True,current_registered_count_after_user_enrollment=1,
  current_database_revision_after_user_enrollment=14,actual_spoken_identity_query_passed=None,
  latest_query_evidence=str(HERE/'README.md'))
 path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
report='我是谁接入当前人脸识别_20261019.md';(ANALYSIS/report).write_text(text+'\n完整证据：`'+str(HERE)+'`。\n',encoding='utf-8')
path=ANALYSIS/'README.md';raw=path.read_text(encoding='utf-8')
entry=f'## 最新：登记成功，“我是谁”接入摄像头结果\n\n[身份查询接入]({report})：真人0.80登记已COMMITTED，库1条/修订14；新只读问句用当前有效人脸身份回答，不让聊天模型猜姓名。查询预检通过，真人新问句/重返仍待反馈。\n\n'
if report not in raw:raw=raw.replace('# 语言模型分析统一入口\n','# 语言模型分析统一入口\n\n'+entry,1)
path.write_text(raw,encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
