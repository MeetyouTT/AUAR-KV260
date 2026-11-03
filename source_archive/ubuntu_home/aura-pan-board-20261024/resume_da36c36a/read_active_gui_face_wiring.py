import ast,json,re,subprocess
from pathlib import Path
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)
root=json.loads(Path(re.search(r'--config (/[^ ;]+)',raw).group(1)).read_text());A=Path(root['runtime'])/'aura';pins=root['component_sha256']
names=sorted(n for n in pins if n.endswith('.py') and any(k in n.lower() for k in ('avatar','native','bridge','pan','command','canvas')))
rows=[]
for n in names:
 p=A/n
 if not p.is_file():continue
 t=p.read_text(errors='replace');m=ast.parse(t)
 ids=sorted({x.id for x in ast.walk(m) if isinstance(x,ast.Name) and x.id in ('FacePanProcess','face_pan_controls','pan_face_follow','allowed_commands')})
 if ids:rows.append({'path':n,'sha256':pins[n],'face_follow_identifiers':ids,'lines':len(t.splitlines())})
with subprocess.Popen(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],stdout=subprocess.PIPE,text=True) as p:pid=p.stdout.read().strip()
import urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
print(json.dumps({'gui_pid':pid,'runtime_root':str(A),'component_pin_count':len(pins),'relevant_files':rows,
 'ui_page':u.get('ui_page'),'manual_pan_keys':sorted(u['manual_pan']),'face_follow_state':u['manual_pan'].get('face_follow'),
 'error':u['manual_pan'].get('error'),'motor_commands':0,'MMIO_opened':False},ensure_ascii=False))
