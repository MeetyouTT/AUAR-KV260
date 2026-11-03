BOOT='55152f95-ea3a-4c6c-82e6-51bd553d96fd'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/83e0f8d63fd4cd76/bundle.tar.gz'
BUNDLE_SHA='83e0f8d63fd4cd76a72b39069c61b3876fb41dff6cca09b36d2accc8c9490805'
SOURCE_SHA='d1278940fc0c4b9ec5a9d5b5a8146fa55d4558b45dc1d869f60ff5a819b99f3a'
TARGET='/home/root/aura-post-power-20261022/helpers/d1278940fc0c4b9e/source.py'
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
