"""Freeze the deployed Windows-only source patch and public metadata."""
import ast,datetime,hashlib,json,re,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
def read(name):return json.loads((H/name).read_text(encoding='utf-8-sig'))
verified=read('release_verification.json');deployment=read('deployment.json');plan=read('source_plan.json')
assert verified['status']=='PASS' and deployment['status']=='COMMITTED'
suites=list(ET.parse(H/'tests.xml').getroot().iter('testsuite'))
assert sum(int(s.get('tests',0)) for s in suites)==210
assert sum(int(s.get('errors',0))+int(s.get('failures',0)) for s in suites)==0
assert read('live_controls_acceptance.json')['status']==read('live_voice_acceptance.json')['status']=='PASS'
entries={}
for name,entry in plan['files'].items():
    path=H/'candidate_source'/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['candidate'] and path.read_bytes()==(A/name).read_bytes()
    entries['candidate_source/'+name]=path
names=('README.md','CONTINUE.md','bootstrap.py','run_tests.py','test_controls.py','test_timeline.py','test_summaries.py','tests_final3.log','tests.xml',
       'prepare_candidate.py','edit_candidate.py','prepare_release.py','source_plan.json','deploy_windows.py','deployment.json',
       'board_baseline.json','manage_owned.ps1','db_checkpoint.py','start_checkpoint.ps1','synthesize_question.ps1',
       'live_controls_acceptance.py','live_controls_acceptance.json','cleanup_public_probe.py','public_probe_cleanup.json',
       'live_voice_acceptance.py','live_voice_acceptance.json','verify_private.py','physical_database_check.json','verify_release.py',
       'release_verification.json','package_release.py')
for name in names:entries[name]=H/name
entries['docs/device_capabilities.md']=A/'skills/aura-devices/references/capabilities.md'
for name,path in entries.items():
    assert path.is_file() and path.suffix.lower() in ('.py','.ps1','.json','.md','.xml','.log')
    if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8'))
manifest={'revision':verified['revision'],'source_fingerprint':verified['fingerprint'],'authority':'Windows','board_migration':False,
          'scope':'Patch for the existing AURA project; excludes private data/media/models/keys/environments and mutable PROGRESS.json',
          'files':{n:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for n,p in sorted(entries.items())}}
raw=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
(H/'verified_manifest.json').write_bytes(raw);archive=H/'verified_source.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name,path in sorted(entries.items()):z.write(path,name)
    z.writestr('verified_manifest.json',raw)
with zipfile.ZipFile(archive) as z:
    assert set(z.namelist())==set(entries)|{'verified_manifest.json'}
    for name,value in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==value['sha256']
memory=read('live_controls_acceptance.json');voice=read('live_voice_acceptance.json')
progress={'status':'WINDOWS_R3_DEPLOYED_AUTOMATED_ACCEPTANCE_PASS','complete':True,
          'scope':'This Windows fact-history, confirmed deletion and dialogue-context batch; not entire doll/memory roadmap',
          'whole_project_complete':False,'user_direction':'先完善Windows对话与记忆，迁移后置','migration_deferred':True,
          'board_migration':False,'authority':'Windows','production_revision':verified['revision'],'source_fingerprint':verified['fingerprint'],
          'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'tests':{'windows_passed':210,'includes_prior_related_tests':True,'arm_run_this_stage':False,'actual_memory_steps':7,'actual_voice_function_checks':7},
          'implemented':['bounded_fact_revision_history','confirmed_date_topic_transcript_deletion','derived_reply_source_invalidation',
                         'immediate_digest_invalidation','skip_unused_context_for_memory_commands','preserve_mutation_on_tts_failure'],
          'original_database_sources_unchanged':True,'public_test_conversation_removed':True,'board_ui_restarted':False,'camera_restarted':False,
          'preserved_parallel_latency_fix':True,'compact_grammar':False,'other_models_preserved':True,
          'other_listeners_preserved':True,'microphone_opened':False,'physical_audio_played':False,'successful_playback_ack':False,
          'board_final':verified['board'],'llm_storage':'D:/AIModels','background_model_inference':False,
          'performance':{'memory_first_pcm_ms':[r['first_pcm_ms'] for r in memory['turns']],
                         'ordinary_first_pcm_ms':[r['result']['first_ms']['audio'] for r in voice['checks'] if r['name'] in ('actual_public_asr_llm_tts_receive','actual_recovery_next_turn')],
                         'frontend':next(r['result'] for r in voice['checks'] if r['name']=='paced_frontend_public_audio'),
                         'strict_20ms_frontend_pass':False,'stable_low_latency_accepted':False},
          'limits':['Fact dates are recorded/corrected dates; voice lists latest two and truncates long values, 32 versions per key',
                    'Delete preview lasts60s; max1000 selected turns and2000 related turns; literal topic <=16 chars',
                    'Visual records/backups/media traces not erased by transcript deletion',
                    'Legacy provenance is conservative; a mixed older-writer downgrade requires rebuilding the legacy safety baseline',
                    'Human microphone/playback and cross-day acceptance remain pending'],
          'pending_this_batch':[],'next_windows_work':['natural_dialogue_and_latency_tail','complete_fact_history_browsing_and_effective_dates',
              'cross_day_human_memory_acceptance','short_word_wake','audiovisual_attribution','field_voiceprint_calibration'],
          'automations_created':False,'source_archive_files':len(entries)+1,'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
(H/'PROGRESS.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
for document in ('README.md','CONTINUE.md'):
    for target in re.findall(r'\]\(([^)]+)\)',(H/document).read_text(encoding='utf-8')):
        assert target.startswith('http') or (H/target).exists(),target
print(json.dumps({'status':progress['status'],'windows_passed':210,'actual_memory_steps':7,'actual_voice_checks':7,
                  'board_migration':False,'archive_files':len(entries)+1,'archive_sha256':progress['source_archive_sha256']}))

