import json,subprocess
from pathlib import Path
unit='aura-avatar-ui.service'
p=subprocess.run(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus','-p','TimeoutStartUSec'],capture_output=True,text=True)
props=dict(s.split('=',1) for s in p.stdout.splitlines() if '=' in s)
n=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');cfg=json.loads((n/'startup/config.json').read_text())
report={'unit':props,'config_waits':{k:v for k,v in cfg.items() if 'wait' in k or 'timeout' in k},'children':[]}
pid=props.get('MainPID')
if pid and pid!='0':
 for child in (Path('/proc')/pid/'task'/pid/'children').read_text().split():
  p=Path('/proc')/child
  if p.exists():report['children'].append({'pid':int(child),'comm':(p/'comm').read_text().strip()})
j=subprocess.run(['journalctl','-u',unit,'-n','18','--no-pager','-o','cat'],capture_output=True,text=True)
report['startup_lines']=[s[:350] for s in j.stdout.splitlines() if any(k in s for k in ['Traceback','Error','failed','Failed','timeout','Timeout','Waiting','Started','Starting','READY','ready'])][-12:]
report['stage_tail']=(n/'runtime/stage.log').read_text()[-1200:] if (n/'runtime/stage.log').exists() else None
print(json.dumps(report))
