BOOT='b7871498-884a-4190-8ba1-6876a63a3f6c'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/0b7fbce3124c8280/bundle.tar.gz'
BUNDLE_SHA='0b7fbce3124c828034592c51192a418affd512084d328f87aab2194031d2f5c2'
SOURCE_SHA='ee3db5fa3068e4a16c0e524d453568569bc127ad7799b60808e98266ef489489'
TARGET='/home/root/aura-post-power-20261022/helpers/ee3db5fa3068e4a1/source.py'
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
