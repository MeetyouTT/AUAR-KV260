BOOT='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
CONTROLLER='/home/root/aura-post-power-20261022/helpers/eca1b3e3f5cb2070/source.py'
PIN='eca1b3e3f5cb2070ebeb1b60f5604f232ef8e7021397919e289494ab9243ba16'
ACTION='check'
import hashlib,json,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
p=Path(CONTROLLER);assert hashlib.sha256(p.read_bytes()).hexdigest()==PIN
r=subprocess.run(['/usr/bin/python3','-B',str(p),ACTION],capture_output=True,text=True,timeout=20)
assert r.returncode==0,(r.stdout,r.stderr)
print(json.dumps({'action':ACTION,'stdout':r.stdout,'controller_sha256':PIN}))
