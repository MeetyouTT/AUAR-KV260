"""Explicitly authorized 0.50 configuration change; preserve DB and code."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LOCAL = ROOT / 'aura/config/board_identity.json'
local_before = LOCAL.read_bytes()
assert json.loads(local_before)['threshold'] == .8
sys.path.insert(0, str(ROOT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

remote = r'''
import hashlib,json,math,os,sqlite3,subprocess,sys,tempfile,time,urllib.request,uuid
from pathlib import Path
def get(port,path,host='127.0.0.1'):
 return json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
def unit(name):
 return subprocess.check_output(['systemctl','cat',name],text=True)
def ui_pid():
 return subprocess.check_output(['systemctl','show','aura-avatar-ui.service','--property=MainPID','--value'],text=True).strip()
def idle():
 u=get(8783,'/api/state');s=u['local_transcription']['service']
 assert u['phase']=='IDLE' and not u['playing'] and not u['automatic_conversation']['enabled'], 'Dialogue is active'
 assert u['local_recording']['state']!='RECORDING' and not s.get('pending'), 'Audio job is active'
 assert not s.get('voice_enrollment',{}).get('active'), 'Voice enrollment is active'
 v=get(8790,'/v1/ui/status')['modules']['identity']
 assert v['enrollment_sampling']['stage'] in ('idle','failed'), 'Enrollment sampling is active'
 return v
idle();before=get(8790,'/health');pc=get(8792,'/health','192.168.50.1')
assert pc['ready'] and not pc['busy'] and pc['identity_features']['ready']
args=Path('/proc/%d/cmdline'%before['pid']).read_bytes().decode().split('\0')
camera_path=Path(args[args.index('--config')+1]).resolve()
root=next(Path(arg) for arg in args if arg.endswith('/ui_camera_service.py')).parents[2].resolve()
camera_raw=camera_path.read_bytes();identity_path=Path(json.loads(camera_raw)['identity']['config']).resolve()
assert identity_path.parent==camera_path.parent and identity_path.name=='board_identity.json'
old=identity_path.read_bytes();cfg=json.loads(old)
assert cfg['threshold']==.8 and cfg['ambiguity_margin']==.1
assert cfg['feature_backend']=={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
updated=dict(cfg,threshold=.5,threshold_origin='user_authorized_experimental_cosine_0.50_not_field_calibrated')
assert {k:v for k,v in updated.items() if k not in ('threshold','threshold_origin')}=={k:v for k,v in cfg.items() if k not in ('threshold','threshold_origin')}
new=(json.dumps(updated,ensure_ascii=False,indent=2)+'\n').encode()
db=Path(cfg['database']).expanduser()
def counts():
 with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as c:
  return {'identities':c.execute('SELECT count(*) FROM identities').fetchone()[0],
   'templates':c.execute('SELECT count(*) FROM templates').fetchone()[0],
   'revision':c.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
db_before=counts();db_hash=digest(db);mode=identity_path.stat().st_mode&0o777
units={name:unit(name) for name in ('aura-camera-ui.service','aura-avatar-ui.service')};gui_pid=ui_pid()
sources={str(p.relative_to(root)):digest(p) for p in root.rglob('*.py')}
models={key:digest(Path(cfg[key])) for key in ('face_model','embedding_model')}
archive_before=before['identity'].get('enrollment_photos',{})
photo_baseline={k:archive_before.get(k) for k in ('latest_session','image_count','outcome')}
# Configuration parsing and the actual production matcher use an isolated in-memory DB.
sys.path.insert(0,str(root))
from board.identity.camera_faces import config_for
from board.identity.store import IdentityStore
from board.identity.live import IdentityService
with tempfile.TemporaryDirectory(prefix='aura-threshold-050-') as folder:
 trial=Path(folder)/'board_identity.json';trial.write_bytes(new)
 parsed=config_for(root,trial);assert parsed['threshold']==.5
store=IdentityStore(':memory:',cfg['model_id'],128,.5,.1)
pad=lambda x,y:(x,y)+(0.,)*126
store.enroll('synthetic-reference','synthetic reference',pad(1.,0.),consent=True)
boundary=[]
for score,want in ((.4999,'UNKNOWN'),(.5,'KNOWN'),(.5001,'KNOWN')):
 actual=store.match(pad(score,math.sqrt(1-score*score)))
 assert actual.state==want,(score,actual.state)
 boundary.append({'score':score,'state':actual.state})
service=IdentityService(store,lambda:None,lambda:None,multi_frame=True)
assert service.sampling.threshold==.5 and service.sampling.margin==.1
service.sampling.candidate={'embedding':pad(1.,0.)}
assert not service.sampling.usable(pad(.4999,math.sqrt(1-.4999**2)),None)
assert service.sampling.usable(pad(.5,math.sqrt(.75)),None)
assert service.sampling.usable(pad(.5,math.sqrt(.75)),.39)
assert not service.sampling.usable(pad(.5,math.sqrt(.75)),.41)
q=(.5,math.sqrt(.75));other=.45;z=math.sqrt(1-other*other)
store.enroll('synthetic-other','synthetic other',pad(other*q[0]-z*q[1],other*q[1]+z*q[0]),consent=True)
assert store.match(pad(*q)).state=='AMBIGUOUS'
store.close()
backup=identity_path.parent/('threshold-050-backup-'+uuid.uuid4().hex[:10]);backup.mkdir(mode=0o700)
(backup/'board_identity.before.json').write_bytes(old)
report={'client_date':'2026-10-19','authorization':'用户明确要求：现在那就调成0.5',
 'status':'PREFLIGHT_PASSED','old_threshold':.8,'new_threshold':.5,'ambiguity_margin':.1,
 'identity_config_path':str(identity_path),'camera_config_path':str(camera_path),'runtime':str(root),
 'backup':str(backup),'boundary_checks':boundary,'enrollment_uses_same_threshold':True,
 'ambiguity_check_passed':True,'database_before':db_before,'database_sha256_before':db_hash,
 'camera_pid_before':before['pid'],'ui_pid_before':gui_pid,'photos_before':photo_baseline,
 'production_sources_checked':len(sources),'models_sha256':models,
 'ui_restarted':False,'pc_model_services_restarted':False,'field_accuracy_calibrated':False,
 'new_enrollment_started':False,'photos_or_templates_exported':False}
def persist():
 (backup/'activation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
persist()
def atomic(raw):
 path=identity_path.with_name(identity_path.name+'.threshold-050-'+uuid.uuid4().hex[:10]+'.tmp')
 with path.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 path.chmod(mode);os.replace(path,identity_path)
def wait_ready():
 deadline=time.monotonic()+55
 while time.monotonic()<deadline:
  try:
   h=get(8790,'/health')
   if (h['identity']['ready'] and h.get('capture_frames',0)>4 and h.get('detected_frames',0)>1
       and not h['identity']['error'] and not h['camera_error'] and not h['detector_error']):return h
  except (OSError,ValueError,KeyError):pass
  time.sleep(.4)
 raise RuntimeError('Camera/identity readiness timed out')
try:
 idle();assert identity_path.read_bytes()==old and counts()==db_before and digest(db)==db_hash
 assert ui_pid()==gui_pid
 subprocess.run(['systemctl','stop','aura-camera-ui.service'],check=True,timeout=25)
 atomic(new)
 subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],check=True,timeout=12)
 after=wait_ready();view=get(8790,'/v1/ui/status')['modules']['identity']
 assert after['pid']!=before['pid'] and after['board_boot_id']==before['board_boot_id']
 argv=Path('/proc/%d/cmdline'%after['pid']).read_bytes().decode().split('\0')
 assert Path(argv[argv.index('--config')+1]).resolve()==camera_path and identity_path.read_bytes()==new
 assert after['detector']==before['detector'] and after['identity']['backend']==before['identity']['backend']
 assert counts()==db_before and digest(db)==db_hash and camera_path.read_bytes()==camera_raw
 assert ui_pid()==gui_pid and all(unit(name)==value for name,value in units.items())
 assert all(digest(root/name)==sha for name,sha in sources.items())
 assert all(digest(Path(cfg[key]))==sha for key,sha in models.items())
 assert view['db_version']==db_before['revision'] and view['enrollment_sampling']['stage']=='idle'
 archive_after=after['identity'].get('enrollment_photos',{})
 assert {k:archive_after.get(k) for k in photo_baseline}==photo_baseline
 pc_after=get(8792,'/health','192.168.50.1');asr=get(8791,'/health','192.168.50.1')
 assert pc_after['ready'] and pc_after['identity_features']['ready'] and asr['ready']
 assert all(pc_after[k]==pc[k] for k in ('llm_model','num_step'))
 report.update(status='THRESHOLD_050_LOADED_VERIFIED_AWAITING_FIELD_TEST',
  camera_pid_after=after['pid'],ui_pid_after=ui_pid(),database_after=counts(),
  database_hash_unchanged=True,config_only_parameters_changed=['threshold','threshold_origin'],
  identity_config_sha256=digest(identity_path),production_sources_unchanged=True,models_unchanged=True,
  body_detector_preserved=True,camera_errors={key:after[key] for key in ('camera_error','detector_error')},
  face_ready=after['identity']['face_targets']['ready'],feature_backend=after['identity']['backend'],
  pc_ready=True,asr_ready=True,current_identity_state=view['state'],photos_unchanged=True,
  camera_restart_count=1,effective_config=updated)
except Exception as exc:
 subprocess.run(['systemctl','stop','aura-camera-ui.service'],capture_output=True,timeout=25)
 atomic(old)
 subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],check=True,timeout=12)
 restored=wait_ready()
 report.update(status='THRESHOLD_050_ROLLED_BACK',error=type(exc).__name__+': '+str(exc),
  restored_threshold=json.loads(identity_path.read_bytes())['threshold'],restored_camera_pid=restored['pid'])
persist();print(json.dumps(report))
'''
result = json.loads(ssh('python3 -B -', remote, timeout=175))
effective = result.pop('effective_config', None)
(HERE / 'activation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
if result['status'] == 'THRESHOLD_050_LOADED_VERIFIED_AWAITING_FIELD_TEST':
    assert LOCAL.read_bytes() == local_before, 'Local config changed concurrently'
    (HERE / 'board_identity.local.before.json').write_bytes(local_before)
    local = json.loads(local_before)
    local.update(threshold=.5, threshold_origin='user_authorized_experimental_cosine_0.50_not_field_calibrated')
    LOCAL.write_text(json.dumps(local, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (HERE / 'board_identity.effective.json').write_text(json.dumps(effective, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    result['local_config_threshold'] = json.loads(LOCAL.read_bytes())['threshold']
    result['local_config_sha256'] = hashlib.sha256(LOCAL.read_bytes()).hexdigest()
    (HERE / 'activation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=True))
assert result['status'] == 'THRESHOLD_050_LOADED_VERIFIED_AWAITING_FIELD_TEST'
