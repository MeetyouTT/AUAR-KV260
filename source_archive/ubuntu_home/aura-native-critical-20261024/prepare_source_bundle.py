"""Create a source-only private staging archive; does not access the board."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

root=Path(__file__).resolve().parent
candidate=json.loads((root/'latest-integrated.json').read_text())
source=Path(candidate['path'])
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w') as archive:
    for name in sorted(candidate['files_sha256']):
        if not name.startswith('aura/'):continue
        raw=(source/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==candidate['files_sha256'][name]
        info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o600;info.mtime=0
        archive.addfile(info,io.BytesIO(raw))
    for name in ('camera-python-manifest.json','candidate.json'):
        raw=(source/name).read_bytes()
        info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o600;info.mtime=0
        archive.addfile(info,io.BytesIO(raw))
raw=gzip.compress(buffer.getvalue(),mtime=0)
digest=hashlib.sha256(raw).hexdigest()
path=Path('/home/ghmd/aura-dpu-vision-20261021/work')/('native-v2-source-'+digest[:16]+'.tar.gz')
with path.open('xb') as stream:stream.write(raw)
metadata={'candidate_id':candidate['candidate_id'],'bundle':str(path),'bytes':len(raw),
          'sha256':digest,'python_files':candidate['python_files'],'scope':'own source only; no models/ELF/config/database'}
(root/'source-staging-plan.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps(metadata))
