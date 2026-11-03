BOOT='a69299ef-17d0-446f-a0df-56c0a08cd2fb'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/bd8fa16ad5baa290/bundle.tar.gz'
BUNDLE_SHA='bd8fa16ad5baa2903e1326b05f794801ef2c594a18f9d1d2ce241876adddd0a7'
SOURCE_SHA='cd1414a846c85c2e73502a1a86dad6eb45e552027fb933e43210c5f70b3665d4'
TARGET='/home/root/aura-post-power-20261022/helpers/cd1414a846c85c2e/source.py'
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
