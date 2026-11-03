#!/usr/bin/env python3
"""Prepare full evidence readback without modifying any board source or firmware."""
import json
from prepare_live import ROOT,manifest
cfg=json.loads((ROOT/'config.json').read_text())
if (ROOT/'reviewed_payload/config.json').exists():
    cfg=json.loads((ROOT/'reviewed_payload/config.json').read_text())
code="""import io,base64,hashlib,json,tarfile
from pathlib import Path
w=Path(%r)
files=[]
for name in ['logs','agent_logs']:
 if (w/name).exists():files.extend(p for p in (w/name).rglob('*') if p.is_file())
for name in ['config.json','controller-status.json','controller.log','candidate-manager.log','original-remove-review.json','baseline/state.json','baseline/kernel.log','baseline/dfx-journal.log','baseline/fstab']:
 p=w/name
 if p.is_file():files.append(p)
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w:gz') as archive:
 for p in sorted(files):archive.add(str(p),arcname=str(p.relative_to(w)),recursive=False)
data=buffer.getvalue()
print(json.dumps({'work':str(w),'archive_bytes':len(data),'archive_sha256':hashlib.sha256(data).hexdigest(),'members':{str(p.relative_to(w)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files},'archive_base64':base64.b64encode(data).decode()}),flush=True)
"""%cfg['work']
manifest('collect-final',[('archive',code,900)])
