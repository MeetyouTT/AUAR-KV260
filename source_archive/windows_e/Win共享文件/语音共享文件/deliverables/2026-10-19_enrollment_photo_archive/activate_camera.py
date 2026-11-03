"""Load tested frontal enrollment policy in camera only; preserve UI, audio and DB."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
p=json.loads((HERE/'preflight.json').read_text(encoding='utf-8'))
assert c['tests_passed'] and c['preflight_passed'] and all(p[k] for k in ('real_models_passed','bootstrap_passed','widget_passed'))
for name,sha in c['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
remote=r'''
import hashlib,json,os,sqlite3,subprocess,time,urllib.request,uuid,re
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);root=Path(c['runtime'])
assert stage.parent==Path('/home/root/aura-enrollment-photos-20261019') and root.parent==stage
get=lambda port,path,host='127.0.0.1':json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
def run(args,timeout=30):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)
def idle():
 s=get(8783,'/api/state');service=s['local_transcription']['service']
 assert s['phase']=='IDLE' and not s['playing'] and not s['paused']
 assert not s['automatic_conversation']['enabled'] and s['local_recording']['state']!='RECORDING'
 assert not service['pending'] and not service.get('voice_enrollment',{}).get('active')
 return s
idle();before=get(8790,'/health');pc=get(8792,'/health','192.168.50.1')
assert pc['ready'] and not pc['busy'] and pc['identity_features']['ready']
assert pc['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and pc['num_step']==16
assert pc['identity_voice_enrollment'].get('identity_query_intent_revision')==2
old_config=json.loads(Path(c['old_camera_config']).read_text());new_config=json.loads(Path(c['camera_config']).read_text())
old_identity=json.loads(Path(old_config['identity']['config']).read_text())
new_identity=json.loads(Path(new_config['identity']['config']).read_text())
assert {k:v for k,v in old_identity.items() if k!='enrollment_photos'}=={k:v for k,v in new_identity.items() if k!='enrollment_photos'}
assert new_identity['threshold']==.8 and new_identity['ambiguity_margin']==.1
assert new_identity['enrollment_photos']=={'enabled':True,'directory':'~/.local/share/aura/enrollment_photos','max_images_per_session':192}
assert {k:v for k,v in old_config.items() if k!='identity'}=={k:v for k,v in new_config.items() if k!='identity'}
db=Path(new_identity['database']).expanduser();digest=hashlib.sha256(db.read_bytes()).hexdigest()
def counts():
 with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as conn:
  return {'identities':conn.execute('SELECT count(*) FROM identities').fetchone()[0],
   'templates':conn.execute('SELECT count(*) FROM templates').fetchone()[0],
   'revision':conn.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
db_before=counts();assert db_before=={'identities':1,'templates':1,'revision':14}
for name,sha in c['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
ui_path=Path('/etc/systemd/system/aura-avatar-ui.service');ui_unit=ui_path.read_bytes()
assert c['old_ui_config'] in ui_unit.decode()
ui_pid=run(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value']).stdout.strip()
unit_path=Path('/etc/systemd/system/aura-camera-ui.service');old=unit_path.read_bytes()
assert c['old_camera_config'] in old.decode();link=os.readlink(unit_path) if unit_path.is_symlink() else None
backup=stage/('activation-backup-'+uuid.uuid4().hex[:10]);backup.mkdir()
(backup/unit_path.name).write_bytes(old);(backup/'rollback.json').write_text(json.dumps({'unit_link':link}))
unit=re.sub(r'^ExecStart=.*$','ExecStart=/usr/bin/python3 -B '+str(root/'aura/board/vision/ui_camera_service.py')+' --config '+c['camera_config'],old.decode(),flags=re.M)
unit=re.sub(r'^WorkingDirectory=.*$','WorkingDirectory='+str(root/'aura'),unit,flags=re.M)
def atomic(raw):
 temp=unit_path.with_name(unit_path.name+'.frontal-tmp');temp.write_bytes(raw);temp.chmod(0o644);os.replace(temp,unit_path)
report={'runtime':str(root),'backup':str(backup),'ui_config':c['old_ui_config'],'ui_pid_before':ui_pid,
 'camera_before':before,'database_before':db_before,'threshold':.8,'ambiguity_margin':.1,
 'matching_threshold_changed':False,'ui_restarted':False,'voice_host_restarted':False,
 'body_dpu_configuration_changed':False,'photos_or_templates_exported':False}
try:
 idle();run(['systemctl','stop','aura-camera-ui.service'],45);atomic(unit.encode())
 run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block','aura-camera-ui.service'])
 deadline=time.monotonic()+130
 while time.monotonic()<deadline:
  try:
   camera=get(8790,'/health');view=get(8790,'/v1/ui/status')
   if (camera.get('identity',{}).get('ready') and not camera.get('camera_error') and not camera.get('detector_error')
       and camera['identity']['sampling_diagnostics'].get('template_policy')=='frontal_medoid_v1'
       and camera['identity'].get('enrollment_photos',{}).get('ready')
       and view['modules']['identity']['target_kind']=='face'):break
  except (OSError,ValueError,KeyError):pass
  time.sleep(.4)
 else:raise RuntimeError('Frontal policy camera failed readiness')
 assert camera['board_boot_id']==before['board_boot_id'] and camera['detector']==before['detector']
 assert counts()==db_before and hashlib.sha256(db.read_bytes()).hexdigest()==digest
 assert ui_path.read_bytes()==ui_unit
 after_ui_pid=run(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value']).stdout.strip()
 assert after_ui_pid==ui_pid
 report.update(status='ENROLLMENT_PHOTO_ARCHIVE_ENABLED_EXISTING_IDENTITY_PRESERVED',camera_after=camera,
  database_after=counts(),database_hash_unchanged=True,ui_pid_after=after_ui_pid,
  current_identity_state=view['modules']['identity']['state'])
except Exception as exc:
 subprocess.run(['systemctl','stop','aura-camera-ui.service'],capture_output=True,timeout=45)
 if link:
  temp=unit_path.with_name(unit_path.name+'.frontal-rollback');temp.symlink_to(link);os.replace(temp,unit_path)
 else:atomic(old)
 run(['systemctl','daemon-reload']);run(['systemctl','start','--no-block','aura-camera-ui.service'])
 report.update(status='ROLLED_BACK',error=type(exc).__name__+': '+str(exc))
(stage/'deployment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('CANDIDATE',repr(c),1)
r=json.loads(ssh('python3 -B -',remote,timeout=200))
(HERE/'deployment.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in ('camera_before','camera_after')},ensure_ascii=True))
assert r['status']=='ENROLLMENT_PHOTO_ARCHIVE_ENABLED_EXISTING_IDENTITY_PRESERVED'
