"""Launch exactly one prepared finite step; never retry on uncertain completion."""
import hashlib,json,subprocess,time
from pathlib import Path
p=Path('/home/root/aura-pan-follow-20261020/prepared-midpoint-05/execute.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='94a843513215de9fde852f2f509e807c69c0cb23a5b8bc9895704650eed7de8a'
assert not Path('/home/root/aura-pan-follow-20261020/midpoint-step-05').exists()
time.sleep(3)
r=subprocess.run(['/usr/bin/python3','-B',str(p)],capture_output=True,text=True,timeout=25)
assert r.returncode==0,(r.returncode,r.stderr[-2000:])
print(json.dumps(json.loads(r.stdout)),flush=True)
