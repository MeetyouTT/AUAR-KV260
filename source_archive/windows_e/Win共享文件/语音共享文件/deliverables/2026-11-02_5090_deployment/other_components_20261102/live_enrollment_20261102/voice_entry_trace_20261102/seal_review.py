import ast,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def xml(name):
 p=HERE/name;cases=list(ET.parse(p).iter('testcase'));fail=[];skipped=[]
 for c in cases:
  key=c.attrib.get('classname','')+'::'+c.attrib['name']
  if c.find('failure') is not None or c.find('error') is not None:fail.append(key)
  if c.find('skipped') is not None:skipped.append(key)
 return dict(tests=len(cases),passed=len(cases)-len(fail)-len(skipped),failed=len(fail),skipped=len(skipped),failure_names=fail,sha256=sha(p))
manifest=json.loads((HERE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
for name,row in manifest['files'].items():
 assert sha(HERE/'baseline'/name)==row['before_sha256'] and sha(HERE/'candidate'/name)==row['after_sha256']
 ast.parse((HERE/'candidate'/name).read_text(encoding='utf-8'))
results={name:xml(name+'.xml') for name in ('CANDIDATE_TRACE_TESTS','BASELINE_TRACE_TESTS','CANDIDATE_ORIGINAL_REGRESSION','BASELINE_ORIGINAL_REGRESSION')}
assert results['CANDIDATE_TRACE_TESTS']['failed']==0 and results['CANDIDATE_TRACE_TESTS']['passed']==19
assert results['BASELINE_TRACE_TESTS']['passed']==6 and results['BASELINE_TRACE_TESTS']['skipped']==13
assert results['CANDIDATE_ORIGINAL_REGRESSION']['tests']==60 and results['CANDIDATE_ORIGINAL_REGRESSION']['passed']==56
assert results['CANDIDATE_ORIGINAL_REGRESSION']['failure_names']==results['BASELINE_ORIGINAL_REGRESSION']['failure_names']
result=dict(status='LOCAL_METADATA_CANDIDATE_FROZEN_NOT_DEPLOYED',files=manifest['files'],validation=results,
 diff_sha256=sha(HERE/'CANDIDATE.diff'),public_projection=[
  'board_business.dialogue.last_voice_route.entry_trace',
  'board_business.dialogue.voice_enrollment.entry_trace'],
 keywords={'has_register':'登记','has_voiceprint':'声纹','has_voice':'声音','has_warming':'升温','has_face':'人脸',
  'has_my_name':'我叫','has_level':'等级','has_i_want':'我要','has_i_would_like':'我想','has_a_bit':'一下',
  'has_voice_word':'声文','has_identity':'身份','has_name_word':'名字'},
 semantics=['Code-constant flags inspect the actual function object imported by each route/handler; they are observations, not authorization or disk hash claims',
  'parser_code_known=false means no parser code was observed in this trace, including no-speech paths that never route',
  'enrollment_checked=false means original short circuit did not call enrollment state; false active alone is not an inactive proof',
  'speaker_state_known/present/active read only original current-actor RAM membership and until; state() is not called, no session is expired or removed',
  'ASR characters are exact for the existing <=4096 bound, with 4097 a saturated invalid-length marker',
  'Business turn count is per handler invocation, capped at8; no transcript/IDs/PCM/exception message is persisted',
  'An explicit reset retains last fixed trace with reset_since_trace=true; the next handler gets a new trace object',
  'Jobs begin each executed capture with a fresh trace; old-generation completion cannot overwrite a newer processed generation',
  'last_voice_route is last processed metadata and intentionally remains available while listener rearms; it is not a current authorization claim'],
 unchanged=['all original parser/grammar/standalone epochs and route decisions',
  'all BoardBusinessRuntime methods including actual AAC initialize_clock',
  'speaker/face sampler, gallery reads, quality thresholds, confirmation/save, owner/scope/deadline checks',
  'ASR c514, original NoSpeech behavior, original TTS/LLM parameters, player/ACK and production service wiring'],
 limitations=['No live incident transcript or captured voice was accessed; grammar mismatch remains a hypothesis until fixed metadata is observed',
  'Synthetic recognizer/store/PCM/provider fixtures only; tests do not claim hardware or model accuracy',
  'Original60 do not all pass: both versions retain the same4 old alias/intent fixture failures',
  'The6 baseline behavior tests pass;13 new metadata-only tests intentionally skip on baseline without projection',
  'No UI/service/device action or SSH/GET/model/private-store access occurred in this task'],
 root_merge='Root only: fresh CAS ea4f/43708 actual sources and preserve latest startup/UI/other modules; update only those two pins and normal root-managed GUI lifecycle.')
(HERE/'VALIDATION_FINAL.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report='''已冻结两文件实际入口诊断候选，仅本地，未部署。

原公开投影无新端点：
board_business.dialogue.last_voice_route.entry_trace
board_business.dialogue.voice_enrollment.entry_trace

Jobs记录固定ASR字数/13个指定词片段布尔、binding_kind、speaker_requested、原enrollment是否实际查询及active、选中capability、handler是否存在/是否恰被调用、返回None/返回/固定异常类别和本次outcome。LIR记录输入/解析后mode、固定kind、business.turn调用次数与None/reply/error、固定异常类别、face FSM active及原当前actor声纹RAM会话是否存在/在原until内active。所有枚举白名单、计数有界；没有原文、姓名、ID、PCM、任意异常message、gallery或快照。业务turn只转发原调用一次。

解析器标志从各调用点实际导入的binding_intent.__code__.co_consts取固定face_only/voice_only存在布尔，而非磁盘SHA。parser_code_known=false明确尚未观察到解析器code（如空语音未路由），不能将两个false误认为已加载旧版。标志只用于定位，不给任何身份授权。声纹RAM观测不调用会删除过期session的state()，不改变采样或超时。

语义注意：enrollment_checked=false是原短路未调用_enrollment_state，不应把其active=false解读成已查得无活动。last_voice_route按原“最后一次已处理”定位保留到重听，失败新turn亦刷新元数据，旧generation最终发布不得覆盖新generation。LIR reset保留上次固定trace并标reset_since_trace，下一次handler新建trace，不残留前轮business结果。

专项19项全过，包含固定片段、真实函数code标志、缺handler/None/异常同对象重抛、隐私canary、下一turn清理、旧代发布拦截、原短路调用次数、public副本与200次轮询，以及6个原行为场景。基线相同6行为场景通过，13新增metadata投影专测在无此字段的基线明确skip。原Jobs+Dialogue共60项两版均56通过、同4旧称呼/路由fixture失败，无新增失败或error，不宣称原60全过。

AST核验：整个BoardBusinessRuntime（含生产AAC clock方法）未变；LIR _entry_for/_new_entry/attach/_visual/_gallery未变。Jobs原方法仅_route/_execute增加旁路元数据，原_admit_text、_put_error、ACK、cancel和其它方法保持。没有改变grammar、mode/epoch/clock、模型/质量、真实FSM、确认/授权、记忆范围或服务流程。自然前缀“我要/我想”等只作为bool，不触发新登记；尚不能把窄grammar推定为现场根因。

原src基于actual_release/runtime：BoardBusiness ea4f4565f558e5e2b6a347360f362e7810dd5792b2d2fe7af3a26389e26514d7；Jobs43708b7fcbf72b11d7a37b01ae090c2cdb3e621b5f334151601206735a34a1fc。root应以最新实际源CAS，仅更新此两pin，保留所有当前UI/clock/split/身份及其它配置；此代理无SSH、GET、板端状态/模型/真实私库或音视频访问，不执行服务动作。实际设备发布和下一次真实口令观察仍由root唯一负责。
'''
(HERE/'HANDOFF.txt').write_text(report,encoding='utf-8')
print(json.dumps({'validation_sha256':sha(HERE/'VALIDATION_FINAL.json'),'handoff_sha256':sha(HERE/'HANDOFF.txt'),'diff_sha256':sha(HERE/'CANDIDATE.diff'),'tests':19}))
