"""Finish the UI manifest after all payload files were already checked."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

p=Path('/home/root/aura-touch-recording-20261015/update-ee6bc2c48a5886ae')
data=b''.join(f.read_bytes() for f in sorted(p.glob('fragment-*')))
with zipfile.ZipFile(io.BytesIO(data)) as archive:
    raw=archive.read('manifest.json')
    manifest=json.loads(raw)
    assert manifest['update_id']=='ee6bc2c48a5886ae'
    for name,row in manifest['files'].items():
        blob=(p/'payload'/name).read_bytes()
        assert len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],name
    path=p/'payload/manifest.json'
    if path.exists():assert json.loads(path.read_text())==manifest
    else:
        with path.open('xb') as out:out.write(raw)
print(json.dumps({'status':'PAYLOAD_VERIFIED','update_id':manifest['update_id'],
    'files':len(manifest['files']),'zip_sha256':hashlib.sha256(data).hexdigest()}))
