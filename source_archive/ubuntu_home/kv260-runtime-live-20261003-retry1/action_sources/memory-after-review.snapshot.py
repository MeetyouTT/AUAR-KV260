import json,os
from pathlib import Path
w=Path('/home/root/kv260-runtime-live-20261003T085031Z')
print(json.dumps({'read_only':True,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':Path('/proc/uptime').read_text().strip(),'meminfo':Path('/proc/meminfo').read_text(),'work_regular_bytes':sum(p.stat().st_size for p in w.rglob('*') if p.is_file()),'test_log_bytes':sum(p.stat().st_size for d in ['logs','agent_logs'] for p in (w/d).rglob('*') if p.is_file()),'driver':Path('/sys/module/zocl/srcversion').read_text().strip()}),flush=True)
