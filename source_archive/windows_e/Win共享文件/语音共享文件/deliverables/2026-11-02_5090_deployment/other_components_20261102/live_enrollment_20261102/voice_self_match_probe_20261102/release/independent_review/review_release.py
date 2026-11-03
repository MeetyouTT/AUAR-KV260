"""Parse/hash final local publication artifacts. Never imports/executes release code."""
import ast
import base64
import copy
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
RELEASE=HERE.parent
PROBE=RELEASE.parent
ENROLL=PROBE.parent
TARGET='board/runtime/board_speaker_business.py'
BEFORE='6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816'
AFTER='f82bc71d00c355c164d43ca0b6a853ea6a32e67c84ffd228791d7070209b907e'
BASE='21c1dbcd454d50875d4fd61c970e269666257dd236c87103c12b1058965de51e'
PREDICTED='4b4d98494d43bd44aa21b28c960fd8480f0f61f4a5741f212fb541abdf4c147b'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_manifest=json.loads((PROBE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
release_manifest=json.loads((RELEASE/'RELEASE_MANIFEST.json').read_text(encoding='utf-8'))
assert set(source_manifest['files'])=={TARGET}
assert source_manifest['files'][TARGET]['before_sha256']==BEFORE
assert source_manifest['files'][TARGET]['after_sha256']==AFTER
assert sha(PROBE/'candidate_runtime'/TARGET)==AFTER
assert sha(PROBE/'baseline_runtime'/TARGET)==BEFORE
assert release_manifest['base_startup_sha256']==BASE
assert release_manifest['source_before']=={TARGET:BEFORE} and release_manifest['source_after']=={TARGET:AFTER}
assert release_manifest['predicted_startup_after_sha256']==PREDICTED
for name,digest in release_manifest['generated_files'].items():assert sha(RELEASE/name)==digest

texts={name:(RELEASE/name).read_text(encoding='utf-8') for name in ('stop_gui_once.py','apply_fix_once.py','start_gui_once.py')}
trees={name:ast.parse(text) for name,text in texts.items()}
def assignment(tree,name):
 node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
 return node.value
def literal(name,var):return ast.literal_eval(assignment(trees[name],var))
payload=literal('apply_fix_once.py','PAYLOAD')
assert payload['base_startup_sha256']==BASE and set(payload['files'])=={TARGET}
entry=payload['files'][TARGET]
assert entry['before_sha256']==BEFORE and entry['candidate_sha256']==AFTER
decoded=base64.b64decode(entry['payload_base64'],validate=True)
assert hashlib.sha256(decoded).hexdigest()==AFTER and decoded==(PROBE/'candidate_runtime'/TARGET).read_bytes()
assert literal('apply_fix_once.py','KEYS')=={TARGET}
assert literal('start_gui_once.py','TARGETS')=={TARGET:AFTER}
assert literal('stop_gui_once.py','EXPECTED_STARTUP')==BASE
guards=[literal(name,'GUARD') for name in ('stop_gui_once.py','start_gui_once.py')]
assert guards[0]==guards[1]==b'[Service]\nKillMode=process\nSendSIGKILL=no\nTimeoutStopSec=infinity\n'
def path_constant(name,var):
 node=assignment(trees[name],var)
 assert isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='Path'
 return ast.literal_eval(node.args[0])
assert len({path_constant(n,'TX') for n in texts})==1
assert path_constant('stop_gui_once.py','OVERRIDE')==path_constant('start_gui_once.py','OVERRIDE')

base_raw=(ENROLL/'voice_entry_name_fix_20261102/release/startup.after.predicted.json').read_bytes()
new_raw=(RELEASE/'startup.after.predicted.json').read_bytes()
assert hashlib.sha256(base_raw).hexdigest()==BASE and hashlib.sha256(new_raw).hexdigest()==PREDICTED
old,new=json.loads(base_raw),json.loads(new_raw)
assert len(old['component_sha256'])==len(new['component_sha256'])==380
assert set(old['component_sha256'])==set(new['component_sha256'])
assert {k for k in old['component_sha256'] if old['component_sha256'][k]!=new['component_sha256'][k]}=={TARGET}
assert old['component_sha256'][TARGET]==BEFORE and new['component_sha256'][TARGET]==AFTER
assert {k:v for k,v in old.items() if k!='component_sha256'}=={k:v for k,v in new.items() if k!='component_sha256'}
assert old['component_sha256']['config/yuki_pair.formal.json']=='998710fc12bf442d6baea501bab0234665b666caa29f4be8f685741d50d82099'
pair=json.loads((PROBE/'yuki_pair.formal.public.json').read_text(encoding='utf-8'))
assert len(pair['runtime_pins'])==10 and TARGET not in pair['runtime_pins']

def helper_class(path,name):
 return ast.dump(next(n for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.ClassDef) and n.name==name),include_attributes=False)
for name in ('_WriterLease','_CheckedEncoder','_GuardedStore'):
 assert helper_class(PROBE/'baseline_runtime'/TARGET,name)==helper_class(PROBE/'candidate_runtime'/TARGET,name)

systemctl=[]
for filename,tree in trees.items():
 for call in ast.walk(tree):
  if (isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='run'
      and isinstance(call.func.value,ast.Name) and call.func.value.id=='subprocess'
      and call.args and isinstance(call.args[0],ast.List)):
   parts=call.args[0].elts
   if len(parts)>=2 and all(isinstance(n,ast.Constant) and isinstance(n.value,str) for n in parts[:2]) and parts[0].value=='systemctl':
    action=parts[1].value
    if action in ('start','stop','restart','kill','try-restart'):
     assert action in ('start','stop') and isinstance(parts[-1],ast.Constant) and parts[-1].value=='aura-avatar-ui.service'
     systemctl.append((filename,action))
assert systemctl==[('stop_gui_once.py','stop'),('start_gui_once.py','start')]
apply=texts['apply_fix_once.py'];stop=texts['stop_gui_once.py'];start=texts['start_gui_once.py']
assert "'other_component_pins_preserved': 379" in apply
assert 'if raw(path) == after[path]: replace(path, after[path], before[path])' in apply
assert "assert len(pair_pins) == 10 and not (set(pair_pins) & KEYS)" in apply
assert "binding = json.loads(raw(selected['path'])); assert len(binding['source_sha256']) == 26" in apply
assert "assert selected['sha256'] == sha(selected['path']) == '99c53c5992355a2a4dfdedceb3cc90d813981328456b987e503459fe6d0691b5'" in apply
assert "assert all(props[k] == before[k] for k in ('Restart', 'KillMode', 'SendSIGKILL', 'TimeoutStopUSec'))" in start
assert 'OVERRIDE.read_bytes() == GUARD' in start and 'OVERRIDE.unlink()' in start
assert 'GUI_STOP_PENDING_NO_FORCE' in stop and 'force_kill_authorized' in stop

report={
 'schema':'aura-self-match-single-file-release-static-review-1',
 'sealed_host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'verdict':'PASS_FINAL_RELEASE_ARTIFACT_BINDING_NO_BLOCKER_SOURCE_SUITES_PENDING_ROOT',
 'source_before_sha256':BEFORE,'source_after_sha256':AFTER,
 'base_startup_sha256':BASE,'predicted_startup_after_sha256':PREDICTED,
 'payload_decoded_equals_final_candidate_runtime_and_manifest':True,
 'only_one_source_and_one_component_pin_changed_other379_preserved':True,
 'other_startup_fields_unchanged':True,
 'formal_pair_10pins_exclude_target_and_guard_preserved':True,
 'selected_face_26source_descriptor_and_checks_preserved':True,
 'original_writer_encoder_and_store_owner_guards_AST_unchanged':True,
 'normal_GUI_stop_and_start_only_once_no_camera_control':True,
 'camera1332_boot_birth_cmdline_guards_preserved':True,
 'temporary_no_force_guard_exact_bytes_and_path_same_stop_start':True,
 'original_four_service_properties_verified_after_guard_removal':True,
 'source_byte_CAS_per_file_owner_checks_and_conditional_rollback_preserved':True,
 'release_manifest_generated_file_hashes_verified':release_manifest['generated_files'],
 'source_manifest_status_at_review':source_manifest.get('status'),
 'source_candidate_functional_or_safety_suite_verdict_not_part_of_this_release_binding_review':True,
 'release_scripts_preparer_device_or_network_executed':False,
 'real_private_database_or_axis_accessed':False,
 'candidate_preparer_or_generated_artifacts_modified':False}
(HERE/'FINAL_RELEASE_REVIEW.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'verdict':report['verdict'],'source_after_sha256':AFTER,
 'predicted_startup_after_sha256':PREDICTED,'report_sha256':sha(HERE/'FINAL_RELEASE_REVIEW.json'),
 'generated_files':release_manifest['generated_files']}))
