"""Record failed human query separately from successful enrollment and lab checks."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'2026-10-19_spoken_identity_query'
feedback={'client_date':'2026-10-19','deployed_revision_1_human_query_passed':False,
 'query_feedback':'仍然普通聊天说不知道',
 'latest_feedback':'语音识别有问题，我说夕蓝，他识别不到',
 'actual_asr_of_the_reported_full_question_available':False,
 'source_reproduction':'夕蓝我是谁 and 西兰我叫什么名字啊 miss the old exact query route',
 'actual_080_enrollment_still_passed':True,'database_revision_at_enrollment':14,
 'threshold':.8,'recognition_accuracy_fixed_by_routing':False,
 'speech_model_changed':False,'followup_scope':'known vocative and full identity-question routing'}
(HERE/'user_feedback.json').write_text(json.dumps(feedback,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ('verification_summary.json','listening.json'):
 path=OLD/name;value=json.loads(path.read_text(encoding='utf-8'))
 value.update(status='REAL_USER_QUERY_FAILED_FOLLOWUP_ROUTING_REPAIR',
  actual_spoken_identity_query_passed=False,actual_new_query_listening_passed=False,
  latest_user_feedback=feedback['latest_feedback'],
  full_question_asr_not_recovered=True,followup_evidence=str(HERE/'user_feedback.json'))
 path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
path=OLD/'README.md';raw=path.read_text(encoding='utf-8')
note=('> 最新真人反馈：本版查询未通过，用户称“仍然普通聊天说不知道”，随后说明称呼“夕蓝”识别有问题。'
      '日志一轮进入身份查询并返回identity_unavailable，其余所见轮次为普通聊天；未取回报告当轮完整ASR，不能归因于一个已知错字。'
      '另有12帧当前对齐脸分数0.437618～0.624089，均低于0.80；未导出照片、模板或登记姓名。'
      '后续称呼/问句修复见 `../2026-10-19_identity_query_routing/README.md`。下文预检通过不代表真人查询通过。\n\n')
if not raw.startswith('> 最新真人反馈：'):path.write_text(note+raw,encoding='utf-8')
print('Recorded actual failed query; retained successful enrollment and original preflight evidence.')
