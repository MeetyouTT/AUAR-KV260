"""Archive reviewed candidates and filtered evidence; preserve older releases."""
import ast,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_single_terminal_integration')
PROBES=Path('/home/ghmd/aura-model-inventory-20261021')
EVIDENCE=Path('/home/ghmd/aura-identity-dpu-check-20261018/evidence')
AUDIO=Path('/home/ghmd/aura-audio-maintenance-20261022')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):return json.loads(path.read_text())


def put(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def copy(source,target):
    raw=source.read_bytes();target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert target.read_bytes()==raw,'Refusing to overwrite different file: '+str(target)
    else:target.write_bytes(raw)


def frozen(root,target):
    count=0
    for line in (root/'FILES.sha256').read_text().splitlines():
        digest,name=line.split('  ',1);assert sha(root/name)==digest
        copy(root/name,target/name);count+=1
    copy(root/'FILES.sha256',target/'FILES.sha256')
    return count


def probe(name):
    status=read(PROBES/(name+'.status.json'))
    assert status['exit_code']==0 and status['console_echo_restored'],name
    return read(PROBES/(name+'.response.json'))


def board_result(folder):
    path=EVIDENCE/folder;status=read(path/'status.json')
    assert status['complete'] and status['console_echo_restored'] and status['responses'][-1]['exit_code']==0
    return read(path/'response.json'),{
        'helper_sha256':status['source_sha256'],'console_echo_restored':True,
        'transport_exit_code':0,'source_evidence_folder':folder}


def main():
    tests=(ROOT/'test-results.txt').read_text()
    assert re.findall(r'Ran (\d+) tests',tests)==['56','45'] and tests.count('\nOK')==2
    assert 'Ran 20 tests' in (AUDIO/'engine-test-results.txt').read_text()
    assert (AUDIO/'engine-test-results.txt').read_text().rstrip().endswith('OK')
    audio,ap=board_result('20261022T095718.379606Z-audio-maintenance-dummy-v2')
    assert audio['candidate_source_sha256']==sha(AUDIO/'idle_maintenance_engine.py')
    assert audio['null_before_rebuild_verified'] and audio['all_synthetic_pipelines_released']
    assert not audio['alsa_opened'] and not audio['production_integration_verified']
    merged,mp=board_result('20261022T095641.034338Z-merged-import-contract')
    assert merged['modules_verified']==13 and merged['actual_dpu_jobs_executed']==0
    assert not merged['production_service_modified'] and not merged['identity_database_opened']
    runs=probe('capture_copy_live_collect_20261022');assert len(runs['runs'])==1
    path,item=next(iter(runs['runs'].items()));live=item['report']
    assert live['passed'] and live['complete'] and live['rollback_verified']
    assert not live['rollback_timer_left_armed'] and live['usb_warning_count']==0
    assert live['observed_seconds']>=60 and live['observed_yolo_hz']>=9
    audit=probe('yunet_active_release_audit');kernel=probe('t3_fault_snapshot_20261022')
    assert audit['pid']==live['restored']['pid']==264975
    assert audit['sface_shadow_absent'] and audit['cu_collector_inactive'] and not audit['active_owned_rollback_timers']
    assert audit['original_database_path_preserved'] and audit['face_backend_hashes_verified']
    assert audit['face_targets']['backend']=='DPU_YUNET_INT8'
    assert audit['camera_unit_sha256']==live['original_unit_sha256']
    for name,pid in live['protected_unit_pids'].items():assert 'MainPID='+pid+'\n' in audit['units'][name]
    original=read(Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_live_baseline/release.json'))
    assert audit['source_hashes']==original['yunet']['candidate_source_sha256']
    put('evidence/audio-dummy-final.json',audio);put('evidence/audio-dummy-provenance.json',ap)
    put('evidence/merged-import-contract.json',merged);put('evidence/merged-import-provenance.json',mp)
    put('evidence/capture-copy-live.json',live)
    put('evidence/capture-copy-live-provenance.json',{'path':path,'board_report_sha256':item['sha256'],
        'shared_format':'Parsed and reindented JSON; original board bytes hash is above'})
    put('evidence/final-active-audit.json',audit);put('evidence/post-copy-audio-tail.json',kernel)
    copy(ROOT/'manifest.json',OUT/'merged-manifest.json')
    copy(ROOT/'bundle-provenance.json',OUT/'bundle-provenance.json')
    copy(ROOT/'test-results.txt',OUT/'merged-test-results.txt')
    for p in sorted((ROOT/'candidate/aura').rglob('*.py')):
        copy(p,OUT/'merged-candidate/aura'/p.relative_to(ROOT/'candidate/aura'))
    producer_count=frozen(Path('/home/ghmd/aura-sface-producer-20261022'),OUT/'producer-candidate')
    timing_count=frozen(Path('/home/ghmd/aura-optional-timing-v2-20261022'),OUT/'timing-candidate')
    for name in ['README.md','idle_maintenance_engine.py','test_idle_maintenance_engine.py',
        'build_board_dummy_check.py','engine-test-results.txt','engine-test-results-initial.txt',
        'actual-source-manifest.json','engine-manifest.json']:
        copy(AUDIO/name,OUT/'audio-maintenance'/name)
    engine_source=Path('/home/ghmd/aura-audio-recovery-20261021/live-source/tools')
    for name in ['gstreamer_persistent_engine.py','gstreamer_audio_engine.py']:
        copy(engine_source/name,OUT/'audio-maintenance/recovered-engine/tools'/name)
    for name in ['build_candidate.py','build_import_bundle.py','board_import_contract_body.py',
        'build_copy_live_check.py','run_tests.py']:
        copy(ROOT/name,OUT/'source'/name)
    for name in ['board_capture_copy_live_20261022.py','board_merged_import_contract_20261022.py',
        'board_audio_maintenance_dummy_20261022_v2.py']:
        copy(Path('/home/ghmd/aura-identity-dpu-check-20261018')/name,OUT/'source'/name)
    for name in ['capture_copy_live_collect_20261022.py','yunet_active_release_audit.py','t3_fault_snapshot_20261022.py']:
        copy(PROBES/name,OUT/'source'/name)
    old=read(Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_parallel_pipeline/evidence/callback-2thread-gst.json'))
    put('evidence/prior-local-callback-benchmark.json',old)
    now=datetime.now(timezone.utc).isoformat()
    release={'release_id':'AURA-SINGLE-TERMINAL-20261022-r1','updated_utc':now,
        'status':'AUDIO_ENGINE_TESTED_MERGED_IMPORT_PASSED_COPY_LIVE_PASSED_RESTORED',
        'single_codex_terminal':True,'new_subagents_started':0,
        'production':{'camera_pid':audit['pid'],'ui_pid':215734,'xserver_pid':1077,
            'yolo':'KV260_DPU','yunet':'KV260_DPU_CNN_ARM_PRE_POST','sface':'WINDOWS_CPU_CONFIGURED_ORIGINAL_DATABASE',
            'runtime':audit['runtime'],'camera_unit_sha256':audit['camera_unit_sha256'],
            'original_source_restored':True,'merged_candidate_enabled':False,'audio_maintenance_enabled':False,
            'shadow_enabled':False,'new_identity_database_created':False},
        'audio_engine':{'software_tests_passed':20,'real_gstreamer_fakesink_passed':True,
            'final_source_sha256':audio['candidate_source_sha256'],'alsa_or_mcp01_exercised':False,
            'owner_barrier_worker_ipc_integrated':False,'root_cause_fixed':False},
        'merged_candidate':{'source_files':13,'software_test_groups_passed':[56,45],
            'board_imported_modules':13,'board_config_check_passed':True,
            'actual_dpu_jobs_in_import_check':0,'live_merged_inference_wiring_verified':False},
        'copy_live_check':{'passed':True,'requested_seconds':60,'observed_seconds':live['observed_seconds'],
            'yolo_hz':live['observed_yolo_hz'],'capture_hz':live['observed_capture_hz'],
            'new_matching_usb_warnings':0,'rollback_verified':True,'ui_and_xserver_pid_preserved':True,
            'candidate_remains_production_enabled':False,'whole_board_cpu_gain_measured':False,
            'scope':'Real UVC callback short observation; no matched input gain or long stability acceptance'},
        'verification':{'source_model_manifest_unit_and_old_database_preserved':True,
            'owned_rollback_timers_inactive':True,'xrt_statistics_off':True,
            'biometric_media_features_database_or_raw_uart_copied_to_shared':False},
        'remaining':['Application owner/IPC/AEC maintenance transaction wiring',
            'Isolated live independent SFace producer and normal-timing validation',
            'Formal model-versioned enrollment and field threshold validation',
            'Same-input whole-pipeline performance and longer stability evidence'],
        'windows_sync_confirmed':False,'files_manifest':'FILES.sha256','validation':'validation.json'}
    put('release.json',release)
    py_count=json_count=links=0
    for p in OUT.rglob('*'):
        assert not p.is_symlink()
        if not p.is_file():continue
        assert '__pycache__' not in p.parts
        assert p.suffix.lower() not in {'.png','.jpg','.jpeg','.webp','.wav','.mp3','.mp4','.npy','.npz','.db','.sqlite','.sqlite3','.raw'}
        if p.suffix=='.py':ast.parse(p.read_text(),filename=str(p));py_count+=1
        if p.suffix=='.json':read(p);json_count+=1
        if p.suffix=='.md':
            for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
                if target.startswith(('http:','https:','#')):continue
                assert (p.parent/target).exists(),(p,target)
                links+=1
    put('validation.json',{'status':'PASS','verified_utc':now,
        'scope':'Artifact hashes, syntax, local links and result consistency, not additional model inference tests',
        'producer_frozen_entries':producer_count,'timing_frozen_entries':timing_count,
        'python_ast_files':py_count,'json_files_before_validation':json_count,'local_links_verified':links,
        'board_audio_gst_is_dummy_sink_only':True,'merged_board_import_is_not_live_inference':True,
        'copy_live_result_and_original_restoration_consistent':True})
    manifest=OUT/'FILES.sha256'
    files=sorted(p for p in OUT.rglob('*') if p.is_file() and p!=manifest)
    manifest.write_text(''.join(sha(p)+'  '+str(p.relative_to(OUT))+'\n' for p in files))
    for line in manifest.read_text().splitlines():
        digest,name=line.split('  ',1);assert sha(OUT/name)==digest
    print(json.dumps({'status':release['status'],'manifest_files_verified':len(files),
        'python_ast_files':py_count,'json_files':json_count,'local_links':links,
        'camera_pid':audit['pid'],'software_test_groups':[20,56,45]}))


if __name__=='__main__':main()
