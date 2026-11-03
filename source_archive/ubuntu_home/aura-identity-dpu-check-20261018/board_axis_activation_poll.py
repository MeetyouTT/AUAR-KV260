"""Read the finite no-PWM activation transaction status; no MMIO."""
import base64
import hashlib
import json
from pathlib import Path

root = Path('/home/root/aura-pan-follow-20261020/activation-axis-04')
value = {'transaction': str(root), 'exists': root.exists()}
for name in ['phase', 'result', 'rollback']:
    path = root/(name+'.json')
    if path.exists():
        value[name] = json.loads(path.read_text())
if 'result' not in value:
    path = root/'worker.log'
    if path.exists():
        value['worker_log_tail'] = path.read_text(errors='replace')[-1500:]
path = root/'failure-traceback.txt'
if path.exists():
    value['failure_traceback'] = path.read_text()[-2000:]
print(json.dumps(value), flush=True)
