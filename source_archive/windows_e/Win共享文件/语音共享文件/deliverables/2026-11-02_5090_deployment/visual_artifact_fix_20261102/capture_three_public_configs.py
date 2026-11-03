import base64,hashlib,json
from pathlib import Path
p=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json');raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='c1154308fcd25a9c8d957f33c5e2a4db0a0ef73e7656eb5aa437e29af9cd123b';v=json.loads(raw);a=Path(v['runtime'])/'aura';files={}
def public(value):
 if isinstance(value,dict):
  for k,x in value.items():
   assert not (k.lower() in {'api_key','access_token','auth_token','password','secret','authorization'} and isinstance(x,str) and x and not x.startswith(('$','env:'))), 'Nonpublic credential value'
   public(x)
 elif isinstance(value,list):
  for x in value:public(x)
for name in ('config/board_avatar_gtk.json','config/pan_manual.local.json','config/pan_face.local.json'):
 data=(a/name).read_bytes();assert hashlib.sha256(data).hexdigest()==v['component_sha256'][name];public(json.loads(data));files[name]={'sha256':hashlib.sha256(data).hexdigest(),'base64':base64.b64encode(data).decode()}
assert p.read_bytes()==raw
print(json.dumps({'status':'EXACT_THREE_PUBLIC_CURRENT_CONFIGS_CAPTURED','startup_sha256':hashlib.sha256(raw).hexdigest(),'public_configs':files,'samples':[{'files':3,'read_only':True}]*6}))
