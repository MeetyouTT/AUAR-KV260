import hashlib,json,urllib.request
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
P=F/'continuous-v10r14';OLD=F/'continuous-v10r12'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'deployment-manifest.json')=='d7bdb9576311df8a6e77fbfe1833532e05cd9e286ada30756e5fbf668db0c3dd'
m=json.loads((P/'deployment-manifest.json').read_text())
for pin in m['files']:
 p=Path(pin['destination']);rel=p.relative_to(P)
 if not p.exists():
  source=OLD/rel;assert sha(source)==pin['sha256']
  p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(source.read_bytes())
 assert sha(p)==pin['sha256']
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:manual=json.load(f)['manual_pan']
assert manual['state']=='READY' and not manual['automatic_following']
assert manual['readback']['flags']==0 and manual['readback']['lease_left_ms']==0
print(json.dumps({'status':'R14_PREPARED_NO_MOTION','pins':len(m['files']),
 'manifest_sha256':sha(P/'deployment-manifest.json'),'readback':manual['readback'],'motor_commands_sent':0}))
