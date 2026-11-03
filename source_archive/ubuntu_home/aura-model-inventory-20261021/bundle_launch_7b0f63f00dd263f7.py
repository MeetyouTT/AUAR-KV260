BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/dbc4ff2b8bf3ec28/bundle.tar.gz'
BUNDLE_SHA='dbc4ff2b8bf3ec2849b8f876bf0b0e4bf789ac378e910c64b321ae7c25555ac9'
SOURCE_SHA='7b0f63f00dd263f7ab3693b389cf0d544b7f6909aae624c5702658d0d72cec4f'
TARGET='/home/root/aura-post-power-20261022/helpers/7b0f63f00dd263f7/source.py'
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
