import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-native-wait-20261023/external/216391c02cc6e719')
report=json.loads((root/'report.json').read_text()) if (root/'report.json').exists() else None
print(json.dumps({'report':report,'unit_state':subprocess.check_output(['systemctl','show','aura-external-sched-216391c02cc6e719.service','-p','ActiveState','--value']).decode().strip()}))
