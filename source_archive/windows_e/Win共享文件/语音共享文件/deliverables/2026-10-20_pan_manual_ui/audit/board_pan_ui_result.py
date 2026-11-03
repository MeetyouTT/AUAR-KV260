"""Read deployment progress/results and live GUI status; never actuates."""
import base64,gzip,hashlib,json,subprocess,urllib.request
from pathlib import Path
p=Path('/home/root/aura-pan-manual-ui-20261020/staged-v1')
result={'deployment_complete':(p/'deployment-result.json').is_file(),'artifacts':{}}
for name in ['deployment-result.json','board-policy-tests.txt','failure-traceback.txt']:
 q=p/name
 if q.is_file():
  raw=gzip.compress(q.read_bytes(),mtime=0);result['artifacts'][name+'.gz']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
if result['deployment_complete']:
 value=json.loads((p/'deployment-result.json').read_text());result['deployment']={k:v for k,v in value.items() if k!='baseline'}
result['unit']={k:subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p',k,'--value'],text=True).strip() for k in ['ActiveState','MainPID','WorkingDirectory','ExecStart']}
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with opener.open('http://127.0.0.1:8783/api/state',timeout=1) as r:value=json.load(r)
 result['ui']={k:value.get(k) for k in ['phase','playing','ui_page','ui_layer','manual_pan','backend']}
except Exception as exc:result['ui']={'unavailable':type(exc).__name__}
print(json.dumps(result),flush=True)
