BOOT='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/4606dba2c920bdcd/bundle.tar.gz'
BUNDLE_SHA='4606dba2c920bdcde0488b3245697b22f618056384f410dda00ed060380e6420'
SOURCE_SHA='c2a6ca06b661a83b063de803ad36f665a04f25db92a056b158179390d3f85431'
TARGET='/home/root/aura-post-power-20261022/helpers/c2a6ca06b661a83b/source.py'
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
