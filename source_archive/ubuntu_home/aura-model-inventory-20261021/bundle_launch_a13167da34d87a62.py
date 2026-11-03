BOOT='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/a6c8bb72a09dbfc0/bundle.tar.gz'
BUNDLE_SHA='a6c8bb72a09dbfc05363dd569cc6018652558e816ee5d03cf4efdcc6ac5af085'
SOURCE_SHA='a13167da34d87a623b00807437041b5725a681b51635526758150af499698c51'
TARGET='/home/root/aura-post-power-20261022/helpers/a13167da34d87a62/source.py'
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
