BOOT='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/5b6d026ea5d916e6/bundle.tar.gz'
BUNDLE_SHA='5b6d026ea5d916e6ae6d67291ff266b6ef4e87f182a6aa85976590b401e64b8c'
SOURCE_SHA='1aa1184549706e590cbafc2457273305657624c7863ee26a0289b2a295771387'
TARGET='/home/root/aura-post-power-20261022/helpers/1aa1184549706e59/source.py'
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
