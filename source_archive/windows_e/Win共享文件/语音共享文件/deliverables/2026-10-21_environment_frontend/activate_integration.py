"""Guarded UI-only activation; original PC model services remain running."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'integration_candidate.json').read_text())
b=json.loads((HERE/'integration_board_baseline.json').read_text())
assert c['tests_passed'] and c['preflight_passed']
assert json.loads((HERE/'integration_smoke.json').read_text())['passed']
assert all(r['over_20ms']==0 for r in json.loads((HERE/'integration_lan_validation.json').read_text())['rows'])
for n,sha in c['files'].items():
 assert hashlib.sha256((HERE/'integration_sources'/n).read_bytes()).hexdigest()==sha,n
remote=r'''
import glob,hashlib,json,os,re,subprocess,time,urllib.request,uuid
from pathlib import Path
c=CANDIDATE;b=BASE;root=Path(c['runtime']);stage=Path(c['stage'])
unit=lambda n:subprocess.check_output(['systemctl','cat',n],text=True)
assert unit('aura-avatar-ui.service')==b['ui_unit'],'Actual UI changed; rebuild required'
for n,sha in dict(c['files'],**c['preserved']).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==sha,n
get=lambda port,path,host='127.0.0.1':json.load(urllib.request.urlopen('http://%s:%s%s'%(host,port,path),timeout=4))
sys=__import__('sys');sys.path.insert(0,str(root/'aura'))
from board.runtime.audio.remote_frontend import health
cfg=json.loads((root/'aura/config/board_avatar_gtk.json').read_text())['audio_frontend']
previous_frontend=bool(json.loads((Path(c['source_runtime'])/'aura/config/board_avatar_gtk.json').read_text()).get('audio_frontend',{}).get('enabled'))
assert health(cfg)['ready']
def quiet():
 u=get(8783,'/api/state');tx=u['local_transcription'];svc=tx['service'];hf=u['handsfree_dialogue']
 ack=svc.get('last_playback_ack') or {}
 assert (u['phase']=='IDLE' and not u['playing'] and not svc['pending']
  and not (hf['microphone_open'] and u['automatic_conversation']['speech_active'])
  and not hf.get('listening_timing',{}).get('holding_utterance')
  and not u.get('voice_barge_in',{}).get('next_utterance_pending')
  and not (tx['state']=='ANSWERED' and (ack.get('request_id')!=tx['request_id'] or not ack.get('committed')))
  and tx['state'] not in ('GENERATING','PLAYING','TRANSCRIBING')
  and u.get('manual_pan',{}).get('state') not in ('MOVING','STOPPING')),'Conversation or motion is active'
 return u
deadline=time.monotonic()+90
while True:
 try:
  u=quiet();pc=get(8792,'/health','192.168.50.1');assert pc['ready'] and not pc['busy'];break
 except (AssertionError,OSError):
  if time.monotonic()>=deadline:raise
  time.sleep(.2)
cam=get(8790,'/health');assert cam['identity']['ready']
camera_unit=unit('aura-camera-ui.service')
camera_cfg=Path(re.findall(r'--config (\S+)',camera_unit)[-1]);camera_raw=camera_cfg.read_bytes()
identity_cfg=Path(json.loads(camera_raw)['identity']['config']);identity_raw=identity_cfg.read_bytes()
db=Path(json.loads(identity_raw)['database']).expanduser();db_sha=hashlib.sha256(db.read_bytes()).hexdigest()
pid=int(subprocess.check_output(['systemctl','show','-p','MainPID','--value','aura-avatar-ui.service'],text=True))
environ=dict(v.split('=',1) for v in Path('/proc/%d/environ'%pid).read_bytes().decode().split('\0') if '=' in v)
pref=Path(environ['HOME'])/'.local/share/aura/handsfree_dialogue.json';chosen=u['handsfree_dialogue']['enabled']
backup=stage/('deployment-'+uuid.uuid4().hex[:8]);backup.mkdir()
override=Path('/etc/systemd/system/aura-avatar-ui.service.d/zzzzzzzzz-aura-audio-frontend-budget-20261021.conf')
assert not override.exists(),'Existing frontend override must be reviewed'
text='[Unit]\nRequiresMountsFor='+str(root)+'\n[Service]\nWorkingDirectory='+str(root/'aura')+'\nExecStart=\nExecStart=/usr/bin/python3 -B '+c['startup']+'/launcher.py --config '+c['startup']+'/config.json\n'
(backup/'before.json').write_text(json.dumps({'ui_unit':b['ui_unit'],'enabled':chosen,'preference_path':str(pref)}))
if pref.exists():(backup/'preference_before.json').write_bytes(pref.read_bytes())
def restore_preference():
 pref.parent.mkdir(parents=True,exist_ok=True);tmp=pref.with_name(pref.name+'.frontend-'+uuid.uuid4().hex[:8])
 tmp.write_text(json.dumps({'version':1,'enabled':chosen}));tmp.chmod(0o600);os.replace(tmp,pref)
def rollback():
 if override.exists():
  assert override.read_text()==text,'Foreign override changed; refuse removal'
  subprocess.run(['systemctl','stop','aura-avatar-ui.service'],check=True,timeout=40);override.unlink()
 restore_preference();subprocess.run(['systemctl','daemon-reload'],check=True)
 subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True)
def wait_ready(frontend,limit=185):
 deadline=time.monotonic()+limit
 while time.monotonic()<deadline:
  try:
   u=get(8783,'/api/state')
   if (u.get('audio_output_state')=='IDLE_READY' and u.get('handsfree_dialogue',{}).get('enabled')==chosen
       and u.get('audio_frontend',{}).get('enabled',False)==frontend):return u
  except (OSError,ValueError):pass
  time.sleep(.5)
 raise RuntimeError('UI readiness deadline')
# Independent detached guard restores the previous entry even if SSH dies.
watch=r"""
import json,os,subprocess,time
from pathlib import Path
backup=Path(BACKUP);override=Path(OVERRIDE);pref=Path(PREF);expected=TEXT;chosen=CHOSEN
deadline=time.monotonic()+300
while time.monotonic()<deadline:
 if (backup/'committed').exists():raise SystemExit(0)
 time.sleep(.5)
