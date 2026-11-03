import hashlib,json,subprocess
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/sface-retry-ab/331f485bd54678ae')
p=root/'prepared.json';v=json.loads(p.read_text());source=Path(v['source'])
assert v['source_sha256']=='331f485bd54678aea972fb09078573eaf45ff08fab82a931fd17709c2e203bf9'
assert hashlib.sha256(source.read_bytes()).hexdigest()==v['source_sha256']
assert v['synthetic_tests_passed'] and not (root/'launch-result.json').exists()
unit='aura-sface-ab-331f485bd54678ae'
result=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=360','--setenv=AURA_SFACE_AB_MODE=run','/usr/bin/python3','-B',str(source)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
assert result.returncode==0,result.stdout.decode(errors='replace')
print(json.dumps({'started':True,'unit':unit,'prepared_root':str(root)}))
