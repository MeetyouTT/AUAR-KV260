"""Launch the prepared repair once; no direct motion."""
import hashlib,json,subprocess
from pathlib import Path
p=Path('/home/root/aura-pan-manual-ui-20261020/camera-fix-v3')
assert hashlib.sha256((p/'deploy.py').read_bytes()).hexdigest()=='8ad7d20754d3b4632ebb5e07de83e8601eae9072f9c99ca377094469402cac80'
with (p/'activation.json').open('x') as marker:
 with (p/'deployment.log').open('xb') as log:
  child=subprocess.Popen(['/usr/bin/python3','-B',str(p/'deploy.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 value={'status':'LAUNCHED_ONCE_DO_NOT_RETRY','pid':child.pid,'path':str(p)}
 marker.write(json.dumps(value)+'\n')
print(json.dumps(value),flush=True)
