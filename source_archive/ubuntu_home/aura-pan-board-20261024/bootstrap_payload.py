BOOT='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
BUNDLE='/home/root/aura-dpu-vision-20261021/staging/c6a2752686b6e75a/bundle.tar.gz'
PIN='c6a2752686b6e75a4e95bfc8fa8f76d4cb40b5dae0621b6b6936fa0945dc0def'
ROOT='/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2'
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
