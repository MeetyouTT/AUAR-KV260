BOOT='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/4a6385a7c0a77021/bundle.tar.gz'
BUNDLE_SHA='4a6385a7c0a770210df55526a90533636b7b0a71d81c564be8167a48e06f6bc4'
SOURCE_SHA='f236f677f64d800be15d1a12e8b464b2b82376bacf2b2e0a7cf20aacea1c9d49'
TARGET='/home/root/aura-post-power-20261022/helpers/f236f677f64d800b/source.py'
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
