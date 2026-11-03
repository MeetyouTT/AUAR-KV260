import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-native-wait-20261023/9a06d89a2899f6ff')
report=json.loads((root/'report.json').read_text()) if (root/'report.json').exists() else None
print(json.dumps({'report':report,'unit_state':subprocess.check_output(['systemctl','show','aura-native-probe-check-9a06d89a2899f6ff.service','-p','ActiveState','--value']).decode().strip()}))
