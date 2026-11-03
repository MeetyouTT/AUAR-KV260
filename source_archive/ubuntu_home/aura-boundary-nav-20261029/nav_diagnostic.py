import json,subprocess,urllib.request
from pathlib import Path
d={}
for p in ['/run/aura-face-zone-last-page.json','/home/root/aura-pan-wide-resume-20261029/55152f95/face-zone-display-status.json']:
 q=Path(p);d[p]=json.loads(q.read_text()) if q.exists() else None
d['editor_journal']=subprocess.check_output(['journalctl','-u','aura-face-zone-editor.service','-n','30','--no-pager','-o','cat'],text=True)[-10000:]
d['editor_unit']=subprocess.check_output(['systemctl','show','aura-face-zone-editor.service','-p','MainPID','-p','ActiveState'],text=True)
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
d['ui']={'page':u['ui_page'],'manual_state':u['manual_pan']['state'],'range':[u['manual_pan']['minimum_us'],u['manual_pan']['maximum_us']]}
print(json.dumps(d))
