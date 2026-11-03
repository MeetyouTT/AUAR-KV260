"""Download a hash-verified official ARM64 wheel, without installing it."""
import hashlib,json,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path('D:/AIModels/audio-frontend-eval-20261021')
version='1.17.3'
with urllib.request.urlopen(f'https://pypi.org/pypi/onnxruntime/{version}/json',timeout=25) as r:
    metadata=json.load(r)
matches=[x for x in metadata['urls'] if 'cp39-cp39' in x['filename'] and 'aarch64' in x['filename']]
assert len(matches)==1
a=matches[0];assert a['size']<25*1024*1024
target=ROOT/a['filename']
if target.exists():data=target.read_bytes()
else:
    with urllib.request.urlopen(a['url'],timeout=35) as r:data=r.read(a['size']+1)
assert len(data)==a['size']
assert hashlib.sha256(data).hexdigest()==a['digests']['sha256']
if not target.exists():target.write_bytes(data)
manifest={'version':version,'filename':a['filename'],'path':str(target),'size':a['size'],
          'url':a['url'],'official_sha256':a['digests']['sha256'],
          'installed_to_system':False,'production_changed':False}
(HERE/'board_runtime_wheel.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest))
