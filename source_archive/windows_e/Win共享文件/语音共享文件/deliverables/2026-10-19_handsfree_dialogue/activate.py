"""Activate tested AV-entry UI + additive camera metadata, with two-unit rollback."""
import hashlib,json,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
before=json.loads((HERE/'before_state.json').read_text(encoding='utf-8'))
assert c['tests_passed'] and c['preflight_passed']
for name,sha in c['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
remote=r'''
import hashlib,json,os,re,sqlite3,subprocess,sys,time,urllib.request,uuid
from pathlib import Path
c=CANDIDATE;b=BEFORE;root=Path(c['runtime']);stage=Path(c['stage'])
assert stage.parent==Path('/home/root/aura-handsfree-dialogue-20261020') and root.parent==stage
get=lambda port,path,host='127.0.0.1':json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
def run(args,timeout=35):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)
def idle():
 s=get(8783,'/api/state');assert s['phase']=='IDLE' and not s['playing'] and not s['paused']
 assert not s['automatic_conversation']['enabled'] and s['local_recording']['state']!='RECORDING'
 assert not s['local_transcription']['service']['pending']
 assert not s['local_transcription']['service'].get('voice_enrollment',{}).get('active');return s
idle();pc=get(8792,'/health','192.168.50.1');assert pc['ready'] and not pc['busy'] and pc['handsfree_entry']['version']==1
camera_before=get(8790,'/health')
assert subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)==b['camera_unit']
assert subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)==b['ui_unit']
old_camera_path=Path(c['old_camera_config']);old_camera=json.loads(old_camera_path.read_text())
assert old_camera==b['camera_config']
old_identity_path=Path(old_camera['identity']['config']);identity_raw=old_identity_path.read_bytes()
identity=json.loads(identity_raw);assert identity==b['identity_config']
assert json.loads((stage/'camera_live_config/board_identity.json').read_text())==identity
db=Path(identity['database']).expanduser();db_hash=hashlib.sha256(db.read_bytes()).hexdigest()
assert db_hash==b['identity_db_sha256']
old_camera_source=Path(re.search(r'ExecStart=\S+ -B (\S+)/aura/board/vision/ui_camera_service.py',b['camera_unit']).group(1))
preserved=['aura/board/vision/ui_camera_service.py','aura/board/identity/live.py','aura/board/identity/store.py',
 'aura/board/identity/camera_faces.py','aura/board/identity/sampling.py','aura/board/vision/person_bytetrack.py']
for name in preserved:assert (root/name).read_bytes()==(old_camera_source/name).read_bytes(),name
for name,sha in c['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
for source in Path(c['source_runtime']).glob('*_settings.json'):
 target=root/source.name;assert not target.is_symlink();target.write_bytes(source.read_bytes())
backup=stage/('activation-backup-'+uuid.uuid4().hex[:10]);backup.mkdir()
units={}
for name in ('aura-avatar-ui.service','aura-camera-ui.service'):
 path=Path('/etc/systemd/system')/name
 units[name]={'text':path.read_text(),'link':os.readlink(path) if path.is_symlink() else None}
 (backup/name).write_bytes(path.read_bytes())
(backup/'rollback.json').write_text(json.dumps(units,indent=2))
def atomic(name,raw,link=None):
 path=Path('/etc/systemd/system')/name;tmp=path.with_name(path.name+'.handsfree-'+uuid.uuid4().hex[:6])
 if link:tmp.symlink_to(link)
 else:tmp.write_text(raw);tmp.chmod(0o644)
 os.replace(tmp,path)
ui=units['aura-avatar-ui.service']['text'].replace(c['source_runtime'],str(root))
ui=re.sub(r'^ExecStart=.*$','ExecStart=/usr/bin/python3 -B '+c['startup']+'/launcher.py --config '+c['startup']+'/config.json',ui,flags=re.M)
cam=units['aura-camera-ui.service']['text']
cam=re.sub(r'^ExecStart=.*$','ExecStart=/usr/bin/python3 -B '+str(root)+'/aura/board/vision/ui_camera_service.py --config '+c['camera_config'],cam,flags=re.M)
cam=re.sub(r'^WorkingDirectory=.*$','WorkingDirectory='+str(root)+'/aura',cam,flags=re.M)
report={'runtime':str(root),'backup':str(backup),'previous_camera_pid':camera_before['pid'],
 'threshold_preserved':identity['threshold'],'identity_database_unchanged':False,
 'speaker_binding_verified':False,'live_voice_acceptance':False,'camera_restarted_for_metadata':True}
try:
 idle();run(['systemctl','stop','aura-avatar-ui.service']);run(['systemctl','stop','aura-camera-ui.service'])
 atomic('aura-avatar-ui.service',ui);atomic('aura-camera-ui.service',cam);run(['systemctl','daemon-reload'])
 run(['systemctl','start','--no-block','aura-camera-ui.service'])
 deadline=time.monotonic()+85
 while time.monotonic()<deadline:
  try:
   camera=get(8790,'/health');s=get(8790,'/v1/ui/status')
   if camera['identity']['ready'] and 'face_attention' in s['modules']['identity']:break
  except (OSError,KeyError,ValueError):pass
  time.sleep(.5)
 else:raise RuntimeError('Camera attention metadata not ready')
 sys.path.insert(0,str(root/'aura'))
 from board.interaction.ui_contract import validate_snapshot,millis
 validate_snapshot(s,Path('/proc/sys/kernel/random/boot_id').read_text().strip(),millis())
 assert old_identity_path.read_bytes()==identity_raw and hashlib.sha256(db.read_bytes()).hexdigest()==db_hash
 run(['systemctl','start','--no-block','aura-avatar-ui.service'])
 deadline=time.monotonic()+185
 while time.monotonic()<deadline:
  try:
   u=get(8783,'/api/state');hf=u.get('handsfree_dialogue',{})
   if (run(['systemctl','is-active','aura-avatar-ui.service'],5).stdout.strip()=='active'
       and hf.get('enabled') and u.get('audio_output_state')=='IDLE_READY'
       and u['local_transcription']['service'].get('persistent_conversation')):break
  except (OSError,KeyError,ValueError,subprocess.CalledProcessError):pass
  time.sleep(.5)
 else:raise RuntimeError('Hands-free UI not ready')
 assert hashlib.sha256(db.read_bytes()).hexdigest()==db_hash
 report.update(status='HANDS_FREE_AV_ENTRY_DEPLOYED',camera_pid=camera['pid'],
  handsfree=hf,ui_phase=u['phase'],recording=u['local_recording']['state'],
  identity_database_unchanged=True,camera_health=camera)
except Exception as exc:
 subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=40)
 subprocess.run(['systemctl','stop','aura-camera-ui.service'],capture_output=True,timeout=35)
 for name,old in units.items():atomic(name,old['text'],old['link'])
 run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block','aura-camera-ui.service'])
 run(['systemctl','start','--no-block','aura-avatar-ui.service'])
 report.update(status='ROLLED_BACK',error=type(exc).__name__+': '+str(exc))
(stage/'deployment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('CANDIDATE',repr(c),1).replace('BEFORE',repr(before),1)
r=json.loads(ssh('python3 -B -',remote,timeout=340))
(HERE/'deployment.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k!='camera_health'}))
assert r['status']=='HANDS_FREE_AV_ENTRY_DEPLOYED'
