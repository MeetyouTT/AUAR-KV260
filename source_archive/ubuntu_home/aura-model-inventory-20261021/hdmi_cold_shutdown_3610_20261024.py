SOURCE='/home/root/aura-post-power-20261022/helpers/3610d09e12307044/source.py'
PIN='3610d09e1230704427f108b497f55624b8312b0d7cd8fe1d6bdbda8478ee27b3'
ROOT='/home/root/aura-native-coldboot-20261024/3610d09e12307044'
import hashlib,json,subprocess,time
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
assert hashlib.sha256(Path(SOURCE).read_bytes()).hexdigest()==PIN
unit='aura-native-cold-shutdown-3610d09e12307044'
p=Path(ROOT)/'shutdown.json';assert not p.exists()
subprocess.run(['systemd-run','--quiet','--no-block','--unit='+unit,'--property=Type=oneshot','--property=TimeoutStartSec=infinity','--property=KillMode=process','--property=SendSIGKILL=no','/usr/bin/python3','-B',SOURCE,'--shutdown'],check=True,capture_output=True,text=True,timeout=5)
until=time.monotonic()+18
while time.monotonic()<until:
 if p.exists():
  r=json.loads(p.read_text())
  if r.get('poweroff_scheduled') or r.get('failure'):
   print(json.dumps({'root':ROOT,'safe_to_disconnect_power':r['safe_to_disconnect_power'],'poweroff_scheduled':r['poweroff_scheduled'],'failure':r.get('failure'),'checkpoint_sha256':r.get('checkpoint_sha256'),'unit':unit}));break
 time.sleep(.1)
else:print(json.dumps({'pending':True,'root':ROOT,'unit':unit,'do_not_disconnect_yet':True}))
