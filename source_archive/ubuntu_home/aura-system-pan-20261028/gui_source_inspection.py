import hashlib,json
from pathlib import Path
g=Path('/home/root/aura-windows-portrait-20261027/handoff-31b0c262c5b74d52966c00b978dfef3f/runtime/aura')
d={}
for n in ['board/motion/manual_vsrv.py','board/motion/current_reference_release.py','board/motion/face_process.py','board/motion/face_pan_process.py','board/motion/manual_process.py']:
 p=g/n
 if p.exists():d[n]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':p.read_text()}
print(json.dumps(d))
