BOOT='5f167a36-a715-4bbb-9186-4dff2bff8ee3'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/a4ec412c7f0d611d/bundle.tar.gz'
BUNDLE_SHA='a4ec412c7f0d611d8e10e9d30ecc6c7fdd916b02ae9d9f91b0c895e458488cfe'
SOURCE_SHA='418a29c4d8cd4949e20ad21701d9a888292a83b43450e94a99f3186b79d1cef7'
TARGET='/home/root/aura-post-power-20261022/helpers/418a29c4d8cd4949/source.py'
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
