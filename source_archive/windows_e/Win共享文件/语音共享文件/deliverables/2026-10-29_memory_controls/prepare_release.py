"""Read-only fresh baseline, frozen source hashes and regression gate."""
import ast,datetime,hashlib,json,shutil,sys,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(A));sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from common.voice_service_capabilities import source_fingerprint,SOURCE_FILES
from board_ssh import ssh
assert not (H/'deployment.json').exists(),'Inspect existing deployment receipt'
plan=json.loads((H/'source_plan.json').read_text(encoding='utf-8'))
suites=list(ET.parse(H/'tests.xml').getroot().iter('testsuite'))
assert sum(int(s.get('tests',0)) for s in suites)==210
assert not sum(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites)
current=source_fingerprint(A)
if current!=plan['production_fingerprint']:
    task=A.parents[1]/'协作任务/2026-10-29_语音延迟修复'
    evidence=json.loads((task/'fingerprint_verification.json').read_text(encoding='utf-8-sig'))
    assert evidence['all_source_changes_explained_by_config']
    old=(task/'voice_latency.before.json').read_bytes();reconstructed=hashlib.sha256()
    for name in SOURCE_FILES:
        data=old if name=='config/voice_latency.json' else (A/name).read_bytes()
        reconstructed.update(name.encode()+b'\0');reconstructed.update(hashlib.sha256(data).digest())
    assert reconstructed.hexdigest()==plan['production_fingerprint'],'Unexplained concurrent source change'
    assert hashlib.sha256((A/'config/voice_latency.json').read_bytes()).hexdigest()==evidence['sha_after']
    plan['rebased_from']=plan['production_fingerprint'];plan['production_fingerprint']=current
    plan['preserved_parallel_change']='compact_grammar=false, completed AURA latency fix; all other source changes excluded by reconstruction'
plan['preserved_latency_sha256']=hashlib.sha256((A/'config/voice_latency.json').read_bytes()).hexdigest()
for name,entry in plan['files'].items():
    target=A/name
    assert (hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None)==entry['before']
    source=H/'candidate_source'/name;ast.parse(source.read_text(encoding='utf-8'),feature_version=(3,9))
    entry['candidate']=hashlib.sha256(source.read_bytes()).hexdigest()
tree=ast.parse((H.parent/'2026-10-28_timeline_summaries/capture_board.py').read_text(encoding='utf-8'))
script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
board=json.loads(ssh('python3 -B -',script,timeout=20))
assert board['preflight_ready'],'Board busy or unavailable; preserve current runtime'
board['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(H/'board_baseline.json').write_text(json.dumps(board,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ('manage_owned.ps1','db_checkpoint.py','start_checkpoint.ps1','synthesize_question.ps1','live_voice_acceptance.py'):
    shutil.copy2(H.parent/'2026-10-28_timeline_summaries'/name,H/name)
p=H/'db_checkpoint.py';p.write_text(p.read_text(encoding='utf-8').replace('summaries-20261028-','controls-20261029-'),encoding='utf-8')
namespace={};exec((H/'candidate_source/common/voice_service_capabilities.py').read_text(encoding='utf-8'),namespace)
digest=hashlib.sha256()
for name in namespace['SOURCE_FILES']:
    path=H/'candidate_source'/name
    if not path.exists():path=A/name
    digest.update(name.encode()+b'\0');digest.update(hashlib.sha256(path.read_bytes()).digest())
plan.update(status='READY_WINDOWS_ONLY',tests_passed=210,candidate_revision=namespace['SERVICE_REVISION'],candidate_fingerprint=digest.hexdigest())
(H/'source_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':plan['status'],'tests':210,'fingerprint':plan['candidate_fingerprint'],'board_runtime':board['actual_runtime'],'pan_preserved':board['pan'],'board_migration':False}))

