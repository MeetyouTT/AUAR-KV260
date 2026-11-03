"""User-authorized 0.80 trial: real public preflight, camera-only reload, rollback."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((ROOT/'deliverables/2026-10-19_windows_face_features/candidate.json').read_text(encoding='utf-8'))
remote=r'''
import hashlib,json,os,sqlite3,subprocess,time,urllib.request,uuid
from pathlib import Path
c=CANDIDATE
get=lambda port,path,host='127.0.0.1':json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
def idle():
 u=get(8783,'/api/state')
 assert u['phase']=='IDLE' and not u['automatic_conversation']['enabled'] and not u['playing']
 assert u['local_recording']['state']!='RECORDING' and not u['local_transcription']['service']['pending']
 return u
idle();before=get(8790,'/health');pc=get(8792,'/health','192.168.50.1')
assert pc['ready'] and not pc['busy'] and pc['identity_features']['ready']
assert pc['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and pc['num_step']==16
argv=Path('/proc/%d/cmdline'%before['pid']).read_bytes().decode().split('\0')
camera_path=Path(argv[argv.index('--config')+1]);assert str(camera_path)==c['camera_config']
camera_raw=camera_path.read_bytes();identity_path=Path(json.loads(camera_raw)['identity']['config'])
old=identity_path.read_bytes();cfg=json.loads(old);assert cfg['threshold']==.85 and cfg['ambiguity_margin']==.1
assert cfg['feature_backend']=={'kind':'windows_sface','host':'192.168.50.1','port':8792,'timeout_ms':650}
root=Path(c['runtime']);assert root.parent==camera_path.parent.parent
for name,sha in c['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
db=Path(cfg['database']).expanduser()
def counts():
 with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as connection:
  return {'identities':connection.execute('SELECT count(*) FROM identities').fetchone()[0],
   'templates':connection.execute('SELECT count(*) FROM templates').fetchone()[0],
   'revision':connection.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
db_before=counts();assert db_before=={'identities':0,'templates':0,'revision':13}
db_hash=hashlib.sha256(db.read_bytes()).hexdigest()
ui_pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','--property=MainPID','--value'],text=True).strip()
unit=subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)
updated=dict(cfg,threshold=.8,threshold_origin='user_authorized_experimental_cosine_0.80_not_field_calibrated')
preserved={key:updated[key]==value for key,value in cfg.items() if key not in ('threshold','threshold_origin')}
assert all(preserved.values())
backup=camera_path.parent/('threshold-080-backup-'+uuid.uuid4().hex[:10]);backup.mkdir()
(backup/'board_identity.before.json').write_bytes(old)
trial=backup/'board_identity.trial.json';new=(json.dumps(updated,indent=2)+'\n').encode();trial.write_bytes(new)
probe=r"""
import json,math,os,tempfile
from pathlib import Path
import cv2
cv2.setNumThreads(2)
from board.identity.camera_faces import CameraFaceExtractor,config_for
from board.identity.store import IdentityStore
from board.identity.sampling import EnrollmentSampling
from board.identity.live import IdentityService
from board.identity.face_targets import FaceTargetService
from board.identity.voice_enrollment import VoiceEnrollment
from board.vision.ui_camera_service import CameraState
from board.vision.reference_faces import YuNetCompat
cfg=config_for(Path.cwd(),Path(TRIAL));assert cfg['threshold']==.8 and cfg['ambiguity_margin']==.1
# Exercise the real matcher at the new boundary and the unchanged ambiguity gap.
pad=lambda x,y:(x,y)+(0.,)*126
with tempfile.TemporaryDirectory(prefix='aura-threshold-080-public-') as directory:
 check=IdentityStore(':memory:',cfg['model_id'],128,.8,.1)
 check.enroll('synthetic-reference','synthetic reference',pad(1.,0.),consent=True)
 assert check.match(pad(.7999,math.sqrt(1-.7999**2))).state=='UNKNOWN'
 assert check.match(pad(.8,.6)).state=='KNOWN'
 assert check.match(pad(.8001,math.sqrt(1-.8001**2))).state=='KNOWN'
 q=(.8,.6);other=.72;z=math.sqrt(1-other*other)
 check.enroll('synthetic-other','synthetic other',pad(other*q[0]-z*q[1],other*q[1]+z*q[0]),consent=True)
 assert check.match(pad(*q)).state=='AMBIGUOUS';check.close()
 gate=EnrollmentSampling(.8,.1,lambda:1000);gate.candidate={'embedding':pad(1.,0.)}
 assert not gate.usable(pad(.7999,math.sqrt(1-.7999**2)),None)
 assert gate.usable(pad(.8,.6),.69) and not gate.usable(pad(.8,.6),.71)
 cfg=dict(cfg,database=str(Path(directory)/'public.sqlite'))
 extractor=CameraFaceExtractor(cfg,face_targets=True)
 store=IdentityStore(cfg['database'],cfg['model_id'],128,.8,.1,allow_cross_thread=True);os.chmod(cfg['database'],0o600)
 clock=[1000];fid=0;state=CameraState('public-trial-boot','public-trial-service',clock=lambda:clock[0])
 service=IdentityService(store,lambda:extractor,state.identity_target,lock=state.lock,
   clock=lambda:clock[0],result_ttl_ms=cfg['result_ttl_ms'],multi_frame=True,backend='WINDOWS_CPU_SFACE_ORT')
 service.ready=True;state.identity=service
 detector=YuNetCompat(cfg['face_model'],score_threshold=cfg['minimum_face_score'],input_size=cfg['input_size'])
 targets=FaceTargetService(lambda:detector,service.offer_face,state.camera_epoch,lock=state.lock,clock=lambda:clock[0])
 targets.ready=True;service.face_targets=targets
 image=cv2.imread('/home/root/aura-adaptation-20261006/identity/reference/lena.jpg');assert image is not None
 image=cv2.resize(image,(640,480))
 def feed(source):
  global fid
  fid+=1;clock[0]+=700;state.captured(clock[0]);targets.process((source,fid,clock[0]),detector)
  packet,service.pending=service.pending,None
  if packet:service.process(packet,extractor)
 try:
  for _ in range(3):feed(image)
  flow=VoiceEnrollment(state.boot,state.snapshot,state.command,simple=True,now_ms=lambda:clock[0],clock=lambda:clock[0]/1000)
  assert flow.handle('帮我登记身份我叫测试访客',state.snapshot())['code']=='prepare_name'
  assert flow.handle('确认登记',state.snapshot())['code']=='sample_auto'
  for _ in range(27):feed(image)
  assert state.snapshot()['modules']['identity']['enrollment_sampling']['counts']=={'collect':10,'validate':5}
  replies=[];flow.guide(lambda reply,final:replies.append((reply['code'],final)))
  assert replies==[('registered',True)] and store.revision==1
  for _ in range(2):feed(image)
  assert state.snapshot()['modules']['identity']['state']=='KNOWN'
  feed(image*0);assert state.snapshot()['modules']['identity']['state']=='UNKNOWN'
 finally:service.close()
