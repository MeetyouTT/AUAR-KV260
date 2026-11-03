import json,subprocess
from pathlib import Path
p=Path('/home/root/aura-native-wait-20261023/recovery/cdb172e26c91629f/report.json')
r=json.loads(p.read_text()) if p.exists() else None
print(json.dumps({'report':r,'unit_state':subprocess.check_output(['systemctl','show','aura-availability-recovery-cdb172e26c91629f.service','-p','ActiveState','--value']).decode().strip()}))
