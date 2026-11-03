"""Validate the measured r6 baseline and tested five-file Windows candidate."""
import ast,hashlib,json,shutil,sys,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(A));sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from common.voice_service_capabilities import source_fingerprint
from board_ssh import ssh
plan=json.loads((H/'source_plan.json').read_text(encoding='utf-8'))
assert plan['status']=='CANDIDATE' and source_fingerprint(A)==plan['production_fingerprint']
assert all(hashlib.sha256((A/n).read_bytes()).hexdigest()==v for n,v in plan['source_before'].items())
suites=list(ET.parse(H/'tests.xml').getroot().iter('testsuite'))
assert sum(int(s.get('tests',0)) for s in suites)==346
assert not sum(int(s.get('errors',0))+int(s.get('failures',0))+int(s.get('skipped',0)) for s in suites)
measurement=json.loads((H/'voice_before.json').read_text(encoding='utf-8'));assert measurement['status']=='PASS' and len(measurement['trials'])==8
baseline=json.loads((H/'board_baseline.json').read_text(encoding='utf-8'))
tree=ast.parse((H.parent/'2026-10-28_timeline_summaries/capture_board.py').read_text(encoding='utf-8'))
script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
current=json.loads(ssh('python3 -B -',script,timeout=20));assert current['preflight_ready']
for key in ('boot','actual_runtime','actual_config','config_sha256','pins','pan','settings'):assert current[key]==baseline[key],key
for name,row in plan['files'].items():
 assert hashlib.sha256((H/'candidate_source'/name).read_bytes()).hexdigest()==row['candidate']
 ast.parse((H/'candidate_source'/name).read_text(encoding='utf-8'))
for name in ('manage_owned.ps1','db_checkpoint.py','start_checkpoint.ps1','deploy_windows.py','verify_private.py','live_handoff.py'):
 shutil.copy2(H.parent/'2026-10-29_listening_bounce'/name,H/name)
for name in ('live_controls_acceptance.py','cleanup_public_probe.py'):
 shutil.copy2(H.parent/'2026-10-29_dialogue_memory_polish'/name,H/name)
p=H/'db_checkpoint.py';s=p.read_text(encoding='utf-8').replace('handoff-20261029-','chatlatency-20261029-');p.write_text(s,encoding='utf-8')
p=H/'deploy_windows.py';s=p.read_text(encoding='utf-8').replace("plan['tests_passed']==284","plan['tests_passed']==346")
needle="    assert voice['capabilities']['queued_voice_admission']==1 and voice['capabilities']['bounded_voice_request_diagnostics']==1"
assert needle in s
s=s.replace(needle,needle+"\n    for key in ('compact_chat_serialization_hint','request_input_fingerprint','precise_timeline_voice_intent'):assert voice['capabilities'][key]==1")
needle="        owners(True)\n        for name in receipt['applied']:"
assert needle in s
s=s.replace(needle,"        ps(['-File',str(H/'manage_owned.ps1'),'-Group','voice','-Stop','-AllowAbsent'])\n        for name in receipt['applied']:")
p.write_text(s,encoding='utf-8')
p=H/'verify_private.py';s=p.read_text(encoding='utf-8').replace("H/'deployment_recovery.json'","H/'deployment.json'");p.write_text(s,encoding='utf-8')
p=H/'live_handoff.py';s=p.read_text(encoding='utf-8').replace("H/'deployment_recovery.json'","H/'deployment.json'");p.write_text(s,encoding='utf-8')
plan.update(status='READY_WINDOWS_ONLY',tests_passed=346)
(H/'source_plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
(H/'PROGRESS.json').write_text(json.dumps({'status':'READY_WINDOWS_CANDIDATE','complete':False,'tests_passed':346,
 'board_migration':False,'production_revision':'voice-turn-handoff-20261029-r6','candidate_revision':plan['candidate_revision'],
 'listening_remains_off':True},indent=2),encoding='utf-8')
print(json.dumps({'status':plan['status'],'tests':346,'baseline_pcm_median_ms':measurement['median_first_pcm_ms'],
 'revision':plan['candidate_revision'],'fingerprint':plan['candidate_fingerprint']}))
