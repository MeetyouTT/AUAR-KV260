BOOT='230ae5f0-997b-432b-a738-0065c0cb5238'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/40eb39e93541012c/bundle.tar.gz'
BUNDLE_SHA='40eb39e93541012c62a746275c7247b1f065f7c5eca7488363bcf2ff45184239'
SOURCE_SHA='71eed27c50dd12b921ce4fe5ff4b9facb8151d9dee6376df48da254beb7fc55c'
TARGET='/home/root/aura-post-power-20261022/helpers/71eed27c50dd12b9/source.py'
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
