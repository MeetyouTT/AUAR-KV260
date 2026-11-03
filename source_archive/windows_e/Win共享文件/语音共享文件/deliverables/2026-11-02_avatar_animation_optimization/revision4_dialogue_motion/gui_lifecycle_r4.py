"""Freshly bound, single-submission original normal GUI lifecycle."""
from pathlib import Path
import argparse,hashlib,json,http.client,subprocess,time,os
HERE=Path(__file__).resolve().parent
E=json.loads((HERE/'expected.json').read_bytes())
P=Path(E['startup_path']);R=Path(E['runtime'])
PROPS='MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,KillMode,SendSIGKILL,TimeoutStopUSec'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def unit(n):
 r=subprocess.run(['systemctl','show',n,'--property='+PROPS],capture_output=True,text=True,check=True,timeout=5)
 return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
def owner(pid):
 p=Path('/proc')/str(pid)
 return dict(pid=int(pid),birth_ticks=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(p/'cmdline'))
def camera():
 u=unit('aura-camera-ui.service');assert u['MainPID']==str(E['camera_owner']['pid']) and u['ActiveState']=='active' and not u['Job'];assert owner(u['MainPID'])==E['camera_owner'];return u
def create(p,raw,mode=0o600):
 p.parent.mkdir(parents=True,exist_ok=True)
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def save(p,x):create(p,(json.dumps(x,sort_keys=True,indent=2)+'\n').encode())
def get():
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:
  c.request('GET','/api/state');r=c.getresponse();v=json.loads(r.read(1048576));assert r.status==200;return v
 finally:c.close()
def closure():
 raw=P.read_bytes();cfg=json.loads(raw);assert Path(cfg['runtime'])/'aura'==R
 assert len(cfg['component_sha256'])==380
 assert all(sha(R/k)==h for k,h in cfg['component_sha256'].items())
 return raw,cfg
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['stop','start']);p.add_argument('--label',required=True);a=p.parse_args()
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id'];camera()
 raw,cfg=closure();u=unit('aura-avatar-ui.service')
 if a.action=='stop':
  assert hashlib.sha256(raw).hexdigest()==E['startup_sha256']
  assert u['MainPID']==str(E['gui_owner']['pid']) and u['ActiveState']=='active' and not u['Job']
  for key in ('gui_owner','camera_owner'):assert owner(E[key]['pid'])==E[key]
  gtk=E['gui_children'][0];assert owner(gtk['pid'])==gtk
  for _ in range(3):
   s=get();h=s['handsfree_dialogue'];b=s['board_business'];d=b.get('dialogue') or {};sp=b.get('speaker') or {}
   assert s['phase']=='IDLE' and not s['playing'] and not s['pending_job']
   assert h['enabled'] is False and h['microphone_open'] is False
   assert s['manual_pan']['automatic_following'] is False
   assert not (d.get('voice_enrollment') or {}).get('active') and not sp.get('active') and sp.get('queued_or_active')==0
   time.sleep(.3)
  pref=json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes());assert pref=={'version':1,'enabled':False}
  backup=HERE/'backup';backup.mkdir(exist_ok=False)
  create(backup/'startup.json',raw)
  for name in ('tools/libaura_yuki.so','config/yuki_pair.formal.json','tools/formal_yuki.py','config/board_avatar_gtk.json','tools/native_yuki.py'):
   source=R/name;create(backup/name,source.read_bytes(),source.stat().st_mode&0o777)
  env={}
  for item in Path('/proc',str(gtk['pid']),'environ').read_bytes().split(b'\0'):
   k,sep,v=item.partition(b'=')
   if sep and k in (b'DISPLAY',b'XAUTHORITY'):env[k.decode()]=os.fsdecode(v)
  save(HERE/'display_environment.json',env)
  guard_path=Path('/run/systemd/system/aura-avatar-ui.service.d')/('zzzzzz-animation-'+HERE.name+'.conf')
  guard=b'[Service]\nKillMode=process\nSendSIGKILL=no\nTimeoutStopSec=infinity\n'
  assert not guard_path.exists()
  save(HERE/('STOP_INTENT_'+a.label+'.json'),dict(startup_sha256=sha(P),gui_before=u,camera_before=camera(),gui_owner=E['gui_owner'],gtk_owner=gtk,guard_path=str(guard_path),single_submission=True,force_kill=False))
  create(guard_path,guard)
  subprocess.run(['systemctl','daemon-reload'],check=True,timeout=7)
  guarded=unit('aura-avatar-ui.service');assert guarded['MainPID']==u['MainPID'] and guarded['KillMode']=='process' and guarded['SendSIGKILL']=='no' and guarded['TimeoutStopUSec']=='infinity'
  assert P.read_bytes()==raw;camera()
  subprocess.run(['systemctl','stop','--no-block','aura-avatar-ui.service'],check=True,timeout=7)
  deadline=time.monotonic()+22
  while time.monotonic()<deadline:
   after=unit('aura-avatar-ui.service')
   if after['MainPID']=='0' and after['ActiveState']=='inactive' and not after['Job']:break
   time.sleep(.4)
  stopped=after['MainPID']=='0' and after['ActiveState']=='inactive' and after['SubState']=='dead' and not after['Job']
  result=dict(status='GUI_NORMAL_STOPPED' if stopped else 'GUI_STOP_PENDING_NO_FORCE',gui=after,camera_owner=owner(E['camera_owner']['pid']),original_GUI_properties={k:u[k] for k in ('Restart','KillMode','SendSIGKILL','TimeoutStopUSec')},saved_listening=pref,stage=str(HERE),startup_sha256=sha(P),normal_stop_sent_once=True)
  if stopped:
   assert after['Result']=='success' and after['ExecMainStatus']=='0'
   for own in (E['gui_owner'],gtk):
    q=Path('/proc')/str(own['pid']);assert not q.exists() or q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]!=own['birth_ticks']
   assert guard_path.read_bytes()==guard;guard_path.unlink();subprocess.run(['systemctl','daemon-reload'],check=True,timeout=7)
   restored=unit('aura-avatar-ui.service');assert all(restored[k]==v for k,v in result['original_GUI_properties'].items())
   result['original_properties_restored']=True
  camera();save(HERE/('STOP_RESULT_'+a.label+'.json'),result);print(json.dumps(result));return
 stop=json.loads((HERE/'STOP_RESULT_original.json').read_bytes());assert stop['status']=='GUI_NORMAL_STOPPED' and stop['original_properties_restored']
 assert u['MainPID']=='0' and u['ActiveState']=='inactive' and u['SubState']=='dead' and not u['Job']
 assert all(u[k]==v for k,v in stop['original_GUI_properties'].items())
 assert sha(P) in (E['startup_sha256'],json.loads((HERE/'PUBLICATION.json').read_bytes())['startup_after'] if (HERE/'PUBLICATION.json').exists() else '')
 save(HERE/('START_INTENT_'+a.label+'.json'),dict(startup_sha256=sha(P),component_count=380,single_submission=True,camera_owner=E['camera_owner']))
 camera();subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,timeout=7)
 time.sleep(1)
 result=dict(status='GUI_NORMAL_START_SUBMITTED_ONCE',unit=unit('aura-avatar-ui.service'),startup_sha256=sha(P),camera_owner=owner(E['camera_owner']['pid']),single_submission=True)
 save(HERE/('START_RESULT_'+a.label+'.json'),result);print(json.dumps(result))
if __name__=='__main__':main()
