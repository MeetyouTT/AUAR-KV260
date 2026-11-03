"""Static/hash/XML review only. Release scripts are parsed, never executed."""
import ast
import base64
import copy
import datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
expected={
 'board/runtime/audio/board_dialogue_jobs.py':'580b2cf796275104cf15f2295afa2de29f82f32eabdd783a4b3aff858840a464',
 'board/runtime/board_business.py':'d034227118063dc4dbfb69f4bc735000980bd166e91262b4953f0db4b1baf5cc'}
trees={}
for relative,digest in expected.items():
 old,new=ROOT/'baseline'/relative,ROOT/'candidate'/relative
 assert sha(new)==digest==manifest['files'][relative]['after_sha256']
 assert sha(old)==manifest['files'][relative]['before_sha256']
 trees[relative]=(ast.parse(old.read_text(encoding='utf-8')),ast.parse(new.read_text(encoding='utf-8')))
 target=HERE/'reviewed_candidate'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(new.read_bytes())
dump=lambda n:ast.dump(n,include_attributes=False)
def cls(tree,name):return next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==name)
def methods(klass):return {n.name:n for n in klass.body if isinstance(n,ast.FunctionDef)}
old_business,new_business=trees['board/runtime/board_business.py']
assert dump(cls(old_business,'BoardBusinessRuntime'))==dump(cls(new_business,'BoardBusinessRuntime'))
old_lir,new_lir=methods(cls(old_business,'LocalIdentityReplies')),methods(cls(new_business,'LocalIdentityReplies'))
lir_changed=sorted(k for k in old_lir if dump(old_lir[k])!=dump(new_lir[k]))
assert set(lir_changed)=={'__init__','reset','public','__call__'}
assert set(new_lir)-set(old_lir)=={'_entry_speaker_presence'}
old_jobs,new_jobs=trees['board/runtime/audio/board_dialogue_jobs.py']
old_j,new_j=methods(cls(old_jobs,'BoardDialogueJobs')),methods(cls(new_jobs,'BoardDialogueJobs'))
jobs_changed=sorted(k for k in old_j if dump(old_j[k])!=dump(new_j[k]))
assert set(jobs_changed)=={'_route','_execute'}
assert set(new_j)-set(old_j)=={'_publish_entry_route_trace'}
assert dump(old_j['_diagnostic_error_class'])==dump(new_j['_diagnostic_error_class'])

def calls(node,kind):
 out=[]
 for n in ast.walk(node):
  if not isinstance(n,ast.Call):continue
  if kind=='asr' and isinstance(n.func,ast.Attribute) and n.func.attr=='transcribe':out.append(n)
  if kind=='handler' and isinstance(n.func,ast.Name) and n.func.id=='handler':out.append(n)
  if kind=='business' and isinstance(n.func,ast.Attribute) and n.func.attr=='turn' and isinstance(n.func.value,ast.Attribute) and n.func.value.attr=='business':out.append(n)
  if kind=='wrapped-business' and isinstance(n.func,ast.Name) and n.func.id=='traced_business_turn':out.append(n)
 return out
assert [dump(n) for n in calls(old_j['_execute'],'asr')]==[dump(n) for n in calls(new_j['_execute'],'asr')]
assert len(calls(old_j['_execute'],'asr'))==1
assert [dump(n) for n in calls(old_j['_route'],'handler')]==[dump(n) for n in calls(new_j['_route'],'handler')]
old_turns=calls(old_lir['__call__'],'business');new_turns=calls(new_lir['__call__'],'wrapped-business')
assert len(old_turns)==len(new_turns)==3
for old,new in zip(old_turns,new_turns):
 assert [dump(n) for n in old.args]==[dump(n) for n in new.args]
 assert [dump(n) for n in old.keywords]==[dump(n) for n in new.keywords]
class OriginalEnrollmentCondition(ast.NodeTransformer):
 def visit_Call(self,node):
  if isinstance(node.func,ast.Name) and node.func.id=='enrollment_active':
   return ast.parse("self._enrollment_state().get('active')",mode='eval').body
  return self.generic_visit(node)
route=OriginalEnrollmentCondition().visit(copy.deepcopy(new_j['_route']))
conditions_old=[dump(n.test) for n in ast.walk(old_j['_route']) if isinstance(n,ast.If)]
conditions_new=[]
for n in ast.walk(route):
 if isinstance(n,ast.If):
  if isinstance(n.test,ast.Compare) and isinstance(n.test.left,ast.Name) and n.test.left.id=='trace':continue
  conditions_new.append(dump(n.test))
