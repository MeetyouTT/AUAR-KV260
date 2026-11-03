"""Start one reviewed UI deployment; inspect results, never blindly retry."""
import hashlib,json,subprocess
from pathlib import Path
p=Path('/home/root/aura-pan-manual-ui-20261020/staged-v1');assert hashlib.sha256((p/'deploy.py').read_bytes()).hexdigest()=='1f604698af21788bf4ecc17d1f12bdad45a6f78ade0a7d7afd1dbf5e6e13cb3e'
with (p/'activation.json').open('x') as marker:
 with (p/'deployment.log').open('xb') as log:
  child=subprocess.Popen(['/usr/bin/python3','-B',str(p/'deploy.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 value={'status':'LAUNCHED_ONCE_DO_NOT_RETRY','pid':child.pid,'path':str(p)}
 marker.write(json.dumps(value)+'\n')
print(json.dumps(value),flush=True)
