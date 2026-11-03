import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
p=root/'baseline-restore-result.json'
if p.exists():report=json.loads(p.read_text())
else:
 log=root/'baseline-restore.log'
 report={'status':'BASELINE_RESTORE_PENDING','worker_log_tail':log.read_text(errors='replace')[-1500:] if log.exists() else 'NOT_STARTED'}
report['units']={unit:subprocess.run(['systemctl','show',unit,'-p','WorkingDirectory','-p','ActiveState','-p','MainPID','--value'],stdout=subprocess.PIPE,text=True,timeout=3).stdout.strip() for unit in ['aura-camera-ui.service','aura-avatar-ui.service']}
report['boot_id_current']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
print(json.dumps(report),flush=True)
