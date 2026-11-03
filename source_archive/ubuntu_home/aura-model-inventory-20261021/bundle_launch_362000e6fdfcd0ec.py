BOOT='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/434ea1fd56e2a56b/bundle.tar.gz'
BUNDLE_SHA='434ea1fd56e2a56b054c6ad4cd1a5e1b04d2eceead4f02c061ad7cbd0725a815'
SOURCE_SHA='362000e6fdfcd0ecdaf5315b63cd0590e6f6c420c0829e423da839e542b12b78'
TARGET='/home/root/aura-post-power-20261022/helpers/362000e6fdfcd0ec/source.py'
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
