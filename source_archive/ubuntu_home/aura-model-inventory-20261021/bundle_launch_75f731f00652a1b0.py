BOOT='50b4fef1-9748-43c7-92bf-3040db8c994e'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/5fd8508dffe92fdf/bundle.tar.gz'
BUNDLE_SHA='5fd8508dffe92fdfc181062225d7d3ba962a609fc41cf48c48fa3de7d83fcafa'
SOURCE_SHA='75f731f00652a1b02166a870f4bad009055c055863c2340ca4c8c033274d0382'
TARGET='/home/root/aura-post-power-20261022/helpers/75f731f00652a1b0/source.py'
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
