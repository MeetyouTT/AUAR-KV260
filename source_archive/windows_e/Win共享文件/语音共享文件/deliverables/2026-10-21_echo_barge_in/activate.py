"""UI-only timing update, preserve all existing overrides, rollback this one."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text());b=json.loads((HERE/'board_baseline.json').read_text())
assert c['tests_passed'] and c['preflight_passed'] and json.loads((HERE/'smoke.json').read_text())['passed']
for n,sha in c['files'].items():
 p=HERE/'merged_sources'/n
 if not p.exists():p=ROOT/n
 assert hashlib.sha256(p.read_bytes()).hexdigest()==sha,n
remote=r'''
import glob,hashlib,json,os,re,subprocess,time,urllib.request,uuid
from pathlib import Path
c=CANDIDATE;b=BASE;root=Path(c['runtime']);stage=Path(c['stage'])
unit=lambda n:subprocess.check_output(['systemctl','cat',n],text=True)
assert unit('aura-avatar-ui.service')==b['ui_unit'],'UI changed; rebuild from actual base'
for n,sha in dict(c['files'],**c['preserved']).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==sha,n
get=lambda port,path,host='127.0.0.1':json.load(urllib.request.urlopen('http://%s:%s%s'%(host,port,path),timeout=4))
def quiet():
 u=get(8783,'/api/state');tx=u['local_transcription'];svc=tx['service'];hf=u['handsfree_dialogue']
 active=hf['microphone_open'] and u['automatic_conversation']['speech_active']
 held=hf.get('listening_timing',{}).get('holding_utterance') or u.get('voice_barge_in',{}).get('next_utterance_pending')
 ack=svc.get('last_playback_ack') or {}
 ack_pending=tx['state']=='ANSWERED' and (ack.get('request_id')!=tx['request_id'] or not ack.get('committed'))
 assert (u['phase']=='IDLE' and not u['playing'] and not svc['pending'] and not active and not held and not ack_pending
  and tx['state'] not in ('GENERATING','PLAYING','TRANSCRIBING')
  and u.get('manual_pan',{}).get('state') not in ('MOVING','STOPPING')),'Current conversation/motion is not idle'
 return u
deadline=time.monotonic()+120
while True:
 try:
  u=quiet();pc=get(8792,'/health','192.168.50.1');assert pc['ready'] and not pc['busy'];break
 except (AssertionError,OSError):
  if time.monotonic()>=deadline:raise
  time.sleep(.2)
cam=get(8790,'/health');assert cam['identity']['ready']
camera_unit=unit('aura-camera-ui.service');camera_cfg=Path(re.findall(r'--config (\S+)',camera_unit)[-1])
camera_raw=camera_cfg.read_bytes();identity_cfg=Path(json.loads(camera_raw)['identity']['config']);identity_raw=identity_cfg.read_bytes()
db=Path(json.loads(identity_raw)['database']).expanduser();db_sha=hashlib.sha256(db.read_bytes()).hexdigest()
pid=int(subprocess.check_output(['systemctl','show','-p','MainPID','--value','aura-avatar-ui.service'],text=True))
environ=dict(v.split('=',1) for v in Path('/proc/%d/environ'%pid).read_bytes().decode().split('\0') if '=' in v)
pref=Path(environ['HOME'])/'.local/share/aura/handsfree_dialogue.json';pref_before=pref.read_bytes() if pref.exists() else None
chosen=u['handsfree_dialogue']['enabled']
override=Path('/etc/systemd/system/aura-avatar-ui.service.d/zzzz-aura-echo-verify-20261021.conf')
assert not override.exists(),'Retain existing override and rebuild explicitly'
backup=stage/('ui-backup-'+uuid.uuid4().hex[:8]);backup.mkdir()
(backup/'before.json').write_text(json.dumps({'ui_unit':b['ui_unit'],'enabled':chosen,'preference_path':str(pref)},indent=2))
if pref_before is not None:(backup/'handsfree-preference.json').write_bytes(pref_before)
def command(value):
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(value).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 return json.load(urllib.request.urlopen(req,timeout=4))
def restore_preference():
 pref.parent.mkdir(parents=True,exist_ok=True)
 tmp=pref.with_name(pref.name+'.timing-'+uuid.uuid4().hex[:8])
 tmp.write_text(json.dumps({'version':1,'enabled':chosen}));tmp.chmod(0o600);os.replace(tmp,pref)
def wait_ready(expected_timing):
 deadline=time.monotonic()+185
 while time.monotonic()<deadline:
  try:
   u=get(8783,'/api/state');hf=u.get('handsfree_dialogue',{})
   if (hf.get('enabled')==chosen and u.get('audio_output_state')=='IDLE_READY'
     and bool(hf.get('listening_timing',{}).get('enabled'))==expected_timing):return u
  except (OSError,ValueError):pass
  time.sleep(.5)
 raise RuntimeError('UI did not become ready')
report={'runtime':str(root),'previous_runtime':c['source_runtime'],'monitor_enabled':chosen,'preference_path':str(pref),
 'backup':str(backup),'override':str(override),'pc_restarted':False,'camera_modified':False,'human_echo_verified':False}
assert quiet()['handsfree_dialogue']['enabled']==chosen,'User monitor choice changed; no UI mutation'
try:
 if chosen:command({'type':'event','event':'cancel'})
 for _ in range(70):
  u=get(8783,'/api/state')
  if not u['handsfree_dialogue']['microphone_open'] and not u['local_transcription']['service']['pending']:break
  time.sleep(.1)
 else:raise RuntimeError('Listener did not release')
 assert not subprocess.run(['fuser',*glob.glob('/dev/snd/pcm*c')],capture_output=True,text=True).stdout.strip(),'Other capture owner present'
 subprocess.run(['systemctl','stop','aura-avatar-ui.service'],check=True,timeout=40)
 probe_run=subprocess.run(['python3','-B',str(stage/'verified_acoustic_probe.py'),str(root),str(stage/'probe_clip.json')],capture_output=True,text=True,timeout=35)
 (stage/'verified_acoustic_probe.log').write_text(probe_run.stdout+probe_run.stderr)
 probe_rows=[json.loads(line[len('VERIFIED_PROBE '):]) for line in probe_run.stdout.splitlines() if line.startswith('VERIFIED_PROBE ')]
 report['acoustic_probe']=probe_rows[-1] if probe_rows else {'passed':False,'error':probe_run.stderr[-1500:]}
 assert probe_run.returncode==0 and report['acoustic_probe']['passed'],'Self-playback gate failed; restore previous UI'
 for src in Path(c['source_runtime']).glob('*_settings.json'):
  target=root/src.name;assert not target.is_symlink();target.write_bytes(src.read_bytes())
 restore_preference()
 text='[Unit]\nRequiresMountsFor='+str(root)+'\n[Service]\nWorkingDirectory='+str(root/'aura')+'\nExecStart=\nExecStart=/usr/bin/python3 -B '+c['startup']+'/launcher.py --config '+c['startup']+'/config.json\n'
 override.write_text(text);override.chmod(0o644)
 subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True)
 u=wait_ready(True);cam_after=get(8790,'/health')
 assert cam_after['pid']==cam['pid'] and cam_after['service_epoch']==cam['service_epoch']
 assert unit('aura-camera-ui.service')==camera_unit and camera_cfg.read_bytes()==camera_raw and identity_cfg.read_bytes()==identity_raw
 assert hashlib.sha256(db.read_bytes()).hexdigest()==db_sha
 assert 'manual_pan' in u and u['voice_barge_in']['enabled']
 effective=unit('aura-avatar-ui.service');assert b['ui_unit'].strip() in effective
 report.update(status='UI_ECHO_VERIFY_DEPLOYED',ui_unit=effective,camera_pid=cam['pid'],camera_epoch=cam['service_epoch'],
  camera_unchanged=True,identity_database_unchanged=True,identity_database_sha256=db_sha,
  handsfree=u['handsfree_dialogue'],voice_barge_in=u['voice_barge_in'],manual_pan_present=True)
except Exception as exc:
 subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=40)
 if override.exists():override.unlink()
 restore_preference();subprocess.run(['systemctl','daemon-reload'],check=True)
 subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True)
 report.update(status='ROLLED_BACK_UI',error=type(exc).__name__+': '+str(exc))
 try:wait_ready(True);report['rollback_recovery_ready']=True
 except Exception as recovery:report['rollback_error']=str(recovery)
(stage/'deployment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('CANDIDATE',repr(c),1).replace('BASE',repr(b),1)
r=json.loads(ssh('python3 -B -',remote,timeout=560))
(HERE/'deployment.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k!='ui_unit'}));assert r['status']=='UI_ECHO_VERIFY_DEPLOYED'
