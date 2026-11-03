BOOT='5f167a36-a715-4bbb-9186-4dff2bff8ee3'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/c604d45b7b167e23/bundle.tar.gz'
BUNDLE_SHA='c604d45b7b167e23923217912277b88a7251f8f0517a5ef2c0ac688cfc575659'
SOURCE_SHA='97d4fc12adca7ca164436cb2c89783e359278b81ac5b43a1f40b0ea38253c84e'
TARGET='/home/root/aura-post-power-20261022/helpers/97d4fc12adca7ca1/source.py'
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
