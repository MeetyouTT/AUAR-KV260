"""Freeze filtered runtime evidence and the exact candidates used on board."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent
RETRY=Path('/home/ghmd/aura-sface-slot-retry-20261022')
BOARD_SOURCES=Path('/home/ghmd/aura-identity-dpu-check-20261018')
PROBES=Path('/home/ghmd/aura-model-inventory-20261021')
OUT=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_sface_retry_board')
data=json.loads((ROOT/'reports-all.json').read_text())
summary=json.loads((ROOT/'results-summary.json').read_text())
fault=json.loads((ROOT/'fault-analysis.json').read_text())
assert len(data['reports'])==3
assert all(row['report']['complete'] and row['report']['rollback_verified'] for row in data['reports'])
assert not data['reports'][0]['report']['passed'] and data['reports'][1]['report']['passed']
assert not data['reports'][2]['report']['passed']
p=PROBES/'sface_ab_final_audit_20261022'
assert json.loads(p.with_suffix('.status.json').read_text())['exit_code']==0
audit=json.loads(p.with_suffix('.response.json').read_text())
assert audit['pid']==data['reports'][-1]['report']['restored']['pid']==378714
assert not audit['active_owned_rollback_timers'] and audit['cu_collector_inactive']
assert audit['pipeline_metrics_disabled'] and audit['sface_shadow_absent']
assert audit['original_database_path_preserved'] and audit['feature_backend']['kind']=='windows_sface'
assert audit['face_targets']['backend']=='DPU_YUNET_INT8'
assert 'Ran 11 tests' in data['synthetic_test_output'] and '\nOK\n' in data['synthetic_test_output']
local=(ROOT/'restore-test-results.txt').read_text()
assert 'Ran 8 tests' in local and '\nOK\n' in local and 'ResourceWarning' not in local
retry_meta=json.loads((RETRY/'manifest.json').read_text())
for name,row in retry_meta['files'].items():
    assert hashlib.sha256((RETRY/'candidate/aura'/name).read_bytes()).hexdigest()==row['sha256']
assert {name:row['sha256'] for name,row in retry_meta['files'].items()}==data['reports'][1]['report']['variant_source_sha256']['B']
assert not OUT.exists(),'Use another version instead of changing a frozen handoff'
OUT.mkdir(parents=True)
def copy(source,name):
    target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
for p in (RETRY/'candidate').rglob('*.py'):copy(p,p.relative_to(RETRY))
for name in ('README.md','bundle-manifest.json','helper-manifest.json','b-only-wrapper-manifest.json',
    'b-only-v2-wrapper-manifest.json','long600-manifest.json','fault-analysis.json','results-summary.json'):
    copy(ROOT/name,name)
for name in ('build_bundle.py','build_helper.py','build_long600.py','summarize_results.py','package_delivery.py'):
    copy(ROOT/name,'source/'+name)
for name in ('board_sface_retry_ab_20261022.py','board_sface_retry_ab_20261022_v2.py',
    'board_sface_b_only_20261022.py','board_sface_b_only_20261022_v2.py','board_sface_b_long600_20261022.py'):
    copy(BOARD_SOURCES/name,'source/'+name)
copy(ROOT/'test_deployment_restore.py','tests/test_deployment_restore.py')
for name in ('restore-test-results.txt','restore-test-results-initial.txt','restore-test-harness-error.txt'):
    copy(ROOT/name,'evidence/'+name)
for index,item in enumerate(data['reports']):
    name=('a-coverage-incomplete','b-60s-passed','b-600s-failed')[index]
    p=OUT/'evidence'/(name+'.json');p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(item,indent=2)+'\n')
for name,value in (('final-active-audit',audit),('launch-records',data['launch_records']),
    ('kernel-after',data['kernel']),('prepared-sources',data['prepared'])):
    (OUT/'evidence'/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
(OUT/'evidence/board-synthetic-tests.txt').write_text(data['synthetic_test_output'])
prepared_status=BOARD_SOURCES/'latest-sface-retry-ab-prepare-v2.json'
v=json.loads(prepared_status.read_text());assert v['complete']
failed=json.loads((BOARD_SOURCES/'latest-sface-retry-ab-prepare.json').read_text())
(OUT/'evidence/initial-prepare-failure.json').write_text(json.dumps(failed,indent=2)+'\n')
manifest=dict(retry_meta,status='B_60S_BOARD_TARGET_PASSED_600S_ATTEMPT_FAILED_YUNET_OVERRUN',
    board_source_hashes_match=True,formal_identity_migrated=False,production_enabled=False)
(OUT/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
release=dict(schema='aura-sface-retry-board-1',written_utc=datetime.now(timezone.utc).isoformat(),
    single_primary_terminal=True,local_rollback_tests=8,board_synthetic_tests=11,
    earlier_candidate_regressions=[67,45],earlier_regressions_repeated_this_stage=False,
    a_b_comparison_passed=False,a_failure='Insufficient face coverage (10/13 one-face samples)',
    b_60s_target_passed=True,b_60s_completed=59,b_60s_hz=summary['rows'][1]['sface_hz'],
    b_600s_completed=False,b_600s_passed=False,
    b_long_fault=fault,final_camera_pid=audit['pid'],final_units=audit['units'],
    production_restored=True,all_owned_rollback_timers_inactive=True,xrt_collector_inactive=True,
    formal_sface_backend='windows_sface',shadow_and_producer_disabled=True,metrics_disabled=True,
    next_priority='Diagnose execute_async wall long tail before repeating 10/30 minutes',
    paired_speedup_proven=False,whole_board_cpu_gain_proven=False,
    new_schedstat_observer_implemented=False,windows_sync_receipt_confirmed=False)
(OUT/'release.json').write_text(json.dumps(release,indent=2)+'\n')
python_files=list(OUT.rglob('*.py'));json_files=list(OUT.rglob('*.json'))
for p in python_files:ast.parse(p.read_text(),filename=str(p))
for p in json_files:json.loads(p.read_text())
validation=dict(python_ast_pass=len(python_files),json_parse_pass=len(json_files)+1,
    all_13_b_sources_match_real_board_hashes=True,failed_a_and_long_reports_preserved=True,
    no_private_images_audio_vectors_identity_store_or_raw_uart_included=True)
(OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
files=sorted(p for p in OUT.rglob('*') if p.is_file())
(OUT/'FILES.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(OUT))+'\n' for p in files))
print(json.dumps({'release':str(OUT),'hashed_files':len(files),'python_files':len(python_files),'json_files':len(json_files)+1},ensure_ascii=False))
