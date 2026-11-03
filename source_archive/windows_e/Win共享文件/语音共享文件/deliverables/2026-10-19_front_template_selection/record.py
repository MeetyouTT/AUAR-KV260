"""Record the steady diagnosis and tested policy; do not imply old template repaired."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
read=lambda n:json.loads((HERE/n).read_text(encoding='utf-8'))
c,d,v,p=[read(n) for n in ('candidate.json','deployment.json','source_verification.json','preflight.json')]
assert d['status']=='FRONTAL_TEMPLATE_POLICY_LOADED_EXISTING_IDENTITY_PRESERVED'
assert d['database_hash_unchanged'] and d['ui_pid_before']==d['ui_pid_after']
assert all(p[k] for k in ('real_models_passed','bootstrap_passed','widget_passed'))
assert v['camera_policy']=='frontal_medoid_v1'
assert '145 passed' in (HERE/'tests_pc.log').read_text(encoding='utf-8')
assert 'Ran 207 tests' in (HERE/'tests_board.log').read_text(encoding='utf-8')
prior=HERE.parent/'2026-10-19_identity_query_routing'
steady=json.loads((prior/'face_consistency_steady.json').read_text(encoding='utf-8'))
summary={'client_date':'2026-10-19','status':'FRONTAL_TEMPLATE_POLICY_LOADED_ORIGINAL_IDENTITY_AWAITS_EXPLICIT_UPDATE',
 'user_steady_check_completed':True,'steady_face_consistency':steady,
 'diagnosis':'steady current faces agree at 0.896496–0.969408 but score 0.705980–0.754973 against saved template',
 'old_saved_template_pose_known':False,
 'source_defect':'pose-unaware medoid and held-out validation could certify a nonfrontal template',
 'template_policy':'frontal_medoid_v1','front_yaw_ratio_limit':.22,'front_roll_limit_degrees':15,
 'minimum_front_candidates':3,'saved_observed_templates_per_identity':1,
 'collection_ms':15000,'maximum_pool_frames_ram':24,'independent_later_front_validation_frames':5,
 'threshold':.8,'ambiguity_margin':.1,'threshold_or_margin_lowered':False,
 'original_fixed_anchor_recovery_and_db_revision_checks_preserved':True,
 'old_identity_automatically_replaced':False,'explicit_spoken_update_still_required':True,
 'pc_tests_passed':145,'linux_tests_passed':207,
 'original_real_public_models_temporary_store_and_ui_preflight_passed':True,
 'new_policy_actual_user_update_passed':None,'new_policy_actual_user_return_recognition_passed':None,
 'camera_runtime':c['runtime'],'ui_config_preserved':c['old_ui_config'],
 'camera_pid':v['camera_pid'],'ui_pid_preserved':True,'voice_host_restarted':False,
 'database_before':d['database_before'],'database_after':d['database_after'],'database_hash_unchanged':True,
 'camera_and_dpu_config_preserved_except_identity_config_path':True,
 'photos_templates_or_names_exported':False,'llm_storage_stays_external':True,
 'rollback_backup':d['backup']}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'listening.json').write_text(json.dumps({'status':'WAITING_FOR_USER_EXPLICIT_ORIGINAL_IDENTITY_UPDATE',
 'actual_user_new_policy_enrollment_passed':None,'actual_user_new_policy_return_recognition_passed':None},indent=2),encoding='utf-8')
text=f'''# 正脸模板选择及独立正脸验证

用户已完成静止正脸检查：5帧彼此相似度0.896496～0.969408，中位0.936844；与当前已保存模板0.705980～0.754973，0帧达到0.80。这次静止数据比之前自然活动段稳定，当前误拒绝更集中在模板/当前输入差异；没有旧登记图片或姿态记录，不能断言旧模板就是侧脸。

源码中确认的缺口：自然15秒视频虽然收集多帧，最终只保存一份实际代表向量。原medoid在所有合格姿态中投票，清晰侧脸可能占多数或将正脸挤出24份RAM池；独立验证也接受yaw比例0.38的转头姿态，提示看镜头并未由姿态检查保证。

新策略保持自然采集、原15秒/10份最低采样及24份RAM上限。池内优先保留合格正脸，以五点比例abs(yaw)≤0.22、abs(roll)≤15度作几何提示（不是校准的头姿模型）；至少3份正脸，从最正面的最多5份中选一份实际medoid，侧脸不参与该投票。原窗口正脸不足时，照常进入验证、触发原有看镜头语音，再自动补足正脸；补采选择帧不算验证帧。随后5份更晚的新正脸逐份达到0.80及0.1图库分差才可保存，侧脸会清掉这轮连续验证进度。未平均向量、未增加模板数量或最大值多模板匹配，原固定起始锚点恢复/目标代次/服务相机/库版本/明确更新确认保持。

## 验证及加载

- Windows145项通过，2项Linux专用用例在板端运行；Linux207项通过。新用例重现“侧脸多数、正脸与侧脸仅0.72相似”时仍选正脸，验证用5份后续正脸；侧脸无法完成验证，清晰侧脸不能挤掉仅有正脸。临时SQLite集成用例登记后新正脸KNOWN、原侧脸UNKNOWN，没有把放松门槛当作修复。
- 公开Lena及原真实YuNet/SFace/Windows CPU链路、临时库完整登记→KNOWN→语音查询→失脸预检通过；真实GUI组件预检通过。公开素材/逻辑时钟不是真人鲁棒性验收。
- 只重载相机身份运行目录到 `{c['runtime']}`；相机PID {v['camera_pid']}，原DPU/ByteTrack及相机配置保持（身份配置路径指向新候选）。UI仍 `{c['old_ui_config']}`，PID不变；PC8792未重启，原Paraformer/27B/OmniVoice16/5项延迟开关保持。
- 用户库前后1身份/1模板/修订14、哈希不变，0.80/0.1保持。静止检查照片、向量与姓名未保存或导出；LLM权重仍D盘。

## 需要一次原身份更新

这次软件加载不会改写旧模板，也不能让旧模板自动变好。点“开始对话”，说“帮我登记身份，我叫……”（填上次登记称呼）；玩偶复述后说“确认更新登记”。按原提示自然看镜头，听到验证提示后正对稍停，系统自动选正脸、取后续帧验证、保存并播报。无需末尾确认或新建另一身份。更新后再问“我是谁”，随后离场重返验证。

当前为**新版加载、用户更新/真人重返待验收**。只改善正脸模板选择和正脸验证，不承诺任意侧脸角度都能认出，也不把UI就绪、公开模型预检当作真人通过。

证据：`../2026-10-19_identity_query_routing/face_consistency_steady.json`、`pose_probe.json`、`tests_pc.log`、`tests_board.log`、`preflight.json`、`deployment.json`、`source_verification.json`、`verification_summary.json`、`verified_source.zip`。

回退：结束对话且没有登记任务后运行本目录 `rollback.py`，只恢复相机unit，保留当前身份库和UI；不恢复已删除身份、不还原任何生物模板。备份 `{d['backup']}`。
'''
(HERE/'README.md').write_text(text,encoding='utf-8')
marker='<!-- front-template-selection-20261019 -->'
block=(marker+'\n- 2026-10-19用户已完成静止正脸检查，5帧彼此0.896496～0.969408、对现模板0.705980～0.754973，均低于0.80；当前特征稳定，旧模板姿态未知，不能断言旧模板是侧脸。'
 '已修复自然视频模板选择忽略姿态及验证允许较大转头的源码缺口：24RAM池保护正脸，abs(yaw五点比例)<=0.22/roll<=15，至少3份正脸、最正面最多5份中选一份实际medoid，后5份独立新正脸逐份0.80/0.1；正脸不足用原验证语音自动补采，选择帧不算验证。'
 '原15秒/10份、单模板、固定原始锚点恢复/同服务相机轨迹/库修订与明确更新确认保持。'
 f'Windows145/Linux207及原真实公开模型/临时库/UI预检通过；相机运行 `{c["runtime"]}`、PID动态读取，UI仍fa8e候选且PID保持，PC8792未重启，原DPU/ByteTrack/语音模型和参数保持。'
 '库1身份/1模板/修订14哈希不变，未自动更新旧模板。新版需用户按原称呼发起并明确确认更新，再验收我是谁及离场重返；不能把新策略加载称真人修复通过。'
 '最新证据 `deliverables/2026-10-19_front_template_selection/README.md`、verification_summary.json。LLM数据D盘，照片/模板/姓名不默认导出。\n<!-- /front-template-selection-20261019 -->\n\n')
path=ROOT/'AGENTS.md';raw=path.read_text(encoding='utf-8')
if marker not in raw:path.write_text(block+raw,encoding='utf-8')
path=ROOT/'README.md';raw=path.read_text(encoding='utf-8')
note=('> **2026-10-19 正脸模板选择修复已加载：** 静止正脸彼此0.90～0.97、对旧模板0.71～0.75；现优先选清晰正脸，并取5份新正脸验证。'
 'Windows145/板端207项和原模型预检通过，原身份1条/修订14保留；需用户按原称呼确认更新一次，再验收识别。'
 '[本轮证据与回退](deliverables/2026-10-19_front_template_selection/README.md)。\n\n')
if not raw.startswith('> **2026-10-19 正脸模板选择修复已加载：**'):path.write_text(note+raw,encoding='utf-8')
path=prior/'verification_summary.json';old=json.loads(path.read_text(encoding='utf-8'))
old.update(steady_face_check_status='COMPLETED_STABLE_CURRENT_FACE_BELOW_TEMPLATE_THRESHOLD',
 steady_face_consistency_read_only=steady,latest_template_selection_evidence=str(HERE/'README.md'))
path.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
path=prior/'README.md';raw=path.read_text(encoding='utf-8')
note='> 后续静止正脸检查已完成：彼此0.90～0.97、对旧模板0.71～0.75；已加载正脸选样修复，原身份保留、明确更新待用户操作。见 `../2026-10-19_front_template_selection/README.md`。\n\n'
if not raw.startswith('> 后续静止正脸检查已完成：'):path.write_text(note+raw,encoding='utf-8')
analysis=ROOT.parent/'语言模型分析';report='正脸模板选择与独立验证_20261019.md'
(analysis/report).write_text(text,encoding='utf-8')
path=analysis/'README.md';raw=path.read_text(encoding='utf-8')
if report not in raw:raw=raw.replace('# 语言模型分析统一入口','# 语言模型分析统一入口\n\n[最新正脸模板选样修复]('+report+')：静止对照已完成；原身份保留，新版需明确更新后验收。',1)
path.write_text(raw,encoding='utf-8')
print(json.dumps({k:summary[k] for k in ('status','camera_runtime','camera_pid','database_after','pc_tests_passed','linux_tests_passed')},ensure_ascii=True))
