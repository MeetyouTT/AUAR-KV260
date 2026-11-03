BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/202450acae5ec5ca/bundle.tar.gz'
BUNDLE_SHA='202450acae5ec5ca04049ed761be6bc28af3987fad2550596ef880cd00f0a523'
SOURCE_SHA='cfcba65b98ee2a2be04925195f43cb13692bebd1fbbbdc5479555ede7291fe5e'
TARGET='/home/root/aura-post-power-20261022/helpers/cfcba65b98ee2a2b/source.py'
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
