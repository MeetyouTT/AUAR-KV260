import json,subprocess
from pathlib import Path
out={'results':{},'units':{}}
for p in Path('/home/root/aura-audio-recovery-20261021').glob('*/result.json'):
 out['results'][str(p)]=json.loads(p.read_text())
for n in ['aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service']:
 out['units'][n]=subprocess.check_output(['systemctl','show',n,'-p','MainPID','-p','ActiveState','-p','NRestarts'],timeout=4).decode().strip()
print(json.dumps(out))
