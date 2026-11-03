"""Fresh metadata only. No device commands, services or private data access."""
import hashlib,json,subprocess,time,http.client
from pathlib import Path
P=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def owner(pid):
 p=Path('/proc')/str(pid)
 return dict(pid=int(pid),birth_ticks=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(p/'cmdline'))
def unit(name):
 r=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,KillMode,SendSIGKILL,TimeoutStopUSec,ControlGroup,ExecStart'],capture_output=True,text=True,timeout=5,check=True)
 return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
def state():
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:
  c.request('GET','/api/state');r=c.getresponse();assert r.status==200
  b=r.read(1048577);assert len(b)<=1048576
  return json.loads(b)
 finally:c.close()
def project(s):
 # State schema/key inventory only, never export texts, names or file contents.
 out={'top_keys':list(s)}
 for k in ('phase','state','page','ui_page','playing','paused','audio_time','runtime_fault_count','avatar_display'):
  if k in s:out[k]=s[k]
 for k in ('handsfree','handsfree_dialogue','automatic_conversation','local_transcription','motion','pan','pan_face','face_follow','board_business','character_pair','portrait'):
  v=s.get(k)
  if isinstance(v,dict):
   out[k]={x:y for x,y in v.items() if x in ('phase','state','enabled','microphone_open','playing','paused','automatic_following','following','can_start','active','ready','runtime_fault_count','pending_count','request_pending','page','avatar_visible','production_selected','status')}
   out[k+'_keys']=list(v)
 return out
raw=P.read_bytes();cfg=json.loads(raw);rt=Path(cfg['runtime'])/'aura'
assert rt.is_dir()
pins=cfg['component_sha256'];bad=[k for k,v in pins.items() if sha(rt/k)!=v]
u=unit('aura-avatar-ui.service');c=unit('aura-camera-ui.service')
children=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  a=p.joinpath('stat').read_text().rsplit(')',1)[1].split()
  if a[1]==u['MainPID']:children.append(owner(int(p.name)))
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
result=dict(host_clock_not_assumed=True,board_monotonic=time.monotonic(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),startup_path=str(P),startup_sha256=hashlib.sha256(raw).hexdigest(),runtime=str(rt),component_count=len(pins),bad_pins=bad,component_sha256=pins,gui_unit=u,camera_unit=c,gui_owner=owner(u['MainPID']) if int(u['MainPID']) else None,camera_owner=owner(c['MainPID']) if int(c['MainPID']) else None,gui_children=children,state=project(state()))
result['native_build_paths']={str(p):p.exists() for p in (Path('/home/root/aura-yuki-validation-20261030/native_integration'),Path('/home/root/aura-yuki-validation-20261030/probe_build/gles2_capture.py'))}
result['state_after']=project(state())
print(json.dumps(result))
