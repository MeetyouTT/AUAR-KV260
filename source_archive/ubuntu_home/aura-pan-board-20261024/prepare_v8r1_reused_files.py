import hashlib,json,urllib.request
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as r:m=json.load(r)['manual_pan']
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
old=F/'continuous-v8/deployment-manifest.json';assert sha(old)=='1c5e6d4c700d5b2e1cb387f4fd1a0af70503b7e516e251f4b701df15af439155'
oldpins={Path(x['destination']).name:x['sha256'] for x in json.loads(old.read_text())['files']}
new=F/'continuous-v8r1';manifest=json.loads((new/'deployment-manifest.json').read_text());copied=[]
for row in manifest['files']:
 dest=Path(row['destination']);assert dest.parent==new
 if dest.exists():assert sha(dest)==row['sha256'];continue
 source=old.parent/dest.name;assert oldpins[dest.name]==row['sha256']==sha(source)
 with dest.open('xb') as out:out.write(source.read_bytes())
 assert sha(dest)==row['sha256'];copied.append(dest.name)
print(json.dumps({'status':'V8R1_UNCHANGED_PINNED_FILES_REUSED','files':copied,'ARM':0,'COMMIT':0}))
