BOOT='55152f95-ea3a-4c6c-82e6-51bd553d96fd'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/c324545aa2c2ee53/bundle.tar.gz'
BUNDLE_SHA='c324545aa2c2ee53b9fc69ffe760f81ad8661ed9c7e0d9bc1ad62a3a4daff3ef'
SOURCE_SHA='8ec54cefedade0f52849d963917c439a50f0c4a91fa5e7c2a579fd448d298656'
TARGET='/home/root/aura-post-power-20261022/helpers/8ec54cefedade0f5/source.py'
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
