import json,subprocess,re,urllib.request
from pathlib import Path
e=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
p=Path(re.search(r'--config (\S+) ',e).group(1));root=Path(json.loads(p.read_text())['runtime'])
s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5))
files=sorted((root/'managed-runs').glob('*/evidence/render_performance.jsonl'),key=lambda x:x.stat().st_mtime,reverse=True)
logs=[]
for p in files[:1]:
 rows=[json.loads(line) for line in p.read_text().splitlines()]
 logs.append(dict(path=str(p),records=len(rows),rows=rows[-24:]))
print(json.dumps(dict(runtime=str(root),effective=e,phase=s['phase'],audio=s.get('audio_output_state'),
                     monitor=s['handsfree_dialogue']['enabled'],error=s.get('error'),display=s['avatar_display'],
                     renderer=s['avatar_renderer'],logs=logs)))
