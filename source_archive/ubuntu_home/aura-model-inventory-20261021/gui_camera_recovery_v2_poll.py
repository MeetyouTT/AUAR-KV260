import json, subprocess
from pathlib import Path
p=Path('/home/root/aura-gui-cpu-20261023/recovery/17a9303670780152/report.json')
report=json.loads(p.read_text()) if p.exists() else {}
print(json.dumps({'report':report,'unit_state':subprocess.check_output(['systemctl','show','aura-current-camera-recovery-17a9303670780152.service','-p','ActiveState','--value']).decode().strip()}))
