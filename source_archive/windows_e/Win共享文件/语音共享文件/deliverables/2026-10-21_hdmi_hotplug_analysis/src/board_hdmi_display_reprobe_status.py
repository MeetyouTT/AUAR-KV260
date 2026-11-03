"""Read the single background display recovery operation without replaying it."""
import json,subprocess
from pathlib import Path
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
root=Path('/home/root/aura-display-reprobe-20261021')/boot/'once'
v={'boot_id':boot,'driver_writes':0}
for name in ['state.json','result.json','independent-recovery.json']:
 p=root/name
 if p.exists():v[name]=json.loads(p.read_text())
v['driver_bound']=Path('/sys/bus/platform/devices/fd4a0000.display/driver').exists()
v['timer']=subprocess.run(['systemctl','show','aura-display-recover-'+boot[:8]+'.timer','-p','ActiveState','-p','SubState'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5).stdout
print(json.dumps(v),flush=True)
