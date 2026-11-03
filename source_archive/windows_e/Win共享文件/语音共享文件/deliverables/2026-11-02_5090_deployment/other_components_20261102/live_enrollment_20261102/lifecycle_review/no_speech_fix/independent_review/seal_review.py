"""Independent exact-AST and XML review. Only local public sources and synthetic receipts."""
import ast
import copy
import datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
FIX = HERE.parent
manifest = json.loads((FIX / 'MANIFEST.json').read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
expected = {
    'board/runtime/audio/board_asr.py': 'c51488ac6bd3563bc3dc42934b321e98e26cb2b58d700318765a60ca4908ef60',
    'board/runtime/audio/board_dialogue_jobs.py': '01b27ede0d8889c35fc9ac990e03538a55fecc7c6a604fb6f781bc5d54c09087'}
trees = {}
for relative, expected_hash in expected.items():
    old, new = FIX / 'baseline' / relative, FIX / 'candidate' / relative
    assert sha(new) == expected_hash == manifest['files'][relative]['candidate_sha256']
    assert sha(old) == manifest['files'][relative]['before_sha256']
    destination = HERE / 'reviewed_candidate' / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(new.read_bytes())
    trees[relative] = [ast.parse(p.read_text(encoding='utf-8')) for p in (old, new)]

dump = lambda n: ast.dump(n, include_attributes=False)
def klass(tree, name): return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
def method(cls, name): return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)

asr_name = 'board/runtime/audio/board_asr.py'
old_asr, new_asr = trees[asr_name]
normal_asr = copy.deepcopy(new_asr)
typed_class = klass(normal_asr, 'BoardNoSpeech')
expected_class = ast.parse('class BoardNoSpeech(ValueError):\n    """The original recognizer completed without any recognized speech text."""\n    pass').body[0]
assert dump(typed_class) == dump(expected_class)
normal_asr.body.remove(typed_class)
raise_nodes = [n for n in ast.walk(normal_asr) if isinstance(n, ast.Raise)
               and isinstance(n.exc, ast.Call) and isinstance(n.exc.func, ast.Name)
               and n.exc.func.id == 'BoardNoSpeech']
assert len(raise_nodes) == 1
raise_nodes[0].exc.func.id = 'ValueError'
assert dump(normal_asr) == dump(old_asr)

jobs_name = 'board/runtime/audio/board_dialogue_jobs.py'
old_jobs, new_jobs = trees[jobs_name]
normal_jobs = copy.deepcopy(new_jobs)
imports = [n for n in normal_jobs.body if isinstance(n, ast.ImportFrom)
           and n.module == 'board.runtime.audio.board_asr']
assert len(imports) == 1 and [(n.name, n.asname) for n in imports[0].names] == [('BoardNoSpeech', None)]
normal_jobs.body.remove(imports[0])
old_cls, normal_cls = klass(old_jobs, 'BoardDialogueJobs'), klass(normal_jobs, 'BoardDialogueJobs')
admit = method(normal_cls, '_admit_text')
original_admit = method(old_cls, '_admit_text')
assert all(isinstance(admit.body[i], ast.ImportFrom) for i in range(3))
assert isinstance(admit.body[3], ast.If) and isinstance(admit.body[4], ast.If)
blank_expected = ast.parse('if not raw_text.strip():\n    raise self._entry_error()').body[0]
assert dump(admit.body[5]) == dump(blank_expected)
assert dump(admit.body[4]) == dump(original_admit.body[4])
admit.body[3] = copy.deepcopy(original_admit.body[3])
del admit.body[5]
assert dump(admit) == dump(original_admit)

execute = method(normal_cls, '_execute')
expected_try = ast.parse('''
try:
    raw = self.asr.transcribe(job.pcm, sample_rate=16000, deadline=job.deadline,
                              cancelled=job.cancelled.is_set)
except BoardNoSpeech as exc:
    self._check(job)
    raise self._entry_error() from exc
''').body[0]
wrapped = [n for n in ast.walk(execute) if isinstance(n, ast.Try)
           and any(isinstance(h.type, ast.Name) and h.type.id == 'BoardNoSpeech' for h in n.handlers)]
assert len(wrapped) == 1 and dump(wrapped[0]) == dump(expected_try)
class UnwrapOnlyExactTypedAsr(ast.NodeTransformer):
    def visit_Try(self, node):
        if node is wrapped[0]: return node.body[0]
        return self.generic_visit(node)
UnwrapOnlyExactTypedAsr().visit(execute)
assert dump(execute) == dump(method(old_cls, '_execute'))
assert dump(normal_jobs) == dump(old_jobs)

def receipt(path):
    root = ET.fromstring(path.read_bytes())
    suites = list(root.iter('testsuite'))
    return {'file': str(path.relative_to(FIX)), 'sha256': sha(path),
            **{key: sum(int(s.attrib.get(key, 0)) for s in suites)
               for key in ('tests', 'failures', 'errors', 'skipped')},
            'failed_cases': sorted(t.attrib.get('classname', '') + '.' + t.attrib.get('name', '')
                                   for t in root.iter('testcase') if t.find('failure') is not None)}

independent = receipt(HERE / 'INDEPENDENT_COUNTEREXAMPLES.xml')
assert (independent['tests'], independent['failures'], independent['errors']) == (7, 0, 0)
pipeline = {label: receipt(FIX / (label + '_PIPELINE.xml')) for label in ('BASELINE', 'CANDIDATE')}
assert (pipeline['CANDIDATE']['tests'], pipeline['CANDIDATE']['failures'], pipeline['CANDIDATE']['errors']) == (31, 0, 0)
assert (pipeline['BASELINE']['tests'], pipeline['BASELINE']['failures'], pipeline['BASELINE']['errors']) == (31, 8, 0)
regression = {label: receipt(FIX / (label + '_ORIGINAL_REGRESSION.xml')) for label in ('BASELINE', 'CANDIDATE')}
assert all((r['tests'], r['failures'], r['errors']) == (70, 7, 0) for r in regression.values())
assert regression['BASELINE']['failed_cases'] == regression['CANDIDATE']['failed_cases']

