import ast
import base64
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;FIX=HERE/'py39_fix'
v1=json.loads((HERE/'INDEPENDENT_REVIEW.json').read_text(encoding='utf-8'))
v2=json.loads((FIX/'INDEPENDENT_REVIEW.json').read_text(encoding='utf-8'))
tests=json.loads((FIX/'PURE_TESTS.json').read_text(encoding='utf-8'))
board=json.loads((FIX/'PURE_TESTS_BOARD_PY39.json').read_text(encoding='utf-8'))
assert tests['status']==board['status']=='PASS' and tests['tests_run']==board['tests']['tests_run']==31
old={r['file']:r['after'] for r in v1['records']};expected={};changes={}
for r in v2['records']:
    name=r['file'];data=(FIX/'candidate'/name).read_bytes();assert hashlib.sha256(data).hexdigest()==r['after']
    expected[name]=dict(before=old[name],after=r['after'])
    if old[name]!=r['after']:changes[name]=base64.b64encode(data).decode()
assert set(changes)=={'continuous_face_control.py'}
assert board['candidate_core_sha256']==expected['continuous_face_control.py']['after']
source=(HERE/'apply_left40_right45.template.py').read_text(encoding='utf-8')
substitutions={
    "import stat\n":"import stat\nimport subprocess\n",
    "OLD=Path('/home/root/aura-pan-wide-20261028/control-10282601-target45-9adb90c3')":
    "OLD=Path('/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-aaaa15bf')",
    "NEW=OLD.with_name('control-10282601-left40-right45-aaaa15bf')":
    "NEW=OLD.with_name('control-10282601-left40-right45-py39-14e598cf')",
    "original-follow-left40-right45-v1":"original-follow-left40-right45-v2-py39",
    'bcb773cd5bf306ac536df0373d1c1b27d01b6564a35839f2623b274442c13a59':'73e532adad9f4769149f6c8b57844fcdc23a3d6df274902015d51323f5390453',
    '775fa3c5d5f694ff8d9eadffb03fe7180935812cc4ab8b55eaa70105a0be66ed':'764ef06b4aa50d5806dff9695ee37716fd660b2ff43d3158aafa403ab72ff090',
    'cfe36df907fc195b083cbf6b44c7e120cbf613324e821c626bac169ad77a5d8b':'9856e25396a55ab4bf17cdcf80b3264aa756919121e19fcb17d89d985ac5097f',
    "assert len(CHANGES)==3 and set(CHANGES)=={'run_face_motion.py','continuous_face_control.py','continuous_session.py'}":
    "assert len(CHANGES)==1 and set(CHANGES)=={'continuous_face_control.py'}",
    "candidate_manifest['scope']=manifest['scope']+'; optional left stop target latched by original trigger side; left 0.40 / right 0.45'":
    "candidate_manifest['scope']=manifest['scope']+'; Python 3.9 compatible Optional annotation; decision logic unchanged'",
    "for name in CHANGES:compile(payload[name],str(NEW/name),'exec')":
    "for name in CHANGES:compile(payload[name],str(NEW/name),'exec')\nprobe=subprocess.run(['python3','-B','-c','import sys;sys.path.insert(0,'+repr(str(NEW))+');import continuous_face_control,continuous_session,hardware_slew_session,run_face_motion;assert continuous_face_control.EdgeConfig(left_target_center_ratio=.4).left_target_center_ratio==.4;assert not any(x in sys.modules for x in (\\\"vsrv_driver\\\",\\\"trajectory\\\"))'],capture_output=True,text=True,timeout=5)\nassert probe.returncode==0,probe.stderr",
    "ORIGINAL_FOLLOW_LEFT40_RIGHT45_SELECTED_STOPPED":"ORIGINAL_FOLLOW_LEFT40_RIGHT45_PY39_SELECTED_STOPPED",
    'source_files_changed=3,unchanged_source_files=22':'source_files_changed=1,unchanged_source_files=24,original_baseline_changed_sources=3,original_baseline_unchanged_sources=22,python39_pure_import_verified=True',
}
for old_text,new_text in substitutions.items():
    assert source.count(old_text)==1,(old_text,source.count(old_text))
    source=source.replace(old_text,new_text,1)
source=source.replace('PAYLOAD_BASE64',base64.b64encode(json.dumps(changes).encode()).decode()).replace(
    'EXPECTED_BASE64',base64.b64encode(json.dumps(expected).encode()).decode())
ast.parse(source)
p=FIX/'apply_py39_fix.prepared.py';assert not p.exists();p.write_text(source,encoding='utf-8')
intent=dict(action='versioned_annotation_compatibility_fix_then_original_ui_start',
    python39_board_tests=31,python310_windows_tests=31,publication_script_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
    changed_from_failed_v1=['continuous_face_control.py'],changed_from_original_baseline=3,left_target=.4,right_target=.45)
(FIX/'PUBLICATION_INTENT.json').write_text(json.dumps(intent,indent=2)+'\n',encoding='utf-8')
print(json.dumps(intent,indent=2))
