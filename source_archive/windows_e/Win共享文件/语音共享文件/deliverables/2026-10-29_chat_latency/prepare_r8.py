"""Reject the slower formatting experiment; preserve precise recall routing."""
import datetime,hashlib,json,shutil,sys,types
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
old=json.loads((H/'source_plan.json').read_text(encoding='utf-8'))
assert json.loads((H/'deployment.json').read_text(encoding='utf-8'))['status']=='COMMITTED'
assert not (H/'source_plan_r8.json').exists()
names=list(old['files'])
for name in names:
 assert hashlib.sha256((A/name).read_bytes()).hexdigest()==old['files'][name]['candidate'],name
 for directory in ('before_r8','candidate_r8_source'):
  dest=H/directory/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(A/name,dest)
path=H/'candidate_r8_source/tools/dialogue_stream.py'
source=path.read_text(encoding='utf-8')
begin=source.index("COMPACT_CHAT_HINT=");end=source.index('def stream_body(',begin)
source=source[:begin]+source[end:]
begin=source.index('    if reply_first and not think:\n');end=source.index('    return body',begin)
source=source[:begin]+source[end:]
source=source.replace("request_sha256=hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest(),\n            compact_chat_hint=COMPACT_CHAT_HINT in body['messages'][0]['content'])",
 "request_sha256=hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest())")
assert 'COMPACT_CHAT_HINT' not in source and 'compact_chat_hint' not in source
path.write_text(source,encoding='utf-8')
path=H/'candidate_r8_source/common/voice_service_capabilities.py'
source=path.read_text(encoding='utf-8').replace('voice-chat-context-20261029-r7','voice-chat-context-20261029-r8')
source=source.replace("'compact_chat_serialization_hint':1,",'')
path.write_text(source,encoding='utf-8')
module=types.ModuleType('candidate_capabilities');exec(compile(source,str(path),'exec'),module.__dict__)
digest=hashlib.sha256()
for name in module.SOURCE_FILES:
 path=H/'candidate_r8_source'/name
 if not path.exists():path=A/name
 digest.update(name.encode()+b'\0');digest.update(hashlib.sha256(path.read_bytes()).digest())
plan={'status':'TESTING','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'production_revision':old['candidate_revision'],'production_fingerprint':old['candidate_fingerprint'],
 'candidate_revision':module.SERVICE_REVISION,'candidate_fingerprint':digest.hexdigest(),
 'preserved_latency_sha256':old['preserved_latency_sha256'],'tests_passed':None,
 'files':{name:{'before':hashlib.sha256((A/name).read_bytes()).hexdigest(),
               'candidate':hashlib.sha256((H/'candidate_r8_source'/name).read_bytes()).hexdigest()} for name in names},
 'decision':'Reject compact prompt: uncached first PCM median worsened 4052.11 to 4352.65 ms; retain precise timeline intent and privacy-safe request diagnostics.',
 'board_migration':False,'listening_remains_off':True}
(H/'source_plan_r8.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
for source_name,target_name,replacements in [
 ('bootstrap.py','bootstrap_r8.py', [('candidate_source','candidate_r8_source')]),
 ('run_tests.py','run_tests_r8.py',[('import bootstrap','import bootstrap_r8 as bootstrap'),('tests.xml','tests_r8.xml')]),
 ('deploy_windows.py','deploy_windows_r8.py',[('source_plan.json','source_plan_r8.json'),('==346','==347'),('deployment.json','deployment_r8.json'),('candidate_source','candidate_r8_source'),("H/'before'","H/'before_r8'"),("'compact_chat_serialization_hint',",'')]),
 ('benchmark_voice.py','benchmark_voice_r8.py',[("choices=['before','after']","choices=['refined']"),("source_plan.json","source_plan_r8.json"),("'production_fingerprint' if args.phase=='before' else 'candidate_fingerprint'","'candidate_fingerprint'"),("if args.phase=='after':","if args.phase=='refined':")]),
 ('live_handoff.py','live_handoff_r8.py',[('deployment.json','deployment_r8.json'),('source_plan.json','source_plan_r8.json'),('live_handoff_final','live_handoff_r8_final')]),
 ('live_controls_acceptance.py','live_controls_acceptance_r8.py',[('deployment.json','deployment_r8.json')]),
 ('verify_private.py','verify_private_r8.py',[('deployment.json','deployment_r8.json')])]:
 source=(H/source_name).read_text(encoding='utf-8')
 for left,right in replacements:source=source.replace(left,right)
 compile(source,str(H/target_name),'exec');(H/target_name).write_text(source,encoding='utf-8')
shutil.copy2(H/'test_serialization.py',H/'test_serialization_r7_archived.py')
path=H/'test_serialization.py';source=path.read_text(encoding='utf-8')
source=source.replace('Memory selection and wire semantics stay intact with an optional formatting hint.','Reject the formatting hint without changing memory selection or model requests.')
source=source.replace('[(True,True),(True,False),(False,False)]','[(True,True),(True,False),(False,False),(False,True)]')
source=source.replace("assert stream.metrics['compact_chat_hint'] is True","assert 'compact_chat_hint' not in stream.metrics")
path.write_text(source,encoding='utf-8')
(H/'PROGRESS.json').write_text(json.dumps({'status':'R7_PERFORMANCE_REJECTED_R8_TESTING','complete':False,
 'production_revision':old['candidate_revision'],'candidate_revision':module.SERVICE_REVISION,
 'original_median_first_pcm_ms':4052.11,'r7_median_first_pcm_ms':4352.65,
 'board_migration':False,'listening_remains_off':True},indent=2),encoding='utf-8')
print(json.dumps({'status':'CANDIDATE_READY_FOR_TEST','revision':module.SERVICE_REVISION,'fingerprint':plan['candidate_fingerprint']}))
