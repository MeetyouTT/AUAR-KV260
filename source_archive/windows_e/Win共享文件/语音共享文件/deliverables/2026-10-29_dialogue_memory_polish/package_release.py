"""Freeze the current Windows patch plus auditable public receipts; never package data/models."""
import ast,datetime,hashlib,json,re,sys,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
read=lambda name:json.loads((H/name).read_text(encoding='utf-8-sig'))
verified,deploy,plan,compare=map(read,('release_verification.json','deployment.json','source_plan.json','comparison.json'))
assert verified['status']==compare['status']=='PASS' and deploy['status']=='COMMITTED'
assert verified['revision']==plan['candidate_revision']=='voice-dialogue-memory-20261029-r4'
assert verified['fingerprint']==plan['candidate_fingerprint']
assert verified['original_database_sources_unchanged'] and verified['other_models_preserved'] and verified['public_test_rows_removed']
assert verified['general_chat_latency_improved'] is False and verified['board_migration'] is False
suites=list(ET.parse(H/'tests.xml').getroot().iter('testsuite'))
assert sum(int(s.get('tests',0)) for s in suites)==267
assert sum(int(s.get('errors',0))+int(s.get('failures',0))+int(s.get('skipped',0)) for s in suites)==0
memory,voice,board=map(read,('live_controls_acceptance.json','live_voice_acceptance.json','board_probe.json'))
assert memory['status']==voice['status']==board['status']=='PASS'
assert len(memory['turns'])==12 and len(voice['checks'])==7 and len(board['turns'])==2
assert read('public_probe_cleanup.json')['actual_source_coverage_verified']
assert read('board_probe_cleanup.json')['only_public_test_conversation_removed']
sys.path.insert(0,str(A))
from common.voice_service_capabilities import source_fingerprint
assert source_fingerprint(A)==verified['fingerprint']
entries={}
for name,entry in plan['files'].items():
 candidate=H/'candidate_source'/name
 assert hashlib.sha256(candidate.read_bytes()).hexdigest()==entry['candidate'] and candidate.read_bytes()==(A/name).read_bytes()
 entries['candidate_source/'+name]=candidate
 if entry['before'] is not None:
  original=H/'before'/name
  assert hashlib.sha256(original.read_bytes()).hexdigest()==entry['before']
  entries['before/'+name]=original
names=('README.md','CONTINUE.md','bootstrap.py','run_tests.py','test_controls.py','test_natural_memory.py',
 'test_timeline.py','test_summaries.py','tests_final.log','tests.xml','prepare_candidate.py','edit_candidate.py',
 'prepare_release.py','source_plan.json','deploy_windows.py','deployment.json','board_baseline.json',
 'manage_owned.ps1','db_checkpoint.py','start_checkpoint.ps1','original_database_checkpoint.json','synthesize_question.ps1',
 'live_controls_acceptance.py','live_controls_acceptance.json','cleanup_public_probe.py','public_probe_cleanup.json',
 'live_voice_acceptance.py','live_voice_acceptance.json','live_voice.log','voice_restart.log',
 'board_client_probe.py','board_probe.json','board_probe_before_cleanup_fix.json','board_probe_cleanup_first_failure.json',
 'board_probe_cleanup.json','finish_board_cleanup.py','benchmark_live.py','benchmark_cleanup.py',
 'benchmark_before.json','benchmark_after.json','experiment.json','build_comparison.py','comparison.json',
 'verify_private.py','physical_database_check.json','verify_release.py','release_verification.json','update_handoff.py','package_release.py')
for name in names:entries[name]=H/name
for path in sorted(H.glob('cleanup_*.json')):entries[path.name]=path
entries['docs/device_capabilities.md']=A/'skills/aura-devices/references/capabilities.md'
for name,path in entries.items():
 assert path.is_file() and path.suffix.lower() in ('.py','.ps1','.json','.md','.xml','.log'),name
 assert not path.is_symlink(),name
 if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8'))
 if path.suffix=='.json':json.loads(path.read_text(encoding='utf-8-sig'))
 assert not re.search(r'(?i)\.(sqlite3?|db|wav|mp3|ogg|jpg|png|gguf|safetensors|bin|pem|key)$',name)
