import hashlib,json,os,subprocess
from pathlib import Path
p=Path('/home/root/aura-post-power-20261022/helpers/10261c1b5b2b7458/source.py')
raw=p.read_text();start=raw.index('def single_owner');end=raw.find('\ndef ',start+5)
out={'reviewed_owner_source':raw[start:end if end>=0 else len(raw)],'device_fds':{}}
for pid in (450495,450525):
    devices=set()
    for fd in (Path('/proc')/str(pid)/'fd').iterdir():
        try:target=os.readlink(fd)
        except (FileNotFoundError,ProcessLookupError):continue
        if target.startswith('/dev/'):devices.add(target)
    out['device_fds'][str(pid)]=sorted(devices)
out['camera_stop_policy']=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','KillMode','-p','KillSignal','-p','TimeoutStopUSec','-p','ActiveState']).decode()
print(json.dumps(out))
