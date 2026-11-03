"""Freeze the reviewed three-source delta and synthetic retry contract tests."""
import ast
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parent
SOURCE=Path('/home/ghmd/aura-sface-slot-retry-20261022')
meta=json.loads((SOURCE/'manifest.json').read_text())
items={}
for name in meta['changed_files']:
    raw=(SOURCE/'candidate/aura'/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==meta['files'][name]['sha256']
    ast.parse(raw);items[name]=raw
for name,row in meta['files'].items():
    assert hashlib.sha256((SOURCE/'candidate/aura'/name).read_bytes()).hexdigest()==row['sha256']
items['retry-manifest.json']=(json.dumps(meta,sort_keys=True,indent=2)+'\n').encode()
items['tests/test_slot_retry.py']=(SOURCE/'tests/test_slot_retry.py').read_bytes()
original=(SOURCE/'tests/test_shadow.py').read_text();tree=ast.parse(original)
helpers='import time\nfrom board.identity.model_store import MODEL_SHA256,WINDOWS_MODEL_ID\n\n'
for name in ('configuration','vector','wait_for'):
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    helpers+=ast.get_source_segment(original,node)+'\n\n'
items['tests/test_shadow.py']=helpers.encode()
items['tests/bootstrap.py']=b'''import builtins,sqlite3
original=builtins.__import__
def guarded(name,*args,**kwargs):
    if name.split('.')[0] in {'xir','vart'}:raise AssertionError('Synthetic tests must not load DPU bindings')
    return original(name,*args,**kwargs)
def no_database(*args,**kwargs):raise AssertionError('Synthetic tests must not open identity storage')
builtins.__import__=guarded
sqlite3.connect=no_database
'''
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w',format=tarfile.PAX_FORMAT) as tar:
    for name,raw in sorted(items.items()):
        if name.endswith('.py'):ast.parse(raw)
        info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o600;info.mtime=0
        tar.addfile(info,io.BytesIO(raw))
blob=gzip.compress(buffer.getvalue(),mtime=0)
out=Path('/home/ghmd/aura-dpu-vision-20261021/work/sface-retry-delta-20261022.tar.gz')
if out.exists():assert out.read_bytes()==blob
else:out.write_bytes(blob)
value={'path':str(out),'sha256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob),
    'files':{name:hashlib.sha256(raw).hexdigest() for name,raw in items.items()},
    'source_files':meta['files'],'changed_files':meta['changed_files']}
(ROOT/'bundle-manifest.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({k:value[k] for k in ('path','sha256','bytes')}))
