"""Inspect the separately failed camera service; no restarts or protection changes."""
import json,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='e004cfbf-fdde-433d-b372-c8e420db2699'
def run(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
    return {'rc':p.returncode,'text':p.stdout[-18000:]}
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'service':run(['systemctl','show','aura-camera-ui.service','-p','MainPID','-p','ExecMainPID','-p','ActiveState','-p','Result','-p','ExecMainStatus','-p','NRestarts','-p','ExecMainStartTimestampMonotonic','-p','ExecMainExitTimestampMonotonic']),
   'journal':run(['journalctl','-b','-u','aura-camera-ui.service','-n','100','--no-pager','-o','cat'])}
p=Path('/sys/module/zocl/refcnt');d['zocl_refcnt']=p.read_text().strip() if p.exists() else None
print(json.dumps(d))
