"""Export fix status and live pan state without issuing movement."""
import base64,gzip,hashlib,json,subprocess,urllib.request
from pathlib import Path
p=Path('/home/root/aura-pan-manual-ui-20261020/fix-v2');value={'deployment_complete':(p/'deployment-result.json').is_file(),'artifacts':{}}
for n in ['deployment-result.json','board-tests.txt','failure-traceback.txt','regression.json']:
 q=p/n
 if q.is_file():
  raw=gzip.compress(q.read_bytes(),mtime=0);value['artifacts'][n+'.gz']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
if value['deployment_complete']:value['deployment']=json.loads((p/'deployment-result.json').read_text())
value['unit']={k:subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p',k,'--value'],text=True).strip() for k in ['ActiveState','MainPID','WorkingDirectory']}
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with opener.open('http://127.0.0.1:8783/api/state',timeout=1) as r:s=json.load(r)
 value['ui']={k:s.get(k) for k in ['phase','playing','ui_page','manual_pan','ui_tick_ms']}
except Exception as e:value['ui']={'unavailable':type(e).__name__}
print(json.dumps(value),flush=True)
