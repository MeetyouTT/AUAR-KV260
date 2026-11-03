BACKUP='/home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/deployment-4d9ad187'
OVERRIDE='/etc/systemd/system/aura-avatar-ui.service.d/zzzzzzzzz-aura-audio-frontend-budget-20261021.conf'
PREF='/root/.local/share/aura/handsfree_dialogue.json'
TEXT='[Unit]\nRequiresMountsFor=/home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/runtime\n[Service]\nWorkingDirectory=/home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/runtime/aura\nExecStart=\nExecStart=/usr/bin/python3 -B /home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/startup/launcher.py --config /home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/startup/config.json\n'
CHOSEN=True

import json,os,subprocess,time
from pathlib import Path
backup=Path(BACKUP);override=Path(OVERRIDE);pref=Path(PREF);expected=TEXT;chosen=CHOSEN
deadline=time.monotonic()+300
while time.monotonic()<deadline:
 if (backup/'committed').exists():raise SystemExit(0)
 time.sleep(.5)
if override.exists() and override.read_text()!=expected:raise RuntimeError('Foreign override; refuse rollback')
subprocess.run(['systemctl','stop','aura-avatar-ui.service'],timeout=40)
if override.exists():override.unlink()
tmp=pref.with_name(pref.name+'.frontend-watchdog');tmp.write_text(json.dumps({'version':1,'enabled':chosen}));tmp.chmod(0o600);os.replace(tmp,pref)
subprocess.run(['systemctl','daemon-reload']);subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'])
(backup/'watchdog_rollback.json').write_text(json.dumps({'status':'DEADLINE_ROLLBACK'}))
