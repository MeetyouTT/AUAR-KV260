"""Package only verified source/metadata; no audio, data, model or credential content."""
import ast,datetime,hashlib,json,re,sys,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
read=lambda name:json.loads((H/name).read_text(encoding='utf-8-sig'))
v,p,live=map(read,('release_verification.json','source_plan.json','live_handoff_final.json'))
assert v['status']==live['status']=='PASS' and p['status']=='RECOVERY_DEPLOYED_AND_VERIFIED'
assert read('deployment_recovery.json')['status']=='COMMITTED'
sys.path.insert(0,str(A))
from common.voice_service_capabilities import source_fingerprint
assert source_fingerprint(A)==v['fingerprint']==p['candidate_fingerprint']
suites=list(ET.parse(H/'tests.xml').getroot().iter('testsuite'))
assert sum(int(s.get('tests',0)) for s in suites)==285
assert not sum(int(s.get('errors',0))+int(s.get('failures',0))+int(s.get('skipped',0)) for s in suites)
assert v['original_database_sources_unchanged'] and v['other_models_preserved'] and v['other_listeners_preserved']
assert len(live['checks'])==5 and all(r['status']=='PASS' for r in live['checks'])
entries={}
for name,row in p['files'].items():
 target=H/'candidate_source'/name
 assert hashlib.sha256(target.read_bytes()).hexdigest()==row['candidate'] and target.read_bytes()==(A/name).read_bytes()
 entries['candidate_source/'+name]=target
 before=H/'before_recovery'/name
 assert hashlib.sha256(before.read_bytes()).hexdigest()==row['before']
 entries['before_recovery/'+name]=before
for name,row in p['original_r4_files'].items():
 if row['before'] is not None:
  target=H/'before'/name;assert hashlib.sha256(target.read_bytes()).hexdigest()==row['before'];entries['before/'+name]=target
 target=H/'attempt1/candidate_source'/name
 assert hashlib.sha256(target.read_bytes()).hexdigest()==row['candidate'];entries['attempt1/candidate_source/'+name]=target
names=('README.md','CONTINUE.md','source_plan.json','bootstrap.py','run_tests.py','test_handoff.py','test_natural_memory.py',
 'test_controls.py','test_timeline.py','test_summaries.py','tests.xml','tests_recovery.log',
 'capture_sources.py','baseline_reproduce.py','baseline_reproduction.json','prepare_candidate.py','edit_candidate.py',
 'prepare_deploy.py','prepare_recovery.py','freeze_recovery.py','deploy_windows.py','deploy_recovery.py',
 'deployment.json','deployment_recovery.json','deployment_recovery_launcher_failure.json','listening_pause.json',
 'manage_owned.ps1','db_checkpoint.py','start_checkpoint.ps1','original_database_checkpoint.json',
 'synthesize_question.ps1','live_handoff.py','live_handoff.json','live_handoff_final.json','live_handoff_final_network.log',
 'verify_private.py','physical_database_check.json','verify_release.py','release_verification.json',
 'board_baseline.json','update_handoff.py','package_release.py',
 'attempt1/source_plan.json','attempt1/deployment.json','attempt1/live_handoff.json','attempt1/tests.xml','attempt1/tests_first.log')
for name in names:entries[name]=H/name
entries['docs/device_capabilities.md']=A/'skills/aura-devices/references/capabilities.md'
for name,target in entries.items():
 assert target.is_file() and target.suffix.lower() in ('.py','.ps1','.json','.md','.xml','.log') and not target.is_symlink(),name
 if target.suffix=='.py':ast.parse(target.read_text(encoding='utf-8'))
 if target.suffix=='.json':json.loads(target.read_text(encoding='utf-8-sig'))
manifest={'revision':v['revision'],'source_fingerprint':v['fingerprint'],'authority':'Windows','board_migration':False,
 'scope':'Existing AURA project patch and public diagnostic receipts; no raw memory, identities, images, audio, models, keys or environments.',
 'files':{n:{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for n,f in sorted(entries.items())}}
raw=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8');archive=H/'verified_source.zip'
assert not archive.exists()
(H/'verified_manifest.json').write_bytes(raw)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for name,target in sorted(entries.items()):z.write(target,name)
 z.writestr('verified_manifest.json',raw)
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None and set(z.namelist())==set(entries)|{'verified_manifest.json'}
 for name,row in manifest['files'].items():
  data=z.read(name);assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
progress={'status':'R6_HANDOFF_FIX_DEPLOYED_AUTOMATED_ACCEPTANCE_PASS','complete':True,
 'scope':'Confirmed HTTP503 cancellation handoff path and warm TTS retention; exact human phrase retest pending.',
 'whole_project_complete':False,'human_retest_pending':True,'user_issue':'识别后跳回聆听',
 'production_revision':v['revision'],'source_fingerprint':v['fingerprint'],
 'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'tests':{'windows_passed':285,'includes_previous_267':True,'handoff_specialized':18,
          'actual_board_handoff_pairs':3,'actual_wake_protocol_checks':2,'arm_pytest_this_stage':False},
 'actual_handoff_first_pcm_ms':v['live_first_pcm_ms'],
 'actual_admission_wait_ms':[next(r['admission_wait_ms'] for r in live['voice_diagnostics']['recent'] if r['request_id']==check['next_request_id']) for check in live['checks'][:3]],
 'busy_or_expired_in_final_probe':False,'original_database_sources_unchanged':True,
 'other_models_preserved':True,'other_listeners_preserved':True,'board_code_changed':False,'board_ui_restarted':False,'camera_restarted':False,
 'board_migration':False,'migration_deferred':True,'microphone_opened_by_agent':False,'physical_audio_played':False,'successful_playback_ack':False,
 'listening_paused_via_existing_ui':True,'listening_remains_off':True,'restore_microphone_automatically':False,
 'board_final':v['board'],'compact_grammar':False,'other_five_latency_options':True,'llm_storage':'D:/AIModels',
 'first_r5_candidate_failed_live_acceptance':True,'failed_attempt_preserved':'attempt1/',
 'recovery_launcher_failure_preserved':'deployment_recovery_launcher_failure.json',
 'human_verbatim_supplied':False,'pending_this_automated_fix':[],
 'limits':['No generic dialogue latency speedup claimed; actual next request PCM 4.69 to8.08 seconds.',
           'One in-flight TTS finishes within its original deadline and is discarded; true faults retain original isolation.',
           'Admission maximum5s does not extend total request or worker deadlines; real overload can still reject.',
           'Wake-only returns listening by design; live wake accuracy and short interjections remain pending.',
           'No microphone/playback/human acoustic or long-run acceptance in this probe.'],
 'automations_created':False,'source_archive_files':len(entries)+1,'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
(H/'PROGRESS.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ('README.md','CONTINUE.md'):
 for target in re.findall(r'\]\(([^)]+)\)',(H/name).read_text(encoding='utf-8')):
  assert target.startswith('http') or (H/target).is_file(),target
result={'status':'PASS','archive_files':len(entries)+1,'archive_bytes':archive.stat().st_size,'sha256':progress['source_archive_sha256'],
 'source_matches_production':True,'crc_pass':True,'links_pass':True}
(H/'package_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
