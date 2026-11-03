BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/b6225927016783a3/bundle.tar.gz'
BUNDLE_SHA='b6225927016783a3f33537d35950e65644afb17c051f18d5a5b8efb164905710'
SOURCE_SHA='66cde810eb059dcebb1698524c9300991c4a6d7c78d395a2b0d885082cc8f893'
TARGET='/home/root/aura-post-power-20261022/helpers/66cde810eb059dce/source.py'
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
