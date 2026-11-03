import hashlib,json,urllib.request
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='16a07283-9e14-45e6-816d-3bda4cf333a7'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
assert not u['manual_pan']['automatic_following'] and u['manual_pan']['state']=='FAULT'
S=F/'shadow-v10r2';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S/'manifest.json')=='51265395999f650b9e00465a5a56f7000d447113c0ff6d53de66db33cefd63ec'
src=F/'continuous-v9/libaura_trajectory.so';dest=S/'libaura_trajectory.so'
assert sha(src)=='d08abd38232b6b7040b84befdd45c925a53885774ece339bdc1bf21f5adedd7a'
if not dest.exists():
 with dest.open('xb') as f:f.write(src.read_bytes())
pins=json.loads((S/'manifest.json').read_text())['files']
assert all(sha(S/n)==h for n,h in pins.items())
print(json.dumps({'status':'SHADOW_R2_PINS_READY','files_verified':len(pins),'MMIO_opened':False,'physical_ARM':0,'physical_COMMIT':0}))
