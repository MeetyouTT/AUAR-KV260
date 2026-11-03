import datetime,hashlib,http.client,json
from pathlib import Path
EXPECTED={'tools/unified_identity_binding.py': '85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809', 'common/identity_links.py': 'e623e5d15f81f5f66505b6345c6f807270409fea67a60f506c61e1f021b7150b', 'common/binding_intent.py': '8cfe3c841248b7ca56553255dcb14e400c5b52ea011e68ecd89a16862a7eb796', 'common/voice_enrollment.py': '238939dbc4afa0559caa8687ff01a67854b606a33df4bdeaf2b0103fb8c994a8', 'tools/enrollment_receipts.py': '01f598d49ab777a90dc0f97cfb79f002bacf17fac61c6e9235c39fb18e646663', 'tools/speaker_device.py': 'da9c199527abdf9e247661d8798f4345cf0b79524f5c2a06394b5dc9c44107de', 'common/speaker_identity.py': 'c3dead40ff6c67bae9c1f77c395ea9b33b2d28cd4479f72644ff210431563e65', 'board/identity/voice_enrollment.py': '83796dd78c57555ea66eeb2b745a89f8b3670945a4406176cb3486111d9466b8', 'tools/binding_hub_runtime.py': '80b20963160242eb06fca69dd0fd5774251d1da626f5de718cefa276bd58b375', 'board/runtime/board_speaker_business.py': '6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816', 'board/runtime/board_business.py': 'b08209eca7979825e26845080bca5e1d64e065d3cabd1178df763a93540573f2', 'board/runtime/audio/face_gallery_readback.py': 'b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'}
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');raw=(root/'startup/config.json').read_bytes();s=json.loads(raw);aura=Path(s['runtime'])/'aura';ui=json.loads((aura/'config/board_avatar_gtk.json').read_bytes());spec=ui['board_business']['face_readback'];bindingraw=Path(spec['path']).read_bytes();binding=json.loads(bindingraw)
checks={};changed_public_sources={}
for name,expected in EXPECTED.items():
 p=aura/name;assert p.is_file() and not p.is_symlink() and p.resolve()==p and p.stat().st_size<150000
 r=p.read_bytes();actual=hashlib.sha256(r).hexdigest();checks[name]={'current_pin':s['component_sha256'].get(name),'actual_sha256':actual,'matches_known_public_source':expected==actual,'pin_matches_actual':s['component_sha256'].get(name)==actual}
 if actual!=expected:changed_public_sources[name]={'sha256':actual,'text':r.decode('utf-8')}
def get(port,path):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
 try:
  c.request('GET',path);r=c.getresponse();b=r.read(2097153);assert r.status==200 and len(b)<=2097152;return json.loads(b)
 finally:c.close()
def stage(value):
 if not isinstance(value,dict):return {}
 out={k:v for k,v in value.items() if k in ('active','available','samples','accepted','count','pool_frames','passed','needed','usable','elapsed_ms','timeout_ms','ready') and type(v) in (bool,int,float)}
 if value.get('stage') in ('idle','name','confirm_name','prepare_name','confirm_update','samples','confirm','sampling','ready','failed','cancelled','completed','update_name'):out['stage']=value['stage']
 return out
g=get(8783,'/api/state');u=get(8790,'/v1/ui/status');enroll=g.get('board_business',{}).get('dialogue',{}).get('voice_enrollment',{});sampling=u.get('modules',{}).get('identity',{}).get('enrollment_sampling',{})
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'startup_sha256':hashlib.sha256(raw).hexdigest(),'source_snapshot_stable':(root/'startup/config.json').read_bytes()==raw,'source_checks':checks,'changed_public_sources':changed_public_sources,'selected_sha256':hashlib.sha256(bindingraw).hexdigest(),'selected_pin_matches_actual':hashlib.sha256(bindingraw).hexdigest()==spec['sha256'],'voice_enrollment':stage(enroll),'voice_enrollment_public_keys':sorted(enroll) if isinstance(enroll,dict) else [],'nested_speaker_stage':stage(enroll.get('speaker',{})) if isinstance(enroll,dict) else {},'nested_speaker_public_keys':sorted(enroll['speaker']) if isinstance(enroll,dict) and isinstance(enroll.get('speaker'),dict) else [],'face_sampling':stage(sampling),'face_sampling_public_keys':sorted(sampling) if isinstance(sampling,dict) else [],'raw_names_ids_templates_images_transcripts_exported':False,'board_mutations':False,'recording_or_command_requested':False,'motor_or_private_store_opened':False}))
