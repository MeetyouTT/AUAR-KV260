import hashlib,json
from pathlib import Path
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');raw=(root/'startup/config.json').read_bytes();s=json.loads(raw);aura=Path(s['runtime'])/'aura';files=[]
for basename in ('board_dialogue_client.py','board_business.py','board_timeline_clock.py'):
 n=next(k for k in s['component_sha256'] if k.endswith('/'+basename))
 p=aura/n;b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==s['component_sha256'][n];files.append({'name':n,'sha256':s['component_sha256'][n],'source':b.decode()})
print(json.dumps({'status':'PINNED_PUBLIC_CLOCK_SOURCE_ONLY','files':files,'startup_sha256':hashlib.sha256(raw).hexdigest()}))
