"""Correct production-entry single-pin publication audit: parse/read/hash only."""
import ast
import base64
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;RELEASE=HERE.parent;TASK=RELEASE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
KEY='tools/production_board_business_gui.py'
BEFORE='b01f6edb9efe88cf95da60900e5ccc32eec93a24ef3f515ab08f51ae2ee6ada8'
AFTER='279ef8deb388e963e846453de71ddfe865fc05ab49e78c496321537234407168'
BASE='474f6640b4a2df3383b8ccb2814db7fe3448965c078dd87f972ba0997b23f7b2'
PREDICTED='e2d8fbbf2f414c322e188038a188f10eec0552c355b00f4d716f3f661c47fab9'
manifest=json.loads((TASK/'SOURCE_MANIFEST.json').read_bytes())
release_manifest=json.loads((RELEASE/'RELEASE_MANIFEST.json').read_bytes())
assert set(manifest['files'])=={KEY}
assert manifest['files'][KEY]['before_sha256']==sha(TASK/'baseline_runtime'/KEY)==BEFORE
assert manifest['files'][KEY]['after_sha256']==sha(TASK/'candidate_runtime'/KEY)==AFTER
assert release_manifest['source_before']=={KEY:BEFORE} and release_manifest['source_after']=={KEY:AFTER}
assert release_manifest['base_startup_sha256']==BASE and release_manifest['predicted_startup_after_sha256']==PREDICTED
for name,digest in release_manifest['generated_files'].items():assert sha(RELEASE/name)==digest
texts={n:(RELEASE/n).read_text(encoding='utf-8') for n in ('stop_gui_once.py','apply_fix_once.py','start_gui_once.py')}
trees={n:ast.parse(v) for n,v in texts.items()}
def assignment(name,var):return next(n.value for n in trees[name].body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==var for t in n.targets))
def literal(name,var):return ast.literal_eval(assignment(name,var))
payload=literal('apply_fix_once.py','PAYLOAD')
assert payload['base_startup_sha256']==BASE and set(payload['files'])=={KEY}
entry=payload['files'][KEY];decoded=base64.b64decode(entry['payload_base64'],validate=True)
assert entry['before_sha256']==BEFORE and entry['candidate_sha256']==hashlib.sha256(decoded).hexdigest()==AFTER
assert decoded==(TASK/'candidate_runtime'/KEY).read_bytes()
assert literal('apply_fix_once.py','KEYS')=={KEY} and literal('start_gui_once.py','TARGETS')=={KEY:AFTER}
assert literal('stop_gui_once.py','EXPECTED_STARTUP')==BASE
def path_value(name,var):
 node=assignment(name,var);assert isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='Path'
 return ast.literal_eval(node.args[0])
assert {path_value(n,'TX') for n in texts}=={'/home/root/aura-5090-recovery-20261102-a6d4a069/voice-threshold-035-production-entry-v1'}
assert path_value('stop_gui_once.py','OVERRIDE')==path_value('start_gui_once.py','OVERRIDE')
guard=literal('stop_gui_once.py','GUARD')
assert guard==literal('start_gui_once.py','GUARD')==b'[Service]\nKillMode=process\nSendSIGKILL=no\nTimeoutStopSec=infinity\n'
assert guard.count(b'\n')==4 and b'\\n' not in guard
old_raw=(RELEASE/'startup.before.read.json').read_bytes();new_raw=(RELEASE/'startup.after.predicted.json').read_bytes()
assert hashlib.sha256(old_raw).hexdigest()==BASE and hashlib.sha256(new_raw).hexdigest()==PREDICTED
old,new=json.loads(old_raw),json.loads(new_raw)
assert len(old['component_sha256'])==len(new['component_sha256'])==380
assert set(old['component_sha256'])==set(new['component_sha256'])
assert {k for k in old['component_sha256'] if old['component_sha256'][k]!=new['component_sha256'][k]}=={KEY}
assert {k:v for k,v in old.items() if k!='component_sha256'}=={k:v for k,v in new.items() if k!='component_sha256'}
assert old['component_sha256'][KEY]==BEFORE and new['component_sha256'][KEY]==AFTER
preserved={'board/runtime/board_speaker_business.py':'e229b6c3c64e75373e74d5fa136b633174ddf9897f6e95bc368899de9dc2c3d7',
 'tools/provisional_voice.py':'1ac360902f2b5790cb0b047110ef0d267940031caaaf20b91ec75c7fef1ab47c',
 'tools/yuki_business_gui.py':'6f04e9f8d7a87a8741f41f321f1c51478236be0b1cec7db7983c7b23f63764fd'}
assert all(old['component_sha256'][k]==new['component_sha256'][k]==v for k,v in preserved.items())
def methods(path):
 tree=ast.parse(path.read_bytes());c=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ProductionGuiBoardBusiness')
 return {n.name:n for n in c.body if isinstance(n,ast.FunctionDef)}
