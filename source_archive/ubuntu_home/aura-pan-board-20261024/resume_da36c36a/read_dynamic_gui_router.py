import json,re,subprocess,urllib.request
from pathlib import Path
unit=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ExecStart'],text=True)
start=re.search(r'--config (/[^ ;]+)',unit).group(1);cfg=json.loads(Path(start).read_text());a=Path(cfg['runtime'])/'aura'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
manual=u['manual_pan'];cmds={}
for path in (a/'tools/face_pan_controls.py',a/'tools/board_avatar_gtk.py',a/'tools/board_avatar_pan.py'):
 if path.is_file():
  body=path.read_text(errors='replace');cmds[path.name]={k:(k in body) for k in ('pan_face_follow','FacePanProcess','Stage','pan_stop','allowed_commands')}
print(json.dumps({'pid':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip(),
 'unit_exec':unit,'startup_sha256':__import__('hashlib').sha256(Path(start).read_bytes()).hexdigest(),
 'runtime_root':str(a),'pin_count':len(cfg['component_sha256']),'manual_state':manual['state'],
 'automatic_following':manual['automatic_following'],'manual_readback':manual.get('readback'),
 'face_follow':manual.get('face_follow'),'ui_page':u.get('ui_page'),'components':cmds}))
