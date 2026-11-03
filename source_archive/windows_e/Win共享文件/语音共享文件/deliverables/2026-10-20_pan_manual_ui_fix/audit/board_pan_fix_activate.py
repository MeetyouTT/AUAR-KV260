"""Start one reviewed UI deployment; inspect results, never blindly retry."""
import hashlib,json,subprocess
from pathlib import Path
p=Path('/home/root/aura-pan-manual-ui-20261020/fix-v2');assert hashlib.sha256((p/'deploy.py').read_bytes()).hexdigest()=='2c2e33887a3ed87743e9af77cad4678f7a6c9881f19178cf5a6fbe16bb7027fa'
with (p/'activation.json').open('x') as marker:
 with (p/'deployment.log').open('xb') as log:
  child=subprocess.Popen(['/usr/bin/python3','-B',str(p/'deploy.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 value={'status':'LAUNCHED_ONCE_DO_NOT_RETRY','pid':child.pid,'path':str(p)}
 marker.write(json.dumps(value)+'\n')
print(json.dumps(value),flush=True)
