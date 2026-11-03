#!/usr/bin/env python3
"""Hash current evidence and verify it; no permission changes or removal."""
import datetime
import hashlib
import json
from pathlib import Path

ROOTS=[Path('/home/ghmd/kv260-runtime-live-20261003'),
       Path('/home/ghmd/kv260-runtime-live-20261003-retry1')]

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda:stream.read(1048576),b''):h.update(data)
    return h.hexdigest()

for root in ROOTS:
    index=root/'EVIDENCE.sha256'
    verification=root/'SEAL_VERIFY.json'
    assert not index.exists() and not verification.exists(),'Refusing to amend sealed index'
    paths=sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    records=[(str(p.relative_to(root)),sha(p)) for p in paths]
    index.write_text(''.join(value+'  '+name+'\n' for name,value in records))
    mismatches=[name for name,value in records if sha(root/name)!=value]
    result={'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'root':str(root),'index':index.name,'index_sha256':sha(index),
            'records':len(records),'mismatches':mismatches,'passed':not mismatches,
            'excluded':['__pycache__','*.pyc',index.name,verification.name]}
    verification.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    assert not mismatches
