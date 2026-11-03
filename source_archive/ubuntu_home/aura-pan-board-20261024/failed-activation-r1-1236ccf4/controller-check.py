BOOT='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
CONTROLLER='/home/root/aura-post-power-20261022/helpers/ce9111604e2f71ed/source.py'
PIN='ce9111604e2f71ede7d3a26a7611ae9b4df6db1a092e3cb4379d46de19981d3a'
ROOT='/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4'
ACTION='check'
import hashlib,json,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
p=Path(CONTROLLER);assert hashlib.sha256(p.read_bytes()).hexdigest()==PIN
command=['/usr/bin/python3','-B',str(p),'--root',ROOT,ACTION]
r=subprocess.run(command,capture_output=True,text=True,timeout=20)
assert r.returncode==0,(r.stdout,r.stderr)
print(json.dumps({'action':ACTION,'stdout':r.stdout,'controller_sha256':PIN}))
