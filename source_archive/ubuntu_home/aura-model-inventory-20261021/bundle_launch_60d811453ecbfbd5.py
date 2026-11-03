BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/8baa24a779a72644/bundle.tar.gz'
BUNDLE_SHA='8baa24a779a7264421c7973a716a86effa10d2eaa333cda4a6a2b12005534a07'
SOURCE_SHA='60d811453ecbfbd5515a9213e49025e8a8ee5e0412a3b68306f2c64f4755dea7'
TARGET='/home/root/aura-post-power-20261022/helpers/60d811453ecbfbd5/source.py'
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
