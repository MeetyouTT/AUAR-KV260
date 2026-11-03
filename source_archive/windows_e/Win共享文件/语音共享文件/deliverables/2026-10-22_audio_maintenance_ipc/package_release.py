"""Freeze source and filtered numeric evidence; never include raw UART/data."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parent
OUT=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_audio_maintenance_ipc')
CHECK=Path('/home/ghmd/aura-identity-dpu-check-20261018')
status=json.loads((CHECK/'latest-audio-maintenance-ipc.json').read_text())
assert status['complete']
evidence=Path(status['evidence'])
board=json.loads((evidence/'response.json').read_text())
assert board['exit_code']==0 and board['production_sources_unchanged']
assert board['kernel_window_covered'] and board['new_matching_usb_warnings']==0
local=(ROOT/'test-results.txt').read_text()
assert re.search(r'Ran 33 tests.*\n\nOK\s*$',local,re.S)
assert 'Ran 33 tests' in board['test_output'] and '\nOK\n' in board['test_output']
check_manifest=json.loads((ROOT/'board-check-manifest.json').read_text())
for rel,digest in check_manifest['sources'].items():
    assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest,rel
assert check_manifest['sources']==board['source_hashes']
assert not OUT.exists(),'Use a new release path instead of rewriting a frozen handoff'
OUT.mkdir(parents=True)
def copy(src,relative):
    target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
for p in (ROOT/'candidate').rglob('*.py'):copy(p,p.relative_to(ROOT))
for p in (ROOT/'recovered').rglob('*.py'):copy(p,p.relative_to(ROOT))
for name in ('README.md','test_maintenance_ipc.py','test-results.txt','test-results-initial.txt',
             'build_board_check.py','package_release.py','gtk-base.json','board-check-manifest.json'):
    copy(ROOT/name,name)
for p in (ROOT/'recovered').glob('manifest*.json'):copy(p,p.relative_to(ROOT))
copy(evidence/'response.json','evidence/board-ipc-synthetic.json')
copy(evidence/'status.json','evidence/board-transport-status.json')
copy(evidence/'source.py','source/board_audio_maintenance_ipc_20261022.py')
release=dict(schema='aura-audio-maintenance-ipc-v1',written_utc=datetime.now(timezone.utc).isoformat(),
    unique_tests=33,local_tests='PASS',local_gstreamer='1.16.3',
    board_same_tests='PASS',board_python=board['board_python'],board_bundle_sha256=board['bundle_sha256'],
    production_sources_unchanged=True,production_units=board['after']['units'],
    candidate_default_enabled=False,production_gtk_verified=False,mcp01_recovery_verified=False,
    source_constraint='one primary agent and one serial terminal workflow',
    remaining=['Production GTK/AEC acceptance','MCP01 hardware recovery and USB root cause',
               'Retained capture/channel idle resource lifecycle','Independent SFace supply live inference',
               'Long-running three-model stability and real identity enrollment/thresholds'])
(OUT/'release.json').write_text(json.dumps(release,indent=2)+'\n')
python_files=list(OUT.rglob('*.py'))
for p in python_files:ast.parse(p.read_text(),filename=str(p))
json_files=list(OUT.rglob('*.json'))
for p in json_files:json.loads(p.read_text())
validation=dict(python_ast_pass=len(python_files),json_parse_pass=len(json_files)+1,
    all_frozen_sources_match_board_manifest=True,local_unique_tests=33,board_repeated_tests=33,
    no_raw_uart_or_biometric_artifacts=True)
(OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
files=sorted(p for p in OUT.rglob('*') if p.is_file())
(OUT/'FILES.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(OUT))+'\n' for p in files))
print(json.dumps({'release':str(OUT),'hashed_files':len(files),'python_files':len(python_files)}))
