BOOT='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/dcb9e1d631475efa/bundle.tar.gz'
BUNDLE_SHA='dcb9e1d631475efaa3db55c69b82ec53d1974a36302e84667e1325f06781a69b'
SOURCE_SHA='f89c6cc683231b93e1c48d7d7962fd354c44cbe0db47fa6caa54811f00c33132'
TARGET='/home/root/aura-post-power-20261022/helpers/f89c6cc683231b93/source.py'
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
