"""Separate failed environment, short/long outcomes, and final original-state audit."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from assess_results import assess

ROOT=Path(__file__).resolve().parent
PROBES=Path('/home/ghmd/aura-model-inventory-20261021')
HELPERS=Path('/home/ghmd/aura-identity-dpu-check-20261018')
OUT=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_cpu_affinity_board')
first=json.loads((ROOT/'result-first.json').read_text())
short=json.loads((ROOT/'result-short.json').read_text())
long=json.loads((ROOT/'result-long.json').read_text())
for value in (first,short,long):
    assert value['report']['complete'] and value['report']['rollback_verified']
    assert value['report']['gil_seconds']==.005
    assert value['report']['affinity_shutdown']['clean_selected_thread_restoration_and_close']
assert not first['report']['passed'] and first['report']['error']=='AssertionError: USB warning during copy-only candidate'
assert short['report']['passed']
assert long['report']['scope']=='CPU_AFFINITY_DUAL_MODEL_600S_ALWAYS_RESTORED'
assert not OUT.exists(),'Publish a separate revision instead of rewriting frozen evidence'
audit_path=PROBES/'thread_switch_final_audit_20261022'
assert json.loads(audit_path.with_suffix('.status.json').read_text())['exit_code']==0
audit=json.loads(audit_path.with_suffix('.response.json').read_text())
assert audit['pid']==long['report']['restored']['pid']
assert audit['pipeline_metrics_disabled'] and audit['cu_collector_inactive']
assert audit['sface_shadow_absent'] and not audit['active_owned_rollback_timers']
assert audit['original_database_path_preserved'] and audit['feature_backend']['kind']=='windows_sface'
recovery=json.loads((ROOT/'audio-recovery-result.json').read_text())
assert recovery['complete'] and recovery['warning_recovered_in_short_sample']
assert recovery['protected_before']==recovery['protected_after']
assert recovery['preference_sha_before']==recovery['preference_sha_after']
native=json.loads(Path('/home/ghmd/aura-thread-sched-20261022/live-bundle.json').read_text())
for value in (first,short,long):
    report=value['report']
    assert report['source_hashes']=={name:row['sha256'] for name,row in native['manifest']['files'].items()}
    assert report['payload_sha256']==short['report']['payload_sha256']
    assert report['policy']==short['report']['policy']
assessments={name:assess(value) for name,value in (('first',first),('short',short),('long',long))}
OUT.mkdir(parents=True)
def copy(source,name):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,p)
for name in ('README.md','build_trial.py','assess_results.py','package_delivery.py',
             'trial-manifest.json','build-validation.json','long-build-validation.json',
             'recovery-build-validation.json'):
    copy(ROOT/name,name)
for name in ('board_cpu_affinity_live_r2_20261022.py','board_cpu_affinity_long600_20261022.py',
             'board_affinity_audio_recover_once_20261022.py'):
    copy(HELPERS/name,'source/'+name)
for name in ('review.md','review-result.json','audio-recovery-review.json','long600-review.json'):
    copy(Path('/home/ghmd/aura-affinity-review-20261022')/name,'review/'+name)
copy(Path('/home/ghmd/aura-affinity-review-20261022/vart-source-review.md'),'review/vart-source-review.md')
vart_note=OUT/'review/vart-source-review.md'
vart_note.write_text('主任务后续更新：已从当时相机449083实际maps读取当前vart.so及libvart-runner.so.3.0.0的SHA，见[数字证据](../evidence/vart-hashes.json)。未关联构建manifest或源码commit，下面“尚未保存SHA”为此前审查时点，源码匹配限制仍成立。更广范围readelf查询曾3秒超时，未取得完整Build ID；之后仅对两个实际VART映射文件作有界哈希，无新runner/DPU作业。\n\n'+vart_note.read_text())
kernel=json.loads((ROOT/'long-kernel.json').read_text())
assert kernel['window_history_covered'] and kernel['matching_warnings_in_candidate_window']==0
copy(ROOT/'long-kernel.json','evidence/long-kernel.json')
for name in ('vart-hashes.json','vart-source-review.json'):
    if (ROOT/name).is_file():copy(ROOT/name,'evidence/'+name)
for name,value in (('trial-first',first),('trial-short',short),('trial-long',long),
                   ('assessment',assessments),('audio-recovery',recovery),('final-active-audit',audit)):
    p=OUT/'evidence'/(name+'.json');p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
for name in ('affinity_preflight_20261022','affinity_baseline_rearm_20261022',
             'affinity_usb_window_20261022','affinity_retry_after_recovery_20261022'):
    if (ROOT/(name+'.json')).exists():copy(ROOT/(name+'.json'),'evidence/'+name+'.json')
    else:
        assert json.loads((PROBES/(name+'.status.json')).read_text())['exit_code']==0
        copy(PROBES/(name+'.response.json'),'evidence/'+name+'.json')
copy(ROOT/'audit-after-first.status.json','evidence/audit-after-first.status.json')
copy(ROOT/'audit-after-first.log','evidence/audit-after-first-error.txt')
release={'schema':'aura-cpu-affinity-board-1','written_utc':datetime.now(timezone.utc).isoformat(),
    'candidate_release':'2026-10-22_cpu_affinity_candidate_r2','candidate_software_tests':28,
    'policy':short['report']['policy'],'gil_seconds':.005,'native_source_files_unchanged':14,
    'first_attempt_passed':False,'first_failure':'new matching USB warning',
    'audio_normal_lifecycle_recovery_performed':True,'recovery_root_cause_fixed':False,
    'short_passed':short['report']['passed'],'long_passed':long['report']['passed'],
    'long_matching_usb_warnings':0,'long_kernel_history_covered':True,
    'short':assessments['short'],'long':assessments['long'],
    'controlled_speedup_proven':False,'dpu_busy_fraction_measured':False,
    'three_model_stability_verified':False,'formal_identity_migrated':False,
    'production_affinity_retained':False,'production_restored':True,'final_camera_pid':audit['pid'],
    'journald_restart_counter_changed_from_28_to_30':True,'all_services_zero_restarts':False,
    'final_units':audit['units'],'all_owned_timers_off':True,'metrics_and_shadow_off':True,
    'windows_receipt_confirmed':False,'biometric_data_or_raw_uart_included':False}
(OUT/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
for p in OUT.rglob('*.py'):ast.parse(p.read_text(),filename=str(p))
for p in OUT.rglob('*.json'):json.loads(p.read_text())
files=sorted(p for p in OUT.rglob('*') if p.is_file())
(OUT/'FILES.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '
    +str(p.relative_to(OUT))+'\n' for p in files))
print(json.dumps({'delivery':str(OUT),'hashed_files':len(files),'long_passed':long['report']['passed']}))
