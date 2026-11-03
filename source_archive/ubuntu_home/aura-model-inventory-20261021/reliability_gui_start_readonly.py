import json,subprocess
from pathlib import Path
out={'read_only':True}
out['service']=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ActiveState','-p','SubState','-p','MainPID','-p','ControlPID','-p','Result','-p','ExecMainCode','-p','ExecMainStatus'],timeout=5).decode().strip()
r=subprocess.run(['journalctl','-u','aura-avatar-ui.service','-n','20','-o','json','--no-pager'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=8)
events=[]
for line in r.stdout.splitlines():
 try:d=json.loads(line);m=d.get('MESSAGE','')
 except ValueError:continue
 if any(k in m.lower() for k in ('failed','error','exception','traceback','starting','started','stopped','timeout','mismatch','unavailable')):
  events.append({'mono_us':d.get('__MONOTONIC_TIMESTAMP'),'message':m[:400]})
out['filtered_events']=events
print(json.dumps(out))
