"""Preserve the failed human result separately from passing software preflights."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
r=json.loads((HERE/'actual_failure.json').read_text(encoding='utf-8'));s=r['failure_summary']
readme=f'''# 2026-10-19 最后验证再次失败：真实会话分数证据

用户反馈最后验证环节仍有问题。此次在Windows CPU提速及自动验证提示版本 `candidate-8ad60843f9d1` 上，直接读取该失败会话保留的RAM数值统计，没有新开采样、访问照片、导出姓名/模板或修改业务程序。

## 已定位的直接原因

- 选样计数达到10，验证计数最终0；90秒采样窗口超时。
- 验证尝试{s['attempts']}次，通过{s['passes']}次；{s['below_threshold']}次低于0.85。
- 最长连续通过{s['longest_consecutive_passes']}次，规则需要连续5次；低分帧使验证计数清零，但不丢弃原候选。
- 最近24帧分数{s['last_scores_min']:.6f}–{s['last_scores_max']:.6f}，中位{s['last_scores_median']:.6f}。完整77份分数未保留，只有完整计数和最后24份明细。
- 整次会话有{s['quality_skips_across_session']}次质量跳帧，{s['track_recovery_rejections']}次轨迹恢复分数拒绝；身份间隔不足{s['margin_rejections_may_overlap']}次，可与分数拒绝重叠。主要被记录的阻塞是匹配分数。

这是该失败会话的数据，区别于前一次只在事后另采现场裁剪的诊断。CPU后端就绪，现场最近处理{r['last_inference_ms']}ms，摄像头/检测/身份服务无错误；此前提速和提示改动并未解决本次匹配稳定性问题。

## 代码核对及边界

`aura/board/identity/sampling.py` 从至少15秒、最多24份合格人脸中，以对其他候选的总余弦最高选一个实际代表特征，质量作为同分排序；随后清空训练列表，再要求5份独立新帧连续达到0.85及0.1其他身份间隔。`live.py` 保存该单个候选特征，不是把多个角度各存一份可识别模板。

所以目前的多帧采样并不等于多角度模板库。单参考特征与严格连续验证组合没有达到用户要求的自然转头登记效果；候选是否偏向某一角度、关键点/裁剪对齐是否抖动、光照与距离是否影响特征，仍不能仅凭分数区分。失败时候选照片、候选姿态与对齐变换未保留，不能断言候选就是侧脸，也不能将原因继续归到用户转头动作。

下一步诊断应在RAM内保留候选的姿态/质量/来源帧与对齐稳定性数值，和独立新帧的匹配一起比较，核对模板选择与输入一致性，再决定选样或模型改动。不得把增加模板、挑过关帧、缩短验证或降低门槛直接当作已验证修复；此前多模板小试未证明改善。0.85保持。

## 当前事实

身份库仍{r['registered_count']}条、修订{r['database_revision']}、权限{r['database_mode']}，本次检查过程哈希不变；这次未完成保存。原语音/人体DPU配置保持，UI已停止对话。最新真人状态应为失败，不能继续标为仅“待验证”或用公开单图预检代替。

完整匿名证据 `actual_failure.json`；复查工具 `inspect.py` 仅输出数值元数据。没有现场照片、视频、身份向量或称呼归档。本轮没有重启服务、更改模型、匹配门槛或写入身份。
'''
(HERE/'README.md').write_text(readme,encoding='utf-8')
old=ROOT/'deliverables/2026-10-19_windows_face_features'
path=old/'verification_summary.json';v=json.loads(path.read_text(encoding='utf-8'))
v.update(status='REAL_USER_VALIDATION_FAILED_SCORE_STABILITY',actual_user_registration_passed=False,
 real_user_feedback='最后验证环节仍有问题',actual_failure=s,
 actual_failure_detail=r['sampling_diagnostics']['last_failure']['detail'],diagnosis_entry=str(HERE/'README.md'))
path.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
path=old/'listening.json';v=json.loads(path.read_text(encoding='utf-8'))
v.update(status='REAL_USER_VALIDATION_FAILED',actual_user_registration_passed=False,
 latest_feedback='最后验证环节仍有问题',failure_metrics=s)
path.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
note='> 最新真人结果：验证再次失败。77次尝试仅16次通过、61次低于0.85，最佳连续3次，要求5次，最终超时。详见[本次真实分数诊断](../2026-10-19_validation_score_failure/README.md)。提速与提示已生效，匹配稳定性仍未解决。\n\n'
path=old/'README.md';raw=path.read_text(encoding='utf-8')
if not raw.startswith('> 最新真人结果：'):path.write_text(note+raw,encoding='utf-8')
marker='<!-- actual-score-failure-20261019 -->'
block=marker+'\n- 2026-10-19 CPU提速/验证提示版 `candidate-8ad60843f9d1` 真人验证再次失败：77尝试、16通过、61低于0.85，最佳连续3/所需5，最终90秒超时；质量跳帧10、恢复拒绝0、间隔拒绝1可重叠，最后24帧0.810381–0.863107/中位0.8305325。候选仍单个代表特征，未保留其姿态，不能断言是侧脸或用户动作原因；提速和语音提示没有解决匹配稳定性。库5条/修订8保持，本轮只读，无重启/改阈值/写库。最新真人状态false而非待验证；证据 `deliverables/2026-10-19_validation_score_failure/README.md`、`actual_failure.json` 优先于旧预检结论。后续保持0.85，先核对候选选择与裁脸/对齐稳定性，不得将放宽验证或更多最大值匹配当作已验证修复。\n<!-- /actual-score-failure-20261019 -->\n\n'
path=ROOT/'AGENTS.md';raw=path.read_text(encoding='utf-8')
if marker not in raw:path.write_text(block+raw,encoding='utf-8')
path=ROOT/'README.md';raw=path.read_text(encoding='utf-8')
note='> **2026-10-19 最新真人验证失败：** 77帧验证，16帧通过，61帧低于0.85，最长连续3帧/要求5帧，最终超时。CPU提速及提示已生效，匹配稳定性仍待解决；库5条/修订8未变。[实际失败分数与代码诊断](deliverables/2026-10-19_validation_score_failure/README.md)。\n\n'
if not raw.startswith('> **2026-10-19 最新真人验证失败：**'):path.write_text(note+raw,encoding='utf-8')
analysis=ROOT.parent/'语言模型分析';report='人脸最后验证失败_实测分数_20261019.md'
(analysis/report).write_text(readme+'\n完整证据目录：`'+str(HERE)+'`。\n',encoding='utf-8')
path=analysis/'README.md';raw=path.read_text(encoding='utf-8')
entry=f'## 最新：最后验证的真实失败分数\n\n[真人失败诊断]({report})：77次验证仅16次通过、61次低于0.85，最佳连续3/要求5，超时；已确认分数稳定性仍未解决。提速/提示均生效，身份库5条/修订8保持。\n\n'
if report not in raw:raw=raw.replace('# 语言模型分析统一入口\n','# 语言模型分析统一入口\n\n'+entry,1)
path.write_text(raw,encoding='utf-8')
print(json.dumps({'recorded':'REAL_USER_VALIDATION_FAILED_SCORE_STABILITY','evidence':str(HERE/'README.md')},ensure_ascii=True))
