import hashlib,json
from pathlib import Path
p=Path('/home/root/aura-dpu-vision-20261021/shadow-pilots/d6f06aa970649c9e-164822/deployment-result.json')
data=p.read_bytes();value=json.loads(data)
assert value['complete'] and value['passed'] and value['rollback_verified']
assert not value['rollback_timer_left_armed'] and value['shadow_completed']>=3 and value['shadow_accepted']>=3
assert value['identity_backend_changed'] is False and value['identity_database_configuration_changed'] is False
assert value['compare_cosine'] is False
assert value['camera_after']['shadow']['identity_decisions_from_shadow']==0
assert value['camera_after']['shadow']['templates_written']==0
print(json.dumps({'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'report':value}))
