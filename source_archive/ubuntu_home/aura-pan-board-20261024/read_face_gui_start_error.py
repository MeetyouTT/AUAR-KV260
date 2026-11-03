"""Read only the newly owned GUI startup failure log and unit properties."""
import json,subprocess
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5')
logs={}
for p in N.rglob('*.log'):
 if p.is_file() and p.name in ('stage.log','launcher.log'):
  size=p.stat().st_size
  with p.open('rb') as f:f.seek(max(0,size-7000));logs[str(p.relative_to(N))]=f.read().decode(errors='replace')
unit=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus'],text=True)
print(json.dumps({'unit':unit,'logs':logs,'root_entries':[p.name for p in (N/'runtime').iterdir()]}))
