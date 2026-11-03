"""Inspect the exact two active GUI sources before applying a guarded patch."""
import hashlib,json
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');cfg=json.loads((N/'startup/config.json').read_text());root=Path(cfg['runtime'])/'aura';rows=[]
for name in ('tools/board_camera_preview.py','tools/board_avatar_gtk.py'):
 p=root/name;raw=p.read_bytes();lines=raw.decode().splitlines();snips=[]
 for i,line in enumerate(lines):
  if ('preview_image.set_visible' in line or 'deadline=' in line or 'preview_placeholder.set_visible' in line or 'frame_visible' in line and 'image=' in line):
   snips.append({'line':i+1,'text':'\n'.join(lines[max(0,i-3):i+4])})
 rows.append({'name':name,'sha256':hashlib.sha256(raw).hexdigest(),'expected':cfg['component_sha256'][name],'snippets':snips})
print(json.dumps({'sources':rows,'backup_files':[str(p.relative_to(N)) for p in (N/'preview-fix-backup').rglob('*') if p.is_file()]}))
