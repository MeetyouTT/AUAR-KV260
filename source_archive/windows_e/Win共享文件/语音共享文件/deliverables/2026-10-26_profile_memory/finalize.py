"""Allowlisted source/evidence only; never traverse private runtime data."""
import datetime,hashlib,json,sys,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];AURA=ROOT/'aura'
sys.path.insert(0,str(AURA))
from common.voice_service_capabilities import source_fingerprint
runtime=json.loads((HERE/'runtime_verification.json').read_text(encoding='utf-8'))
assert runtime['health_ready'] and runtime['profile_access']['configured']
assert runtime['source_fingerprint']==source_fingerprint(AURA)
board=json.loads((HERE/'board_candidate_verification.json').read_text(encoding='utf-8'))
assert board['status']=='PASS' and board['production_deployed'] is False
xml=ET.parse(HERE/'verifier.xml')
tests=[t for t in xml.iter('testcase') if t.find('skipped') is None]
assert len(tests)==303 and all(t.find('failure') is None and t.find('error') is None for t in tests)
progress={'updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'WINDOWS_BACKEND_LIVE_BOARD_CANDIDATE_VERIFIED',
    'migration':'deferred','windows_profile_control_configured':True,'real_profile_created':False,
    'regression_passed':303,'regression_skipped':2,'additional_subtests_passed':27,
    'new_profile_tests_passed':43,'board_candidate_checks_passed':3,
    'production_board_changed':False,'microphone_used':False,'playback':False,
    'source_fingerprint':runtime['source_fingerprint'],
    'pending':['controlled integration of profile picker into production board UI',
               'human profile selection/listening/interruption/noise acceptance',
               'speaker field calibration and automatic attribution',
               'later summary/expiry/task and backup deletion-watermark operations',
               'remaining motion/vision/full-project work']}
(HERE/'PROGRESS.json').write_text(json.dumps(progress,indent=2),encoding='utf-8')
entries={}
for p in (HERE/'before').rglob('*.py'):
    relative=p.relative_to(HERE/'before').as_posix()
    entries['before/'+relative]=p
    entries['windows/'+relative]=ROOT/relative
for name in ('common/profile_access.py','common/profile_memory.py','common/profile_selection.py',
             'tools/profile_control.py','tools/profile_cli.py','tools/profile_selection_ui.py',
             'tests/framework/test_profile_memory.py','tests/framework/test_profile_frontend.py',
             'config/profile_access.local.json'):
    entries['windows/aura/'+name]=AURA/name
for p in (HERE/'board_candidate').rglob('*.py'):entries['board_candidate/'+p.relative_to(HERE/'board_candidate').as_posix()]=p
names=['README.md','PROGRESS.json','baseline.json','verifier.log','verifier.xml','board_base.json',
       'board_candidate.json','board_candidate_verification.json','runtime_verification.json',
       'public_voice_after_upgrade.json','database_backup.json','validate.py','build_board_candidate.py',
       'verify_board_candidate.py','verify_runtime.py','snapshot_board_sources.py','backup_runtime.py','finalize.py']
for name in names:entries['evidence/'+name]=HERE/name
assert all(p.is_file() and p.stat().st_size<2_000_000 for p in entries.values())
manifest={n:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for n,p in sorted(entries.items())}
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
with zipfile.ZipFile(HERE/'source_and_tests.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name,p in sorted(entries.items()):z.write(p,name)
    z.write(HERE/'SOURCE_MANIFEST.json','SOURCE_MANIFEST.json')
with zipfile.ZipFile(HERE/'source_and_tests.zip') as z:
    assert z.testzip() is None
    for name,meta in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==meta['sha256']
print(json.dumps({'status':'VERIFIED','files':len(manifest),'package_bytes':(HERE/'source_and_tests.zip').stat().st_size,
                  'windows_backend_live':True,'board_candidate_only':True}))
