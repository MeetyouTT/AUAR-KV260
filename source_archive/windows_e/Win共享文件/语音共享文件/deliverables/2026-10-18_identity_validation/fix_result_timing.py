"""Fit evidence TTL to measured ARM inference while retaining target freshness."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
d=json.loads((HERE/'deployment.json').read_text(encoding='utf-8'))
remote=r'''
import hashlib,json,os,re,subprocess,time,urllib.request,uuid
from pathlib import Path
d=DEPLOYMENT;root=Path(d['runtime']);stage=root.parent
def get(port,path):return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
before=get(8790,'/health');ui=get(8783,'/api/state')
assert not ui['automatic_conversation']['enabled'] and ui['local_recording']['state']!='RECORDING'
assert str(Path('/proc/%d/cwd'%before['pid']).resolve())==str(root/'aura')
unit=Path('/etc/systemd/system/aura-camera-ui.service');old=unit.read_bytes();assert str(root) in old.decode()
backup=stage/('timing-backup-'+uuid.uuid4().hex[:10]);backup.mkdir();(backup/unit.name).write_bytes(old)
configs=stage/'camera_live_config';configs.mkdir(exist_ok=False)
identity=json.loads((root/'aura/config/board_identity.json').read_text());assert identity['result_ttl_ms']==1500
identity['result_ttl_ms']=3000
identity_path=configs/'board_identity.json';identity_path.write_text(json.dumps(identity,indent=2)+'\n')
camera=json.loads((root/'aura/config/board_camera_ui.json').read_text())
camera['identity']['config']=str(identity_path)
camera_path=configs/'board_camera_ui.json';camera_path.write_text(json.dumps(camera,indent=2)+'\n')
new=re.sub(r'^ExecStart=.*$',
 'ExecStart=/usr/bin/python3 -B '+str(root/'aura/board/vision/ui_camera_service.py')+' --config '+str(camera_path),old.decode(),flags=re.M)
def atomic(raw):
 temp=unit.with_name(unit.name+'.timing-tmp');temp.write_bytes(raw);temp.chmod(0o644);os.replace(temp,unit)
report={'old_ttl_ms':1500,'new_ttl_ms':3000,'backup':str(backup),'camera_config':str(camera_path),
 'identity_config':str(identity_path),'ui_restarted':False,'matching_threshold_changed':False,
 'capture_target_freshness_checks_changed':False,'before':before,
 'config_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (camera_path,identity_path)}}
try:
 subprocess.run(['systemctl','stop','aura-camera-ui.service'],check=True,timeout=20)
 atomic(new.encode());subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
 subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],check=True,timeout=15)
 deadline=time.monotonic()+35
 while time.monotonic()<deadline:
  try:
   after=get(8790,'/health')
   if after.get('identity_recognition') and not after.get('camera_error') and not after.get('detector_error'):break
  except OSError:pass
  time.sleep(.3)
 else:raise RuntimeError('Timing candidate did not become ready')
 assert after['detector']==before['detector']
 report.update(status='TIMING_FIX_LOADED',after=after)
except Exception as ex:
 subprocess.run(['systemctl','stop','aura-camera-ui.service'],capture_output=True,timeout=20)
 atomic(old);subprocess.run(['systemctl','daemon-reload'],capture_output=True,timeout=15)
 subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],capture_output=True,timeout=15)
 report.update(status='TIMING_FIX_ROLLED_BACK',error=str(ex))
(stage/'timing_fix.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('DEPLOYMENT',repr(d))
r=json.loads(ssh('python3 -',remote,timeout=100))
(HERE/'timing_fix.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in ('before','after')},ensure_ascii=True))
assert r['status']=='TIMING_FIX_LOADED'
