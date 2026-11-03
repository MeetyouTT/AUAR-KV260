"""Use the pinned SFace model's documented cosine baseline; camera-only reload."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import hashlib,json,os,subprocess,time,urllib.request,uuid
from pathlib import Path
get=lambda port,path:json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
before=get(8790,'/health');ui=get(8783,'/api/state')
assert not ui['automatic_conversation']['enabled'] and ui['phase']=='IDLE' and ui['local_recording']['state']!='RECORDING'
argv=Path('/proc/%d/cmdline'%before['pid']).read_bytes().decode().split('\0')
camera_path=Path(argv[argv.index('--config')+1])
expected=Path('/home/root/aura-identity-validation-20261018/candidate-d843e37e7d4a/camera_live_config/board_camera_ui.json')
assert camera_path==expected
identity_path=Path(json.loads(camera_path.read_text())['identity']['config']);old=identity_path.read_bytes()
cfg=json.loads(old);assert cfg['model_id']=='sface-2021dec-0ba9fbfa01b5' and cfg['threshold']==.85
updated=dict(cfg,threshold=.363,threshold_origin='opencv_sface_lfw_reference_cosine_0.363_not_field_calibrated',
 threshold_reference='https://docs.opencv.org/4.9.0/d0/dd4/tutorial_dnn_face.html')
preserved={key:updated[key]==value for key,value in cfg.items() if key not in ('threshold','threshold_origin')}
assert all(preserved.values()) and updated['ambiguity_margin']==.1 and updated['result_ttl_ms']==3000
backup=camera_path.parent/('matching-backup-'+uuid.uuid4().hex[:12]);backup.mkdir();(backup/identity_path.name).write_bytes(old)
db=Path(cfg['database']).expanduser();db_before=hashlib.sha256(db.read_bytes()).hexdigest()
def atomic(raw):
 temp=identity_path.with_name(identity_path.name+'.matching-tmp');temp.write_bytes(raw);temp.chmod(0o644);os.replace(temp,identity_path)
report={'before':before,'old_threshold':.85,'new_threshold':.363,'ambiguity_margin':.1,'backup':str(backup),
 'identity_config':str(identity_path),'preserved_parameters':preserved,'ui_restarted':False,
 'basis':'Documented OpenCV SFace LFW cosine reference plus 8 real post-enrollment scores 0.734-0.818 rejected at 0.85',
 'field_accuracy_calibrated':False,'templates_exported':False}
try:
 subprocess.run(['systemctl','stop','aura-camera-ui.service'],check=True,timeout=20)
 atomic((json.dumps(updated,indent=2)+'\n').encode())
 subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],check=True,timeout=15)
 deadline=time.monotonic()+35
 while time.monotonic()<deadline:
  try:
   after=get(8790,'/health')
   if after.get('identity',{}).get('ready') and after.get('capture_frames',0)>4 and not after.get('camera_error') and not after.get('detector_error'):break
  except OSError:pass
  time.sleep(.25)
 else:raise RuntimeError('Matching configuration did not become ready')
 assert after['detector']==before['detector'] and after['board_boot_id']==before['board_boot_id']
 assert hashlib.sha256(db.read_bytes()).hexdigest()==db_before,'Identity database unexpectedly changed during camera reload'
 report.update(status='MATCHING_THRESHOLD_LOADED',after=after,database_unchanged=True,
  identity_config_sha256=hashlib.sha256(identity_path.read_bytes()).hexdigest())
except Exception as exc:
 subprocess.run(['systemctl','stop','aura-camera-ui.service'],capture_output=True,timeout=20)
 atomic(old);subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],capture_output=True,timeout=15)
 report.update(status='MATCHING_THRESHOLD_ROLLED_BACK',error=str(exc))
print(json.dumps(report))
'''
result=json.loads(ssh('python3 -B -',remote,timeout=90))
(HERE/'matching_threshold_fix.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in result.items() if key not in ('before','after')},ensure_ascii=True))
assert result['status']=='MATCHING_THRESHOLD_LOADED'
