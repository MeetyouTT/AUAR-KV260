import hashlib,http.client,json
from pathlib import Path
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');startupraw=(root/'startup/config.json').read_bytes();startup=json.loads(startupraw);aura=Path(startup['runtime'])/'aura';ui=json.loads((aura/'config/board_avatar_gtk.json').read_bytes());binding=json.loads(Path(ui['board_business']['face_readback']['path']).read_bytes());run=json.loads(Path(binding['camera_config']).read_bytes());native=Path(run['native_execution']['source_manifest']).parent/'aura'
def get(port,path):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
 try:
  c.request('GET',path);r=c.getresponse();b=r.read(2097153);assert r.status==200 and len(b)<=2097152;return json.loads(b)
 finally:c.close()
h=get(8790,'/health');g=get(8783,'/api/state');d=h['identity'].get('match_diagnostics',{})
sources={}
for namespace,base,names in [('native',native,('board/identity/live.py','board/identity/camera_faces.py','board/identity/model_store.py')),('business',aura,('tools/profile_control.py',)),('startup',root,('startup/launcher.py',))]:
 for name in names:
  p=base/name
  if not p.is_file():continue
  assert not p.is_symlink() and p.resolve()==p and p.stat().st_size<80000
  raw=p.read_bytes();sources[namespace+'/'+name]={'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode('utf-8')}
launch=json.loads((Path(startup['runtime'])/'launch.json').read_bytes());args=launch['args']
profile=g.get('board_business',{}).get('dialogue',{}).get('profile_memory',{});enroll=g.get('board_business',{}).get('dialogue',{}).get('voice_enrollment',{})
print(json.dumps({'source_snapshot_stable':(root/'startup/config.json').read_bytes()==startupraw,'sources':sources,'match_diagnostics_keys':sorted(d) if isinstance(d,dict) else [],'match_diagnostics_numeric_policy':{k:d[k] for k in ('threshold','ambiguity_margin','result_ttl_ms') if isinstance(d,dict) and k in d and type(d[k]) in (int,float)},'match_diagnostics_reason_enum':next((d[k] for k in ('reason_code','reason','state','status') if isinstance(d,dict) and d.get(k) in ('WAITING_FRAME','NO_FACE_OR_TARGET','TARGET_UNCONFIRMED','LOW_SIMILARITY','EMPTY_GALLERY','MATCHED','AMBIGUOUS','STALE_OR_FOREIGN_RESULT','KNOWN','UNKNOWN')),None),'launch_args_type':type(args).__name__,'launch_args_keys':sorted(args) if isinstance(args,dict) else [],'profile_memory_public_keys':sorted(profile) if isinstance(profile,dict) else [],'voice_enrollment_public_keys':sorted(enroll) if isinstance(enroll,dict) else [],'raw_identity_or_dialogue_exported':False,'board_mutations':False}))
