"""Separate a useful setting experiment from an unproven root-cause claim."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
from assess_results import assess

ROOT=Path(__file__).resolve().parent
PROBES=Path('/home/ghmd/aura-model-inventory-20261021')
BOARD=Path('/home/ghmd/aura-identity-dpu-check-20261018')
OUT=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_gil_interval_trial')
short=json.loads((ROOT/'result-short.json').read_text())
long=json.loads((ROOT/'result-long.json').read_text())
assert short['report']['complete'] and short['report']['passed'] and short['report']['rollback_verified']
assert long['report']['complete'] and long['report']['rollback_verified']
assert long['report']['scope']=='GIL_1MS_DUAL_MODEL_600S_ALWAYS_RESTORED'
assert 'Ran 6 tests' in (ROOT/'wrapper-test-results.txt').read_text() and '\nOK\n' in (ROOT/'wrapper-test-results.txt').read_text()
audit_path=PROBES/'thread_switch_final_audit_20261022'
assert json.loads(audit_path.with_suffix('.status.json').read_text())['exit_code']==0
audit=json.loads(audit_path.with_suffix('.response.json').read_text())
assert audit['pid']==long['report']['restored']['pid']
assert not audit['active_owned_rollback_timers'] and audit['cu_collector_inactive']
assert audit['pipeline_metrics_disabled'] and audit['sface_shadow_absent']
assert audit['original_database_path_preserved'] and audit['feature_backend']['kind']=='windows_sface'
native=json.loads(Path('/home/ghmd/aura-thread-sched-20261022/live-bundle.json').read_text())
for report in (short['report'],long['report']):
    assert report['source_hashes']=={name:row['sha256'] for name,row in native['manifest']['files'].items()}
    assert report['experimental_process_setting']['actual_start_seconds']==.001
    assert report['wrapper_sha256']==hashlib.sha256((ROOT/'gil_camera_launcher.py').read_bytes()).hexdigest()
assert not OUT.exists(),'Freeze a new handoff version instead of rewriting existing evidence'
OUT.mkdir(parents=True)
def copy(src,name):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,p)
for name in ('gil_camera_launcher.py','test_gil_launcher.py','build_trial.py','package_delivery.py','assess_results.py',
             'wrapper-test-results.txt','trial-manifest.json','README.md'):
    copy(ROOT/name,name)
for name in ('board_gil_switch_1ms_20261022.py','board_gil_1ms_long600_20261022.py'):
    copy(BOARD/name,'source/'+name)
copy('/home/ghmd/aura-thread-sched-20261022/live-bundle.json','pinned-native-bundle.json')
for name in ('gil_preflight_state_20261022','gil_baseline_rearm_20261022','gil_journal_preflight_20261022','gil_long_relaunch_20261022'):
    assert json.loads((PROBES/(name+'.status.json')).read_text())['exit_code']==0
    copy(PROBES/(name+'.response.json'),'evidence/'+name+'.json')
for name,value in (('short-120s',short),('long-600s',long),('final-active-audit',audit)):
    target=OUT/'evidence'/(name+'.json');target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(value,indent=2)+'\n')
assessments={'short':assess(short),'long':assess(long)}
(OUT/'evidence'/'snapshot-assessment.json').write_text(json.dumps(assessments,indent=2)+'\n')
release={'schema':'aura-gil-interval-trial-1','written_utc':datetime.now(timezone.utc).isoformat(),
    'changed_interpreter_setting_seconds':.001,'original_start_setting_seconds':.005,
    'setting_scope':'isolated camera interpreter only, verified at startup',
    'native_14_source_hashes_unchanged':True,'wrapper_tests':6,
    'native_regressions_inherited':[67,66],'native_tests_not_repeated':True,
    'short_passed':short['report']['passed'],'short_observed_seconds':short['report'].get('observed_seconds'),
    'short_yolo_hz':short['report'].get('observed_yolo_hz'),
    'short_yunet_hz':short['report'].get('observed_yunet_hz'),
    'long_passed':long['report']['passed'],'long_observed_seconds':long['report'].get('observed_seconds'),
    'long_error':long['report'].get('error'),
    'long_harness_scope':'throughput, optional-slot protection and restoration; not all-sample freshness',
    'long_all_sampled_face_results_fresh':assessments['long']['all_sampled_face_results_fresh'],
    'long_sampled_face_results_at_or_over_ttl':assessments['long']['face_age_samples_at_or_over_ttl'],
    'long_cpu_percent_of_board':long['report']['cpu_window']['cpu_percent_of_board'],
    'dpu_busy_fraction_measured_in_this_trial':False,
    'root_cause_proven':False,'same_input_speedup_proven':False,
    'three_model_long_stability_proven':False,'formal_identity_migrated':False,
    'production_setting_retained':False,'production_restored':True,'final_camera_pid':audit['pid'],
    'final_units':audit['units'],'all_owned_timers_off':True,'xrt_collector_off':True,
    'metrics_and_shadow_off':True,'hard_30ms_or_5ms_guard_changed':False,
    'kernel_priority_or_cpu_affinity_changed':False,'windows_receipt_confirmed':False}
(OUT/'release.json').write_text(json.dumps(release,indent=2)+'\n')
py=list(OUT.rglob('*.py'));js=list(OUT.rglob('*.json'))
for p in py:ast.parse(p.read_text(),filename=str(p))
for p in js:json.loads(p.read_text())
(OUT/'validation.json').write_text(json.dumps({'python_ast_pass':len(py),'json_parse_pass':len(js)+1,
    'all_native_sources_match_previous_observer_trial':True,'short_and_long_outcomes_separate':True,
    'no_biometric_data_or_raw_uart_included':True},indent=2)+'\n')
files=sorted(p for p in OUT.rglob('*') if p.is_file())
(OUT/'FILES.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(OUT))+'\n' for p in files))
print(json.dumps({'release':str(OUT),'hashed_files':len(files),'long_passed':long['report']['passed']}))
