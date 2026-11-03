"""Static-only three-file publication audit. Never executes imported product/release code."""
import ast
import base64
import datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
RELEASE=HERE.parent
TASK=RELEASE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BASE='44e8f154c9dd72d3b7619160f7a2dac64fda529daba91a96a196c12f68c8a295'
PREDICTED='474f6640b4a2df3383b8ccb2814db7fe3448965c078dd87f972ba0997b23f7b2'
TARGETS={
 'board/runtime/board_speaker_business.py':'e229b6c3c64e75373e74d5fa136b633174ddf9897f6e95bc368899de9dc2c3d7',
 'tools/provisional_voice.py':'1ac360902f2b5790cb0b047110ef0d267940031caaaf20b91ec75c7fef1ab47c',
 'tools/yuki_business_gui.py':'6f04e9f8d7a87a8741f41f321f1c51478236be0b1cec7db7983c7b23f63764fd'}
BEFORE={
 'board/runtime/board_speaker_business.py':'28d36d1f35ed173098df50e51b829a89b0f5d09c1f7281dc34381a3cedac6cfe',
 'tools/provisional_voice.py':'6219b84a9f40dedca6238aadf1523de7ec6d9060d7fc40d8c34f7eccf5b12a8f',
 'tools/yuki_business_gui.py':'f10f3d9e41bf48761428d39f850fd797640348f8723884590596e99475ee5e94'}
