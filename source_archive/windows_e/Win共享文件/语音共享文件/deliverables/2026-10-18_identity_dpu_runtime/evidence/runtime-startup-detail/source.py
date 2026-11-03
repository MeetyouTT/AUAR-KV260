import base64,hashlib,json,subprocess,urllib.request
from pathlib import Path
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
old=Path('/home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b')
report={'status':'READ_ONLY_STARTUP_DETAIL','artifacts':{},'logs':{}}
for name,path in [('actual-launcher.py',old/'startup/launcher.py'),('actual-startup-config.json',old/'startup/config.json')]:
 data=path.read_bytes();report['artifacts'][name]={'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
for label,base in [('old',old),('candidate',root/'candidate')]:
 for rel in ['runtime/stage.log','runtime/launch.json']:
  path=base/rel
  if not path.exists():continue
  text=path.read_text(errors='replace')[-12000:]
  if rel.endswith('.log'):
   lines=[l for l in text.splitlines() if l.startswith(('Traceback','  File ','    ','RuntimeError:','ValueError:','FileNotFoundError:','ModuleNotFoundError:','TypeError:','PermissionError:','OSError:'))]
   report['logs'][label]=lines[-30:]
  else:
   value=json.loads(text);report['logs'][label+'_launch']={k:value.get(k) for k in ('pid','supervisor_pid','log','session')}
try:
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as response:ui=json.load(response)
 report['ui']={k:ui.get(k) for k in ('ui_page','phase','playing','automatic_conversation')}
except Exception as exc:report['ui_error']=str(exc)
report['supervisor']=subprocess.run(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState'],stdout=subprocess.PIPE,text=True,timeout=5).stdout
print(json.dumps(report),flush=True)
