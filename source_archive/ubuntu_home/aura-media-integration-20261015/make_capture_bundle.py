"""Collect a minimal, hashed capture release; do not change installed services."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
AURA = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
files = {name: (AURA/name).read_bytes() for name in (
    'board/runtime/audio/capture.py', 'host/model_service/protocol.py',
    'tools/board_audio_capture.py')}
for name in ('board/__init__.py', 'board/runtime/__init__.py', 'board/runtime/audio/__init__.py',
             'host/__init__.py', 'host/model_service/__init__.py'):
    files[name] = b'"""Minimal standalone capture release; no model imports."""\n'
manifest = {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            for name, data in sorted(files.items())}
release_id = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
manifest_data = json.dumps({'release_id': release_id, 'files': manifest}, indent=2).encode()
stream = io.BytesIO()
with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, data in sorted(dict(files, **{'manifest.json': manifest_data}).items()):
        entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        archive.writestr(entry, data)
blob = stream.getvalue()
path = ROOT/('capture-'+release_id+'.zip')
if path.exists():
    assert path.read_bytes() == blob
else:
    with path.open('xb') as out:
        out.write(blob)
record = {'release_id': release_id, 'zip': path.name, 'bytes': len(blob),
          'sha256': hashlib.sha256(blob).hexdigest(),
          'board_root': '/home/root/aura-audio-capture-20261015/releases/'+release_id,
          'files': manifest}
(ROOT/'capture_bundle.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({key: record[key] for key in ('release_id','zip','bytes','sha256','board_root')}))