before,after=methods(TASK/'baseline_runtime'/KEY),methods(TASK/'candidate_runtime'/KEY)
assert {k for k in before if ast.dump(before[k],include_attributes=False)!=ast.dump(after[k],include_attributes=False)}=={'_attach_speaker'}
calls=[n for n in ast.walk(after['_attach_speaker']) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='create' and isinstance(n.func.value,ast.Name) and n.func.value.id=='BoardSpeakerBusiness']
assert len(calls)==1
calibration=next(k.value for k in calls[0].keywords if k.arg=='calibration')
assert isinstance(calibration,ast.Dict)
calibration_values=ast.literal_eval(calibration)
assert calibration_values=={'threshold':.35,'margin':.1,'consistency':.6,'field_calibrated':False}
mutations=[]
for name,tree in trees.items():
 for c in ast.walk(tree):
  if isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and c.func.attr=='run' and isinstance(c.func.value,ast.Name) and c.func.value.id=='subprocess' and c.args and isinstance(c.args[0],ast.List):
   p=c.args[0].elts
   if len(p)>1 and all(isinstance(n,ast.Constant) for n in p[:2]) and p[0].value=='systemctl' and p[1].value in ('start','stop','restart','kill','try-restart'):
    assert p[1].value in ('start','stop') and isinstance(p[-1],ast.Constant) and p[-1].value=='aura-avatar-ui.service'
    mutations.append((name,p[1].value))
assert mutations==[('stop_gui_once.py','stop'),('start_gui_once.py','start')]
stop,apply,start=(texts[n] for n in ('stop_gui_once.py','apply_fix_once.py','start_gui_once.py'))
for piece in ("before['MainPID'] == '266240'","Path('/proc/266240/stat')","== '1966956'","Path('/proc/266299/stat')","== '1970527'",'ccbc67ecf109ddbd5098b410e137fd258aa68b8161b7290ddb2c746bd30ead85','GUI_STOP_PENDING_NO_FORCE'):
 assert piece in stop
assert "not Path('/proc/266240').exists() and not Path('/proc/266299').exists()" in apply
for text in texts.values():assert all(x in text for x in ('1332','2236','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'))
assert "'other_component_pins_preserved': 379" in apply
assert 'if raw(path) == after[path]: replace(path, after[path], before[path])' in apply
assert 'assert len(pair_pins) == 10 and not (set(pair_pins) & KEYS)' in apply
assert "binding = json.loads(raw(selected['path'])); assert len(binding['source_sha256']) == 26" in apply
assert '99c53c5992355a2a4dfdedceb3cc90d813981328456b987e503459fe6d0691b5' in apply
assert 'OVERRIDE.read_bytes() == GUARD' in start and 'OVERRIDE.unlink()' in start
assert "assert all(props[k] == before[k] for k in ('Restart', 'KillMode', 'SendSIGKILL', 'TimeoutStopUSec'))" in start
report={'schema':'aura-threshold035-production-entry-release-review-1','sealed_host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'verdict':'PASS_CORRECT_PRODUCTION_ENTRY_SINGLE_PIN_RELEASE_NO_BLOCKER',
 'target':KEY,'before_sha256':BEFORE,'after_sha256':AFTER,'base_startup_sha256':BASE,'predicted_startup_after_sha256':PREDICTED,
 'payload_equals_candidate_and_manifests':True,'only_one_pin_changed_other379_and_all_other_fields_preserved':True,
 'earlier_three_threshold_product_pins_preserved':preserved,
 'actual_ProductionGuiBoardBusiness_attach_speaker_passes_explicit_calibration':calibration_values,
 'other_ProductionGuiBoardBusiness_methods_AST_unchanged':True,
 'GUI266240_GTK266299_birth_cmd_guards_match_request':True,
 'normal_stop_start_once_GUI_only_no_force_camera1332_untouched':True,
 'temporary_guard_true_newlines_path_and_bytes_match_restore_original4_properties':True,
 'byte_CAS_owner_recheck_conditioned_rollback_preserved':True,'selected_face26_and_formal_pair10_guards_preserved':True,
 'generated_file_hashes_verified':release_manifest['generated_files'],
 'old_V2_not_reviewed_or_approved_here':True,
 'device_network_private_database_audio_or_product_release_code_executed':False,
 'product_or_release_artifacts_modified':False,'live_actual_threshold_readback_not_claimed':True}
(HERE/'REVIEW_VERDICT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'verdict':report['verdict'],'report_sha256':sha(HERE/'REVIEW_VERDICT.json'),
 'candidate_sha256':AFTER,'predicted_startup_after_sha256':PREDICTED,'generated_files':release_manifest['generated_files']}))
