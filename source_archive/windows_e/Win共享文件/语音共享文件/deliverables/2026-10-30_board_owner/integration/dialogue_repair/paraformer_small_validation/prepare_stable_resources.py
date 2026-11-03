"""Verify and copy only the approved small ASR resources to a versioned board model path."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'first_wait_streaming_validation'))
from root_generate_fixtures import ssh

REMOTE = r'''
import hashlib,json,os,pathlib,shutil
Path=pathlib.Path
src=Path('/home/root/aura-public-streaming-validation-20261031/paraformer-small-63ddc3cd0f2810b6')
dst=Path('/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6')
rows={
 'model.int8.onnx':(81828675,'3ef6c19369b912f7caf3cef8e545c5ccd1a33d9d7ec792a46668dc41c4b229ec'),
 'tokens.txt':(75352,'4b2d964e18b9cf139b473003b6698fb2ed9a2a5ec55b93daa677b28f578897aa')}
def checked(path,size,expected):
 assert path.is_file() and not any(p.is_symlink() for p in (path,*path.parents))
 assert path.stat().st_size==size
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 assert h.hexdigest()==expected
for name,(size,pin) in rows.items():checked(src/name,size,pin)
assert not any(p.is_symlink() for p in (dst,*dst.parents))
dst.mkdir(mode=0o700,parents=True,exist_ok=True)
assert shutil.disk_usage(dst).free>300*1024*1024
for name,(size,pin) in rows.items():
 target=dst/name
 if not target.exists():
  tmp=dst/(name+'.verified-new')
  with tmp.open('xb') as out,(src/name).open('rb') as inp:
   shutil.copyfileobj(inp,out,1048576);out.flush();os.fsync(out.fileno())
  checked(tmp,size,pin)
  os.chmod(tmp,0o444);os.rename(tmp,target)
  directory=os.open(str(dst),os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(directory)
  finally:os.close(directory)
 checked(target,size,pin)
print(json.dumps(dict(status='STABLE_ASR_RESOURCES_PREPARED_NOT_ACTIVATED',directory=str(dst),files=[dict(name=k,size=v[0],sha256=v[1]) for k,v in rows.items()],production_configuration_changed=False)))
'''

if __name__ == '__main__':
    value = json.loads(ssh('python3 -B -', REMOTE, timeout=35))
    (HERE / 'STABLE_RESOURCES.json').write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(value))
