import json,hashlib,http.client,subprocess
from pathlib import Path
def get():
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:c.request('GET','/api/state');r=c.getresponse();return json.loads(r.read(2097152))
 finally:c.close()
def unit(n):
 r=subprocess.run(['systemctl','show',n,'--property=MainPID,ActiveState,SubState,Job'],capture_output=True,text=True,timeout=4);return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
v=get();h=v.get('handsfree_dialogue') or {};b=v.get('board_business') or {};sp=b.get('speaker') or {};en=(b.get('dialogue') or {}).get('voice_enrollment') or {}
r={'read_only':True,'phase':v.get('phase'),'ui_page':v.get('ui_page'),'handsfree':{k:h.get(k) for k in ('enabled','microphone_open','state')},'playing':v.get('playing'),'pending_job':bool(v.get('pending_job')),'following':(v.get('manual_pan') or {}).get('automatic_following'),'speaker_active':sp.get('active'),'speaker_queued':sp.get('queued_or_active'),'enrollment_active':en.get('active'),'units':{n:unit(n) for n in ('aura-avatar-ui.service','aura-camera-ui.service','aura-face-zone-editor.service')}}
for key,path in {'editor':'/home/root/aura-boundary-nav-20261029/editor-page-sync-v2/face_zone_editor.py','startup':'/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json'}.items():
 p=Path(path);r[key+'_exists']=p.is_file();r[key+'_sha256']=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
print(json.dumps(r))
