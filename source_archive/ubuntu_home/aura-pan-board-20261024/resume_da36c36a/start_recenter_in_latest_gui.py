import hashlib,json,time,urllib.request
import subprocess
from pathlib import Path
G=Path('/home/root/aura-pan-current-20261024/da36c36a/gui-reference-bound-v2');A=G/'runtime/aura'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
cfg=json.loads((G/'startup/config.json').read_text());assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
face=json.loads((A/'config/pan_face.local.json').read_text());assert face['release_root']=='/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v11r1'
assert face['duration_s']==0
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get():
 with op.open(base+'/api/state',timeout=3) as f:return json.load(f)
before=get();h=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with h.open('http://127.0.0.1:8790/health',timeout=3) as f:health=json.load(f)
m=before['manual_pan'];r=m.get('readback') or {}
assert before['phase']=='IDLE' and not before.get('playing') and before.get('audio_output_state')=='IDLE_READY'
assert health['pid']==375319 and not health['dpu_schedule']['owner_fenced'] and health['identity']['ready']
assert m['state']=='READY' and not m['automatic_following'] and r.get('flags')==0 and r.get('lease_left_ms')==0
request=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
with op.open(request,timeout=4) as f:reply=json.load(f)
assert reply.get('ok'),reply
time.sleep(1)
after=get();manual=after['manual_pan'];assert manual['automatic_following']
s=json.loads((Path('/home/root/aura-pan-current-20261024/da36c36a')/'state.json').read_text())
s.update(phase='V11_RECENTER_RUNNING_IN_CURRENT_ANIMATION_GUI',automatic_following=True,current_gui_pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)))
(Path('/home/root/aura-pan-current-20261024/da36c36a')/'state.json').write_text(json.dumps(s,indent=2)+'\n')
f=manual.get('face_follow') or {}
print(json.dumps({'status':s['phase'],'start_reply':reply,'camera_pid':health['pid'],'gui_pid':s['current_gui_pid'],
 'mode':f.get('state'),'reason':f.get('reason'),'message':manual.get('message'),
 'automatic_following':manual['automatic_following'],'limits_us':[1400,1600],'duration_s':face['duration_s']}))
