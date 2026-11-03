"""Launch exactly one prepared finite step; never retry on uncertain completion."""
import hashlib,json,subprocess,time
from pathlib import Path
p=Path('/home/root/aura-pan-follow-20261020/prepared-midpoint-06/execute.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='24a20e84d75e90499721d7d75258177ef0bce24e2b8347c202b8d60b8cd79770'
assert not Path('/home/root/aura-pan-follow-20261020/midpoint-step-06').exists()
time.sleep(3)
r=subprocess.run(['/usr/bin/python3','-B',str(p)],capture_output=True,text=True,timeout=25)
assert r.returncode==0,(r.returncode,r.stderr[-2000:])
print(json.dumps(json.loads(r.stdout)),flush=True)
