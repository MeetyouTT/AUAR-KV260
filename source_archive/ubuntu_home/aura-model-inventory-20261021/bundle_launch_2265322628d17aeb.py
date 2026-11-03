BOOT='e004cfbf-fdde-433d-b372-c8e420db2699'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/e529ce6cd4e5a383/bundle.tar.gz'
BUNDLE_SHA='e529ce6cd4e5a383ef1b75ea7e47f6d29668227d2cf2e1349676c5d314733568'
SOURCE_SHA='2265322628d17aebcc7d643aa5fc6d243df92fe2228893f19c5625a59bdc891f'
TARGET='/home/root/aura-post-power-20261022/helpers/2265322628d17aeb/source.py'
import hashlib,json,runpy,tarfile
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
p=Path(BUNDLE);assert hashlib.sha256(p.read_bytes()).hexdigest()==BUNDLE_SHA
with tarfile.open(p,'r:gz') as a:
 assert a.getnames()==['source.py']
 m=a.getmember('source.py');assert m.isfile() and m.size<300000
 raw=a.extractfile(m).read();assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
target=Path(TARGET);assert Path('/home/root/aura-post-power-20261022/helpers') in target.parents
assert target.parent.resolve()==target.parent and not target.is_symlink()
target.parent.mkdir(parents=True,exist_ok=True);assert target.parent.resolve()==target.parent
if target.exists():assert target.read_bytes()==raw
else:
 with target.open('xb') as f:f.write(raw)
runpy.run_path(str(target),run_name='__main__')
