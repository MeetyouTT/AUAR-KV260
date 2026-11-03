"""Reuse verified board payload bytes; upload only the corrected manifest files."""
import base64
import json
from pathlib import Path
import zipfile

WORK=Path(__file__).resolve().parent
bundle=json.loads((WORK/'capture_bundle.json').read_text())
old=json.loads((WORK/'generations/005fdaf883ebcb7b/manifest.json').read_text())
old_root='/home/root/aura-asr-integration-20261016/update-005fdaf883ebcb7b/payload'
with zipfile.ZipFile(WORK/bundle['zip']) as archive:
    manifest=json.loads(archive.read('manifest.json'))
    changed={name:base64.b64encode(archive.read(name)).decode() for name,row in manifest['files'].items()
             if row!=old['files'].get(name)}
source='''"""Install corrected, audited ASR update using unchanged verified staged bytes."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
MANIFEST = %r
OVERRIDES = %r
OLD = Path(%r)
STAGE = Path(%r)
assert not STAGE.exists()
PAYLOAD=STAGE/'payload';PAYLOAD.mkdir(parents=True)
for name,row in MANIFEST['files'].items():
    data=base64.b64decode(OVERRIDES[name],validate=True) if name in OVERRIDES else (OLD/name).read_bytes()
    assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    target=PAYLOAD/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(data)
(PAYLOAD/'manifest.json').write_text(json.dumps(MANIFEST,indent=2)+'\\n')
p=subprocess.run(['python3','-B',str(PAYLOAD/'board_deploy.py')],
                 stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=38)
if p.returncode:
    print(json.dumps({'exit_code':p.returncode,'output':p.stdout[-8000:]}));raise SystemExit(p.returncode)
print(p.stdout,end='')
'''%(manifest,changed,old_root,bundle['board_root'])
(WORK/'board_stage_fixed.py').write_text(source)
ready=WORK/'board_ready.py'
ready.write_text(ready.read_text().replace('update-005fdaf883ebcb7b','update-'+manifest['update_id']))
print(json.dumps({'update_id':manifest['update_id'],'changed_payloads':list(changed),'helper_bytes':len(source.encode())}))
