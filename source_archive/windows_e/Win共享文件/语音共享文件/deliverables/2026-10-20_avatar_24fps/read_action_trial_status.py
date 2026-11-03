import subprocess,json
from pathlib import Path
p=Path('/home/root/aura-speech-motion-20261021/0e98f7830e27')
files={name:(p/name).read_text() if (p/name).exists() else None for name in ('committed','trial-finished','watchdog_rollback.json','trial.json')}
print(json.dumps({'files':files,'service':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ActiveState','-p','SubState','-p','MainPID','-p','Result'],text=True),'journal':subprocess.check_output(['journalctl','-u','aura-avatar-ui.service','-n','18','--no-pager'],text=True)}))
