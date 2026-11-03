BOOT='3336afd3-7926-40b3-b5fd-e17b86256830'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/eb3e6ee1846f9757/bundle.tar.gz'
BUNDLE_SHA='eb3e6ee1846f9757b0b58cb2eecb592679fd94524223e2f99855c6917d356bdc'
SOURCE_SHA='94c54706b323e41d415db38395e2ee19bf0bbab98185de523331e072c73b954e'
TARGET='/home/root/aura-post-power-20261022/helpers/94c54706b323e41d/source.py'
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
