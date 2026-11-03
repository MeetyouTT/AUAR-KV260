BOOT='a69299ef-17d0-446f-a0df-56c0a08cd2fb'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/f23346c211b25c20/bundle.tar.gz'
BUNDLE_SHA='f23346c211b25c207e7edc3c9756b7a871f3374aed8949bd82acd739f8a28136'
SOURCE_SHA='3843d29c4b93e4f9dfa3b9adb5bb6dc6d931955551524ee6e461b82522102fb6'
TARGET='/home/root/aura-post-power-20261022/helpers/3843d29c4b93e4f9/source.py'
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
