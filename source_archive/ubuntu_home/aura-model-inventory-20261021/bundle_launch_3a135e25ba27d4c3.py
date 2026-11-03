BOOT='a69299ef-17d0-446f-a0df-56c0a08cd2fb'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/5bf97d75b57d910a/bundle.tar.gz'
BUNDLE_SHA='5bf97d75b57d910aa62643e6bce4a395e4928edab2b702203ec7766b4e2e0154'
SOURCE_SHA='3a135e25ba27d4c36a188cba48978bd91bcbce1fea640315d0f10eed6f966b3d'
TARGET='/home/root/aura-post-power-20261022/helpers/3a135e25ba27d4c3/source.py'
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
