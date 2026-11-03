ROOT='/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4'
PREFIX='aura-pan-vsrv2-1236ccf4'
import json,subprocess
from pathlib import Path
root=Path(ROOT);result={'state':json.loads((root/'trial-state.json').read_text())}
for name in ['manual-restore-result.json','coexistence-window.json','finite-step-result.json']:
 p=root/name
 if p.exists():result[name]=json.loads(p.read_text())
for suffix in ['manual-recovery.service','guard.timer']:
 p=subprocess.run(['systemctl','show',PREFIX+'-'+suffix,'--property=ActiveState,SubState,MainPID,Result,ExecMainStatus'],capture_output=True,text=True)
 result[suffix]=dict(s.split('=',1) for s in p.stdout.splitlines() if '=' in s)
result['firmware_name']=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
print(json.dumps(result))
