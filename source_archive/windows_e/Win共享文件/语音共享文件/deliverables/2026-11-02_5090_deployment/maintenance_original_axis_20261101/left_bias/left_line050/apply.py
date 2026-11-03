import datetime,hashlib,http.client,json,os,subprocess,time,uuid
from pathlib import Path
B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');S=B/'startup/config.json';Z=Path('/home/root/aura-pan-wide-resume-20261029/55152f95/face-zone-settings.json');T=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-follow-leftline050-v1')
assert hashlib.sha256(S.read_bytes()).hexdigest()=='bcb773cd5bf306ac536df0373d1c1b27d01b6564a35839f2623b274442c13a59'
assert Path('/proc/97312/stat').read_text().rsplit(')',1)[1].split()[19]=='2695022'
assert Path('/proc/131169/stat').read_text().rsplit(')',1)[1].split()[19]=='2854440'
def request(kind=None):
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:
  if kind:c.request('POST','/api/command',json.dumps({'type':kind}).encode(),{'Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783','Content-Type':'application/json'})
  else:c.request('GET','/api/state')
  r=c.getresponse();v=json.loads(r.read(2097153));assert r.status==200
  return v
 finally:c.close()
def unit():
 r=subprocess.run(['systemctl','show','aura-face-zone-editor.service','--property=MainPID,ActiveState,SubState,Job'],capture_output=True,text=True,timeout=4)
 assert r.returncode==0
 return dict(v.split('=',1) for v in r.stdout.splitlines() if '=' in v)
def create(p,data):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
request('pan_stop');end=time.monotonic()+12
while True:
 p=request()['manual_pan'];rb=p.get('readback') or {}
 if p.get('automatic_following') is False and p.get('state')=='READY' and rb.get('flags')==0 and rb.get('lease_left_ms')==0:break
 assert time.monotonic()<end
 time.sleep(.25)
r=subprocess.run(['systemctl','stop','--no-block','aura-face-zone-editor.service'],capture_output=True,text=True,timeout=6);assert r.returncode==0
end=time.monotonic()+12
while unit()!={'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':''}:
 assert time.monotonic()<end
 time.sleep(.25)
assert not Path('/proc/131169').exists()
old=Z.read_bytes();v=json.loads(old)
assert v['board_boot_id']=='903cfade-b93c-48fa-804e-379be1967313' and v['left_camera_ratio']==.075 and v['right_ratio']==.7158253629442671 and v['target_center_ratio']==.5
face=json.loads((B/'runtime/aura/config/pan_face.local.json').read_text());assert face['arguments']['zone-settings']==str(Z) and face['arguments']['target-center-ratio']=='0.45'
assert not T.exists();T.mkdir(mode=0o700);create(T/'zone.before.json',old)
new=dict(v,left_camera_ratio=.05,updated_mono_ms=int(time.monotonic()*1000));data=(json.dumps(new,indent=2)+'\n').encode()
assert {k:x for k,x in new.items() if k not in ('left_camera_ratio','updated_mono_ms')}=={k:x for k,x in v.items() if k not in ('left_camera_ratio','updated_mono_ms')}
tmp=Z.with_name('.'+Z.name+'.left050-'+uuid.uuid4().hex+'.tmp');create(tmp,data);assert Z.read_bytes()==old;os.replace(tmp,Z)
fd=os.open(Z.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
record={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'left_camera_ratio_before':.075,'left_camera_ratio_after':.05,'right_ratio':v['right_ratio'],'stop_target_center_ratio':.45,'white_line_center_ratio':.5,'startup_sha256':hashlib.sha256(S.read_bytes()).hexdigest(),'only_zone_parameter_changed':True,'gui_camera_models_unchanged':True,'normal_editor_stop_once':True}
create(T/'configured.json',(json.dumps(record,indent=2)+'\n').encode());create(T/'start-intent.json',b'{"normal_editor_start_once":true}\n')
r=subprocess.run(['systemctl','start','--no-block','aura-face-zone-editor.service'],capture_output=True,text=True,timeout=6);assert r.returncode==0
record.update(editor_start_returncode=r.returncode,editor_unit=unit())
print(json.dumps(record))
