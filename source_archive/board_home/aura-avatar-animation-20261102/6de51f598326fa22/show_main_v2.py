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

e=json.loads(Path(__file__).with_name('expected.json').read_bytes())
assert sha(P)==e['startup_sha256'] and owner(e['gui_owner']['pid'])==e['gui_owner'] and owner(e['camera_owner']['pid'])==e['camera_owner']
s=state();assert not s['playing'] and not s['pending_job'] and s['manual_pan']['automatic_following'] is False
assert s['handsfree_dialogue']['enabled'] is False and s['handsfree_dialogue']['microphone_open'] is False
before=s['ui_page'];sent=False
if before!='main':
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:
  c.request('POST','/api/command',json.dumps({'type':'ui_page','page':'main'}),{'Content-Type':'application/json','Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783'})
  r=c.getresponse();raw=r.read(1048576);assert r.status==200;sent=True
 finally:c.close()
for _ in range(15):
 s=state()
 if s['ui_page']=='main' and s['avatar_display']['visible'] is True:break
 time.sleep(.2)
assert s['ui_page']=='main' and s['avatar_display']['visible'] is True
print(json.dumps(dict(status='MAIN_CHARACTER_VISIBLE',before_page=before,after_page=s['ui_page'],page_request_sent_once=sent,listening_enabled=s['handsfree_dialogue']['enabled'],no_audio_axis_camera_or_model_request=True)))
