import json,subprocess
from pathlib import Path
w=Path('/home/root/kv260-runtime-live-20261003T082232Z')
print('STATUS', (w/'controller-status.json').read_text())
logs=list((w/'logs').glob('*-kernel.log'))
for p in logs:
 lines=p.read_text().splitlines();print('KERNEL',p.name,len(lines),len(p.read_bytes()),'FIRST',lines[:3],'LAST',lines[-6:])
b=next(p for p in logs if 'before-original-remove-kernel' in p.name).read_text().splitlines()
a=next(p for p in logs if 'after-original-remove-kernel' in p.name).read_text().splitlines()
anchor=b[-16:];matches=[i+16 for i in range(len(a)-15) if a[i:i+16]==anchor]
print('ANCHOR_END_INDEXES',matches)
if matches:print('NEW_LINES',json.dumps(a[matches[-1]:],indent=2))
print('CANDIDATE_LOG_EXISTS',(w/'candidate-manager.log').exists())
print('CURRENT',subprocess.check_output(['dfx-mgr-client','-listPackage'],text=True))
print('DRIVER',Path('/sys/module/zocl/srcversion').read_text())
