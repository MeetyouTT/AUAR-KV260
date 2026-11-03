import hashlib,json,shutil,urllib.request
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as r:m=json.load(r)['manual_pan']
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
pins={'libvsrv_batch.so':'93e17fdfd312a565e7cd560b73c7958f34eda3f9024ebeb25327e95494009b76',
      'libaura_trajectory.so':'d08abd38232b6b7040b84befdd45c925a53885774ece339bdc1bf21f5adedd7a'}
for name,digest in pins.items():
 source=F/'continuous-v6'/name;dest=F/'continuous-v7'/name
 assert hashlib.sha256(source.read_bytes()).hexdigest()==digest and not dest.exists()
 with dest.open('xb') as out:out.write(source.read_bytes())
 assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
print(json.dumps({'status':'V7_PINNED_LIBRARIES_REUSED','files':list(pins),'ARM':0,'COMMIT':0}))