manifest={'revision':verified['revision'],'source_fingerprint':verified['fingerprint'],'authority':'Windows',
 'board_migration':False,'whole_project_complete':False,
 'scope':'Patch for the existing AURA project and runtime; excludes raw data, identity templates, media, models, keys, environments and mutable PROGRESS.json.',
 'files':{name:{'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for name,path in sorted(entries.items())}}
raw=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
archive=H/'verified_source.zip';assert not archive.exists(),'Inspect existing archive instead of replacing it'
(H/'verified_manifest.json').write_bytes(raw)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for name,path in sorted(entries.items()):z.write(path,name)
 z.writestr('verified_manifest.json',raw)
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 assert set(z.namelist())==set(entries)|{'verified_manifest.json'}
 for name,value in manifest['files'].items():
  data=z.read(name);assert len(data)==value['bytes'] and hashlib.sha256(data).hexdigest()==value['sha256'],name
progress={'status':'WINDOWS_R4_DEPLOYED_SCOPED_AUTOMATED_ACCEPTANCE_PASS','complete':True,
 'scope':'This batch: natural current fact answers, indexed history, automatic provenance safety and measured target-path effect.',
 'whole_project_complete':False,'full_memory_roadmap_complete':False,
 'user_direction':'继续完善Windows对话与记忆并验证效果；板端迁移暂缓','migration_deferred':True,
 'board_migration':False,'authority':'Windows','production_revision':verified['revision'],'source_fingerprint':verified['fingerprint'],
 'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'tests':{'windows_passed':267,'includes_prior_related_210':True,'arm_pytest_this_stage':False,
          'actual_memory_steps':12,'actual_voice_function_checks':7,'existing_board_client_exchanges':2},
 'implemented':['natural_explicit_current_fact_answers_without_llm','indexed_full_stored_history_values_1_to_32',
                'chinese_history_ordinals','natural_previous_value_questions','automatic_old_writer_provenance_safety',
                'complete_source_marker_including_empty_context','skip_unused_context_for_direct_memory_answers'],
 'original_database_sources_unchanged':True,'public_test_conversations_removed':True,
 'board_ui_restarted':False,'camera_restarted':False,'hub_restarted':False,
 'preserved_parallel_latency_fix':True,'compact_grammar':False,'other_models_preserved':True,'other_listeners_preserved':True,
 'microphone_opened':False,'physical_audio_played':False,'successful_playback_ack':False,'new_motion_started':False,
 'board_final':verified['board'],'llm_storage':'D:/AIModels','background_model_inference':False,
 'performance':{'fact_repeat_first_pcm_median_ms':[compare['repeat_before']['median_first_pcm_ms'],compare['repeat_after']['median_first_pcm_ms']],
   'fact_repeat_first_text_median_ms':[compare['repeat_before']['median_first_text_ms'],compare['repeat_after']['median_first_text_ms']],
   'repeat_first_pcm_reduction_percent':compare['repeat_first_pcm_reduction_percent'],
   'after_repeat_tts_cache_hits':compare['repeat_after']['tts_cache_hits'],'initial_cache_miss':compare['initial_cache_miss'],
   'general_chat_control':compare['general_chat_control'],'frontend':verified['frontend'],
   'strict_20ms_frontend_passed':verified['strict_frontend_20ms_passed'],'stable_general_low_latency_accepted':False,
   'board_first_pcm_ms':[t['first_pcm_ms'] for t in board['turns']]},
 'limits':['Target speedup includes direct fact routing and repeated TTS cache; not raw model acceleration.',
           'General chat controls were slower after in this small sample; cause unconfirmed, further work required.',
           'Natural fact queries are a conservative whitelist; face identity routing and permissions remain.',
           'Fact dates are recorded/corrected time, not actual effective dates; 32 versions/key, stored value <=64 chars.',
           'Unknown provenance uses conservative withholding rather than reconstructing past sources.',
           'Transcript deletion leaves visual events and private backups intact.',
           'Human audio, cross-day memory and whole-device acceptance are still pending.'],
 'pending_this_batch':[],
 'next_windows_work':['general_dialogue_first_sentence_and_tts_tail','fact_effective_dates_and_richer_history',
                      'cross_day_human_memory_acceptance','short_word_wake','speaking_frame_tail',
                      'audiovisual_attribution','field_voiceprint_calibration'],
 'automations_created':False,'source_archive_files':len(entries)+1,
 'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
# Write progress before validating its README link.
(H/'PROGRESS.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
for document in ('README.md','CONTINUE.md'):
 for target in re.findall(r'\]\(([^)]+)\)',(H/document).read_text(encoding='utf-8')):
  assert target.startswith('http') or (H/target).is_file(),target
result={'status':'PASS','archive_files':len(entries)+1,'archive_bytes':archive.stat().st_size,
 'archive_sha256':progress['source_archive_sha256'],'source_and_archive_match':True,'crc_pass':True,'links_pass':True}
(H/'package_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