assert conditions_old==conditions_new

def xml(path):
 root=ET.fromstring(path.read_bytes());suites=list(root.iter('testsuite'))
 return {'file':str(path.relative_to(ROOT)),'sha256':sha(path),
  **{k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')},
  'failed_cases':sorted(c.attrib.get('classname','')+'.'+c.attrib.get('name','') for c in root.iter('testcase') if c.find('failure') is not None)}
independent=xml(HERE/'INDEPENDENT_TRACE.xml');assert (independent['tests'],independent['failures'],independent['errors'])==(6,0,0)
author={name:xml(ROOT/(name+'.xml')) for name in ('CANDIDATE_TRACE_TESTS','BASELINE_TRACE_TESTS','CANDIDATE_ORIGINAL_REGRESSION','BASELINE_ORIGINAL_REGRESSION')}
assert (author['CANDIDATE_TRACE_TESTS']['tests'],author['CANDIDATE_TRACE_TESTS']['failures'],author['CANDIDATE_TRACE_TESTS']['errors'])==(19,0,0)
assert (author['BASELINE_TRACE_TESTS']['tests'],author['BASELINE_TRACE_TESTS']['failures'],author['BASELINE_TRACE_TESTS']['skipped'])==(19,0,13)
for name in ('CANDIDATE_ORIGINAL_REGRESSION','BASELINE_ORIGINAL_REGRESSION'):
 assert (author[name]['tests'],author[name]['failures'],author[name]['errors'])==(60,4,0)
assert author['CANDIDATE_ORIGINAL_REGRESSION']['failed_cases']==author['BASELINE_ORIGINAL_REGRESSION']['failed_cases']

release=ROOT/'release'
release_receipts={name:{'sha256':sha(release/name),'parsed_only_not_executed':True} for name in ('stop_gui_once.py','apply_trace_once.py','start_gui_once.py')}
apply_source=(release/'apply_trace_once.py').read_text(encoding='utf-8')
apply_tree=ast.parse(apply_source)
payload_node=next(n for n in apply_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PAYLOAD' for t in n.targets))
payload=ast.literal_eval(payload_node.value)
assert set(payload['files'])==set(expected)
assert payload['base_startup_sha256']=='6f9653641a99ba8e5c8bed85f9628c87f9b22e54e205531e285e11a17611de7a'
for relative,digest in expected.items():
 entry=payload['files'][relative];content=base64.b64decode(entry['payload_base64'],validate=True)
 assert hashlib.sha256(content).hexdigest()==entry['candidate_sha256']==digest
 assert content==(ROOT/'candidate'/relative).read_bytes()
 assert entry['before_sha256']==manifest['files'][relative]['before_sha256']
release_receipts['apply_trace_once.py']['payload_exactly_matches_reviewed_candidate_bytes']=True
release_receipts['apply_trace_once.py']['only_two_targets']=True
release_receipts['apply_trace_once.py']['base_startup_matches_normal_stop_expected']=True
release_audit={
 'normal_stop_only_GUI_with_no_force_temporary_guard':True,
 'stop_checks_paused_idle_and_exact_GUI_camera_boot_birth_cmdline_and_380_pins':True,
 'pending_stop_does_not_allow_apply':True,
 'apply_requires_GUI_inactive_dead_and_old_two_processes_absent':True,
 'apply_checks_both_original_source_hashes_and_replaces_only_two_pins_plus_startup':True,
 'other378_component_pins_and_other_startup_fields_preserved':True,
 'each_replace_uses_source_byte_CAS_and_owner_recheck':True,
 'rollback_only_replaces_bytes_still_equal_to_this_transaction_output':True,
 'camera_only_verified_not_controlled':True,
 'start_removes_only_original_guard_bytes_and_restores_four_original_service_properties':True,
 'start_verifies_380_pins_and_camera_owner_then_single_normal_GUI_start':True,
 'reviewer_release_scripts_executed':False,
 'live_owner_or_device_preconditions_rechecked_by_reviewer':False}
report={
 'schema':'aura-voice-entry-trace-independent-review-1',
 'sealed_host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'verdict':'PASS_METADATA_CANDIDATE_AND_RELEASE_STATIC_REVIEW_NO_BLOCKER',
 'candidate_hashes':expected,'baseline_hashes':{k:v['before_sha256'] for k,v in manifest['files'].items()},
 'privacy':'New projections contain only bounded numeric counts,13 fixed fragment booleans,fixed enums and original fixed error categories; no names,IDs,target values,transcripts,PCM or arbitrary exception messages',
 'parser_code_flags_are_observations_not_authorization_or_loaded_disk_hash_proof':True,
 'ASR_callsite_and_args_identical':True,'handler_callsite_and_args_identical':True,
 'three_business_turn_callsites_keep_exact_original_args_and_kwargs':True,
 'route_IF_conditions_after_local_enrollment_wrapper_normalization_identical':True,
 'jobs_changed_original_methods':jobs_changed,'LIR_changed_original_methods':lir_changed,
 'entire_BoardBusinessRuntime_including_AAC_clock_AST_unchanged':True,
 'original_Job_public_ACK_cancel_NoSpeech_admission_diagnostic_error_allowlist_AST_unchanged':True,
 'speaker_presence_reads_only_existing_RAM_dict_membership_and_until_without_state_or_expire':True,
 'business_SystemExit_same_exception_object_rethrown_once_verified':True,
 'existing_public_projection_returns_detached_trace_copies':True,
 'trace_semantics_boundary':['Latest executed Jobs capture replaces previous route metadata,including blank/error captures',
  'LIR reset marks last trace; next handler invocation allocates a new trace',
  'enrollment_checked=false means short-circuit skipped the state lookup',
  'speaker presence/active is an unsynchronized diagnostic instant,not identity authorization'],
 'independent_tests':independent,'author_XML_receipts':author,
 'original_regression_boundary':'Both60:56pass/same4oldalias/intentfixturefail/0error; baseline6behaviorpass+13metadataonlyskip',
 'release_script_hashes':release_receipts,'release_static_audit':release_audit,
 'product_incident_root_cause_or_behavior_repair_claimed':False,
 'real_board_GET_SSH_models_private_databases_audio_or_axis_accessed':False,
 'candidate_producer_tests_or_product_sources_modified_by_reviewer':False}
(HERE/'REVIEW_VERDICT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
text='''两文件入口诊断候选独审通过，无可部署阻断；release脚本仅静态审查通过，未执行。

Jobs580b2cf796275104cf15f2295afa2de29f82f32eabdd783a4b3aff858840a464
Businessd034227118063dc4dbfb69f4bc735000980bd166e91262b4953f0db4b1baf5cc

新增trace仅有界计数、13个固定片段布尔、固定kind/capability/phase/outcome和原异常类别白名单；没有原文、称呼、IDs、target原值、PCM或任意异常message。parser代码常量标志只是观察，不是授权或磁盘版本证明。RAM speaker窥视只读当前actor的sessions成员和until，不调用state()、不expire、不开库。

独立6例全过：空ASR恰1次且不进handler；原speaker-query/active-enrollment/explicit-memory短路和调用次数；过期RAM session观察不删除或读私有字段；business.turn抛SystemExit同对象恰1次重抛，公开只记other类别。AST核对ASR与handler原调用参数相同、三处business.turn参数原样转发；_route条件在还原本地enrollment wrapper后完全相同。BoardBusinessRuntime整个class含实际AAC clock方法AST未变；原_admit_text/_put_error/ACK/cancel/public投影等方法未改。

作者19专项全过，基线6原行为通过、13新投影测试明确skip。原60两版56通过、同4旧称呼/intent夹具失败、0error，保留此边界。

release的PAYLOAD只在RAM做字节哈希校验未输出内容，与审阅两文件逐字节一致。stop仅正常GUI stop且临时no-force guard，pending不推进；apply要求停稳和旧GUI两PID消失，380源全核、每文件CAS/owner再核，仅改两源和两pin，异常条件回滚不会覆盖外来变化；start仅移除自有精确guard，daemon-reload后核原Restart/KillMode/SendSIGKILL/TimeoutStopUSec恢复才单次正常start。camera只校验，不控制。设备owner等实际前提由root现场核，审阅者未访问。

解释边界：Jobs字段代表最后执行capture，包括空/错误capture；LIR reset保留trace并标记，下一次handler会新建trace；enrollment_checked=false表示短路没查状态；speaker RAM窥视是诊断瞬间，不是身份或授权。此候选用于捕获现场入口，没有宣称行为已修复。

未SSH/GET/模型/真实DB/照片/语音/轴操作；未修改候选或producer测试、产品源，仅写independent_review产物。
'''
(HERE/'REVIEW.txt').write_text(text,encoding='utf-8')
print(json.dumps({name:sha(HERE/name) for name in ('REVIEW_VERDICT.json','REVIEW.txt','INDEPENDENT_TRACE.xml','test_independent_trace.py')}))
