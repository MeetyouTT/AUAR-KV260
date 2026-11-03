import ast,gzip,hashlib,io,json,tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
files={str(p.relative_to(ROOT/'candidate/aura')):p.read_bytes()
    for p in (ROOT/'candidate/aura').rglob('*.py')}
assert len(files)==14
for raw in files.values():ast.parse(raw)
meta={'status':'OBSERVER_CANDIDATE_NOT_PRODUCTION_RETAINED','default_enabled':False,
    'observer_modes':{'1':'full proc scheduler counters; board overhead prerequisite failed',
        'switches':'context switches only; board overhead prerequisite pending'},
    'files':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in files.items()},
    'tests':[67,66],'native_runtime_and_schedule_sources_unchanged':True}
files['candidate-manifest.json']=(json.dumps(meta,sort_keys=True,indent=2)+'\n').encode()
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w',format=tarfile.PAX_FORMAT) as archive:
    for name,raw in sorted(files.items()):
        item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o600;item.mtime=0
        archive.addfile(item,io.BytesIO(raw))
raw=gzip.compress(buffer.getvalue(),mtime=0)
path=Path('/home/ghmd/aura-dpu-vision-20261021/work/thread-switch-observer-20261022.tar.gz')
if path.exists():assert path.read_bytes()==raw
else:path.write_bytes(raw)
v={'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'manifest':meta}
(ROOT/'live-bundle.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps({k:v[k] for k in ('path','sha256','bytes')}))