print(json.dumps({'status':'PASS_080_BOUNDARY_MARGIN_PUBLIC_REAL_MODEL_AUTOMATIC_SAVE_AND_LOSS',
 'threshold':.8,'ambiguity_margin':.1,'threshold_boundary_and_margin_checked':True,
 'public_image_only':True,'logical_capture_clock':True,'quality_or_pose_injected':False,
 'user_database_accessed':False,'camera_opened':False,'photos_saved':False}))
""".replace('TRIAL',repr(str(trial)))
run=subprocess.run(['python3','-B','-c',probe],cwd=root/'aura',
 env=dict(os.environ,PYTHONPATH=str(root/'aura'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=100)
(backup/'preflight.log').write_text(run.stdout+run.stderr)
report={'client_date':'2026-10-19','authorization':'用户同意下一轮试用0.80',
 'old_threshold':.85,'new_threshold':.8,'ambiguity_margin':.1,'backup':str(backup),
 'identity_config':str(identity_path),'preserved_parameters':preserved,'preflight_passed':run.returncode==0,
 'preflight_log':run.stdout+run.stderr,'status':'PREFLIGHT_FAILED','camera_before':before,
 'ui_restarted':False,'pc_model_services_restarted':False,'field_accuracy_calibrated':False,
 'database_before':db_before,'templates_exported':False,'photos_accessed':False}
def atomic(raw):
 temp=identity_path.with_name(identity_path.name+'.threshold-080-tmp')
 temp.write_bytes(raw);temp.chmod(0o644);os.replace(temp,identity_path)
if run.returncode==0:
 try:
  idle();assert counts()==db_before and identity_path.read_bytes()==old
  subprocess.run(['systemctl','stop','aura-camera-ui.service'],check=True,timeout=30)
  atomic(new);subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],check=True,timeout=15)
  deadline=time.monotonic()+70
  while time.monotonic()<deadline:
   try:
    after=get(8790,'/health');view=get(8790,'/v1/ui/status')
    if (after['identity']['ready'] and after.get('capture_frames',0)>4 and not after['camera_error']
       and not after['detector_error'] and not after['identity']['error']):break
   except (OSError,ValueError,KeyError):pass
   time.sleep(.3)
  else:raise RuntimeError('Camera did not become ready after threshold reload')
  args=Path('/proc/%d/cmdline'%after['pid']).read_bytes().decode().split('\0')
  assert Path(args[args.index('--config')+1])==camera_path and identity_path.read_bytes()==new
  assert after['pid']!=before['pid'] and after['board_boot_id']==before['board_boot_id']
  assert after['detector']==before['detector'] and after['identity']['backend']=='WINDOWS_CPU_SFACE_ORT'
  assert counts()==db_before and hashlib.sha256(db.read_bytes()).hexdigest()==db_hash
  assert camera_path.read_bytes()==camera_raw
  assert subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)==unit
  assert subprocess.check_output(['systemctl','show','aura-avatar-ui.service','--property=MainPID','--value'],text=True).strip()==ui_pid
  assert view['modules']['identity']['people']==[] and view['modules']['identity']['db_version']==13
  assert view['modules']['identity']['enrollment_sampling']['stage']=='idle';idle()
  report.update(status='THRESHOLD_080_LOADED_AWAITING_REAL_USER_TRIAL',camera_after=after,
   database_after=counts(),database_hash_unchanged=True,registered_count=0,
   identity_config_sha256=hashlib.sha256(new).hexdigest(),active_code_sha256=c['files'])
 except Exception as exc:
  subprocess.run(['systemctl','stop','aura-camera-ui.service'],capture_output=True,timeout=30)
  atomic(old);subprocess.run(['systemctl','start','--no-block','aura-camera-ui.service'],capture_output=True,timeout=15)
  report.update(status='THRESHOLD_080_ROLLED_BACK',error=type(exc).__name__+': '+str(exc))
report['pc_after']=get(8792,'/health','192.168.50.1')
(backup/'activation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('CANDIDATE',repr(c),1)
r=json.loads(ssh('python3 -B -',remote,timeout=240))
(HERE/'threshold_080_preflight.log').write_text(r.pop('preflight_log'),encoding='utf-8')
(HERE/'threshold_080_activation.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in r.items() if key not in ('camera_before','camera_after','pc_after','active_code_sha256')},ensure_ascii=True))
assert r['status']=='THRESHOLD_080_LOADED_AWAITING_REAL_USER_TRIAL'
path=ROOT/'aura/config/board_identity.json';old=path.read_bytes();cfg=json.loads(old)
assert cfg['threshold']==.85
folder=HERE/'before';folder.mkdir(exist_ok=True);(folder/'board_identity.local.json').write_bytes(old)
cfg.update(threshold=.8,threshold_origin='user_authorized_experimental_cosine_0.80_not_field_calibrated')
path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
