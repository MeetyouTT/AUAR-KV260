import hashlib,json
from pathlib import Path
g=Path('/home/root/aura-system-pan-20261028/gui-continuity-v1');root=g/'runtime/aura';d={'startup_sha256':hashlib.sha256((g/'startup/config.json').read_bytes()).hexdigest(),'files':{}}
for p in (root/'board/motion').glob('*.py'):
 d['files'][str(p.relative_to(root))]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':p.read_text()}
for n in ['tools/board_avatar_pan.py','tools/face_pan_controls.py']:
 p=root/n
 if p.exists():d['files'][n]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':p.read_text()}
print(json.dumps(d))
