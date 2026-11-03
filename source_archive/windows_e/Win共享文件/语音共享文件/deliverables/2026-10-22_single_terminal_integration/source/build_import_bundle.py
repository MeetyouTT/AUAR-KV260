import gzip,hashlib,io,json,tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
meta=json.loads((ROOT/'manifest.json').read_text());items={}
for name,record in meta['files'].items():
    raw=(ROOT/'candidate/aura'/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==record['sha256'] and len(raw)==record['bytes']
    items[name]=raw
items['candidate-manifest.json']=(json.dumps(meta,sort_keys=True,indent=2)+'\n').encode()
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w') as archive:
    for name,raw in sorted(items.items()):
        item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o600;item.mtime=0
        archive.addfile(item,io.BytesIO(raw))
raw=gzip.compress(buffer.getvalue(),mtime=0)
path=Path('/home/ghmd/aura-dpu-vision-20261021/work/single-terminal-merged-20261022.tar.gz')
if path.exists():assert path.read_bytes()==raw
else:path.write_bytes(raw)
value={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'path':str(path),'source_files':len(meta['files'])}
(ROOT/'bundle-provenance.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value))
