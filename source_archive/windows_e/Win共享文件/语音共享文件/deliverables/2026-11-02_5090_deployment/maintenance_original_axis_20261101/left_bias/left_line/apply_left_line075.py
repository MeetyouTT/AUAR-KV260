import copy,datetime,hashlib,http.client,json,os,stat,subprocess,time,uuid
from pathlib import Path
B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');A=B/'runtime/aura';S=B/'startup/config.json';F=A/'config/pan_face.local.json'
Z=Path('/home/root/aura-pan-wide-resume-20261029/55152f95/face-zone-settings.json')
T=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-follow-leftline075-v1')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encode(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def sync(p):
 f=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(f)
 finally:os.close(f)
def create(p,data,mode=0o600):
 f=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
 with os.fdopen(f,'wb') as w:w.write(data);w.flush();os.fsync(w.fileno())
 sync(p.parent)
def replace(p,old,new):
 st=p.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_uid==0 and p.read_bytes()==old
 temp=p.with_name('.'+p.name+'.left075-'+uuid.uuid4().hex+'.tmp');create(temp,new,stat.S_IMODE(st.st_mode))
 assert p.read_bytes()==old
 os.replace(temp,p);sync(p.parent)
def unit(name):
 r=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job'],capture_output=True,text=True,timeout=4)
 assert r.returncode==0
 return dict(v.split('=',1) for v in r.stdout.splitlines() if '=' in v)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
assert sha(S)=='ff7c0599d8b719b66dadee193553b937027de72867f266e1cb443320a9b5dc4e'
assert unit('aura-face-zone-editor.service')=={'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':''}
assert unit('aura-avatar-ui.service')=={'MainPID':'97308','ActiveState':'active','SubState':'running','Job':''}
assert unit('aura-camera-ui.service')=={'MainPID':'79866','ActiveState':'active','SubState':'running','Job':''}
startup=json.loads(S.read_text());assert len(startup['component_sha256'])==380 and all(sha(A/k)==v for k,v in startup['component_sha256'].items())
ui=json.loads((A/'config/board_avatar_gtk.json').read_text());binding=json.loads(Path(ui['board_business']['face_readback']['path']).read_text())
assert len(binding['source_sha256'])==25 and str(Z) not in binding['source_sha256']
assert str(Z) not in json.loads((A/'config/face_gallery_readback.local.json').read_text())['source_sha256']
assert all(sha(k)==v for k,v in binding['source_sha256'].items())
face=json.loads(F.read_text());oldzone=Path(face['arguments']['zone-settings']);zone=json.loads(Z.read_text());other=json.loads(oldzone.read_text())
for k in ('board_boot_id','left_camera_ratio','right_ratio','target_center_ratio','frame_width','frame_height','mirror_horizontal','viewport'):assert zone[k]==other[k]
assert zone['left_camera_ratio']==.1 and zone['right_ratio']==.7158253629442671 and zone['target_center_ratio']==.5
assert face['arguments']['target-center-ratio']=='0.45'
newzone=copy.deepcopy(zone);newzone.update(left_camera_ratio=.075,updated_mono_ms=int(time.monotonic()*1000))
newface=copy.deepcopy(face);newface['arguments']['zone-settings']=str(Z)
newstartup=copy.deepcopy(startup);newstartup['component_sha256']['config/pan_face.local.json']=hashlib.sha256(encode(newface)).hexdigest()
assert {k:v for k,v in newzone.items() if k not in ('left_camera_ratio','updated_mono_ms')}=={k:v for k,v in zone.items() if k not in ('left_camera_ratio','updated_mono_ms')}
assert not T.exists();T.mkdir(mode=0o700);sync(T.parent)
before={Z:Z.read_bytes(),F:F.read_bytes(),S:S.read_bytes()};after={Z:encode(newzone),F:encode(newface),S:encode(newstartup)}
for i,(p,v) in enumerate(before.items()):create(T/(str(i)+'-'+p.name),v)
changed=[]
try:
 for p,v in after.items():changed.append(p);replace(p,before[p],v)
 assert all(sha(A/k)==v for k,v in newstartup['component_sha256'].items())
 assert all(sha(k)==v for k,v in binding['source_sha256'].items())
 assert oldzone.read_bytes()==encode(other) or json.loads(oldzone.read_text())==other
except BaseException:
 for p in reversed(changed):
  if p.read_bytes()==after[p]:replace(p,after[p],before[p])
 raise
record={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'LEFT_LINE075_CONFIGURED_EDITOR_START_PENDING','left_camera_ratio':.075,'previous_left_camera_ratio':.1,'right_ratio':zone['right_ratio'],'stop_target_center_ratio':.45,'white_line_center_ratio':.5,'single_shared_editor_and_controller_settings':str(Z),'historical_controller_zone_preserved':str(oldzone),'startup_after_sha256':sha(S),'face_config_sha256':sha(F),'components_verified':380,'selected_source_pins_verified':25,'changed_component_keys':['config/pan_face.local.json'],'gui_restarted':False,'camera_restarted':False,'editor_only_restarted':True}
create(T/'configured.json',encode(record));create(T/'editor-start-intent.json',encode({'utc':record['utc'],'normal_start_once':True}))
r=subprocess.run(['systemctl','start','--no-block','aura-face-zone-editor.service'],capture_output=True,text=True,timeout=6)
record.update(editor_start_returncode=r.returncode,editor_unit=unit('aura-face-zone-editor.service'))
create(T/'editor-start-requested.json',encode(record));print(json.dumps(record));assert r.returncode==0
