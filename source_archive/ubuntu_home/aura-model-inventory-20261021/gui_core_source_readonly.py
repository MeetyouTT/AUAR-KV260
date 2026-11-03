import base64,gzip,hashlib,json
from pathlib import Path
root=Path('/home/root/aura-speech-motion-20261021/de989bf024a9/runtime/aura/tools')
names={'realtime_facials.py','idle_body_compositor.py'}
matches={}
for path in sorted(root.glob('*.py')):
 raw=path.read_bytes()
 if b'compose_resize' in raw or b'native_enqueue' in raw:
  matches[path.name]=[{'line':n,'code':line.strip()[:220]} for n,line in enumerate(raw.decode().splitlines(),1) if 'compose_resize' in line or 'native_enqueue' in line or "timings['core']" in line]
  names.add(path.name)
files={}
for name in sorted(names):
 p=root/name
 if not p.is_file():continue
 raw=p.read_bytes();assert len(raw)<250000
 files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
out={'root':str(root),'matches':matches,'files':files}
data=json.dumps(out,separators=(',',':')).encode()
print(json.dumps({'gzip_base64':base64.b64encode(gzip.compress(data,mtime=0)).decode(),'files':len(files)}))
