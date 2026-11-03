"""Launch exactly one prepared finite step; never retry on uncertain completion."""
import hashlib,json,subprocess,time
from pathlib import Path
p=Path('/home/root/aura-pan-follow-20261020/prepared-midpoint-04/execute.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='c4b129b1555889b9678c13cfd3bea16b50e0d0c09cd8e782999e37eaae464111'
assert not Path('/home/root/aura-pan-follow-20261020/midpoint-step-04').exists()
time.sleep(3)
r=subprocess.run(['/usr/bin/python3','-B',str(p)],capture_output=True,text=True,timeout=25)
assert r.returncode==0,(r.returncode,r.stderr[-2000:])
print(json.dumps(json.loads(r.stdout)),flush=True)
