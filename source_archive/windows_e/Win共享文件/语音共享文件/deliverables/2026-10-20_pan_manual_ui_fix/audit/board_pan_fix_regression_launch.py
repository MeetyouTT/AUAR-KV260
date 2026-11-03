import hashlib,json,subprocess
from pathlib import Path
p=Path('/home/root/aura-pan-manual-ui-20261020/fix-v2')
assert hashlib.sha256((p/'regression.py').read_bytes()).hexdigest()=='3ff0a1e598d086c8bcfa2ba7926e370c55087c9e25096e26f500769b66a06c4a'
with (p/'regression-started.json').open('x') as f:f.write(json.dumps({'single_execution':True})+'\n')
r=subprocess.run(['/usr/bin/python3','-B',str(p/'regression.py')],capture_output=True,text=True,timeout=25)
assert r.returncode==0,r.stderr[-1400:]
print(json.dumps(json.loads(r.stdout)),flush=True)
