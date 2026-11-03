"""Recover only this owned Windows service from the precisely observed TTS failure."""
import ast,datetime,hashlib,json,shutil,subprocess,sys,time,urllib.request,urllib.error,uuid,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'));from board_ssh import ssh
plan=json.loads((H/'source_plan.json').read_text());baseline=json.loads((H/'board_baseline.json').read_text(encoding='utf-8'))
original=json.loads((H/'attempt1/source_plan.json').read_text())
assert plan['status']=='CANDIDATE_RECOVERY'
suites=list(ET.parse(H/'tests.xml').getroot().iter('testsuite'))
assert sum(int(s.get('tests',0)) for s in suites)==285
assert not sum(int(s.get('errors',0))+int(s.get('failures',0))+int(s.get('skipped',0)) for s in suites)
resume=sys.argv[1:]==['--resume-owned-stop']
assert sys.argv[1:] in ([],['--resume-owned-stop'])
previous=None
if resume:
 previous=json.loads((H/'deployment_recovery.json').read_text(encoding='utf-8'))
 assert previous['status']=='ROLLING_BACK' and previous['error']=="NameError: name 'uuid' is not defined"
 assert previous['applied']==[] and previous['stop_voice']['stopped'] and 'checkpoint_before' not in previous
 assert not (H/'deployment_recovery_launcher_failure.json').exists()
 shutil.copy2(H/'deployment_recovery.json',H/'deployment_recovery_launcher_failure.json')
else:assert not (H/'deployment_recovery.json').exists()
receipt={'status':'PREPARING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'authority':'Windows','board_migration':False,'board_ui_restarted':False,'camera_restarted':False,
 'other_models_stopped':False,'hub_restarted':False,'files':plan['files'],'applied':[]}
def save():(H/'deployment_recovery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def health(allow_failure=False):
 try:
  with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=5) as r:return json.load(r)
 except urllib.error.HTTPError as exc:
  if not allow_failure or exc.code!=503:raise
  return json.loads(exc.read())
tree=ast.parse((H/'deploy_windows.py').read_text(encoding='utf-8'))
names=('ps','gate','models','listeners','owners','checkpoint','start')
defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
exec(compile(ast.Module(body=defs,type_ignores=[]),'recovery_operations','exec'),globals())
try:
 if resume:
  absent=json.loads(ps(['-File',str(H/'manage_owned.ps1'),'-Group','voice','-AllowAbsent']))
  assert absent['owned_python_ids']==[]
  first={'busy':False,'ready':False,'source_fingerprint':plan['production_fingerprint'],
    'dependencies':{'tts':previous['known_initial_failure']},
    'latency_options':json.loads((H/'deployment.json').read_text(encoding='utf-8'))['latency_options']}
  receipt['resumed_from_owned_stopped_service']=True
 else:first=health(True)
 assert not first['busy'] and first['source_fingerprint']==plan['production_fingerprint']
 if not first['ready']:
  tts=first['dependencies']['tts']
  assert tts['quarantined'] and not tts['alive'] and tts['error']=='TimeoutError: Speech worker deadline expired'
 receipt['known_initial_failure']=first['dependencies']['tts'];receipt['guard']=gate();time.sleep(.25);gate()
 assert hashlib.sha256((A/'config/voice_latency.json').read_bytes()).hexdigest()==plan['preserved_latency_sha256']
 for name,entry in plan['files'].items():
  assert hashlib.sha256((A/name).read_bytes()).hexdigest()==entry['before'],name
  assert hashlib.sha256((H/'candidate_source'/name).read_bytes()).hexdigest()==entry['candidate'],name
 receipt['models_before']=models();receipt['other_listeners']=listeners()
 if resume:
  assert all(r in receipt['models_before'] for r in previous['models_before'])
  assert receipt['other_listeners']==previous['other_listeners']
  receipt['owner_before']=absent;receipt['stop_voice']=previous['stop_voice']
 else:receipt['owner_before']=owners();receipt['stop_voice']=owners(True)
 save();receipt['checkpoint_before']=checkpoint('before');save()
 for name,entry in plan['files'].items():
  assert hashlib.sha256((A/name).read_bytes()).hexdigest()==entry['before'],name
  shutil.copy2(H/'candidate_source'/name,A/name);receipt['applied'].append(name);save()
 receipt['status']='STARTING';save();voice=start()
 assert voice['ready'] and not voice['busy'] and voice['service_revision']==plan['candidate_revision']
 assert voice['source_fingerprint']==plan['candidate_fingerprint'] and voice['latency_options']==first['latency_options']
 assert voice['voice_request_diagnostics']['admission_wait_max_ms']==5000 and voice['dependencies']['tts']['alive']
 receipt['after_guard']=gate();assert listeners()==receipt['other_listeners']
 assert all(r in models() for r in receipt['models_before'])
 receipt['checkpoint_after']=checkpoint('after')
 for kind,old in receipt['checkpoint_before']['databases'].items():
  if old['exists']:
   new=receipt['checkpoint_after']['databases'][kind]['counts']
   assert all(old['counts'][t]==new[t] for t in old['counts']),kind
 receipt.update(status='COMMITTED',revision=voice['service_revision'],fingerprint=voice['source_fingerprint'],
   latency_options=voice['latency_options'],finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
except Exception as exc:
 receipt.update(status='ABORTED_BEFORE_CHANGES' if not receipt.get('stop_voice') else 'ROLLING_BACK',error=type(exc).__name__+': '+str(exc));save()
 if receipt.get('stop_voice'):
  ps(['-File',str(H/'manage_owned.ps1'),'-Group','voice','-Stop','-AllowAbsent'])
  for name,entry in original['files'].items():
   path=A/name
   current=hashlib.sha256(path.read_bytes()).hexdigest()
   assert current in (plan['files'][name]['before'],plan['files'][name]['candidate']),name
   if entry['before'] is None:path.unlink()
   else:shutil.copy2(H/'before'/name,path)
  receipt['rollback_revision']=start()['service_revision']
  receipt['status']='ROLLED_BACK_R4_CODE_LATEST_DATABASE_RETAINED';save()
 raise
save();print(json.dumps({'status':receipt['status'],'revision':receipt['revision'],'fingerprint':receipt['fingerprint'],'board_restarted':False}))
