import ast
import base64
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;NEW=HERE/'recovery_stability_20261102_v3';PREVIOUS=HERE/'py39_fix'
prior=json.loads((PREVIOUS/'INDEPENDENT_REVIEW.json').read_text(encoding='utf-8'))
review=json.loads((NEW/'INDEPENDENT_REVIEW.json').read_text(encoding='utf-8'))
tests=json.loads((NEW/'PURE_TESTS.json').read_text(encoding='utf-8'))
board=json.loads((NEW/'PURE_TESTS_BOARD_PY39.json').read_text(encoding='utf-8'))
assert tests['status']==board['status']=='PASS' and tests['tests_run']==board['tests']['tests_run']==42
old={r['file']:r['after'] for r in prior['records']};expected={};changes={}
for r in review['records']:
    name=r['file'];data=(NEW/'candidate'/name).read_bytes();assert hashlib.sha256(data).hexdigest()==r['after']
    expected[name]=dict(before=old[name],after=r['after'])
    if old[name]!=r['after']:changes[name]=base64.b64encode(data).decode()
assert set(changes)=={'run_face_motion.py','continuous_face_control.py','continuous_session.py'}
assert board['candidate_core_sha256']==expected['continuous_face_control.py']['after']
source=(HERE/'apply_left40_right45.template.py').read_text(encoding='utf-8')
substitutions={
    "import stat\n":"import stat\nimport subprocess\n",
    "OLD=Path('/home/root/aura-pan-wide-20261028/control-10282601-target45-9adb90c3')":
    "OLD=Path('/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-py39-14e598cf')",
    "NEW=OLD.with_name('control-10282601-left40-right45-aaaa15bf')":
    "NEW=OLD.with_name('control-10282601-left40-right45-stable150-35d5e154')",
    'original-follow-left40-right45-v1':'original-follow-left40-right45-v3-stable150',
    'bcb773cd5bf306ac536df0373d1c1b27d01b6564a35839f2623b274442c13a59':'941b8fc4814eabecf3063b74a968b17a2b649c9573e4f2d04698a780a8fe7c74',
    '775fa3c5d5f694ff8d9eadffb03fe7180935812cc4ab8b55eaa70105a0be66ed':'29fb4ab0bfb5b00037cde25a1e5b3ab0dfc7706f6cc95a5a37fb076e3d6c3829',
    'cfe36df907fc195b083cbf6b44c7e120cbf613324e821c626bac169ad77a5d8b':'da3ecf2fd05f3146ab56c1c969090c9902d3b7af2d1b5753d5e41307f1e9afed',
    "candidate_manifest['scope']=manifest['scope']+'; optional left stop target latched by original trigger side; left 0.40 / right 0.45'":
    "candidate_manifest['scope']=manifest['scope']+'; opt-in 150ms and 3 admitted images plus new detection before rearm after protective interruption; original STOP/TTL/lease unchanged'",
    "new_face['arguments']['target-center-ratio']='0.45';new_face['arguments']['left-target-center-ratio']='0.40'":
    "new_face['arguments']['target-center-ratio']='0.45';new_face['arguments']['left-target-center-ratio']='0.40';new_face['arguments']['rearm-stability-ms']='150'",
    "for name in CHANGES:compile(payload[name],str(NEW/name),'exec')":
    "for name in CHANGES:compile(payload[name],str(NEW/name),'exec')\nprobe=subprocess.run(['python3','-B','-c','import sys;sys.path.insert(0,'+repr(str(NEW))+');import continuous_face_control,continuous_session,hardware_slew_session,run_face_motion;assert continuous_face_control.EdgeConfig(rearm_stability_ms=150).rearm_stability_ms==150;assert not any(x in sys.modules for x in (\\\"vsrv_driver\\\",\\\"trajectory\\\"))'],capture_output=True,text=True,timeout=5)\nassert probe.returncode==0,probe.stderr",
    'ORIGINAL_FOLLOW_LEFT40_RIGHT45_SELECTED_STOPPED':'ORIGINAL_FOLLOW_LEFT40_RIGHT45_STABLE150_SELECTED_STOPPED',
    'left_stop_target_center_ratio=.4,right_stop_target_center_ratio=.45,center_tolerance_ratio=.03,':
    'left_stop_target_center_ratio=.4,right_stop_target_center_ratio=.45,center_tolerance_ratio=.03,rearm_stability_ms=150,rearm_min_distinct_sources=3,rearm_requires_new_detection=True,',
}
for old_text,new_text in substitutions.items():
    assert source.count(old_text)==1,(old_text,source.count(old_text));source=source.replace(old_text,new_text,1)
source=source.replace('PAYLOAD_BASE64',base64.b64encode(json.dumps(changes).encode()).decode()).replace(
    'EXPECTED_BASE64',base64.b64encode(json.dumps(expected).encode()).decode())
ast.parse(source);p=NEW/'apply_stable150.prepared.py';assert not p.exists();p.write_text(source,encoding='utf-8')
intent=dict(action='versioned_original_follower_recovery_stability_gate',board_python39_tests=42,windows_python310_tests=42,
    publication_script_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),changed_sources=sorted(changes),
    rearm_stability_ms=150,rearm_distinct_sources=3,requires_new_detection=True,left_target=.4,right_target=.45,
    source_ttl_ms=250,detection_anchor_ttl_ms=500,protection_stop_immediate=True,
    limitation='Reduces short restart bursts; it cannot prevent genuine source loss or prove shaft mechanics. Field acceptance remains pending.')
(NEW/'PUBLICATION_INTENT.json').write_text(json.dumps(intent,indent=2)+'\n',encoding='utf-8')
print(json.dumps(intent,indent=2))
