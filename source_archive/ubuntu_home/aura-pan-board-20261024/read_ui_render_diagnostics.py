import hashlib,json,subprocess,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');A=N/'runtime/aura';log=(N/'runtime/stage.log').read_text();op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
source=A/'tools/board_avatar_gtk.py';lines=source.read_text().splitlines()
print(json.dumps({'gtk_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'render_errors':[x for x in log.splitlines() if any(t in x for t in ('STAGE ERROR','Traceback','Error:','CRITICAL'))][-20:],
 'preview_source_lines':[x.strip() for x in lines if any(t in x for t in ('preview_placeholder.set_visible','preview_image.set_visible'))],
 'page':u.get('ui_page'),'stage_errors':u.get('stage_errors'),'preview':u['ui_runtime'].get('preview_metrics'),
 'renderer':u.get('avatar_renderer',{}).get('presentation',{}).get('render_owner'),
 'stage_tail':log[-2500:]}))
