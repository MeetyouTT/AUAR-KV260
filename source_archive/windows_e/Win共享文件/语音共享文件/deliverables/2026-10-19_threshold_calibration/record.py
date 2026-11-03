"""Record authorized deletion and offline comparison without altering thresholds."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];ANALYSIS=ROOT.parent/'语言模型分析'
read=lambda file:json.loads((HERE/file).read_text(encoding='utf-8'))
deleted=read('delete_all_receipt.json');comparison=read('threshold_comparison.json')
assert deleted['after']=={'identities':0,'templates':0,'revision':13}
rows={row['threshold']:row for row in comparison['threshold_rows']}
readme='''# 2026-10-19 阈值离线对比与身份库清空

用户要求查看阈值，并在询问旧5条记录是否不同人时回答“不确定，你全部删除”。已通过正式身份删除接口逐项提交并核对COMMITTED，身份/模板均5→0，库修订8→13，实时身份列表为空、状态UNKNOWN、采样idle。正式删除会清空当前结果/待处理帧并重置采样，在途计算须核对库修订，旧结果不能恢复身份。不创建数据库或生物模板备份，不导出姓名/向量，不重启服务。

## 离线分数对照

来源是实际失败会话77次验证中最后保留的24份分数，非重新采集，也不是完整77帧。保持0.1身份间隔，直接调用生产EnrollmentSampling.usable判断条件；用等分数的二维数值投影代替未保存的原128维向量，仅重放判定，不重跑模型或完整登记。

| 试验阈值 | 24帧通过数 | 最长连续通过 | 分数条件可凑齐5帧 |
| --- | --- | --- | --- |
'''
for threshold in (.85,.84,.83,.82,.8,.363):
    row=rows[threshold]
    readme+=f"| {threshold} | {row['passed']}/24 | {row['longest_consecutive']} | {'是' if row['score_gate_could_complete_five'] else '否'} |\n"
readme+='''
0.80在这段已有画面上足以通过分数条件，无需为了这段数据直接降到0.363。0.80只是可供下一轮比较的试验点，不是已经校准的安全/通用阈值；不能据此宣称可以可靠认人。完整77次验证在0.85下16通过、61分数拒绝、最长3连续；上表0.85的3/24、最长1仅指末尾24份。

这些24帧的原身份间隔均大于0.1，故保持原间隔时结果不变。但间隔针对的是旧库其他“记录”，人员归属未知，不等于已核验的其他人。选图、质量跳帧、目标恢复、写入回执与验证期限无法完整回放；阈值不同也可能改变后续运行路径，上表不是一次成功登记验收。

## 官方参考与误认限制

[OpenCV官方SFace演示](https://docs.opencv.org/4.9.0/d0/dd4/tutorial_dnn_face.html)的余弦阈值为0.363，对应LFW参考结果，不是针对现场摄像头身份库标定的1:N阈值。0.85/0.80均是相似度门槛，不是85%/80%准确率。阈值应按真实同人及不同人数据、可接受误认/漏认来标定；[NIST 1:N评测](https://pages.nist.gov/frvt/html/frvt1N.html)按误识别目标设阈值并测漏识别。

另将以前独立会话12份匿名库内匹配分数做对照：0.363和0.50均接受12/12，0.60接受6/12，0.70及以上接受0/12。由于最高分的旧记录究竟是谁无法确认，这不能算正确识别率或误认率；没有足够的带真实身份标签的不同人对照，最终阈值仍未标定。

## 当前状态

- 活动配置阈值仍0.85、歧义间隔0.1。本轮只修改用户明确要求清空的身份记录，未改模型、阈值、采样/验证策略或语音/视觉程序。
- 活动身份库为0条身份、0份模板、修订13。历史“5条/修订8”是此前部署/失败诊断的快照，不应再当当前库状态。
- 新登记从空库开始，不能把被删除身份自动恢复。下一轮需要新的明确姓名/登记确认及新视频，不能复用本次已清除的会话授权。
- 0.80可作为下一轮候选试验值；当前用户此前明确保留0.85，本轮“看看”和“全部删除”未指定新的阈值，因此没有隐式切换。阈值最终取值还需独立新帧及不同人对照。

证据：`delete_all_receipt.json`、`threshold_comparison.json`。`clear_identities.py`执行正式逐项删除（不可当只读探针重复运行）；`compare_thresholds.py`仅离线数值分析。未访问、保存或导出现场照片、视频、姓名或人脸向量；原LLM数据仍D盘。
'''
(HERE/'README.md').write_text(readme,encoding='utf-8')
summary={'client_date':'2026-10-19','status':'IDENTITY_LIBRARY_EMPTY_OFFLINE_THRESHOLD_COMPARISON_COMPLETE',
 'user_authorized_delete_all':True,'registered_count':0,'template_count':0,'database_revision':13,
 'threshold':.85,'ambiguity_margin':.1,'threshold_changed':False,'runtime_restarted':False,
 'threshold_080_passed_retained_frames':rows[.8]['passed'],'threshold_085_passed_retained_frames':rows[.85]['passed'],
 'retained_frame_count':24,'candidate_trial_threshold':.8,'candidate_deployed':False,
 'calibrated_threshold':None,'false_match_rate':None,'different_person_labels_available':False,
 'production_deletion_commits_verified':5,'database_backup_created':False,'photos_accessed':False,
 'templates_exported':False,'historical_reports_are_not_current_library_state':True}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
marker='<!-- empty-identity-library-threshold-20261019 -->'
block=marker+'\n- 2026-10-19用户回答旧5条身份归属“不确定，你全部删除”，已通过正式identity_delete逐项COMMITTED清空全部5身份及5模板，库修订8→13，实时people空/UNKNOWN、采样idle，缓存和在途结果通过删除接口/库修订失效，无数据库备份/模板导出/重启。当前活动库0条/修订13，下方5条/修订8为历史快照，禁止当当前值或自动恢复旧记录。用户“那你看看”授权阈值对比；失败会话最后24份分数、保持0.1间隔：0.85通过3/24最长1，0.84通过9/24最长3，0.83通过14/24最长6，0.80及0.363均24/24最长24。只重放分数门槛，不能当完整77帧/模型/登记成功或误认校准。旧库人员归属未知、缺可靠不同人样本，误认率未测；0.80仅候选试验值尚未部署，正式仍0.85/0.1，不能默认为用户已授权改阈值。最新证据 `deliverables/2026-10-19_threshold_calibration/README.md`、`delete_all_receipt.json`、`threshold_comparison.json` 优先。新登记须新会话及原明确姓名确认。原模型/语音/DPU/跟踪保持，LLM数据D盘。\n<!-- /empty-identity-library-threshold-20261019 -->\n\n'
path=ROOT/'AGENTS.md';raw=path.read_text(encoding='utf-8')
if marker not in raw:path.write_text(block+raw,encoding='utf-8')
path=ROOT/'README.md';raw=path.read_text(encoding='utf-8')
note='> **2026-10-19 身份库已按用户要求清空：** 5条身份及模板全部删除，当前0条/修订13。最后24帧离线门槛对比：0.85通过3/24，0.80通过24/24；缺可靠不同人对照，尚非误认校准。正式阈值仍0.85，0.80仅候选。[删除回执与阈值分析](deliverables/2026-10-19_threshold_calibration/README.md)。\n\n'
if not raw.startswith('> **2026-10-19 身份库已按用户要求清空：**'):path.write_text(note+raw,encoding='utf-8')
report='人脸阈值对照与身份库清空_20261019.md';(ANALYSIS/report).write_text(readme+'\n原始证据：`'+str(HERE)+'`。\n',encoding='utf-8')
path=ANALYSIS/'README.md';raw=path.read_text(encoding='utf-8')
entry=f'## 最新：阈值离线对比及清空身份库\n\n[对比与删除记录]({report})：按用户要求已清空全部5条身份/模板，当前0条/修订13；0.80在失败会话末24帧的分数回放中24/24通过，正式仍0.85，缺不同人对照，最终阈值未标定。\n\n'
if report not in raw:raw=raw.replace('# 语言模型分析统一入口\n','# 语言模型分析统一入口\n\n'+entry,1)
path.write_text(raw,encoding='utf-8')
for folder in ('2026-10-19_windows_face_features','2026-10-19_validation_score_failure'):
    path=ROOT/'deliverables'/folder/'verification_summary.json'
    if path.exists():
        value=json.loads(path.read_text(encoding='utf-8'))
        value.update(current_registered_count_after_explicit_delete=0,current_database_revision_after_explicit_delete=13,
                     latest_identity_clearance_evidence=str(HERE/'delete_all_receipt.json'))
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
