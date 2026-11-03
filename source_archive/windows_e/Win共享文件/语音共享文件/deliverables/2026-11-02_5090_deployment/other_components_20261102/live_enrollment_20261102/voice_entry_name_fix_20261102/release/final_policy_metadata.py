import http.client,json,hashlib
from pathlib import Path
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()=='21c1dbcd454d50875d4fd61c970e269666257dd236c87103c12b1058965de51e'
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
try:
 c.request('GET','/api/state');r=c.getresponse();raw=r.read(2097153);assert r.status==200 and len(raw)<=2097152;v=json.loads(raw)
finally:c.close()
b=v.get('board_business') or {};s=b.get('speaker') or {};d=b.get('dialogue') or {};f=d.get('voice_enrollment') or {};h=v.get('handsfree_dialogue') or {}
print(json.dumps({'speaker_policy':{k:s.get(k) if type(s.get(k)) is bool else None for k in ('ready','active','speaker_calibrated','automatic_profile_access','pcm_persisted')},'registration_inactive':f.get('active') is False,'entry_cleared':f.get('entry_mode') is None,'main_ready_visible':v.get('ui_page')=='main' and (v.get('character_pair') or {}).get('state')=='READY' and (v.get('avatar_display') or {}).get('visible') is True,'listening_enabled':h.get('enabled') is True,'runtime_fault_count':(v.get('runtime_faults') or {}).get('count'),'private_values_exported':False,'board_mutations':False}))
