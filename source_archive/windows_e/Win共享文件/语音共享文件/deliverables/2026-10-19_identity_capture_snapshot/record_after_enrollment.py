"""Record numeric replay distinctly from a controlled human recognition test."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
r=json.loads((HERE/'after_enrollment_scores.json').read_text(encoding='utf-8'))
assert r['database_hash_unchanged'] and r['selected_photo_replay_vs_database']>.999999
assert r['archive_final_validation']['pass_080']==5
text='''# 登记照片与模板一致性复核（2026-10-19）

已用当前原Windows CPU SFace重新计算板端本轮已存的25张112×112人脸图，只读读取身份库1份模板（修订15），未导出特征、姓名或新照片。

- 最终选中图与正式保存模板的余弦相似度1.000000，照片对应的特征与身份库一致。
- 13张采集图有10张达到0.80，范围0.751378～1.000000，中位0.898795。
- 7张质量筛除图全部低于0.80，范围0.528969～0.750084，中位0.593755。
- 最终5张独立验证图全部达到0.80，范围0.813952～0.897079，中位0.851029；和登记时保存的数值一致。
- 随后12秒取得21份当前模型输入，0份达到0.80，范围0.167645～0.405261，中位0.254755；27次生产状态均UNKNOWN。这段没有用户声明当时镜头前的人员/姿态，不能将其当作已确认本人的受控准确度测试，更不能据此归因于眼镜或特定姿态。

诊断保持数据库哈希、0.80门槛、0.1分差及模型配置。首轮遇到一次特征服务瞬时不可用，降频重试后完整完成；不把服务忙当匹配分数。

下一步：已请刚登记的本人单独、在与登记接近的距离正对镜头，准备后触发约10秒的只读检查。此后分别观察轻微转头、离开与重返；只有用户确认的人体条件和实际分数/查询结果一致时，才记录真人验收。无需重新登记、无需调整阈值。证据为同目录`after_enrollment_scores.json`。
'''
(HERE/'after_enrollment_review.md').write_text(text,encoding='utf-8')
summary_path=HERE/'verification_summary.json'
s=json.loads(summary_path.read_text(encoding='utf-8'))
s.update(selected_photo_replay_matches_database=True,
    final_validation_replay_passed=True,read_only_post_enrollment_evidence='after_enrollment_scores.json',
    uncontrolled_current_scores_are_not_confirmed_person_test=True,
    controlled_frontal_check_status='WAITING_FOR_USER_READY',stable_person_recognition_accepted=False)
summary_path.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
marker='<!-- post-enrollment-replay-20261019 -->'
path=ROOT/'AGENTS.md';raw=path.read_text(encoding='utf-8')
if marker not in raw:
 path.write_text(marker+'\n- 2026-10-19本轮25张存图只读回放：selected对库模板余弦1.0，最终5验证重算0.813952～0.897079全部>=0.80，库修订15哈希未变；13采集10达标、7质量拒绝均未达标。随后12秒21当前帧0.167645～0.405261/0达标，但用户未声明当时人员/姿态，不能当本人受控测试或据此归因眼镜。已请求刚登记的本人正对同距离准备10秒检查，待用户“开始检查”；不重登/改阈值。证据deliverables/2026-10-19_identity_capture_snapshot/after_enrollment_review.md及after_enrollment_scores.json。\n<!-- /post-enrollment-replay-20261019 -->\n\n'+raw,encoding='utf-8')
print(json.dumps({'template_matches_selected_photo':True,'database_revision':15,
 'next_step':'WAITING_FOR_CONTROLLED_FRONTAL_CHECK','production_changed':False}))
