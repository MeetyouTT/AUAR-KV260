
import os,shutil,subprocess
from pathlib import Path
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
for name in ['aura-avatar-ui.service','aura-camera-ui.service']:
 subprocess.run(['systemctl','stop',name],timeout=35,check=False)
for name in ['aura-camera-ui.service','aura-avatar-ui.service']:
 target=Path('/etc/systemd/system')/name
 temp=target.with_name(name+'.rollback-'+str(os.getpid()))
 shutil.copy2(root/'activation-backup-final'/name,temp);os.replace(str(temp),str(target))
subprocess.run(['systemctl','daemon-reload'],check=True,timeout=10)
for name in ['aura-camera-ui.service','aura-avatar-ui.service']:
 subprocess.run(['systemctl','start','--no-block',name],check=True,timeout=10)
