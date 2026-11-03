BOOT='25b3d8ed-84e5-4a81-a2d6-6c8de1733a5f'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/12f8b9b66b1adc42/bundle.tar.gz'
BUNDLE_SHA='12f8b9b66b1adc422be1ee6e69a4c29a40a87afad079b05678b5690b994bb413'
SOURCE_SHA='15d8d8f6a596610a77f26c555f92877f3dad11a4535881cf63b914b7c99c618d'
TARGET='/home/root/aura-post-power-20261022/helpers/15d8d8f6a596610a/source.py'
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
