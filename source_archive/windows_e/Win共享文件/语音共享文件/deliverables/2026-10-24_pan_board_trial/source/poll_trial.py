BOOT='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
ROOT='/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2'
PREFIX='aura-pan-vsrv2-1236ccf4-r2'
import json,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
root=Path(ROOT);p=root/'trial-state.json'
result={'boot':BOOT,'state':json.loads(p.read_text()) if p.exists() else None}
for name in ['prepared.json','id-stop.json','coexistence-window.json','finite-step-result.json']:
 f=root/name
 if f.exists():result[name]=json.loads(f.read_text())
for name in ['activation','guard.timer','guard.service']:
 unit=PREFIX+'-'+name if '.' in name else PREFIX+'-'+name+'.service'
 q=subprocess.run(['systemctl','show',unit,'--property=ActiveState,SubState,MainPID,Result,ExecMainStatus'],capture_output=True,text=True)
 result[unit]=dict(s.split('=',1) for s in q.stdout.splitlines() if '=' in s)
print(json.dumps(result))
