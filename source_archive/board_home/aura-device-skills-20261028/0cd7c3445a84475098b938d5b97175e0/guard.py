
import subprocess
from pathlib import Path
s=Path('/home/root/aura-device-skills-20261028/0cd7c3445a84475098b938d5b97175e0');p=Path('/etc/systemd/system/aura-avatar-ui.service.d/zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz-aura-device-skills.conf')
if (s/'committed').exists() or (s/'rolled_back').exists():raise SystemExit(0)
if p.is_file() and str(s) in p.read_text():
 subprocess.run(['systemctl','stop','aura-avatar-ui.service'],timeout=40)
 p.unlink();subprocess.run(['systemctl','daemon-reload'],check=True,timeout=20)
 subprocess.run(['systemctl','start','--no-block','aura-avatar-ui.service'],check=True,timeout=20)
 (s/'rolled_back').write_text('Watchdog restored previous entry')