if override.exists() and override.read_text()!=expected:raise RuntimeError('Foreign override; refuse rollback')
subprocess.run(['systemctl','stop','aura-avatar-ui.service'],timeout=40)
if override.exists():override.unlink()
tmp=pref.with_name(pref.name+'.frontend-watchdog');tmp.write_text(json.dumps({'version':1,'enabled':chosen}));tmp.chmod(0o600);os.replace(tmp,pref)
subprocess.run(['systemctl','daemon-reload']);subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'])
(backup/'watchdog_rollback.json').write_text(json.dumps({'status':'DEADLINE_ROLLBACK'}))
"""
watch='BACKUP='+repr(str(backup))+'\nOVERRIDE='+repr(str(override))+'\nPREF='+repr(str(pref))+'\nTEXT='+repr(text)+'\nCHOSEN='+repr(chosen)+'\n'+watch
(backup/'watchdog.py').write_text(watch)
log=(backup/'watchdog.log').open('w')
guard=subprocess.Popen(['python3','-B',str(backup/'watchdog.py')],start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=log);log.close()
report={'runtime':str(root),'previous_runtime':c['source_runtime'],'override':str(override),'backup':str(backup),
 'watchdog_pid':guard.pid,'monitor_enabled':chosen,'pc_model_services_restarted':False,'human_acceptance':False}
try:
 assert quiet()['handsfree_dialogue']['enabled']==chosen
 if chosen:
  req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps({'type':'event','event':'cancel'}).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
  json.load(urllib.request.urlopen(req,timeout=4))
 for _ in range(70):
  u=get(8783,'/api/state')
  if not u['handsfree_dialogue']['microphone_open'] and not u['local_transcription']['service']['pending']:break
  time.sleep(.1)
 else:raise RuntimeError('Listener did not release')
 assert not subprocess.run(['fuser',*glob.glob('/dev/snd/pcm*c')],capture_output=True,text=True).stdout.strip(),'Other microphone owner'
 subprocess.run(['systemctl','stop','aura-avatar-ui.service'],check=True,timeout=40)
 for src in Path(c['source_runtime']).glob('*_settings.json'):
  target=root/src.name;assert not target.is_symlink();target.write_bytes(src.read_bytes())
 restore_preference();override.write_text(text);override.chmod(0o644)
 subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True)
 u=wait_ready(True);observed=[]
 for _ in range(12):
  u=get(8783,'/api/state');h=health(cfg)
  assert h['ready'] and u['audio_frontend']['enabled'] and u['handsfree_dialogue']['enabled']==chosen
  assert not u.get('error') and not u['local_recording'].get('error') and not u['voice_barge_in'].get('error')
  observed.append({'phase':u['phase'],'audio_output_state':u['audio_output_state'],'frontend':u['audio_frontend'],
   'microphone_open':u['handsfree_dialogue']['microphone_open'],'renderer':u.get('avatar_renderer',{})});time.sleep(1)
 after=get(8790,'/health')
 assert after['pid']==cam['pid'] and after['service_epoch']==cam['service_epoch']
 assert unit('aura-camera-ui.service')==camera_unit and camera_cfg.read_bytes()==camera_raw and identity_cfg.read_bytes()==identity_raw
 assert hashlib.sha256(db.read_bytes()).hexdigest()==db_sha
 assert str(Path(c['startup'])/'config.json') in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
 assert u['voice_barge_in']['enabled'] and 'manual_pan' in u
 assert (root/'aura/board/runtime/rendering/render_performance.py').exists() or 'render_performance' in str(c['preserved'])
 report.update(status='LOCAL_FRONTEND_DEPLOYED',observed=observed,camera_unchanged=True,camera_pid=cam['pid'],
  camera_epoch=cam['service_epoch'],identity_database_unchanged=True,final_frontend=u['audio_frontend'],
  phase=u['phase'],audio_output_state=u['audio_output_state'],frontend_health=health(cfg))
 (backup/'committed').write_text('COMMITTED\n')
except Exception as exc:
 report.update(status='ROLLED_BACK',error=type(exc).__name__+': '+str(exc))
 try:rollback();wait_ready(previous_frontend);report['rollback_ready']=True;(backup/'committed').write_text('ROLLED_BACK\n')
 except Exception as recovery:report['rollback_error']=str(recovery)
(stage/'integration_deployment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''
remote=remote.replace('c=CANDIDATE;b=BASE;', 'c='+repr(c)+';b='+repr(b)+';',1)
r=json.loads(ssh('python3 -B -',remote,timeout=440))
(HERE/'integration_deployment.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k!='observed'}));assert r['status']=='LOCAL_FRONTEND_DEPLOYED'
