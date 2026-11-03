import hashlib,json,subprocess
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/sface-retry-ab/331f485bd54678ae')
source=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/a9dfd6aff4f15cf6/source.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='a9dfd6aff4f15cf67a69b19ae9b328262de2ec2a1644d764f54e21b7c9ef13a4'
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
p=root/'b-only-v2-launch-result.json';v=json.loads(p.read_text())
assert v.get('error')=='RuntimeError: No face within bounded pre-start wait'
archive=root/'b-only-v2-pre-r3.json';assert not archive.exists();p.rename(archive)
unit='aura-sface-b-only-a9dfd6aff4f15cf6-r3'
r=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=270','--setenv=AURA_SFACE_B_ONLY_RUN=1','/usr/bin/python3','-B',str(source)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=8)
assert r.returncode==0,r.stdout.decode(errors='replace')
print(json.dumps({'started':True,'unit':unit,'scope':'B_ONLY_MEASUREMENT_NO_AB_RATIO'}))
