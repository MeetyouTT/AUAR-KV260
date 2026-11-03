"""Package a verified source patch and metadata; never include private databases/media."""
import ast,datetime,hashlib,json,re,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
def read(name):return json.loads((H/name).read_text(encoding='utf-8-sig'))
deployment=read('deployment.json');verified=read('release_verification.json')
assert deployment['status']=='COMMITTED' and verified['status']=='PASS'
assert read('physical_database_check.json')['original_sources_unchanged']
assert read('live_summary_acceptance.json')['status']==read('live_voice_acceptance.json')['status']=='PASS'
assert read('arm_tests.json')['returncode']==0 and '64 passed' in read('arm_tests.json')['log']
suites=list(ET.parse(H/'tests.xml').getroot().iter('testsuite'))
assert sum(int(s.get('tests',0)) for s in suites)==169
assert not sum(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites)
plan=read('deployment_preview.json');entries={}
for name,entry in plan['files'].items():
    source=H/'candidate_source'/name
    assert hashlib.sha256(source.read_bytes()).hexdigest()==entry['candidate']
    assert source.read_bytes()==(A/name).read_bytes()
    entries['candidate_source/'+name]=source
names=('README.md','CONTINUE.md','bootstrap.py','run_tests.py','test_timeline.py','test_summaries.py',
       'benchmark.py','benchmark.json','arm_tests.py','arm_tests.json','tests_final.log','tests.xml',
       'capture_board.py','board_baseline.json','deploy_windows.py','deployment_preview.json','deployment.json',
       'deployment_first_timeout.json','manage_owned.ps1','start_devices_before.py','start_devices_candidate.py',
       'db_checkpoint.py','start_checkpoint.ps1','diagnostic_voice_entry.py','launch_models_diagnostic.py',
       'start_voice_diagnostic.ps1','synthesize_question.ps1','live_summary_acceptance.py','live_summary_acceptance.json',
       'remove_probe.py','probe_removed.json','live_voice_acceptance.py','live_voice_acceptance.json',
       'verify_private.py','verify_deployment.py','physical_database_check.json','release_verification.json',
       'voice_startup_stacks.log','package_deployed.py')
for name in names:entries[name]=H/name
for name,path in entries.items():
    assert path.is_file() and path.suffix.lower() in ('.py','.ps1','.json','.md','.xml','.log')
    if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8'))
    assert (b'-----BEGIN '+b'PRIVATE KEY-----') not in path.read_bytes()
manifest={'purpose':'Source patch and metadata for the existing project; hashes cover archive members excluding this manifest itself.',
          'revision':verified['windows_revision'],'source_fingerprint':verified['source_fingerprint'],
          'files':{name:{'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size} for name,path in sorted(entries.items())},
          'excluded':['private databases and backups','identity templates','images and audio','models','keys','virtual environments','mutable PROGRESS.json']}
manifest_bytes=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
(H/'verified_manifest.json').write_bytes(manifest_bytes)
archive=H/'verified_source.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as bundle:
    for name,path in sorted(entries.items()):bundle.write(path,name)
    bundle.writestr('verified_manifest.json',manifest_bytes)
with zipfile.ZipFile(archive) as bundle:
    assert set(bundle.namelist())==set(entries)|{'verified_manifest.json'}
    assert bundle.read('verified_manifest.json')==manifest_bytes
    for name,entry in manifest['files'].items():assert hashlib.sha256(bundle.read(name)).hexdigest()==entry['sha256']
for path in (H/'README.md',H/'CONTINUE.md'):
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        assert target.startswith('http') or (path.parent/target).exists(),target
progress={'status':'DEPLOYED_AUTOMATED_ACCEPTANCE_PASS','complete':True,
    'scope':'timeline background episode/day summaries deployment; not the entire memory roadmap or doll',
    'production_deployed':True,'offline_implementation_complete':True,'user_hold_board':False,'user_direction':'可以实际部署了',
    'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'production_source_revision':verified['windows_revision'],'production_source_fingerprint':verified['source_fingerprint'],
    'production_device_revision':deployment['after_hub']['revision'],'source_files_applied':len(plan['files']),
    'tests':{'windows_passed':169,'arm_passed':64,'overlap_with_previous_stage':True,'arm_run_this_stage':True,
             'live_service_tests_run_this_stage':True,'live_summary_checks':4,'live_voice_checks':7},
    'benchmark':read('benchmark.json'),'source_mutations_to_canonical_code':True,'board_formal_runtime_mutations':False,
    'board_ui_restarted':False,'camera_restarted':False,'isolated_arm_test_bundle_created':True,
    'production_restarts':{'voice':True,'device_hub':True,'asr_recovered':True,'frontend_recovered':True},
    'live_database_migrations':True,'original_database_sources_preserved':True,'real_models_called':True,
    'background_model_inference':False,'raw_images_saved':False,'microphone_opened':False,'physical_audio_played':False,
    'other_model_owners_preserved':True,'llm_storage':'D:/AIModels','authority':'Windows',
    'board_final':verified['board'],'pending_this_deployment':[],
    'known_limitations':['First cold startup exceeded unchanged 300s deadline and rolled back; second ready in approximately 144s; variability not proven resolved',
                         'No human microphone, audible playback or cross-day acceptance'],
    'later_plan_items':['fact_validity_history','conversation_date_topic_deletion','PS_authoritative_storage_handoff','cross_day_human_acceptance',
                        'short_word_wake','speaking_long_frames','audiovisual_speaker_attribution','field_voiceprint_calibration'],
    'automations_created':False,'verified_source_archive_files':len(entries)+1,
    'verified_source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
    'historical_offline_archive_sha256':hashlib.sha256((H/'candidate_source.zip').read_bytes()).hexdigest()}
(H/'PROGRESS.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':progress['status'],'archive_files':progress['verified_source_archive_files'],
    'archive_sha256':progress['verified_source_archive_sha256'],'windows_passed':169,'arm_passed':64,'board_ui_restarted':False}))
