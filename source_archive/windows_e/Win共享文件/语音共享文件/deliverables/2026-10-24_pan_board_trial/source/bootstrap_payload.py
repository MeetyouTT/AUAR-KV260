BOOT='c5f247b9-76b9-40a3-85ca-96578055eb5c'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/0aa4d5b65720d44d/bundle.tar.gz'
PIN='0aa4d5b65720d44dda91c6208a8c7ce3669c7a4d9275bf0b9c5dc6ea6ebc25d8'
ROOT='/home/root/aura-pan-vsrv2-20261024/778d2512-c5f247b9'
import hashlib,json,runpy,tarfile
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
archive=Path(BUNDLE);assert hashlib.sha256(archive.read_bytes()).hexdigest()==PIN
root=Path(ROOT);root.mkdir(parents=True,exist_ok=True,mode=0o700)
assert root.resolve()==root
with tarfile.open(archive,'r:gz') as tar:
 meta=json.load(tar.extractfile('payload.json'))
 assert meta['board_root']==str(root) and meta['baseline']['boot_id']==BOOT
 members=tar.getmembers();assert len(members)<30 and sum(m.size for m in members)<2000000
 assert set(tar.getnames())==set(meta['files'])|{'payload.json'}
 for item in members:
  path=Path(item.name);assert item.isfile() and not path.is_absolute() and '..' not in path.parts
  target=root/path;target.parent.mkdir(parents=True,exist_ok=True);assert target.parent.resolve()==target.parent and not target.is_symlink()
  raw=tar.extractfile(item).read()
  if item.name!='payload.json':assert hashlib.sha256(raw).hexdigest()==meta['files'][item.name]
  if target.exists():assert target.read_bytes()==raw
  else:
   with target.open('xb') as f:f.write(raw)
runpy.run_path(str(root/'prepare_payload_board.py'),run_name='__main__')
