BOOT='55152f95-ea3a-4c6c-82e6-51bd553d96fd'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/ca9fd99775f36a5b/bundle.tar.gz'
BUNDLE_SHA='ca9fd99775f36a5bae77b281e04f6e609275f753d2bcd9b30adf18f2fca8968b'
SOURCE_SHA='4113a51901707918a83d06e4d2352881b5444ee0fd59e598513c5e5900ae3104'
TARGET='/home/root/aura-post-power-20261022/helpers/4113a51901707918/source.py'
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
