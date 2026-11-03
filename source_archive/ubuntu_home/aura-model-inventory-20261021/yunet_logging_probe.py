import collections,json,subprocess
from pathlib import Path
out={}
for pid in ['95658','1036']:
 p=Path('/proc')/pid
 if p.exists():out[pid]=p.joinpath('cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')[:600]
data=subprocess.check_output(['journalctl','-n','400','-o','json','--no-pager'],timeout=5)
records=[json.loads(s) for s in data.splitlines()]
out['identifiers']=dict(collections.Counter(s.get('SYSLOG_IDENTIFIER','') for s in records))
out['units']=dict(collections.Counter(s.get('_SYSTEMD_UNIT','') for s in records))
out['timestamps']=[s.get('__REALTIME_TIMESTAMP') for s in records[:1]+records[-1:]]
out['messages']=[]
for s in records:
 if s.get('_SYSTEMD_UNIT')=='aura-camera-ui.service' or s.get('SYSLOG_IDENTIFIER')=='kernel':
  m=s.get('MESSAGE','')[:500]
  if m not in out['messages']:out['messages'].append(m)
  if len(out['messages'])>=10:break
out['unit']=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=5).decode()
print(json.dumps(out))
