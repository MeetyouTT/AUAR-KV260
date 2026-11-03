"""Freeze tested r4 and verify current production/board state before Windows update."""
import ast,hashlib,json,shutil,sys,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A));sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from common.voice_service_capabilities import source_fingerprint
from board_ssh import ssh
plan=json.loads((H/'source_plan.json').read_text(encoding='utf-8'));assert plan['status']=='CANDIDATE_IMPLEMENTED'
assert source_fingerprint(A)==plan['production_fingerprint']
assert all(hashlib.sha256((A/n).read_bytes()).hexdigest()==digest for n,digest in plan['source_before'].items())
suites=list(ET.parse(H/'tests.xml').getroot().iter('testsuite'))
assert sum(int(s.get('tests',0)) for s in suites)==267
assert not sum(int(s.get('failures',0))+int(s.get('errors',0)) for s in suites)
before=json.loads((H/'benchmark_before.json').read_text(encoding='utf-8'));assert before['status']=='PASS'
assert len({r['input_sha256'] for r in before['trials']})==1
assert len({r['timing']['llm']['input_sha256'] for r in before['trials']})==1
for name,entry in plan['files'].items():
    path=A/name;assert (hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None)==entry['before']
    path=H/'candidate_source'/name;ast.parse(path.read_text(encoding='utf-8'),feature_version=(3,9));entry['candidate']=hashlib.sha256(path.read_bytes()).hexdigest()
baseline=json.loads((H/'board_baseline.json').read_text(encoding='utf-8'))
tree=ast.parse((H.parent/'2026-10-28_timeline_summaries/capture_board.py').read_text(encoding='utf-8'))
script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
current=json.loads(ssh('python3 -B -',script,timeout=20));assert current['preflight_ready']
for key in ('boot','actual_runtime','actual_config','config_sha256','pins','settings','pan'):assert current[key]==baseline[key],key
namespace={};exec((H/'candidate_source/common/voice_service_capabilities.py').read_text(encoding='utf-8'),namespace)
digest=hashlib.sha256()
for name in namespace['SOURCE_FILES']:
    path=H/'candidate_source'/name
    if not path.exists():path=A/name
    digest.update(name.encode()+b'\0');digest.update(hashlib.sha256(path.read_bytes()).digest())
plan.update(status='READY_WINDOWS_ONLY',tests_passed=267,candidate_revision=namespace['SERVICE_REVISION'],candidate_fingerprint=digest.hexdigest())
(H/'source_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ('deploy_windows.py','live_controls_acceptance.py','cleanup_public_probe.py','live_voice_acceptance.py'):
    shutil.copy2(H.parent/'2026-10-29_memory_controls'/name,H/name)
p=H/'deploy_windows.py';t=p.read_text(encoding='utf-8').replace("plan['tests_passed']==210","plan['tests_passed']==267")
t=t.replace("    assert voice['latency_options']==first['latency_options']","    assert voice['latency_options']==first['latency_options']\n    assert voice['capabilities']['natural_fact_answers']==1 and voice['capabilities']['memory_source_coverage']==1")
p.write_text(t,encoding='utf-8')
print(json.dumps({'status':plan['status'],'tests':267,'revision':plan['candidate_revision'],'fingerprint':plan['candidate_fingerprint'],'board_migration':False}))

