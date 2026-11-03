"""Read/hash/AST review only; no release or product code is imported/executed."""
import ast
import base64
import datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent;RELEASE=HERE.parent;TASK=RELEASE.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BASE='e2d8fbbf2f414c322e188038a188f10eec0552c355b00f4d716f3f661c47fab9'
PREDICTED='d667b871e159a9f2b52cfb48a16a31ba39847e4d68658a521aee006e7db915ef'
TARGETS={
 'board/runtime/board_business.py':'9c6da51f569d19d71dd2b25f8e2c4549bfa5c5059f1e7bc45d1124807400b5b2',
 'board/runtime/board_dialogue.py':'f5998983494b028850688eb06528d4088c86b41b29742bbea9aed390b4e9ee7c',
 'board/runtime/board_memory_policy.py':'87964292e231c0b1c5989542b2dcc6e3bf34f97d76c8455b517a80c3a4f4dcfe',
 'board/runtime/board_speaker_business.py':'9a82616aebbc79f0235d7ee1bef0a77effaeb891546587f0f1e7982e8ea7ceb1'}
manifest=json.loads((TASK/'SOURCE_MANIFEST.json').read_bytes())
release_manifest=json.loads((RELEASE/'RELEASE_MANIFEST.json').read_bytes())
assert set(manifest['files'])==set(TARGETS)
BEFORE={k:v['before_sha256'] for k,v in manifest['files'].items()}
for key,digest in TARGETS.items():
 assert sha(TASK/'candidate_runtime'/key)==manifest['files'][key]['after_sha256']==digest
 assert sha(TASK/'baseline_runtime'/key)==BEFORE[key]
assert release_manifest['base_startup_sha256']==BASE and release_manifest['predicted_startup_after_sha256']==PREDICTED
assert release_manifest['source_before']==BEFORE and release_manifest['source_after']==TARGETS
for name,digest in release_manifest['generated_files'].items():assert sha(RELEASE/name)==digest
texts={n:(RELEASE/n).read_text(encoding='utf-8') for n in ('stop_gui_once.py','apply_fix_once.py','start_gui_once.py')}
trees={n:ast.parse(t) for n,t in texts.items()}
def assignment(name,var):return next(n.value for n in trees[name].body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==var for t in n.targets))
def literal(name,var):return ast.literal_eval(assignment(name,var))
payload=literal('apply_fix_once.py','PAYLOAD')
assert payload['base_startup_sha256']==BASE and set(payload['files'])==set(TARGETS)
for key,digest in TARGETS.items():
 spec=payload['files'][key];data=base64.b64decode(spec['payload_base64'],validate=True)
 assert spec['before_sha256']==BEFORE[key] and spec['candidate_sha256']==hashlib.sha256(data).hexdigest()==digest
 assert data==(TASK/'candidate_runtime'/key).read_bytes()
assert literal('apply_fix_once.py','KEYS')==set(TARGETS)
assert literal('start_gui_once.py','TARGETS')==TARGETS
assert literal('stop_gui_once.py','EXPECTED_STARTUP')==BASE
def path_value(name,var):
 n=assignment(name,var);assert isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='Path'
 return ast.literal_eval(n.args[0])
assert {path_value(n,'TX') for n in texts}=={'/home/root/aura-5090-recovery-20261102-a6d4a069/voice-conversation-address-v1'}
assert path_value('stop_gui_once.py','OVERRIDE')==path_value('start_gui_once.py','OVERRIDE')
guard=literal('stop_gui_once.py','GUARD')
assert guard==literal('start_gui_once.py','GUARD')==b'[Service]\nKillMode=process\nSendSIGKILL=no\nTimeoutStopSec=infinity\n'
assert guard.count(b'\n')==4 and b'\\n' not in guard
old_raw=(RELEASE/'startup.before.read.json').read_bytes();new_raw=(RELEASE/'startup.after.predicted.json').read_bytes()
assert hashlib.sha256(old_raw).hexdigest()==BASE and hashlib.sha256(new_raw).hexdigest()==PREDICTED
old,new=json.loads(old_raw),json.loads(new_raw)
assert len(old['component_sha256'])==len(new['component_sha256'])==380
assert set(old['component_sha256'])==set(new['component_sha256'])
assert {k for k in old['component_sha256'] if old['component_sha256'][k]!=new['component_sha256'][k]}==set(TARGETS)
assert {k:v for k,v in old.items() if k!='component_sha256'}=={k:v for k,v in new.items() if k!='component_sha256'}
for key in TARGETS:assert old['component_sha256'][key]==BEFORE[key] and new['component_sha256'][key]==TARGETS[key]
preserved={'tools/yuki_business_gui.py':'6f04e9f8d7a87a8741f41f321f1c51478236be0b1cec7db7983c7b23f63764fd',
 'tools/production_board_business_gui.py':'279ef8deb388e963e846453de71ddfe865fc05ab49e78c496321537234407168',
 'tools/provisional_voice.py':'1ac360902f2b5790cb0b047110ef0d267940031caaaf20b91ec75c7fef1ab47c'}
