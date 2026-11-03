"""Copy only allowlisted sources, frozen candidates and numeric evidence."""
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SHARED=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_cpu_dpu_implementation')
CAL=Path('/home/ghmd/aura-sface-calibration-20261022')
PROBES=Path('/home/ghmd/aura-model-inventory-20261021')


def copy(source,target):
    data=source.read_bytes();target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert target.read_bytes()==data,'Different existing delivery file: '+str(target)
    else:target.write_bytes(data)


def js(path):return json.loads(path.read_text())


def put(name,value):
    path=SHARED/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def probe(name):
    status=js(PROBES/(name+'.status.json'))
    assert status['exit_code']==0 and status['console_echo_restored']
    return js(PROBES/(name+'.response.json'))


def main():
    cal_manifest=js(CAL/'patch-manifest.json')
    assert hashlib.sha256((CAL/'patch-manifest.json').read_bytes()).hexdigest()=='ee72779ef73f860d73517941efa2f65d75d9551d2321f639a3bba1a287a541af'
    for line in (CAL/'FILES.sha256').read_text().splitlines():
        sha,name=line.split('  ',1);source=CAL/name
        assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
        copy(source,SHARED/'calibration-candidate'/name)
    copy(CAL/'FILES.sha256',SHARED/'calibration-candidate/FILES.sha256')
    for dirname in ['metrics-candidate','combined-candidate','metrics-tests']:
        for source in sorted((ROOT/dirname).rglob('*.py')):
            copy(source,SHARED/source.relative_to(ROOT))
    for name in ['metrics-manifest.json','combined-manifest.json','combined-test-results.txt',
        'metrics-test-results.txt','metrics-integration-test-results.txt','longrun-test-results.txt','longrun-v3-test-results.txt']:
        copy(ROOT/name,SHARED/name)
    for name in ['build_metrics_overlay.py','run_metrics_tests.py','build_combined_candidate.py',
        'run_combined_tests.py','test_pipeline_metrics.py','test_shadow_long.py','summarize_observation.py']:
        copy(ROOT/name,SHARED/'source'/name)
    for name in ['board_sface_shadow_long_20261022_v2.py','board_sface_shadow_long_20261022_v3.py',
        'board_audio_recover_20261022.py','board_calibration_contract_20261022.py']:
        copy(Path('/home/ghmd/aura-identity-dpu-check-20261018')/name,SHARED/'source'/name)
    for name in ['yunet_active_release_audit.py','rearm_yunet_after_audio_20261022.py','t3_progress_20261022.py',
        't3_final_evidence_20261022.py','t3_fault_snapshot_20261022.py','t3_warning_onset_20261022.py',
        'restored_health_window_20261022.py','metrics_board_contract_20261022.py','vision_load_probe.py']:
        copy(PROBES/name,SHARED/'source'/name)
    for source_name,dest in [
        ('longrun-failed-full.json','evidence/longrun-failed-full.json'),
        ('audio-recovery-full.json','evidence/audio-recovery-full.json'),
        ('longrun-board-provenance.json','evidence/longrun-board-provenance.json'),
        ('observation-summary/summary.json','evidence/observation-summary.json'),
        ('observation-summary/intervals.csv','evidence/observation-intervals.csv'),
        ('early-load-observed.json','evidence/post-rollback-fault-load.json'),
        ('restored-load.json','evidence/restored-load.json')]:copy(ROOT/source_name,SHARED/dest)
    for name,dest in [('t3_fault_snapshot_20261022','evidence/latest-kernel-tail.json'),
        ('t3_warning_onset_20261022','evidence/recorded-warning-search.json'),
        ('rearm_yunet_after_audio_20261022','evidence/rearm-yunet.json'),
        ('restored_health_window_20261022','evidence/restored-health-window.json'),
        ('yunet_active_release_audit','evidence/active-release-audit.json'),
        ('metrics_board_contract_20261022','evidence/metrics-board-contract.json')]:put(dest,probe(name))
    # Preserve first fault snapshot separately: latest probe was after recovery.
    fault_lines=(ROOT/'fault-snapshot.log').read_text().splitlines()
    put('evidence/initial-fault-snapshot.json',json.loads(fault_lines[0]))
    contract_dir=Path('/home/ghmd/aura-identity-dpu-check-20261018/evidence/20261022T081223.201921Z-calibration-contract-only')
    contract=js(contract_dir/'response.json');transport=js(contract_dir/'status.json')
    assert transport['complete'] and transport['console_echo_restored']
    assert contract['checks_passed']==8 and contract['source_sha256']==cal_manifest['source_files'][5]['sha256']
    assert contract['runtime_verified'] is False and contract['dpu_opened'] is False
    put('evidence/calibration-board-contract.json',contract)
    put('evidence/calibration-board-contract-provenance.json',{
        'script_sha256':transport['source_sha256'],'console_echo_restored':transport['console_echo_restored'],
        'transport_exit_code':transport['responses'][-1]['exit_code'],
        'scope':'Standard-library synthetic compatibility only, not actual camera or DPU inference'})
    combined=(ROOT/'combined-test-results.txt').read_text()
    assert re.findall(r'Ran (\d+) tests',combined)==['46','10'] and combined.count('\nOK')==2
    audit=probe('yunet_active_release_audit');health=probe('restored_health_window_20261022')
    assert audit['pid']==192540 and audit['sface_shadow_absent'] and audit['cu_collector_inactive']
    assert not audit['active_owned_rollback_timers'] and audit['original_database_path_preserved']
    audio=js(ROOT/'audio-recovery-full.json');long=js(ROOT/'longrun-failed-full.json');load=js(ROOT/'restored-load.json')
    assert audio['complete'] and audio['warning_recovered_in_short_sample'] and not audio.get('error')
    assert long['complete'] and not long['passed'] and long['rollback_verified']
    release={
        'release_id':'AURA-CPU-DPU-IMPLEMENT-20261022-r1',
        'updated_utc':datetime.now(timezone.utc).isoformat(),
        'status':'SOFTWARE_CANDIDATES_PASSED_LONG_RUN_FAILED_AUDIO_RECOVERED_TWO_MODEL_RESTORED',
        'current_production':{'yolo':'KV260_DPU','yunet':'KV260_DPU_CNN_ARM_PRE_POST',
            'sface':'WINDOWS_CPU_CONFIGURED_ORIGINAL_DATABASE','sface_shadow_enabled':False,
            'calibration_enabled':False,'pipeline_metrics_enabled':False,
            'camera_pid':192540,'ui_supervisor_pid':191322,'xserver_supervisor_pid':1077,
            'camera_root':audit['runtime'],'unit_sha256':audit['camera_unit_sha256']},
        'T1':{'overlay_files':9,'software_tests_passed':46,'standard_library_board_synthetic_checks_passed':8,
            'runtime_wiring_board_verified':False,'field_threshold_validated':False,
            'deployment_threshold_validated':False,'new_database_created':False},
        'T2':{'overlay_files':3,'software_checks_passed':15,'standard_library_board_simulation_passed':True,
            'runtime_instrumentation_deployed':False,'full_stage_coverage':False},
        'merged_candidate':{'source_files':11,'regression_tests_passed':56,'board_deployed':False},
        'T3':{'target_seconds':1800,'passed':False,'last_healthy_sample_elapsed_s':long['samples'][-1]['elapsed_s'],
            'recorded_samples':len(long['samples']),'actual_completions_at_last_healthy_sample':20,
            'error':long['error'],'failure_snapshot_saved':False,'rollback_verified':True,
            'shadow_identity_decisions_at_last_healthy_sample':0,'templates_written_at_last_healthy_sample':0,
            'v3_failure_snapshot_fix_software_checks':6,'v3_executed':False},
        'audio':{'warning_recurred':True,'current_recurrence_cleared':True,'root_cause_fixed':False,
            'causal_relation_to_dpu_overrun_established':False,'original_app_lifecycle_restarted_once':True,
            'after_recovery_warning_count':audio['after']['xhci_warning_count'],
            'after_recovery_observation_s':audio['after']['seconds'],'new_sound_or_capture_accepted':False,
            'protected_config_and_preference_hashes_preserved':audio['protected_after']==audio['protected_before']
                and audio['preference_sha_after']==audio['preference_sha_before']},
        'restored_short_window':{'cpu_pct_board':load['cpu_percent_of_board'],
            'xrt_task_busy_pct':load['dpu_task_busy_percent'],'xrt_command_count':load['dpu_commands_completed'],
            'yolo_hz':health['yolo_hz'],'capture_hz':health['capture_hz'],
            'scope':'Sequential15s windows after recovery, not a new30min gate or pure hardware comparison'},
        'verification':{'unit_model_manifest_sources_match':True,'old_database_path_preserved':True,
            'owned_rollback_timers_inactive':True,'xrt_statistics_off':True,
            'windows_sync_confirmed':False,'windows_current_health_accepted':False,
            'real_face_audio_embeddings_database_raw_uart_copied_to_shared':False},
        'next_priority':['Low-overhead fault-time observation and audio recurrence/optional latency investigation',
            'Measure and improve actual SFace admission/completion rate under fixed gates',
            'Isolated instrumentation/calibration wiring acceptance then repeat long-run and formal enrollment'],
        'files_manifest':'FILES.sha256','validation':'validation.json'}
    put('release.json',release)
    print(json.dumps({'status':release['status'],'merged_tests_passed':56,'production_camera_pid':192540}))


if __name__=='__main__':main()