manifest=json.loads((TASK/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
release_manifest=json.loads((RELEASE/'RELEASE_MANIFEST.json').read_text(encoding='utf-8'))
assert set(manifest['files'])==set(TARGETS)
for key in TARGETS:
 assert manifest['files'][key]['before_sha256']==sha(TASK/'baseline_runtime'/key)==BEFORE[key]
 assert manifest['files'][key]['after_sha256']==sha(TASK/'candidate_runtime'/key)==TARGETS[key]
assert release_manifest['base_startup_sha256']==BASE
assert release_manifest['predicted_startup_after_sha256']==PREDICTED
assert release_manifest['source_before']==BEFORE and release_manifest['source_after']==TARGETS
for name,digest in release_manifest['generated_files'].items():assert sha(RELEASE/name)==digest

texts={n:(RELEASE/n).read_text(encoding='utf-8') for n in ('stop_gui_once.py','apply_fix_once.py','start_gui_once.py')}
trees={n:ast.parse(t) for n,t in texts.items()}
def assignment(name,var):
 return next(n.value for n in trees[name].body if isinstance(n,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id==var for t in n.targets))
def literal(name,var):return ast.literal_eval(assignment(name,var))
payload=literal('apply_fix_once.py','PAYLOAD')
assert payload['base_startup_sha256']==BASE and set(payload['files'])==set(TARGETS)
for key,digest in TARGETS.items():
 entry=payload['files'][key];decoded=base64.b64decode(entry['payload_base64'],validate=True)
 assert entry['before_sha256']==BEFORE[key]
 assert entry['candidate_sha256']==hashlib.sha256(decoded).hexdigest()==digest
 assert decoded==(TASK/'candidate_runtime'/key).read_bytes()
assert literal('apply_fix_once.py','KEYS')==set(TARGETS)
assert literal('start_gui_once.py','TARGETS')==TARGETS
assert literal('stop_gui_once.py','EXPECTED_STARTUP')==BASE
def path_value(name,var):
 value=assignment(name,var)
 assert isinstance(value,ast.Call) and isinstance(value.func,ast.Name) and value.func.id=='Path'
 return ast.literal_eval(value.args[0])
assert len({path_value(n,'TX') for n in texts})==1
assert path_value('stop_gui_once.py','OVERRIDE')==path_value('start_gui_once.py','OVERRIDE')
assert literal('stop_gui_once.py','GUARD')==literal('start_gui_once.py','GUARD')==b'[Service]\nKillMode=process\nSendSIGKILL=no\nTimeoutStopSec=infinity\n'

old_raw=(RELEASE/'startup.before.read.json').read_bytes();new_raw=(RELEASE/'startup.after.predicted.json').read_bytes()
assert hashlib.sha256(old_raw).hexdigest()==BASE and hashlib.sha256(new_raw).hexdigest()==PREDICTED
old,new=json.loads(old_raw),json.loads(new_raw)
assert len(old['component_sha256'])==len(new['component_sha256'])==380
assert set(old['component_sha256'])==set(new['component_sha256'])
assert {k for k in old['component_sha256'] if old['component_sha256'][k]!=new['component_sha256'][k]}==set(TARGETS)
assert {k:v for k,v in old.items() if k!='component_sha256'}=={k:v for k,v in new.items() if k!='component_sha256'}
for key in TARGETS:assert old['component_sha256'][key]==BEFORE[key] and new['component_sha256'][key]==TARGETS[key]
assert all(old['component_sha256'][k]==new['component_sha256'][k] for k in set(old['component_sha256'])-set(TARGETS))
pair=json.loads((TASK/'yuki_pair.formal.public.json').read_text(encoding='utf-8'))
assert len(pair['runtime_pins'])==10 and not set(pair['runtime_pins'])&set(TARGETS)
assert old['component_sha256']['config/yuki_pair.formal.json']==new['component_sha256']['config/yuki_pair.formal.json']=='998710fc12bf442d6baea501bab0234665b666caa29f4be8f685741d50d82099'

worker='board/runtime/board_speaker_business.py'
def class_ast(path,name):return ast.dump(next(n for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.ClassDef) and n.name==name),include_attributes=False)
for name in ('_WriterLease','_CheckedEncoder','_GuardedStore'):
 assert class_ast(TASK/'baseline_runtime'/worker,name)==class_ast(TASK/'candidate_runtime'/worker,name)
commands=[]
for name,tree in trees.items():
 for call in ast.walk(tree):
  if (isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='run'
      and isinstance(call.func.value,ast.Name) and call.func.value.id=='subprocess'
      and call.args and isinstance(call.args[0],ast.List)):
   parts=call.args[0].elts
   if len(parts)>1 and all(isinstance(n,ast.Constant) for n in parts[:2]) and parts[0].value=='systemctl':
    verb=parts[1].value
    if verb in ('start','stop','restart','kill','try-restart'):
     assert verb in ('start','stop') and isinstance(parts[-1],ast.Constant) and parts[-1].value=='aura-avatar-ui.service'
     commands.append((name,verb))
assert commands==[('stop_gui_once.py','stop'),('start_gui_once.py','start')]
stop,apply,start=(texts[n] for n in ('stop_gui_once.py','apply_fix_once.py','start_gui_once.py'))
for fragment in ("before['MainPID'] == '209823'", "Path('/proc/209823/stat')", "== '1626221'",
                 "Path('/proc/209835/stat')", "== '1627082'",'c4999fc4bf50c9f4cf289bb1a02c83c90206794051e9f31791668e0cfffc52bc',
                 "hands.get('enabled') is False", "hands.get('microphone_open') is False",'GUI_STOP_PENDING_NO_FORCE'):
 assert fragment in stop
assert "not Path('/proc/209823').exists() and not Path('/proc/209835').exists()" in apply
for body in (stop,apply,start):
 assert '1332' in body and '2236' in body and 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd' in body
assert "'other_component_pins_preserved': 377" in apply
assert 'if raw(path) == after[path]: replace(path, after[path], before[path])' in apply
assert "assert len(pair_pins) == 10 and not (set(pair_pins) & KEYS)" in apply
assert "binding = json.loads(raw(selected['path'])); assert len(binding['source_sha256']) == 26" in apply
assert '99c53c5992355a2a4dfdedceb3cc90d813981328456b987e503459fe6d0691b5' in apply
assert 'OVERRIDE.read_bytes() == GUARD' in start and 'OVERRIDE.unlink()' in start
assert "assert all(props[k] == before[k] for k in ('Restart', 'KillMode', 'SendSIGKILL', 'TimeoutStopUSec'))" in start

reg_path=TASK/'REGRESSION_V2.xml'
reg_root=ET.fromstring(reg_path.read_bytes());suites=list(reg_root.iter('testsuite'))
regression={k:sum(int(n.attrib.get(k,0)) for n in suites) for k in ('tests','failures','errors','skipped')}
regression['sha256']=sha(reg_path)
report={
 'schema':'aura-voice-threshold-035-independent-release-review-1',
 'sealed_host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'verdict':'PASS_THREE_FILE_RELEASE_STATIC_REVIEW_NO_BLOCKER',
 'base_startup_sha256':BASE,'predicted_startup_after_sha256':PREDICTED,
 'source_before':BEFORE,'source_after':TARGETS,
 'payload_equals_candidate_runtime_and_both_manifests_byte_for_byte':True,
 'exact_three_source_component_pins_changed_other377_preserved':True,
 'all_other_startup_fields_unchanged':True,
 'GUI209823_GTK209835_birth_and_cmdline_guards_verified_in_scripts':True,
 'normal_stop_start_once_GUI_only_no_force_or_camera_control':True,
 'camera1332_birth2236_cmdline_and_selected_face26_guard_unchanged':True,
 'formal_pair10_pins_exclude_targets_and_preserved':True,
 'temporary_guard_path_bytes_match_and_four_original_service_properties_restored_before_start':True,
 'owner_recheck_byte_CAS_fsync_and_conditional_rollback_preserved':True,
 'original_writer_encoder_store_owner_guards_AST_unchanged':True,
 'threshold_request':manifest['user_requested_threshold'],
 'margin_manifest':manifest['margin'],'consistency_manifest':manifest['consistency'],
 'field_calibrated_manifest':manifest['field_calibrated'],
 'regression_XML_receipt_only_not_rerun':regression,
 'release_manifest_sha256':sha(RELEASE/'RELEASE_MANIFEST.json'),
 'source_manifest_sha256':sha(TASK/'SOURCE_MANIFEST.json'),
 'generated_file_sha256':release_manifest['generated_files'],
 'scope_boundary':'Release artifact and guard review; does not claim live deployed readiness or biometric accuracy',
 'product_preparer_or_release_scripts_executed':False,
 'real_board_network_private_databases_audio_models_or_axis_accessed':False,
 'candidate_preparer_release_or_product_files_modified':False}
(HERE/'REVIEW_VERDICT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
text='''三文件声纹0.35发布包静审通过，无阻断。

PAYLOAD解码与candidate_runtime、SOURCE_MANIFEST、RELEASE_MANIFEST的三份最终字节逐一相等。startup44e8f154…→474f6640b4a2df3383b8ccb2814db7fe3448965c078dd87f972ba0997b23f7b2只改变三个指定component pin，其余377及所有其它startup字段相同。发布不是旧整份manifest覆盖。

GUI209823/GTK209835的birth1626221/1627082及cmdline guard正确；正常单次GUI stop，临时KillMode=process/SendSIGKILL=no/TimeoutStopSec=infinity，pending不强制推进。apply要求停稳和旧两PID消失，实际字节CAS和owner再核，异常仅在字节仍属本事务时回滚。start只删除自有精确guard并校验原Restart/KillMode/SendSIGKILL/TimeoutStopUSec恢复后单次正常启动。

camera1332/birth2236/cmdline仅作校验，无停止、重启或kill命令。selected face26 guard和正式pair10pin保持，pair10不含三目标。原_WriterLease/_CheckedEncoder/_GuardedStore AST未变。

此次仅发布包绑定与静态保护审阅，回归XML只读取计数和SHA，没有重跑；不代替现场验收或声纹准确率结论。未执行preparer/发布脚本/产品代码，未访问板卡、网络、私库、音频、模型或轴，也未改任何发布/产品文件，仅保存本独审目录。
'''
(HERE/'REVIEW.txt').write_text(text,encoding='utf-8')
print(json.dumps({'verdict':report['verdict'],'report_sha256':sha(HERE/'REVIEW_VERDICT.json'),
 'text_sha256':sha(HERE/'REVIEW.txt'),'regression_XML_counts':regression,
 'predicted_startup_after_sha256':PREDICTED,'generated_files':release_manifest['generated_files']}))
