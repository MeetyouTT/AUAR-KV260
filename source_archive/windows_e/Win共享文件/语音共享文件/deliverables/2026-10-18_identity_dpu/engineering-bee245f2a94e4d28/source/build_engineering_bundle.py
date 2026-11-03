"""Create a hashed experimental bundle, with no actual user identity data."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).parent
compiled = json.loads((ROOT/'compiled-engineering-result.json').read_text())
payload = {'sface_engineering.xmodel': ROOT/'compiled-engineering/sface_engineering.xmodel',
           'hardware-reference.npz': ROOT/'hardware-reference.npz',
           'board_engineering_smoke.py': ROOT/'board_engineering_smoke.py'}
rows = {name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size} for name, p in payload.items()}
assert rows['sface_engineering.xmodel']['sha256'] == compiled['sha256']
release = compiled['sha256'][:16]
manifest = {'scope': 'ENGINEERING_SINGLE_PUBLIC_REFERENCE_AND_SYNTHETIC_ONLY', 'files': rows,
            'target_fingerprint': compiled['target_fingerprint'], 'accuracy_accepted': False,
            'production_identity_deployment': False}
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for name, p in payload.items():
        archive.writestr(name, p.read_bytes())
    archive.writestr('manifest.json', json.dumps(manifest, indent=2)+'\n')
blob = buffer.getvalue()
source = Path('/home/ghmd/kv260-adaptation-check-20261006/identity-dpu-engineering-20261018')
source.mkdir(exist_ok=True)
path = source/('engineering-'+hashlib.sha256(blob).hexdigest()[:16]+'.zip')
if path.exists():
    assert path.read_bytes() == blob
else:
    path.write_bytes(blob)
dest = '/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/'+release+'/engineering.zip'
entry = {'source': str(path), 'destination': dest, 'sha256': hashlib.sha256(blob).hexdigest()}
(source/'transfer-manifest.json').write_text(json.dumps([entry], indent=2)+'\n')
(ROOT/'engineering-bundle.json').write_text(json.dumps(dict(entry, bytes=len(blob), model_sha256=compiled['sha256'], stage=str(Path(dest).parent)), indent=2)+'\n')
print(json.dumps(dict(entry, bytes=len(blob))))
