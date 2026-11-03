BOOT='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/acc4b676132384fe/bundle.tar.gz'
BUNDLE_SHA='acc4b676132384fec6e796c7466fa5d2a70ad7a7043d56a24d9c2a73aeb61681'
SOURCE_SHA='51577169406ed06e5981df0ae7c45693adeb808daf23b51d015e84380749ad85'
TARGET='/home/root/aura-post-power-20261022/helpers/51577169406ed06e/source.py'
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
