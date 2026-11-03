BOOT='c006a771-c3e4-4d4f-97d7-ade3dd774619'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/cf945a242cb98689/bundle.tar.gz'
BUNDLE_SHA='cf945a242cb986896451c535a159a3bc17d5b086336e1178b75adda7904924a6'
SOURCE_SHA='663fb4c582a4321b1d314b6ee0af37da3a6b6fbe2622025a2057ede4c4bb082a'
TARGET='/home/root/aura-post-power-20261022/helpers/663fb4c582a4321b/source.py'
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
