"""Launch the already-prepared one-shot sweep after the user's start cue."""
import hashlib,json,subprocess,time
from pathlib import Path
p=Path('/home/root/aura-pan-follow-20261020/prepared-wide-visible-01/execute.py')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='368705eb0c20947b64ccf4b28e7fb51ab1286905810594f9dbe5d349ccd71e36'
assert not Path('/home/root/aura-pan-follow-20261020/visible-direction-wide-01').exists()
time.sleep(3)
r=subprocess.run(['/usr/bin/python3','-B',str(p)],capture_output=True,text=True,timeout=25)
assert r.returncode==0,(r.returncode,r.stderr[-2000:])
print(json.dumps(json.loads(r.stdout)),flush=True)
