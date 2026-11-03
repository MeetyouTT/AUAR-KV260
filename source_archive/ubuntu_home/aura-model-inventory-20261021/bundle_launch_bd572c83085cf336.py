BOOT='e004cfbf-fdde-433d-b372-c8e420db2699'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/810f48ce1fd75087/bundle.tar.gz'
BUNDLE_SHA='810f48ce1fd75087d365b8a2fad5c954ffca7da9196dc287de1afe06a2f82491'
SOURCE_SHA='bd572c83085cf336d73c5859d37201c20f7058a92155cf0d734a2dbbdcc965ab'
TARGET='/home/root/aura-post-power-20261022/helpers/bd572c83085cf336/source.py'
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