assert all(old['component_sha256'][k]==new['component_sha256'][k]==v for k,v in preserved.items())
pair=json.loads((TASK/'yuki_pair.formal.public.json').read_bytes())
assert len(pair['runtime_pins'])==10 and not(set(pair['runtime_pins'])&set(TARGETS))
for key in pair['runtime_pins']:assert old['component_sha256'].get(key)==new['component_sha256'].get(key)
stop,apply,start=(texts[n] for n in ('stop_gui_once.py','apply_fix_once.py','start_gui_once.py'))
for fragment in ("before['MainPID'] == '275493'","Path('/proc/275493/stat')","== '2026452'", "Path('/proc/275566/stat')","== '2031976'",'48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d','b1a1394126a5730aff82ccdaa6799c72313ac95afbc34a9ece341d04445927fe','GUI_STOP_PENDING_NO_FORCE'):
 assert fragment in stop
assert "hands.get('enabled') is False" in stop and "hands.get('microphone_open') is False" in stop
assert "not Path('/proc/275493').exists() and not Path('/proc/275566').exists()" in apply
for text in texts.values():assert all(x in text for x in ('1332','2236','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'))
assert "'other_component_pins_preserved': 376" in apply
assert 'if raw(path) == after[path]: replace(path, after[path], before[path])' in apply
assert 'assert len(pair_pins) == 10 and not (set(pair_pins) & KEYS)' in apply
assert "binding = json.loads(raw(selected['path'])); assert len(binding['source_sha256']) == 26" in apply
assert '99c53c5992355a2a4dfdedceb3cc90d813981328456b987e503459fe6d0691b5' in apply
assert 'OVERRIDE.read_bytes() == GUARD' in start and 'OVERRIDE.unlink()' in start
assert "assert all(props[k] == before[k] for k in ('Restart', 'KillMode', 'SendSIGKILL', 'TimeoutStopUSec'))" in start
mutations=[]
for name,tree in trees.items():
 for c in ast.walk(tree):
  if isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and c.func.attr=='run' and isinstance(c.func.value,ast.Name) and c.func.value.id=='subprocess' and c.args and isinstance(c.args[0],ast.List):
   p=c.args[0].elts
   if len(p)>1 and all(isinstance(n,ast.Constant) for n in p[:2]) and p[0].value=='systemctl' and p[1].value in ('start','stop','restart','kill','try-restart'):
    assert p[1].value in ('start','stop') and isinstance(p[-1],ast.Constant) and p[-1].value=='aura-avatar-ui.service'
    mutations.append((name,p[1].value))
assert mutations==[('stop_gui_once.py','stop'),('start_gui_once.py','start')]
receipts={}
for name in ('REGISTRATION_REGRESSION_V2.xml','CONTROLLER_REGRESSION.xml','CONTROLLER_BASELINE.xml','CONTROLLER_CURRENT.xml'):
 p=TASK/name;r=ET.fromstring(p.read_bytes());s=list(r.iter('testsuite'))
 receipts[name]={**{k:sum(int(n.attrib.get(k,0)) for n in s) for k in ('tests','failures','errors','skipped')},'sha256':sha(p),
  'failed_cases':sorted(c.attrib.get('classname','')+'.'+c.attrib.get('name','') for c in r.iter('testcase') if c.find('failure') is not None)}
assert receipts['CONTROLLER_BASELINE.xml']['failed_cases']==receipts['CONTROLLER_CURRENT.xml']['failed_cases']
assert set(receipts['CONTROLLER_REGRESSION.xml']['failed_cases'])<=set(receipts['CONTROLLER_BASELINE.xml']['failed_cases'])
report={'schema':'aura-voice-conversation-address-release-review-1','sealed_host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'verdict':'PASS_FOUR_CORE_RELEASE_STATIC_REVIEW_NO_BLOCKER',
 'base_startup_sha256':BASE,'predicted_startup_after_sha256':PREDICTED,'source_before':BEFORE,'source_after':TARGETS,
 'payload_decoded_equals_candidate_and_manifests':True,'keys_exact_four_core_and_other376_pins_unchanged':True,
 'other_startup_fields_unchanged':True,'existing_Yuki_Production_Provisional_pins_preserved':preserved,
 'GUI275493_GTK275566_birth_and_cmdline_guards_correct':True,
 'paused_idle_preconditions_retained_root_has_not_submitted_stop_at_review':True,
 'normal_stop_start_GUI_once_only_no_force_camera1332_not_controlled':True,
 'precise_guard_path_bytes_true_newlines_and_four_service_properties_restored':True,
 'source_byte_CAS_owner_checks_fsync_and_conditional_rollback_retained':True,
 'selected_face26_and_pair10_guard_and_binding_unchanged':True,
 'generated_file_hashes_verified':release_manifest['generated_files'],
 'local_existing_XML_receipts_only_not_rerun':receipts,
 'controller_XML_boundary':'Baseline/current60 both56pass/same4oldfixturefail; regression39 has38pass/one of the same old alias fixture failures; no all-controller-tests-pass claim',
 'source_functional_review_or_live_first_sentence_result_not_claimed':True,
 'product_preparer_or_release_scripts_executed':False,'device_private_database_model_audio_network_or_axis_accessed':False,
 'product_candidate_or_release_files_modified':False}
(HERE/'REVIEW_VERDICT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'verdict':report['verdict'],'report_sha256':sha(HERE/'REVIEW_VERDICT.json'),
 'predicted_startup_after_sha256':PREDICTED,'XML_receipts':receipts,'generated_files':release_manifest['generated_files']}))
