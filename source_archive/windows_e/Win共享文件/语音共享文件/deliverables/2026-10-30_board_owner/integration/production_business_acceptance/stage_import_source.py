"""Stage a frozen public source closure for offline private import; no GUI/Store."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
INPUT=HERE.parent/'production_business_overlay'
TARGET='/home/root/aura-board-business-20261030/import-source-84f61727a69e7925'
ZIP_SHA='84f61727a69e79254335de8e279fba0e5bdc176ed232d5be3eb1fb51e42aab6c'
MANIFEST_SHA='6925a7262db0a34d4e129f5a1976e82f08d6b10c552e4eb577f33685a143f8c1'
REMOTE=r'''
import ast,base64,hashlib,io,json,os,stat,zipfile
from pathlib import Path,PurePosixPath
sha=lambda raw:hashlib.sha256(raw).hexdigest()
manifest_raw=base64.b64decode(MANIFEST,validate=True);raw=base64.b64decode(ARCHIVE,validate=True)
assert sha(manifest_raw)==MANIFEST_SHA and sha(raw)==ZIP_SHA
m=json.loads(manifest_raw);base=Path('/home/root/aura-character-xuefei-20261030/f94fca2c94288acb')
cfgraw=(base/'startup/config.json').read_bytes();assert sha(cfgraw)=='4c78824ba9c1c04bb95389a49b64215a7f624a323becae637bc8d4e7c4db4d7e'
cfg=json.loads(cfgraw);payload={}
for name,pin in cfg['component_sha256'].items():
 p=base/'runtime/aura'/name;assert p.resolve()==p and not p.is_symlink()
 value=p.read_bytes();assert sha(value)==pin;payload['aura/'+name]=value
with zipfile.ZipFile(io.BytesIO(raw)) as z:
 names=z.infolist();assert len(names)==len(set(x.filename for x in names)) and sum(x.file_size for x in names)<33554432
 for item in names:
  p=PurePosixPath(item.filename)
  assert str(p)==item.filename and not p.is_absolute() and '..' not in p.parts and p.parts[0]=='aura'
  assert not item.is_dir() and not stat.S_ISLNK(item.external_attr>>16) and item.file_size<16777216
  payload[item.filename]=z.read(item)
assert set(payload)==set(m['files']) and len(payload)==438
for name,value in payload.items():
 assert sha(value)==m['files'][name]['sha256']
 if name.endswith('.py'):ast.parse(value,feature_version=(3,9))
root=Path(TARGET);assert root.parent==Path('/home/root/aura-board-business-20261030') and root.resolve()==root and not root.exists()
root.mkdir(mode=0o700,parents=True)
for name,value in payload.items():
 p=root/name;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(value);f.flush();os.fsync(f.fileno())
print(json.dumps(dict(status='OFFLINE_IMPORT_SOURCE_STAGED',target=str(root),files=len(payload),
 source_manifest_sha256=MANIFEST_SHA,models_or_stores_or_gui_opened=False)))
'''

def main():
    raw=(INPUT/'production_business.overlay.zip').read_bytes()
    manifest=(INPUT/'production_business.manifest.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ZIP_SHA and hashlib.sha256(manifest).hexdigest()==MANIFEST_SHA
    values=dict(TARGET=TARGET,ZIP_SHA=ZIP_SHA,MANIFEST_SHA=MANIFEST_SHA,
        ARCHIVE=base64.b64encode(raw).decode(),MANIFEST=base64.b64encode(manifest).decode())
    result=json.loads(ssh('python3 -B -','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+REMOTE,timeout=40))
    (HERE/'import_source_staged.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':main()
