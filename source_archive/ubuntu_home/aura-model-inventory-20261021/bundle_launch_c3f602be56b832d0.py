BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/bc19626353569227/bundle.tar.gz'
BUNDLE_SHA='bc196263535692276270fd5dca890ce5be8191b1c452b86394d4f50e05a07a81'
SOURCE_SHA='c3f602be56b832d049c10836d8b5dd7498a5b3300115c0cd9a2e74471f8ccd69'
TARGET='/home/root/aura-post-power-20261022/helpers/c3f602be56b832d0/source.py'
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
