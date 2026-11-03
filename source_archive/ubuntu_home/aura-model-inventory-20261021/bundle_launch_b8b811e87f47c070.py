BOOT='5f167a36-a715-4bbb-9186-4dff2bff8ee3'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/8a663644cc58cf82/bundle.tar.gz'
BUNDLE_SHA='8a663644cc58cf82eed7b6451ca3eb0d628f10b90334b98ef27697dde8b305d9'
SOURCE_SHA='b8b811e87f47c070ef3c4cba2b844ae47cc75cf9ab93613cc24f7495632fcd63'
TARGET='/home/root/aura-post-power-20261022/helpers/b8b811e87f47c070/source.py'
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
