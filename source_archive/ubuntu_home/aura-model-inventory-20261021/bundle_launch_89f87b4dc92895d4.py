BOOT='5f167a36-a715-4bbb-9186-4dff2bff8ee3'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/a4dc4b250e3a2b75/bundle.tar.gz'
BUNDLE_SHA='a4dc4b250e3a2b752d1384379fa7251a9f654cafa036d3b29514441801d889b8'
SOURCE_SHA='89f87b4dc92895d4e185a5d0d5dd1c677a6385fe3044804b7748e99bb50373fd'
TARGET='/home/root/aura-post-power-20261022/helpers/89f87b4dc92895d4/source.py'
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
