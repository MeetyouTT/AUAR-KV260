BOOT='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/ac1e47b09db72853/bundle.tar.gz'
BUNDLE_SHA='ac1e47b09db728535adc759956c6678e8c200da982198410f2cf0132ef905bc5'
SOURCE_SHA='96420fc26d811e16bd47b8b3d16a0b1a6b3ea9759ba5490564205fc9c0065bb4'
TARGET='/home/root/aura-post-power-20261022/helpers/96420fc26d811e16/source.py'
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
