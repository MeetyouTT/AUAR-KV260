BOOT='25b3d8ed-84e5-4a81-a2d6-6c8de1733a5f'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/aab92808edc38d53/bundle.tar.gz'
BUNDLE_SHA='aab92808edc38d53469dbdac1874a35eb12bd689b8e148605ad77ce72ae1807e'
SOURCE_SHA='376e4921416108f4b7be038c42b05a516ae76851ea03cce90f49736d0ab88566'
TARGET='/home/root/aura-post-power-20261022/helpers/376e4921416108f4/source.py'
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
