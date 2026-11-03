
import json,subprocess,time
from pathlib import Path
stage=Path('/home/root/aura-animation-dialogue-20261026/d6d1617467724213b3d9fd3d11530a47');drop=Path('/etc/systemd/system/aura-avatar-ui.service.d/zzzzzzzzzzzzzzzzzzzzzzzzzzzzzz-aura-animation-dialogue.conf')
if (stage/'committed').exists() or (stage/'trial_finished').exists():raise SystemExit(0)
if drop.exists() and str(stage) not in drop.read_text():raise SystemExit('Unrelated override; no rollback')
subprocess.run(['systemctl','stop','aura-avatar-ui.service'],capture_output=True,timeout=45)
if drop.exists():drop.unlink()
subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=20)
subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,capture_output=True,timeout=20)
(stage/'watchdog_rollback.json').write_text(json.dumps({'reason':'UI trial was not committed','at':time.time()}))
