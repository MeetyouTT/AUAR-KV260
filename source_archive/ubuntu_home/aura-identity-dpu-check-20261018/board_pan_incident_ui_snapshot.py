"""Inspect changed GUI version and the safety lock; never reconnect or ARM."""
import base64,gzip,hashlib,json,os,subprocess,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));v={}
try:
 with op.open('http://127.0.0.1:8783/api/state',timeout=1) as r:s=json.load(r)
 v['ui']={k:s.get(k) for k in ['phase','playing','ui_page','sequence','ui_tick_ms','manual_pan','error']}
except Exception as e:v['ui']={'unavailable':type(e).__name__}
p=Path('/home/root/aura-pan-incident-20261020');v['interlock']=json.loads((p/'lock-status.json').read_text())
pid=v['interlock']['pid'];v['interlock_live']=str(p/'lock_guard.py').encode() in Path('/proc/%d/cmdline'%pid).read_bytes()
root=Path(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','WorkingDirectory','--value'],text=True).strip())
v['hashes']={rel:hashlib.sha256((root/rel).read_bytes()).hexdigest() for rel in ['board/motion/manual.py','board/motion/manual_process.py','board/motion/manual_vsrv.py','tools/pan_controls.py','tools/board_avatar_gtk.py','tools/native_pixels.cpp','tools/native_pixels.py','tools/native_video.py','tools/libaura_pixels.so']}
candidate=Path('/home/root/aura-render24-rgb565-20261020/887c4b6b2b5d')
v['candidate_files']=[{'name':str(q.relative_to(candidate)),'bytes':q.stat().st_size} for q in candidate.glob('*') if q.is_file()]
v['json_keys']={}
for q in candidate.glob('*.json'):
 try:
  data=json.loads(q.read_text());v['json_keys'][q.name]=list(data) if isinstance(data,dict) else type(data).__name__
 except (ValueError,OSError):pass
v['artifacts']={}
for rel in ['startup/config.json','startup/launcher.py']:
 q=candidate/rel
 if q.is_file():
  raw=gzip.compress(q.read_bytes(),mtime=0);v['artifacts'][rel.replace('/','__')+'.gz']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
with op.open('http://127.0.0.1:8790/health',timeout=1) as r:s=json.load(r)
v['camera']={k:s.get(k) for k in ['pid','capture_hz','detection_hz','camera_error','detector_error']}
print(json.dumps(v),flush=True)
