BOOT='a69299ef-17d0-446f-a0df-56c0a08cd2fb'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/8ef30b64541162a9/bundle.tar.gz'
BUNDLE_SHA='8ef30b64541162a9499bf206f4d5eea84a937ab2df5e81b8546427711b0028fe'
SOURCE_SHA='e6b226031b0ce5e1722c897e310c41b61f5eace810faab63c067c6e2c6c7da27'
TARGET='/home/root/aura-post-power-20261022/helpers/e6b226031b0ce5e1/source.py'
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
