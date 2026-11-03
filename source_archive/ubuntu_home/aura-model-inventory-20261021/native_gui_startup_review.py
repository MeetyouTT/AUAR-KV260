import json,hashlib,subprocess
from pathlib import Path
p=Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce/startup/launcher.py')
config=json.loads((p.parent/'config.json').read_text())
print(json.dumps({'launcher_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'launcher_source':p.read_text(),
 'configuration_keys':sorted(config),
 'service':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','After','-p','Requires','-p','TimeoutStartUSec','-p','ExecStartPre'],text=True)}))
