BOOT='a69299ef-17d0-446f-a0df-56c0a08cd2fb'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/92f2b0e6ed8f28f8/bundle.tar.gz'
BUNDLE_SHA='92f2b0e6ed8f28f8ab496cd1a64b9bebf93eca6e3f5f1fed1274413d61dce6a6'
SOURCE_SHA='0dd821c1e1723fe2cfe4d1b5e2b20d04b9c3defb20aec6d84f17098b1b2226f0'
TARGET='/home/root/aura-post-power-20261022/helpers/0dd821c1e1723fe2/source.py'
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
