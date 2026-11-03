BOOT='25b3d8ed-84e5-4a81-a2d6-6c8de1733a5f'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/b9ab1f97b4c05767/bundle.tar.gz'
BUNDLE_SHA='b9ab1f97b4c05767a0f421fed6ccbca5c2ceadf11757bba8a8748956caf51eb2'
SOURCE_SHA='a878bbd5303bf1a3c5be9244af884e45dd4fc1d32eabc6319c3a64dc6f86aeac'
TARGET='/home/root/aura-post-power-20261022/helpers/a878bbd5303bf1a3/source.py'
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
