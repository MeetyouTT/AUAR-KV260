BOOT='89760db2-7019-49c6-a379-b92fb98b8a5b'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/2158e927b393eacc/bundle.tar.gz'
BUNDLE_SHA='2158e927b393eacc8e6ad021c84625c83521f9edf828a1249f22bab54eff988e'
SOURCE_SHA='8658361435e6b086ec9a44fb893208e477e26cf4bc2f98a8611b663bc0a4e554'
TARGET='/home/root/aura-post-power-20261022/helpers/8658361435e6b086/source.py'
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
