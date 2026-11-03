"""Prepare official matched ARM SDK wheels; do not install into production."""
import hashlib,json,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path('D:/AIModels/audio-frontend-eval-20261021')
rows=[]
for package in ('sherpa-onnx','sherpa-onnx-core'):
    with urllib.request.urlopen(f'https://pypi.org/pypi/{package}/1.13.8/json',timeout=25) as r:m=json.load(r)
    matches=[a for a in m['urls'] if 'aarch64' in a['filename'] and
             ('cp39-cp39' in a['filename'] if package=='sherpa-onnx' else 'py3-none' in a['filename'])]
    assert len(matches)==1
    a=matches[0];assert a['size']<25*1024*1024
    path=ROOT/a['filename']
    if path.exists():data=path.read_bytes()
    else:
        with urllib.request.urlopen(a['url'],timeout=40) as r:data=r.read(a['size']+1)
    assert len(data)==a['size'] and hashlib.sha256(data).hexdigest()==a['digests']['sha256']
    if not path.exists():path.write_bytes(data)
    rows.append({'package':package,'version':'1.13.8','filename':a['filename'],'path':str(path),
                 'bytes':a['size'],'sha256':a['digests']['sha256'],'url':a['url'],
                 'requires_dist':m['info']['requires_dist']})
r={'wheels':rows,'production_installed':False}
(HERE/'sherpa_runtime_wheels.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r))
