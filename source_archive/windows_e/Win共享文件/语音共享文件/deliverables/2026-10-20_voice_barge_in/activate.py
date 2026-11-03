"""Switch only the UI, retaining the CURRENT camera/motion unit and user choice."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
baseline=json.loads((HERE/'board_baseline.json').read_text(encoding='utf-8'))
b={'aura-avatar-ui.service':baseline['ui_unit'],'aura-camera-ui.service':baseline['camera_unit']}
assert c['tests_passed'] and c['preflight_passed']
smoke=json.loads((HERE/'smoke.json').read_text(encoding='utf-8'))
assert smoke['passed'] and smoke['runtime']==c['runtime']
for n,sha in c['files'].items():
 source=HERE/'merged_sources'/n
 if not source.exists():source=ROOT/n
 assert hashlib.sha256(source.read_bytes()).hexdigest()==sha,n
base=baseline
prep=HERE/'pre_test_state.json'
if prep.exists():
 prepared=json.loads(prep.read_text(encoding='utf-8'))
 if not prepared.get('restored'):base=dict(base,desired_enabled=prepared['original_monitor_enabled'])
probe=base64.b64encode((HERE/'acoustic_probe.py').read_bytes()).decode()
control={}
if '--await-trigger' in sys.argv:
 import uuid
 control={'path':c['stage']+'/controlled-'+uuid.uuid4().hex}
 (HERE/'controlled_test.json').write_text(json.dumps(control),encoding='utf-8')
remote=r'''
import base64,glob,hashlib,json,os,re,subprocess,time,urllib.request,uuid
from pathlib import Path
c=CANDIDATE;b=BEFORE;base=BASELINE;control=CONTROL;stage=Path(c['stage']);root=Path(c['runtime'])
def get(port,path,host='127.0.0.1'):
 return json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
def unit(name):return subprocess.check_output(['systemctl','cat',name],text=True)
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=40)
def quiet():
 u=get(8783,'/api/state')
 assert u['phase']=='IDLE' and not u['playing'] and not u['paused'],'Dialogue is active'
 assert not u['local_transcription']['service']['pending'],'Request still in flight'
 assert not u['local_transcription']['service'].get('voice_enrollment',{}).get('active'),'Enrollment is active'
 assert not (u['local_recording']['state']=='RECORDING' and u['automatic_conversation'].get('speech_active')),'User is speaking'
 return u
assert unit('aura-avatar-ui.service')==c['ui_unit']==b['aura-avatar-ui.service']
assert unit('aura-camera-ui.service')==b['aura-camera-ui.service'],'Camera startup changed; re-inspect'
for n,sha in c['files'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==sha,n
for n,sha in c['preserved'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==sha,n
assert not any('board_speaker_sampler.py' in row for row in subprocess.check_output(['ps','-eo','args'],text=True).splitlines()),'Speaker sampling window still open'
idle_deadline=time.monotonic()+170
while True:
 try:
  quiet();pc=get(8792,'/health','192.168.50.1');assert pc['ready'] and not pc['busy'],'Model is still busy'
  break
 except (AssertionError,OSError):
  if time.monotonic()>=idle_deadline:raise
  time.sleep(.5)
camera=get(8790,'/health');assert camera['identity']['ready']
camera_unit=unit('aura-camera-ui.service');camera_path=Path(re.search(r'--config (\S+)',camera_unit).group(1))
camera_raw=camera_path.read_bytes();camera_cfg=json.loads(camera_raw)
identity_path=Path(camera_cfg['identity']['config']);identity_raw=identity_path.read_bytes()
db=Path(json.loads(identity_raw)['database']).expanduser();db_sha=hashlib.sha256(db.read_bytes()).hexdigest()
u=quiet();was_enabled=u['handsfree_dialogue']['enabled']
chosen=base.get('desired_enabled',was_enabled)
pref=Path(base['ui_home'])/'.local/share/aura/handsfree_dialogue.json';pref_before=pref.read_text() if pref.exists() else None
old_path=Path('/etc/systemd/system/aura-avatar-ui.service')
old={'text':old_path.read_text(),'link':os.readlink(old_path) if old_path.is_symlink() else None}
backup=stage/('ui-backup-'+uuid.uuid4().hex[:10]);backup.mkdir()
(backup/'rollback.json').write_text(json.dumps({'unit':old,'preference':pref_before,'enabled':chosen},indent=2))
new=old['text'].replace(c['source_runtime'],str(root))
new=re.sub(r'^ExecStart=.*$','ExecStart=/usr/bin/python3 -B '+c['startup']+'/launcher.py --config '+c['startup']+'/config.json',new,flags=re.M)
def atomic_unit(raw,link=None):
 tmp=old_path.with_name(old_path.name+'.hf-'+uuid.uuid4().hex[:8])
 if link:tmp.symlink_to(link)
 else:tmp.write_text(raw);tmp.chmod(0o644)
 os.replace(tmp,old_path)
def command(value):
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(value).encode(),
  headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 return json.load(urllib.request.urlopen(req,timeout=4))
report={'backup':str(backup),'runtime':str(root),'previous_camera_pid':camera['pid'],
 'monitor_enabled_preserved':chosen,'monitor_was_enabled_before':was_enabled,
 'monitor_choice_source':'restore_pre_test_choice' if 'desired_enabled' in base else 'preserve_current_explicit_choice','preference_path':str(pref),
 'camera_modified':False,'pc_restarted':False,'live_hearing_verified':False}
try:
 quiet()
 if was_enabled:command({'type':'event','event':'cancel'})
 for _ in range(50):
  u=get(8783,'/api/state')
  if not u['handsfree_dialogue']['enabled'] and u['local_recording']['state']!='RECORDING' and not u['local_transcription']['service']['pending']:break
  time.sleep(.1)
 else:raise RuntimeError('Listener did not release microphone')
 assert not subprocess.run(['fuser',*glob.glob('/dev/snd/pcm*c')],capture_output=True,text=True).stdout.strip(),'Microphone belongs to another process'
 run(['systemctl','stop','aura-avatar-ui.service'])
 probe_path=stage/'acoustic_probe.py';probe_path.write_bytes(base64.b64decode(PROBE))
 probe_run=subprocess.run(['python3','-B',str(probe_path),str(root),*([control['path']] if control else [])],env=dict(os.environ,DISPLAY=':0'),
  capture_output=True,text=True,timeout=230 if control else 40)
 (stage/'acoustic_probe.log').write_text(probe_run.stdout+probe_run.stderr)
 probe_rows=[json.loads(line[6:]) for line in probe_run.stdout.splitlines() if line.startswith('PROBE ')]
 report['acoustic_probe']=probe_rows[-1] if probe_rows else {'passed':False,'error':probe_run.stderr[-1800:]}
 assert probe_run.returncode==0 and report['acoustic_probe']['passed'],'Real loudspeaker echo check failed; retaining previous UI'
 for src in Path(c['source_runtime']).glob('*_settings.json'):
  target=root/src.name;assert not target.is_symlink();target.write_bytes(src.read_bytes())
 sys_path=__import__('sys').path;sys_path.insert(0,str(root/'aura'))
 from common.handsfree_settings import HandsFreeSettings
 HandsFreeSettings(pref).write(chosen)
 atomic_unit(new);run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block','aura-avatar-ui.service'])
 deadline=time.monotonic()+185
 while time.monotonic()<deadline:
  try:
   u=get(8783,'/api/state');hf=u.get('handsfree_dialogue',{})
   if (hf.get('enabled')==chosen and 'diagnostics' in hf and u['audio_output_state']=='IDLE_READY'
       and u['local_transcription']['service'].get('persistent_conversation')):break
  except (OSError,ValueError,KeyError):pass
  time.sleep(.5)
 else:raise RuntimeError('Updated UI not ready')
 cam=get(8790,'/health')
 assert cam['pid']==camera['pid'] and cam['service_epoch']==camera['service_epoch']
 assert unit('aura-camera-ui.service')==camera_unit and camera_path.read_bytes()==camera_raw and identity_path.read_bytes()==identity_raw
 assert hashlib.sha256(db.read_bytes()).hexdigest()==db_sha
 report.update(status='UI_ONLY_DEPLOYED',camera_pid=cam['pid'],camera_service_unchanged=True,
  identity_database_unchanged=True,identity_threshold=json.loads(identity_raw)['threshold'],handsfree=hf,
  ui_unit=unit('aura-avatar-ui.service'),identity_db_sha256=db_sha,
  camera_unit=camera_unit,camera_config_sha256=hashlib.sha256(camera_raw).hexdigest(),
  identity_config_sha256=hashlib.sha256(identity_raw).hexdigest())
except Exception as e:
 subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=40)
 atomic_unit(old['text'],old['link'])
 if pref_before is None:pref.unlink(missing_ok=True)
 else:pref.write_text(pref_before);pref.chmod(0o600)
 if 'desired_enabled' in base:
  import sys
  sys.path.insert(0,str(root/'aura'))
  from common.handsfree_settings import HandsFreeSettings
  HandsFreeSettings(pref).write(chosen)
 run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block','aura-avatar-ui.service'])
 report.update(status='ROLLED_BACK_UI',error=type(e).__name__+': '+str(e))
 deadline=time.monotonic()+185
 while time.monotonic()<deadline:
  try:
   restored=get(8783,'/api/state')
   if 'handsfree_dialogue' in restored:
    report['rollback_recovery_ready']=True;break
  except (OSError,ValueError):pass
  time.sleep(.5)
(stage/'deployment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('CANDIDATE',repr(c),1).replace('BEFORE',repr(b),1).replace('BASELINE',repr(base),1).replace('CONTROL',repr(control),1).replace('PROBE',repr(probe),1)
r=json.loads(ssh('python3 -B -',remote,timeout=600))
(HERE/'deployment.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in ('ui_unit','camera_unit')}))
assert r['status']=='UI_ONLY_DEPLOYED'
