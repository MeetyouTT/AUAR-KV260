import hashlib,json,subprocess,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ExecStart','--value'],text=True)
paths=[str(p) for p in Path('/home/root').glob('aura-*/**/config/pan_face.local.json') if 'runtime/aura/config/' in str(p)]
found=[]
for name in paths:
 try:
  p=Path(name);d=json.loads(p.read_text());found.append(dict(path=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
    parent_is_execstart= str(p.parents[4]/'startup/launcher.py') in raw,mode=d.get('mode'),
    duration=d.get('duration_s'),manifest_sha256=d.get('manifest_sha256'),release_path=d.get('release_root')))
 except (OSError,ValueError):pass
print(json.dumps({'gui_pid':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip(),
 'face_state':u['manual_pan']['state'],'following':u['manual_pan']['automatic_following'],'face_follow_component':u['manual_pan'].get('face_follow'),
 'gui_command':raw,'matching_configs':found},ensure_ascii=False))
