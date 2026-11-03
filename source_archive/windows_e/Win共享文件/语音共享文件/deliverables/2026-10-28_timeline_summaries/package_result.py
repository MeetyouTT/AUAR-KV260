"""Freeze the tested offline candidate without touching production code or data."""
import ast,datetime,hashlib,json,re,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
H=Path(__file__).resolve().parent
assert not (H/'deployment.json').exists(),'Historical offline packager; preserve deployment receipts and use package_deployed.py'
plan=json.loads((H/'deployment_preview.json').read_text(encoding='utf-8'))
benchmark=json.loads((H/'benchmark.json').read_text(encoding='utf-8'))
xml=ET.parse(H/'tests.xml').getroot();suites=list(xml.iter('testsuite'))
tests=sum(int(s.get('tests',0)) for s in suites)
assert tests==169 and sum(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites)==0
assert benchmark['pass'] and plan['status']=='READY_OFFLINE_USER_HOLD' and not plan['applied']
entries={}
for path in (H/'candidate_source').rglob('*.py'):
    name=path.relative_to(H/'candidate_source').as_posix()
    assert hashlib.sha256(path.read_bytes()).hexdigest()==plan['files'][name]['candidate']
    ast.parse(path.read_text(encoding='utf-8'));entries['candidate_source/'+name]=path
for name in ('README.md','CONTINUE.md','bootstrap.py','run_tests.py','test_timeline.py','test_summaries.py',
             'benchmark.py','prepare_release.py','arm_tests.py','start_devices_before.py','start_devices_candidate.py',
             'deployment_preview.json','package_result.py'):
    path=H/name
    if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8'))
    entries[name]=path
manifest={name:{'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size} for name,path in sorted(entries.items())}
archive=H/'candidate_source.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as bundle:
    for name,path in sorted(entries.items()):bundle.write(path,name)
with zipfile.ZipFile(archive) as bundle:
    assert set(bundle.namelist())==set(manifest)
    for name in bundle.namelist():assert hashlib.sha256(bundle.read(name)).hexdigest()==manifest[name]['sha256']
(H/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
progress={'status':'OFFLINE_CANDIDATE_READY_USER_HOLD','complete':False,'offline_implementation_complete':True,
    'production_deployed':False,'user_hold_board':True,'user_direction':'是，先保留板端现状',
    'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'production_source_revision':plan['expected_production_revision'],'production_source_fingerprint':plan['expected_production_fingerprint'],
    'candidate_revision':plan['candidate_revision'],'candidate_fingerprint':plan['candidate_fingerprint'],
    'candidate_device_revision':plan['hub_candidate'],'candidate_files':len(plan['files']),
    'tests':{'windows_passed':tests,'overlap_with_previous_stage':True,'arm_run_this_stage':False,'live_service_tests_run_this_stage':False},
    'benchmark':benchmark,'source_mutations_to_canonical_code':False,'board_mutations':False,
    'production_restarts':False,'live_database_migrations':False,'real_models_called':False,
    'background_model_inference':False,'raw_images_saved':False,'llm_storage':'D:/AIModels',
    'pending':['User confirms the parallel board test is finished','Fresh actual runtime and source preflight',
               'ARM isolated memory tests','WMI production-view snapshots and controlled service deployment','Actual speech and source-revocation acceptance'],
    'later_plan_items':['fact_validity_history','conversation_date_topic_deletion','PS_authoritative_storage_handoff','cross_day_human_acceptance'],
    'automations_created':False,'source_archive_files':len(manifest),
    'source_archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
(H/'PROGRESS.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
links=[]
for path in (H/'README.md',H/'CONTINUE.md'):
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        if not target.startswith('http') and not (path.parent/target).exists():links.append(target)
assert not links,links
print(json.dumps({'status':progress['status'],'windows_tests':tests,'arm_deferred':True,
    'canonical_source_unchanged':True,'source_files':len(manifest),'archive_sha256':progress['source_archive_sha256']}))
