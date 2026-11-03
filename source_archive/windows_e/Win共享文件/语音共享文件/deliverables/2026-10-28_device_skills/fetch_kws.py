"""Read an official release and extract only a small offline CPU KWS model to D:."""
import hashlib,json,tarfile,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;dest=Path(r'D:\AIModels\wake-keyword')
name='sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20.tar.bz2'
req=urllib.request.Request('https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/kws-models',headers={'User-Agent':'Aura-device-validation'})
with urllib.request.urlopen(req,timeout=30) as f:release=json.load(f)
asset=next(a for a in release['assets'] if a['name']==name)
assert asset['size']<100000000 and asset['browser_download_url'].startswith('https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/')
dest.mkdir(parents=True,exist_ok=True);archive=dest/name
if not archive.exists():
 part=archive.with_suffix(archive.suffix+'.part');assert not part.exists(),'Inspect previous partial download first'
 with urllib.request.urlopen(asset['browser_download_url'],timeout=30) as f,part.open('xb') as o:
  total=0
  while chunk:=f.read(1024*1024):
   total+=len(chunk);assert total<=asset['size'];o.write(chunk)
 assert part.stat().st_size==asset['size'];part.replace(archive)
sha=hashlib.sha256(archive.read_bytes()).hexdigest()
if asset.get('digest'):assert asset['digest']=='sha256:'+sha
names=['encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx','decoder-epoch-13-avg-2-chunk-8-left-64.onnx',
       'joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx','tokens.txt']
files={}
with tarfile.open(archive,'r:bz2') as tar:
 for n in names:
  matches=[m for m in tar.getmembers() if Path(m.name).name==n]
  assert len(matches)==1 and matches[0].isfile() and matches[0].size<15000000
  raw=tar.extractfile(matches[0]).read();p=dest/n
  if p.exists():assert p.read_bytes()==raw
  else:p.write_bytes(raw)
  files[n]={'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
v={'source':asset['browser_download_url'],'release_asset_id':asset['id'],'archive_sha256':sha,
   'publisher_digest':asset.get('digest'),'files':files,'status':'ISOLATED_EVALUATION_ONLY','weights_in_shared_tree':False}
(H/'kws_model_manifest.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
(dest/'manifest.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
print(json.dumps(v))
