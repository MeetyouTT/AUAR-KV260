"""Export source and filtered runtime errors, no image/identity data."""
import base64,gzip,hashlib,json,subprocess
from pathlib import Path
root=Path(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','WorkingDirectory','--value'],text=True).strip())
paths=['tools/board_camera_preview.py','tools/native_video.py','tools/board_avatar_worker.py','board/vision/local_preview.py','board/interaction/ui_services.py','tools/pan_controls.py','tools/board_avatar_pan.py','tools/realtime_bridge.py']
artifacts={};hashes={}
for rel in paths:
 p=root/rel;data=p.read_bytes();hashes[rel]=hashlib.sha256(data).hexdigest();raw=gzip.compress(data,mtime=0)
 artifacts[rel.replace('/','__')+'.gz']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
errors={}
for name,log in [('gui',root.parent/'stage.log'),('camera',Path('/home/root/aura-handsfree-dialogue-20261020/candidate-0c0a8ab46ec2/runtime/stage.log'))]:
 try:
  lines=log.read_text(errors='replace').splitlines();errors[name]={'bytes':log.stat().st_size,'lines':len(lines),'issues':[s for s in lines if any(w in s.lower() for w in ['traceback','error','critical','warning','failed','exception'])][-80:]}
 except OSError as e:errors[name]=type(e).__name__
print(json.dumps({'root':str(root),'hashes':hashes,'errors':errors,'artifacts':artifacts}),flush=True)
