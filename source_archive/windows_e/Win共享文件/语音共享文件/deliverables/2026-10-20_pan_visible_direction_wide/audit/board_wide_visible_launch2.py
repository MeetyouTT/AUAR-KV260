"""Launch exactly one prepared wide sweep; never retry on uncertain completion."""
import hashlib,json,subprocess,time
from pathlib import Path
p=Path('/home/root/aura-pan-follow-20261020/prepared-wide-visible-02/execute.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='c00674778ad1ebd4fb3c3cd4f08aeaa60bb396344eb1942eca50b7db2bf5db57'
assert not Path('/home/root/aura-pan-follow-20261020/visible-direction-wide-01').exists()
time.sleep(3)
r=subprocess.run(['/usr/bin/python3','-B',str(p)],capture_output=True,text=True,timeout=25)
assert r.returncode==0,(r.returncode,r.stderr[-2000:])
print(json.dumps(json.loads(r.stdout)),flush=True)
