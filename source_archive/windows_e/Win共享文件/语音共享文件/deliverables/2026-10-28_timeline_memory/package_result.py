"""Package only reviewed code/docs; never running databases, images or models."""
import datetime,hashlib,json,zipfile
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
def read(name):return json.loads((H/name).read_text(encoding='utf-8-sig'))
deployment=read('deployment.json');release=read('release_verification.json');voice=read('live_voice_acceptance.json')
model=read('real_model_check.json');persistence=read('live_persistence.json');arm=read('arm_tests.json');benchmark=read('benchmark.json')
assert deployment['status']=='COMMITTED' and all(r['status']=='PASS' for r in (release,voice,model,persistence))
assert arm['returncode']==0 and benchmark['passed']
entries={}
for path in (H/'candidate_source').rglob('*'):
    if path.is_file() and path.suffix in ('.py','.json'):
        name=path.relative_to(H/'candidate_source').as_posix();actual=A/name
        assert actual.read_bytes()==path.read_bytes(),'Applied source changed: '+name
        entries['aura/'+name]=actual
for name in ('SKILL.md','references/capabilities.md'):
    entries['aura/skills/aura-devices/'+name]=A/'skills/aura-devices'/name
entries['deliverables/2026-10-28_device_skills/start_devices.py']=H.parent/'2026-10-28_device_skills/start_devices.py'
for name in ('README.md','CONTINUE.md','bootstrap.py','test_timeline.py','run_tests.py','arm_tests.py','benchmark.py',
             'deploy_windows.py','manage_owned.ps1','verify_deployment.py','inspect_current.py','inspect_runtime.py',
             'inspect_service_databases.py','inspect_database_locations.py','install_timezone.py','live_persistence.py',
             'real_model_check.py','live_voice_acceptance.py','start_devices_before.py','start_devices_candidate.py','package_result.py'):
    entries['deliverables/2026-10-28_timeline_memory/'+name]=H/name
manifest={name:{'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size} for name,path in sorted(entries.items())}
archive=H/'verified_source.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as bundle:
    for name,path in sorted(entries.items()):bundle.write(path,name)
with zipfile.ZipFile(archive) as bundle:
    assert set(bundle.namelist())==set(manifest)
    assert all(hashlib.sha256(bundle.read(name)).hexdigest()==row['sha256'] for name,row in manifest.items())
    assert all(Path(name).suffix in ('.py','.json','.ps1','.md') for name in bundle.namelist())
(H/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
progress={'status':'TIMELINE_V1_DEPLOYED_AUTOMATED_ACCEPTANCE_PASSED','complete':False,'milestone_complete':True,
          'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'windows_revision':release['windows_revision'],'source_fingerprint':release['windows_source_fingerprint'],
          'device_revision':'device-timeline-v1','memory_authority':'Windows','actual_board_code_changed':False,
          'board_runtime':release['board']['runtime'],'board_boot':release['board']['boot'],'deployment_boot':release['deployment_boot'],
          'state':{k:release['board'][k] for k in ('phase','listening','microphone_open','following','mechanical','mixer')},
          'timezone':'America/Los_Angeles','calendar_source':'host_received_utc','visual_history_days':30,'visual_history_limit':10000,
          'raw_images_saved':False,'speaker_auto_profile_access':False,
          'tests':{'windows_passed':144,'arm_passed':39,'overlap_do_not_add':True,'actual_llm_checks':3,'actual_public_voice_checks':7},
          'voice_first_pcm_ms':[r['result']['first_ms']['audio'] for r in voice['checks'] if r['name'] in ('actual_public_asr_llm_tts_receive','actual_recovery_next_turn')],
          'real_visual_persistence':'PASS','physical_private_database_view':'independent_WMI','private_snapshot_kind':'post_upgrade',
          'other_model_owners_preserved':release['other_model_owners_preserved'],'llm_storage':'D:/AIModels',
          'remaining':['background_episode_daily_summaries','fact_validity_history','conversation_date_topic_deletion',
                       'PS_authoritative_storage_handoff','cross_day_human_acceptance'],
          'inherited_open':['short_wake_ai_ei','speaking_long_frames','speaker_field_calibration','audiovisual_attribution','mechanical_exact_binding'],
          'automations_created':False,'archive_files':len(manifest),'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
(H/'PROGRESS.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':progress['status'],'source_files':len(manifest),'archive_sha256':progress['source_archive_sha256']}))
