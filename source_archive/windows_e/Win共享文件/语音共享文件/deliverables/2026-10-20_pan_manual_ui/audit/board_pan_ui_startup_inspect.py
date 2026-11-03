"""Read latest startup configuration and driver transport without actuation."""
import base64,gzip,hashlib,json,subprocess
from pathlib import Path
wd=Path(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','WorkingDirectory','--value'],text=True).strip())
candidate=wd.parents[1]
paths={'current-startup-launcher.py':candidate/'startup/launcher.py','current-startup-config.json':candidate/'startup/config.json','current-vsrv-transport.py':Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked/vsrv_transport.py')}
arts={}
for n,p in paths.items():
 if p.is_file():
  raw=gzip.compress(p.read_bytes(),mtime=0);arts[n+'.gz']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
print(json.dumps({'candidate':str(candidate),'artifacts':arts}),flush=True)
