import ast,datetime,hashlib,http.client,json
from pathlib import Path
EXPECTED={'tools/production_board_business_gui.py': 'b01f6edb9efe88cf95da60900e5ccc32eec93a24ef3f515ab08f51ae2ee6ada8', 'board/runtime/audio/channel_jobs.py': '015e13d27db25819d002c4c87087802e02e8b65ac10119bf467635871b458822', 'board/interaction/ui_services.py': 'b55ee295e2cb5494f387fbaa4aa081fd1d6bffd57588c018c5f31daae56bd711', 'board/identity/voice_enrollment.py': '83796dd78c57555ea66eeb2b745a89f8b3670945a4406176cb3486111d9466b8', 'board/runtime/board_business.py': 'b08209eca7979825e26845080bca5e1d64e065d3cabd1178df763a93540573f2'}
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');sr=(root/'startup/config.json').read_bytes();s=json.loads(sr);aura=Path(s['runtime'])/'aura';ui=json.loads((aura/'config/board_avatar_gtk.json').read_bytes());binding=json.loads(Path(ui['board_business']['face_readback']['path']).read_bytes());run=json.loads(Path(binding['camera_config']).read_bytes());manifestpath=Path(run['native_execution']['source_manifest']);manifest=json.loads(manifestpath.read_bytes());native=manifestpath.parent/'aura'
checks={}
for name,expected in EXPECTED.items():
 actual=hashlib.sha256((aura/name).read_bytes()).hexdigest();checks[name]={'actual_sha256':actual,'pin_matches_actual':s['component_sha256'].get(name)==actual,'matches_reviewed_public_source':actual==expected}
def get(port,path):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
 try:
  c.request('GET',path);r=c.getresponse();b=r.read(2097153);assert r.status==200 and len(b)<=2097152;return json.loads(b)
 finally:c.close()
h=get(8790,'/health');u=get(8790,'/v1/ui/status');i=u.get('modules',{}).get('identity',{});photos=h.get('identity',{}).get('enrollment_photos',{})
photo_health_functions={}
for name,pin in manifest['files'].items():
 if 'photo' not in name or not name.endswith('.py'):continue
 p=native/name;r=p.read_bytes();assert hashlib.sha256(r).hexdigest()==pin;tree=ast.parse(r.decode('utf-8'));lines=r.decode('utf-8').splitlines()
 for n in ast.walk(tree):
  if isinstance(n,ast.FunctionDef) and n.name in ('health','finish','validated'):
   photo_health_functions[name+'::'+n.name]={'path':str(p),'sha256':pin,'source':'\n'.join(lines[n.lineno-1:n.end_lineno])}
operation=i.get('last_operation',{});operation=operation if isinstance(operation,dict) else {}
state_keys=('stage','state','outcome','status','reason_code','error_code')
photo_projection={}
allowed={'ACTIVE','PENDING','COMMITTED','FAILED','REJECTED','idle','collect','validate','ready','failed','committed','cancelled','collecting','validated'}
for key,item in photos.items():
 if type(item) in (bool,int,float):photo_projection[key]=item
 if isinstance(item,dict):photo_projection[key]={'keys':sorted(item),'fixed_states':{k:item[k] for k in state_keys if k in item and item[k] in allowed},'error_present':any(bool(item.get(k)) for k in ('error','reason','error_code'))}
people=i.get('people');caps=u.get('capabilities',{})
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'startup_sha256':hashlib.sha256(sr).hexdigest(),'source_snapshot_stable':(root/'startup/config.json').read_bytes()==sr,'source_checks':checks,'face_catalog_count_from_api':len(people) if isinstance(people,list) else None,'identity_capabilities':{k:caps.get(k) for k in ('identity_enroll','identity_sample_start','identity_sample_cancel') if type(caps.get(k)) is bool},'last_operation_public_keys':sorted(operation),'last_operation_contains_timestamp_field':any('time' in k or 'mono' in k or 'stamp' in k for k in operation),'photo_archive_public_keys':sorted(photos),'photo_archive_projection':photo_projection,'photo_public_source_functions':photo_health_functions,'real_private_databases_templates_or_photos_opened':False,'board_mutations':False}))
