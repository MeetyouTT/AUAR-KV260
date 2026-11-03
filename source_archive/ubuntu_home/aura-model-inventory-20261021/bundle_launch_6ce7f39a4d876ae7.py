BOOT='55152f95-ea3a-4c6c-82e6-51bd553d96fd'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/9fb62493a292f74e/bundle.tar.gz'
BUNDLE_SHA='9fb62493a292f74efbd4b771e7c85962f99462e813fd936a3b1dfb1b9723d5f5'
SOURCE_SHA='6ce7f39a4d876ae75b4492cd3062d94632a8d9afeb5ca4757b397b67fd20ed03'
TARGET='/home/root/aura-post-power-20261022/helpers/6ce7f39a4d876ae7/source.py'
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
