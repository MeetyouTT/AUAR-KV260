"""Switch the two tested board units atomically, with automatic rollback."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
u=json.loads((HERE/'ui_candidate.json').read_text(encoding='utf-8'))
p=json.loads((HERE/'preflight.json').read_text(encoding='utf-8'))
assert c['tests_passed'] and u['tests_passed'] and u['preflight_passed'] and p['static_reference_check']['status']=='PASS'
remote=r'''
import hashlib,json,os,re,subprocess,time,urllib.request,uuid
from pathlib import Path
c=CANDIDATE;u=UI;stage=Path(c['stage']);root=Path(u['runtime'])
assert root.parent==stage and stage.parent==Path('/home/root/aura-identity-validation-20261018')
def run(args,timeout=35):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)
def get(port,path,host='127.0.0.1'):return json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
def pc():
 try:return get(8792,'/health','192.168.50.1')
 except Exception as ex:return {'unavailable':str(ex)}
def idle():
 s=get(8783,'/api/state')
 assert s['phase']=='IDLE' and not s['playing'] and not s['paused']
 assert s['local_recording']['state']!='RECORDING' and not s['local_transcription']['service']['pending']
 assert not s.get('automatic_conversation',{}).get('enabled')
 return s
before=idle();camera_before=get(8790,'/health');pc_before=pc()
assert str(Path('/proc/%d/cwd'%camera_before['pid']).resolve().parent)==c['source_runtime']
assert json.loads((Path(c['source_runtime'])/'aura/config/board_camera_ui.json').read_text())==c['old_camera_config']
for name,sha in u['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
camera_cfg=json.loads((root/'aura/config/board_camera_ui.json').read_text())
assert {k:v for k,v in camera_cfg.items() if k!='identity'}=={k:v for k,v in c['old_camera_config'].items() if k!='identity'}
paths={n:Path('/etc/systemd/system')/n for n in ('aura-camera-ui.service','aura-avatar-ui.service')}
old={n:path.read_bytes() for n,path in paths.items()}
links={n:os.readlink(str(path)) if path.is_symlink() else None for n,path in paths.items()}
assert u['old_ui_config'] in old['aura-avatar-ui.service'].decode()
backup=stage/('activation-backup-'+uuid.uuid4().hex[:10]);backup.mkdir()
for n,raw in old.items():(backup/n).write_bytes(raw)
(backup/'rollback.json').write_text(json.dumps({'unit_links':links,'previous_ui_config':u['old_ui_config']},indent=2))
new={}
new['aura-camera-ui.service']=old['aura-camera-ui.service'].decode().replace(c['source_runtime'],str(root)).encode()
unit=old['aura-avatar-ui.service'].decode().replace(u['source_runtime'],str(root))
unit=re.sub(r'^ExecStart=.*$','ExecStart=/usr/bin/python3 -B '+u['startup']+'/launcher.py --config '+u['startup']+'/config.json',unit,flags=re.M)
new['aura-avatar-ui.service']=unit.encode()
for n,raw in new.items():(stage/n).write_bytes(raw)
def atomic(path,raw):
 temp=path.with_name(path.name+'.identity-tmp');temp.write_bytes(raw);temp.chmod(0o644);os.replace(temp,path)
def restore():
 for n,path in paths.items():
  if links[n]:
   tmp=path.with_name(path.name+'.identity-rollback');tmp.symlink_to(links[n]);os.replace(tmp,path)
  else:atomic(path,old[n])
 run(['systemctl','daemon-reload'])
 run(['systemctl','start','--no-block','aura-camera-ui.service','aura-avatar-ui.service'])
report={'status':'STARTING','runtime':str(root),'backup':str(backup),'camera_before':camera_before,
 'pc_before':pc_before,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'identity_database':'/home/root/.local/share/aura/identities.sqlite3','automatic_enrollment':False,
 'dpu_camera_tracking_config_preserved':True}
try:
 idle()
 run(['systemctl','stop','aura-avatar-ui.service','aura-camera-ui.service'])
 # DPU is exclusive. Its unchanged model/backend preflight runs after release.
 check=run(['python3','-B',str(root/'aura/board/vision/ui_camera_service.py'),'--check'],timeout=45)
 (stage/'camera_preflight.log').write_text(check.stdout+check.stderr)
 report['camera_preflight']=json.loads(check.stdout)
 for n,path in paths.items():atomic(path,new[n])
 run(['systemctl','daemon-reload'])
 run(['systemctl','start','--no-block','aura-camera-ui.service','aura-avatar-ui.service'])
 deadline=time.monotonic()+150
 while time.monotonic()<deadline:
  try:
   camera=get(8790,'/health');s=get(8783,'/api/state')
   identity=camera.get('identity',{})
   if identity.get('error'):raise RuntimeError(identity['error'])
   active=run(['systemctl','is-active','aura-avatar-ui.service'],timeout=5).stdout.strip()
   if active=='active' and camera.get('identity_recognition') and not camera.get('camera_error') and not camera.get('detector_error') and s.get('audio_output_state')=='IDLE_READY':break
  except (OSError,ValueError,subprocess.CalledProcessError):pass
  time.sleep(.4)
 else:raise RuntimeError('Candidate failed to become ready')
 report.update(status='DEPLOYED_IDENTITY_READY_AWAITING_USER_ENROLLMENT',camera_after=camera,
  ui_phase=s['phase'],automatic=s['automatic_conversation'])
 db=Path(report['identity_database']);report['database_mode']=oct(db.stat().st_mode&0o777)
 view=get(8790,'/v1/ui/status')
 report['identity_state']=view['modules']['identity']['state']
 report['enrolled_people_count']=len(view['modules']['identity']['people'])
 report['can_enroll']=view['capabilities']['identity_enroll']
 assert camera['detector']==camera_before['detector']
 assert not s['automatic_conversation']['enabled']
except Exception as ex:
 subprocess.run(['systemctl','stop','aura-avatar-ui.service','aura-camera-ui.service'],capture_output=True,timeout=40)
 restore();report.update(status='ROLLED_BACK',error=type(ex).__name__+': '+str(ex))
report['pc_after']=pc()
(stage/'deployment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report))
'''.replace('CANDIDATE',repr(c)).replace('UI',repr(u))
r=json.loads(ssh('python3 -',remote,timeout=240))
(HERE/'deployment.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=True));assert r['status']=='DEPLOYED_IDENTITY_READY_AWAITING_USER_ENROLLMENT'
