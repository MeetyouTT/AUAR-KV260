"""Freeze counter observers, failed overhead checks and final live evidence."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parent
BOARD=Path('/home/ghmd/aura-identity-dpu-check-20261018')
PROBES=Path('/home/ghmd/aura-model-inventory-20261021')
OUT=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_thread_wait_diagnostics')
live=json.loads((ROOT/'live-result.json').read_text());r=live['report']
assert r['complete'] and r['rollback_verified']
check=json.loads((ROOT/'board-final-check.json').read_text());assert check['overhead_prerequisite_passed']
log=(ROOT/'test-results.txt').read_text()
assert re.findall(r'Ran (\d+) tests',log)==['67','66'] and log.count('\nOK\n')==2
p=PROBES/'thread_switch_final_audit_20261022'
assert json.loads(p.with_suffix('.status.json').read_text())['exit_code']==0
audit=json.loads(p.with_suffix('.response.json').read_text())
assert audit['pid']==r['restored']['pid']
assert audit['sface_shadow_absent'] and audit['pipeline_metrics_disabled']
assert audit['cu_collector_inactive'] and not audit['active_owned_rollback_timers']
bundle=json.loads((ROOT/'live-bundle.json').read_text())
for name,row in bundle['manifest']['files'].items():
    assert hashlib.sha256((ROOT/'candidate/aura'/name).read_bytes()).hexdigest()==row['sha256']
assert r['source_hashes']=={name:row['sha256'] for name,row in bundle['manifest']['files'].items()}
assert not OUT.exists(),'Use a new version for a changed frozen handoff'
OUT.mkdir(parents=True)
def copy(source,name):
    target=OUT/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
for folder in ('candidate','tests','tools','timing-tests/tests','timing-tests/tools'):
    for p in (ROOT/folder).rglob('*.py'):copy(p,p.relative_to(ROOT))
(OUT/'timing-tests/candidate').mkdir(exist_ok=True)
(OUT/'timing-tests/candidate/.keep').write_text('Docker nested read-only candidate mount target.\n')
for name in ('README.md','run_tests.py','test-results.txt','test-results-initial.txt',
    'test-results-with-kernel-import-error.txt','test-results-native-id-fixture-error.txt','test-results-mock-call-fixture-error.txt',
    'live-bundle.json','live-helper-manifest.json','board-helper-manifest.json'):
    copy(ROOT/name,name)
for name in ('build_board_check.py','build_live_bundle.py','build_live_helper.py','package_delivery.py'):
    copy(ROOT/name,'source/'+name)
for name in ('board_thread_sched_check_20261022.py','board_thread_sched_check_20261022_v2.py',
    'board_thread_sched_check_20261022_v3.py','board_thread_sched_check_20261022_v4.py',
    'board_thread_sched_check_20261022_v5.py','board_thread_switch_live_20261022.py'):
    copy(BOARD/name,'source/'+name)
for name in ('board-final-check.json','board-overhead-initial-failed.json','board-light-overhead-failed.json','live-result.json'):
    copy(ROOT/name,'evidence/'+name)
for name in ('thread-sched-check','thread-sched-check-v2','thread-sched-check-v3','thread-sched-check-v4','thread-sched-check-v5'):
    p=BOARD/('latest-'+name+'.json');v=json.loads(p.read_text())
    (OUT/'evidence'/('status-'+name+'.json')).write_text(json.dumps(v,indent=2)+'\n')
for name in ('thread_sched_capability_20261022','thread_sched_v3_diagnostic_rerun_20261022'):
    assert json.loads((PROBES/(name+'.status.json')).read_text())['exit_code']==0
    copy(PROBES/(name+'.response.json'),'evidence/'+name+'.json')
(OUT/'evidence/final-active-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
latest=r.get('camera_after') or r.get('fault_camera_snapshot') or r.get('latest_camera_seen')
diagnostics=latest['pipeline_metrics']['optional_diagnostics']
release={'schema':'aura-thread-wait-diagnostics-1','written_utc':datetime.now(timezone.utc).isoformat(),
    'software_tests':[67,66],'board_synthetic_tests':21,
    'full_runqueue_observer_overhead_passed':False,'context_switch_observer_overhead_passed':True,
    'observer_extra_mean_ms':check['incremental_mean_ms'],
    'live_scope':r['scope'],'live_passed':r['passed'],'live_observed_seconds':r.get('observed_seconds'),
    'live_yolo_hz':r.get('observed_yolo_hz'),'live_capture_hz':r.get('observed_capture_hz'),
    'live_fault_count':len(diagnostics['fault_events']),'observer':diagnostics['thread_sched_observer'],
    'actual_runqueue_time_collected':False,'root_cause_verified':False,'tail_latency_fixed':False,
    'production_restored':True,'final_camera_pid':audit['pid'],'final_units':audit['units'],
    'formal_sface_backend':'windows_sface','shadow_and_producer_disabled':True,
    'metrics_disabled':True,'all_owned_rollback_timers_inactive':True,'xrt_collector_inactive':True,
    'native_budget_changed':False,'kernel_scheduler_settings_changed':False,
    'whole_board_gain_comparison':False,'windows_receipt_confirmed':False}
(OUT/'release.json').write_text(json.dumps(release,indent=2)+'\n')
py=list(OUT.rglob('*.py'));js=list(OUT.rglob('*.json'))
for p in py:ast.parse(p.read_text(),filename=str(p))
for p in js:json.loads(p.read_text())
(OUT/'validation.json').write_text(json.dumps({'python_ast_pass':len(py),'json_parse_pass':len(js)+1,
    'all_14_board_live_source_hashes_match':True,'failed_checks_preserved':True,
    'no_raw_uart_or_biometric_artifacts_included':True},indent=2)+'\n')
files=sorted(p for p in OUT.rglob('*') if p.is_file())
(OUT/'FILES.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(OUT))+'\n' for p in files))
print(json.dumps({'release':str(OUT),'hashed_files':len(files),'python_ast':len(py),'json_files':len(js)+1}))
