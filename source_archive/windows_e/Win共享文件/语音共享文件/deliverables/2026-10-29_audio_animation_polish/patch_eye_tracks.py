"""Keep current registered blink geometry when selecting emotional body assets."""
from pathlib import Path
H=Path(__file__).resolve().parent
old="self.overlay('idle_normal',t,meta.get('body_index',0),pose=meta['body_face_matrix'])"
new="self.overlay(meta.get('body_asset','idle_normal'),t,meta.get('body_index',0),pose=meta['body_face_matrix'])"
for relative in ('candidate/board/tools/facial_layers.py','candidate/renderer_snapshot/tools/facial_layers.py'):
 path=H/relative;source=path.read_text(encoding='utf-8');assert source.count(old)==1,relative
 source=source.replace(old,new);compile(source,str(path),'exec');path.write_text(source,encoding='utf-8')
print('Current pose-aware blink handling extended to the actual selected body')
