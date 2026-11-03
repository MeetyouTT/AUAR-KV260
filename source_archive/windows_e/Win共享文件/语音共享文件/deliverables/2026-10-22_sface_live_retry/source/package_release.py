"""Freeze real runtime evidence and a distinct, untested-on-board retry candidate."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parent
RETRY=Path('/home/ghmd/aura-sface-slot-retry-20261022')
INVENTORY=Path('/home/ghmd/aura-model-inventory-20261021')
MERGED=Path('/home/ghmd/aura-single-terminal-integration-20261022')
OUT=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_sface_live_retry')
def read_probe(name):
    assert json.loads((INVENTORY/(name+'.status.json')).read_text())['exit_code']==0
    return json.loads((INVENTORY/(name+'.response.json')).read_text())
report=read_probe('merged_live_full_result_20261022')['report']
audit=read_probe('merged_post_release_audit_20261022')
kernel=read_probe('merged_kernel_after_20261022')
assert report['passed'] and report['complete'] and report['rollback_verified']
assert audit['cu_collector_inactive'] and not audit['active_owned_rollback_timers']
assert audit['pipeline_metrics_disabled'] and audit['sface_shadow_absent']
assert audit['pid']==report['restored']['pid'] and audit['detection_advanced']
final=report['camera_after'];diagnostics=final['pipeline_metrics']['optional_diagnostics']
assert int(kernel['kernel_window_first_mono_us'])/1e6<=diagnostics['started_mono_ns']/1e9
assert (kernel['latest_matching_usb_warning_mono_us'] is None or
    int(kernel['latest_matching_usb_warning_mono_us'])/1e6<diagnostics['started_mono_ns']/1e9)
assert not diagnostics['fault_events'] and diagnostics['diagnostic_errors']==0
log=(RETRY/'test-results.txt').read_text()
assert re.findall(r'Ran (\d+) tests',log)==['67','45'] and log.count('\nOK\n')==2
old=json.loads((MERGED/'manifest.json').read_text())
changed=[];retry_files={}
for p in sorted((RETRY/'candidate/aura').rglob('*.py')):
    name=str(p.relative_to(RETRY/'candidate/aura'));raw=p.read_bytes();ast.parse(raw)
    digest=hashlib.sha256(raw).hexdigest();retry_files[name]={'sha256':digest,'bytes':len(raw)}
    if digest!=old['files'][name]['sha256']:changed.append(name)
assert set(changed)=={'board/identity/deferred.py','board/identity/sface_shadow.py','board/vision/dpu_sface.py'}
retry_manifest={'status':'SOFTWARE_CANDIDATE_NOT_BOARD_TESTED','base_live_bundle_sha256':
    '0dd98eee68320ec7fbf5e60832f88360a88272ffa0ff21423eead8bfccee9d33',
    'changed_files':changed,'files':retry_files,'slot_retry_default_enabled':False,
    'same_scheduler_source_preserved':True,'same_runtime_source_preserved':True}
(RETRY/'manifest.json').write_text(json.dumps(retry_manifest,indent=2)+'\n')
native=final['shadow']['execution'];counts=diagnostics['counters']['sface']
summary=dict(scope='REAL_FACE_MERGED_13_SOURCE_SHORT_RUNTIME_CHECK_ONLY',
    observed_seconds=report['observed_seconds'],yolo_hz=report['observed_yolo_hz'],
    yunet_hz=report['observed_yunet_hz'],capture_hz=report['observed_capture_hz'],
    cpu_percent_of_board=report['cpu_window']['cpu_percent_of_board'],
    sface_completed_window=report['shadow_completed_window'],
    sface_completed_window_hz=report['shadow_completed_window']/report['observed_seconds'],
    sface_total_requests=native['requests'],sface_slot_denials=native['slot_denials'],
    sface_rejected_deadline=counts['rejected_deadline'],sface_rejected_active=counts['rejected_active'],
    crop_prepared=final['producer']['prepared'],crop_submitted=final['producer']['submitted'],
    sampled_face_counts=[x.get('face_count') for x in report['samples']],
    native_normal_samples={k:v['wait_wall_ms']['count'] for k,v in diagnostics['normal_success_timings'].items()},
    native_timing_scope='whole candidate process, including startup; calling thread CPU only; not pure DPU hardware time',
    optional_faults=0,new_usb_warnings=0,kernel_window_covered=True,
    yolo_primary_period_overruns_total=final['dpu_schedule']['primary_period_overruns'],
    optional_schedule=final['dpu_schedule']['optional'],
    sface_crop_to_feature_latency_ms=final['shadow']['accepted_latency_ms'],
    throughput_target_met=False,throughput_gain_proven=False,long_stability_proven=False,
    formal_identity_migrated=False,identity_decisions_from_shadow=0,templates_written=0,
    rollback_verified=True,final_camera_pid=audit['pid'],final_units=audit['units'])
assert not OUT.exists(),'Frozen handoff already exists; use a new release version'
OUT.mkdir(parents=True)
def copy(src,relative):
    target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
for p in (RETRY/'candidate').rglob('*.py'):copy(p,p.relative_to(RETRY))
for folder in ('tests','tools'):
    for p in (RETRY/folder).rglob('*.py'):copy(p,p.relative_to(RETRY))
for name in ('README.md','run_tests.py','manifest.json','test-results.txt','test-results-initial.txt'):
    copy(RETRY/name,'retry-'+name if name=='README.md' else name)
for name in ('build_live_check.py','preparation-validation.json','helper-manifest.json','package_release.py'):
    copy(ROOT/name,'source/'+name)
copy('/home/ghmd/aura-identity-dpu-check-20261018/board_merged_live_20261022.py','source/board_merged_live_20261022.py')
copy(MERGED/'manifest.json','tested-merged-manifest.json')
for name,value in (('live-60s',report),('final-active-audit',audit),('kernel-after',kernel),('summary',summary)):
    target=OUT/'evidence'/str(name+'.json');target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(value,indent=2)+'\n')
release=dict(schema='aura-sface-live-and-retry-v1',written_utc=datetime.now(timezone.utc).isoformat(),
    live_bundle_sha256=retry_manifest['base_live_bundle_sha256'],live_merged_short_test_passed=True,
    retry_tests=[67,45],retry_board_verified=False,retry_effect_on_throughput_verified=False,
    production_restored=True,final_camera_pid=audit['pid'],formal_sface_backend='windows_sface',
    audio_maintenance_production_enabled=False,shadow_producer_and_metrics_production_enabled=False,
    summary=summary)
(OUT/'release.json').write_text(json.dumps(release,indent=2)+'\n')
copy(ROOT/'README.md','README.md')
python_files=list(OUT.rglob('*.py'));json_files=list(OUT.rglob('*.json'))
for p in python_files:ast.parse(p.read_text(),filename=str(p))
for p in json_files:json.loads(p.read_text())
validation=dict(python_ast_pass=len(python_files),json_parse_pass=len(json_files)+1,
    tested_live_manifest_matches_report=report['candidate_source_sha256']=={k:v['sha256'] for k,v in old['files'].items()},
    retry_changed_sources=changed,biometric_files_or_raw_uart_included=False)
assert validation['tested_live_manifest_matches_report']
(OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
files=sorted(p for p in OUT.rglob('*') if p.is_file())
(OUT/'FILES.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(OUT))+'\n' for p in files))
print(json.dumps({'release':str(OUT),'hashed_files':len(files),'summary':summary},ensure_ascii=False))
