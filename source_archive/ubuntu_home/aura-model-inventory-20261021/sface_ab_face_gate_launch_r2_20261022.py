import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/sface-retry-ab/331f485bd54678ae')
source=Path(json.loads((root/'prepared.json').read_text())['source'])
assert hashlib.sha256(source.read_bytes()).hexdigest()=='331f485bd54678aea972fb09078573eaf45ff08fab82a931fd17709c2e203bf9'
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
old=root/'launch-result.json';prior=json.loads(old.read_text())
assert prior.get('error')=='AssertionError: One actual face is required before A/B start'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));deadline=time.monotonic()+24;counts=[];stable=0
while time.monotonic()<deadline:
 with op.open('http://127.0.0.1:8790/v1/ui/status',timeout=2) as f:value=json.load(f)
 count=value.get('modules',{}).get('identity',{}).get('face_count');counts.append(count)
 stable=stable+1 if count==1 else 0
 if stable>=3:break
 time.sleep(.5)
if stable>=3:
 archive=root/'launch-result-before-r2.json';assert not archive.exists();old.rename(archive)
 unit='aura-sface-ab-331f485bd54678ae-r2'
 result=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=360','--setenv=AURA_SFACE_AB_MODE=run','/usr/bin/python3','-B',str(source)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5)
 assert result.returncode==0,result.stdout.decode(errors='replace')
 print(json.dumps({'started':True,'unit':unit,'face_samples':counts}))
else:print(json.dumps({'started':False,'reason':'FACE_NOT_STABLE','face_samples':counts}))
