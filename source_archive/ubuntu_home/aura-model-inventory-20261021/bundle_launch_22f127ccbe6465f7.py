BOOT='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/0098a8181fa25b1e/bundle.tar.gz'
BUNDLE_SHA='0098a8181fa25b1e34014a3d15e8d284956d96c2a8c8048465b0505429b68e0e'
SOURCE_SHA='22f127ccbe6465f7ee00aea2d722a026f2708e38bd9378e38d39ef79a77efa4e'
TARGET='/home/root/aura-post-power-20261022/helpers/22f127ccbe6465f7/source.py'
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