audit = {
    'exact_whole_module_ast_equal_after_reversing_only_declared_changes': True,
    'asr_added_only_typed_subclass_and_existing_empty_raise_type': True,
    'asr_lock_pcm_decode_cancel_deadline_and_normal_return_ast_unchanged': True,
    'jobs_added_only_typed_import_two_localized_method_changes': True,
    'typed_catch_encloses_only_original_transcribe_call': True,
    'typed_catch_rechecks_original_job_cancel_owner_deadline_before_entry_rejected': True,
    'blank_direct_text_check_after_original_type_length_and_control_character_rejection': True,
    'all_other_jobs_methods_exact_ast_unchanged': True,
    'sql_guard_lock_order_ttl_face_owner_ack_and_playback_logic_changed': False,
    'new_network_devices_models_private_store_or_axis_calls_added': False}
(HERE / 'STATIC_AUDIT.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
verdict = {
    'schema': 'aura-no-speech-two-file-independent-review-1',
    'sealed_host_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'verdict': 'PASS_FINAL_TWO_FILE_CANDIDATE_NO_CODE_BLOCKER',
    'candidate_sha256': expected,
    'before_sha256': {p: manifest['files'][p]['before_sha256'] for p in expected},
    'source_manifest_sha256': sha(FIX / 'MANIFEST.json'),
    'diff_sha256': sha(FIX / 'CANDIDATE.diff'),
    'independent_counterexamples': independent,
    'author_actual_pipeline': pipeline,
    'author_original_regression': regression,
    'original_regression_boundary': 'Both70:63pass/same7fail/0error; author classifies4old-character-alias and3missing-character_pair GUI fixtures',
    'rejected_intermediate_jobs_sha256': '2d68450e72916310595334dfa54a2471540c3cf0fb884a6080ee76d53dda55ee',
    'intermediate_review_boundary': 'Four exception cases passed on intermediate2d684; final verdict uses only01b27 with control-character order preserved',
    'static_audit': audit,
    'content_write_boundary': 'Blank ASR does not reach dialogue begin/generated/ACK, LLM, identity commands or voice sample collection in synthetic pipeline',
    'existing_housekeeping_sql_boundary': 'Original preempt_compaction still executes before ASR and writes bm_tasks/bm_meta activity_revision; no zero-SQL claim; code and order unchanged',
    'no_author_candidate_or_producer_test_modification_by_reviewer': True,
    'devices_network_model_private_database_axis_accessed_by_reviewer': False,
    'reviewer_actual_files_touched': 'Only independent_review artifacts',
    'four_file_confirmation_trace_candidate': 'NOT_REVIEWED_NOT_APPROVED_FOR_PRODUCTION',
    'live_boundary': 'Review is synthetic/local. Root still owns exact-source deployment and live enrollment acceptance'}
(HERE / 'REVIEW_VERDICT.json').write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding='utf-8')
text = '''两文件空语音修复独立审阅：最终候选通过，无代码阻断点。

board_asr.py final SHA256 c51488ac6bd3563bc3dc42934b321e98e26cb2b58d700318765a60ca4908ef60
board_dialogue_jobs.py final SHA256 01b27ede0d8889c35fc9ac990e03538a55fecc7c6a604fb6f781bc5d54c09087

独立7场景全过：同错误文本的普通ValueError、同名但不同类的异常、在ASR之后抛出的真正BoardNoSpeech，都保持generic错误与原reset；真正ASR typed空结果才走entry_rejected、保留原授权epoch/owner/expiry并不进入LLM、身份命令、声纹采样或对话提交；直接raw换行、制表和CRLF保持原协议拒绝。测试完全基于RAM合成，未打开设备、网络、模型或真实库。

整模块AST逆向核验通过。ASR只新增BoardNoSpeech(ValueError)，将原空结果raise换成该类型，原PCM约束、解码、锁、取消/期限和正常返回不变。Jobs只新增该类型import、raw空白局部分类、transcribe调用的窄catch；catch再次执行原_check后才转原_entry_error。最终raw空白检查位于原类型/长度及控制字符拒绝之后。其余Jobs模块AST相同，原guard/SQL顺序/锁顺序/faceowner/TTL/ACK/播放语义未改。

作者实际流水线专项XML核实：最终31/31通过，基线23通过/8失败/0error。原70项两版各63通过、相同7失败、0error；作者解释为4个旧称呼别名和3个GUI夹具缺character_pair，保留此边界。中间Jobs2d684只有4个异常反例已过，其控制字符顺序随后收紧；本通过结论仅属于最终01b27。

数据库表述边界：原store.preempt_compaction在ASR之前执行，会维护bm_tasks和bm_meta activity_revision，最终两文件保留了这段既有SQL及顺序。因此可说没有新增对话/身份/声纹保存事务，不能说全流程零SQL写入。未为消除维护SQL而扩大本修复范围。

四文件confirmation_failure_trace候选未审阅、不计通过、不建议随本修复发布。审阅者只写本地independent_review产物，未改作者候选/测试或生产。部署及现场人脸→声纹→ACTIVE验收仍归root。
'''
(HERE / 'REVIEW.txt').write_text(text, encoding='utf-8')
print(json.dumps({name: sha(HERE/name) for name in ('REVIEW_VERDICT.json', 'REVIEW.txt', 'STATIC_AUDIT.json', 'INDEPENDENT_COUNTEREXAMPLES.xml', 'test_independent_no_speech.py')}))
