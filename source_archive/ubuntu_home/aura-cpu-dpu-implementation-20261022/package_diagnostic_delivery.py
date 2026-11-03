import ast,csv,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path

PRIVATE=Path(__file__).resolve().parent
PROBES=Path('/home/ghmd/aura-model-inventory-20261021')
SHARED=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_dpu_audio_diagnosis')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def js(p):return json.loads(p.read_text())


def put(name,value):
    p=SHARED/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def copy(source,target):
    value=source.read_bytes();target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert target.read_bytes()==value,str(target)
    else:target.write_bytes(value)


def frozen_copy(root,target):
    for line in (root/'FILES.sha256').read_text().splitlines():
        expected,name=line.split('  ',1);assert sha(root/name)==expected
        copy(root/name,target/name)
    copy(root/'FILES.sha256',target/'FILES.sha256')


def probe(name):
    status=js(PROBES/(name+'.status.json'))
    assert status['exit_code']==0 and status['console_echo_restored']
    return js(PROBES/(name+'.response.json'))


def main():
    diag=Path('/home/ghmd/aura-dpu-audio-diagnosis-20261022')
    cpu=Path('/home/ghmd/aura-capture-copy-candidate-20261022')
    frozen_copy(diag,SHARED/'diagnostic-candidate')
    frozen_copy(diag/'analysis-120s',SHARED/'diagnostic-candidate/analysis-120s')
    frozen_copy(cpu,SHARED/'capture-copy-candidate')
    short=js(PRIVATE/'yunet-diagnostic-120s-full.json')
    assert short['passed'] and short['complete'] and short['rollback_verified']
    assert short['diagnostic_completed_waits']==295 and short['formal_identity_or_long_run_accepted'] is False
    put('evidence/yunet-diagnostic-120s-full.json',short)
    progress=probe('yunet_diagnostic_progress_20261022')
    blocked=[v for name,v in progress['launches'].items() if '1c22a77bce0e723c' in name]
    assert len(blocked)==1 and 'USB audio already warning in baseline' in blocked[0]['error']
    put('evidence/extended-600s-preflight-refusal.json',blocked[0])
    put('evidence/extension-baseline-fault.json',json.loads((PRIVATE/'extension-baseline-fault.log').read_text().splitlines()[0]))
    recovery=probe('recovery_order_result_20261022')['result']
    assert recovery['phase']=='FAILED' and recovery['error']=='AssertionError: '
    put('evidence/recovery-order-original-result.json',recovery)
    accepted=probe('recovery_order_acceptance_20261022')
    assert accepted['independent_acceptance_passed'] and accepted['camera_pid']==215707
    assert accepted['original_counter_comparison_crossed_camera_processes']
    put('evidence/recovery-order-independent-acceptance.json',accepted)
    audit=probe('yunet_active_release_audit')
    assert audit['pid']==215707 and audit['sface_shadow_absent'] and audit['cu_collector_inactive']
    assert not audit['active_owned_rollback_timers'] and audit['original_database_path_preserved']
    put('evidence/active-release-audit.json',audit)
    for name,dest in [('windows_readonly_health_20261022','evidence/windows-health-readonly.json'),
        ('camera_readonly_controls_20261022','evidence/camera-readonly-controls.json')]:put(dest,probe(name))
    for name in ['diagnostic-deployment-provenance.json','extended-diagnostic-preparation.json','diagnostic-helper-test-results.txt']:
        copy(PRIVATE/name,SHARED/'source'/name)
    for name in ['build_yunet_diagnostic.py','build_extended_diagnostic.py','test_yunet_diagnostic_helper.py']:
        copy(PRIVATE/name,SHARED/'source'/name)
    for name in ['board_yunet_diagnostic_20261022_v2.py','board_yunet_diagnostic_20261022_600s.py',
        'board_recover_audio_camera_order_20261022.py','board_recover_audio_camera_order_20261022_v2_NOT_RUN.py']:
        copy(Path('/home/ghmd/aura-identity-dpu-check-20261018')/name,SHARED/'source'/name)
    for name in ['yunet_diagnostic_progress_20261022.py','yunet_diagnostic_collect_20261022.py',
        'recovery_order_acceptance_20261022.py','windows_readonly_health_20261022.py','camera_readonly_controls_20261022.py',
        'yunet_active_release_audit.py']:
        copy(PROBES/name,SHARED/'source'/name)
    copy(Path('/home/ghmd/aura-dpu-vision-20261021/work/yunet-diagnostic-20261022.tar.gz'),SHARED/'source/yunet-diagnostic.tar.gz')
    release={'release_id':'AURA-DPU-DIAGNOSIS-20261022-r1','updated_utc':datetime.now(timezone.utc).isoformat(),
        'status':'SHORT_DIAGNOSTIC_OBSERVED_EXTENDED_BASELINE_REFUSED_RECOVERY_ORDER_INDEPENDENTLY_VERIFIED',
        'production':{'camera_pid':215707,'ui_pid':215734,'xserver_pid':1077,
            'yolo':'KV260_DPU','yunet':'KV260_DPU_CNN_ARM_PRE_POST','sface':'WINDOWS_CPU_CONFIGURED_ORIGINAL_DATABASE',
            'shadow_enabled':False,'diagnostic_instrumentation_enabled':False,'capture_copy_candidate_deployed':False,
            'runtime':audit['runtime'],'camera_unit_sha256':audit['camera_unit_sha256']},
        'short_diagnostic':{'seconds':short['observation_elapsed_s'],'native_successful_waits':295,
            'yolo_hz':short['observed_yolo_hz'],'yunet_hz':short['observed_yunet_hz'],
            'cpu_pct_board':short['pilot_cpu_total']['cpu_percent_of_board'],
            'fault_events':len(short['camera_after']['dpu_schedule']['optional_diagnostics']['fault_events']),
            'new_usb_warnings':short['usb_audio_warning_count'],'rollback_verified':True,
            'formal_or_long_run_accepted':False},
        'extended_attempt':{'target_s':600,'candidate_started':False,'outcome':'REFUSED_NEW_USB_WARNINGS_IN_BASELINE',
            'baseline_camera_pid':209792,'new_600s_test_result_exists':False},
        'recovery_order':{'order':['original_idle_audio_closed','same_original_camera_unit_restarted','original_audio_reopened'],
            'original_script_complete':False,'original_script_counter_validation_error_retained':True,
            'independent_read_only_acceptance_passed':True,'latest_retained_warning_age_s_at_acceptance':accepted['latest_retained_warning_age_s'],
            'root_cause_fixed':False,'long_term_prevention_proven':False,'new_sound_or_capture_accepted':False},
        'software_tests':{'diagnostic_core':29,'offline_kernel_filter':6,'short_controller':4,'capture_copy_callback':8},
        'capture_copy':{'removed_array_copies_per_frame':1,'bytes_per_copy':921600,'software_tests_passed':8,
            'cpu_or_ddr_gain_measured':False,'board_deployed':False},
        'limits':{'normal_thread_cpu_distribution_available':False,'hardware_execution_time_measured':False,
            'sface_formal_identity_accepted':False,'field_people_and_labels_confirmed':False,
            'windows_current_health_accepted':False,'windows_sync_confirmed':False},
        'verification':{'original_source_model_unit_and_database_preserved':True,'owned_timers_inactive':True,
            'xrt_statistics_off':True,'biometric_media_vectors_database_or_raw_uart_shared':False},
        'files_manifest':'FILES.sha256','validation':'validation.json'}
    put('release.json',release)
    files=sorted(p for p in SHARED.rglob('*') if p.is_file() and p.name!='FILES.sha256')
    py_count=json_count=links=0
    for p in files:
        assert not p.is_symlink() and '__pycache__' not in p.parts
        assert p.suffix.lower() not in {'.jpg','.jpeg','.png','.webp','.wav','.mp3','.mp4','.npy','.npz','.db','.sqlite','.sqlite3','.raw'}
        if p.suffix=='.py':ast.parse(p.read_text(),filename=str(p));py_count+=1
        if p.suffix=='.json':js(p);json_count+=1
        if p.suffix=='.md':
            for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
                if target.startswith(('http:','https:','#')):continue
                assert (p.parent/target).exists(),(p,target)
                links+=1
    put('validation.json',{'status':'PASS','verified_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Frozen artifact hashes, syntax, local links and evidence consistency; not additional hardware or field tests',
        'python_files_ast_parsed':py_count,'json_files_parsed_before_validation':json_count,'local_links_verified':links,
        'short_diagnostic_and_rollback_verified':True,'extended_test_refusal_preserved':True,
        'recovery_original_assertion_and_independent_proof_separate':True,'no_production_optimization_promotion':True})
    manifest=SHARED/'FILES.sha256'
    all_files=sorted(p for p in SHARED.rglob('*') if p.is_file() and p!=manifest)
    manifest.write_text(''.join(sha(p)+'  '+str(p.relative_to(SHARED))+'\n' for p in all_files))
    for line in manifest.read_text().splitlines():
        expected,name=line.split('  ',1);assert sha(SHARED/name)==expected
    print(json.dumps({'status':release['status'],'artifact_files_verified':len(all_files),'current_camera_pid':215707,
        'python_ast_files':py_count,'json_files':json_count,'local_links_verified':links}))


if __name__=='__main__':main()
