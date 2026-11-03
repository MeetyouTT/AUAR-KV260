import ast,datetime,hashlib,http.client,json,os,subprocess,time
from pathlib import Path
BOOT='903cfade-b93c-48fa-804e-379be1967313'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
p=root/'startup/config.json';r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':BOOT,'startup_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
assert r['startup_sha256']=='092c2ccf0872cae2f6e13c81e2d8b8a2ffe3b0800ab701566128b5c7947159af'
s=json.loads(p.read_bytes());a=Path(s['runtime'])/'aura'
def raw(p):
 p=Path(p);assert p.is_file() and not p.is_symlink() and p.suffix not in ('.db','.sqlite','.sqlite3');assert p.stat().st_size<=64000000;return p.read_bytes()
def digest(p):return hashlib.sha256(raw(p)).hexdigest()
r['component_count']=len(s['component_sha256'])
keys=[k for k in s['component_sha256'] if any(w in k.lower() for w in ('binding_hub','unified_identity_binding','provisional_voice','face_gallery_readback','board_speaker','identity/resolve'))]
r['relevant_components']={k:{'expected_sha256':s['component_sha256'][k],'actual_sha256':digest(a/k)} for k in keys}
assert r['relevant_components']['tools/unified_identity_binding.py']['actual_sha256']=='85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
assert all(v['actual_sha256']==v['expected_sha256'] for v in r['relevant_components'].values())
source=raw(a/'tools/unified_identity_binding.py').decode();tree=ast.parse(source)
r['identity_source_mtime_ns']=(a/'tools/unified_identity_binding.py').stat().st_mtime_ns
r['patch_uses_existing_voice_query_predicate']="from tools.provisional_voice import query_reply" in source and "query_reply(text,{'state':'UNKNOWN'}) is not None" in source and "IDENTITY_QUERY_DURING_VOICE_ENROLLMENT" in source
ui=json.loads(raw(a/'config/board_avatar_gtk.json'));selected=ui['board_business']['face_readback'];binding=json.loads(raw(selected['path']))
r['selected_binding_sha256']=digest(selected['path']);assert r['selected_binding_sha256']==selected['sha256']=='9ab2533d2c3000d61095f54de2e8199f53461ac085e2f58230ab36149be6af1f'
r['selected_binding_source_count']=len(binding['source_sha256'])
r['binding_camera_owner']={k:binding.get(k) for k in ('board_boot_id','camera_pid','camera_start_ticks','camera_config')}
cam=Path('/proc/79866');r['camera_owner']={'pid':79866,'birth_ticks':(cam/'stat').read_text().rsplit(')',1)[1].split()[19],'command_sha256':hashlib.sha256((cam/'cmdline').read_bytes()).hexdigest()}
assert r['camera_owner']=={'pid':79866,'birth_ticks':'2265436','command_sha256':'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'}
assert binding['board_boot_id']==BOOT and binding['camera_pid']==79866 and binding['camera_start_ticks']=='2265436'
assert digest(binding['camera_config'])==binding['source_sha256'][binding['camera_config']]=='c8df0795664d21d52eab3a4f1cf55e0d1a721577d547c512e83ee1931d80871d'
proc=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,SubState,Result,Job'],capture_output=True,text=True,timeout=3);assert proc.returncode==0
unit=dict(line.split('=',1) for line in proc.stdout.splitlines() if '=' in line);r['gui_unit']=unit
if unit['MainPID']!='0':
 owner=Path('/proc')/unit['MainPID'];r['supervisor_owner']={'pid':int(unit['MainPID']),'birth_ticks':(owner/'stat').read_text().rsplit(')',1)[1].split()[19],'command_sha256':hashlib.sha256((owner/'cmdline').read_bytes()).hexdigest()}
 launch=Path(s['runtime'])/'launch.json'
 if launch.is_file():
  launch=json.loads(raw(launch));r['launch_matches_unit']=launch.get('boot_id')==BOOT and launch.get('supervisor_pid')==int(unit['MainPID'])
  if r['launch_matches_unit']:
   gtk=Path('/proc')/str(launch['pid']);cmd=gtk.joinpath('cmdline').read_bytes();r['gtk_owner']={'pid':launch['pid'],'birth_ticks':(gtk/'stat').read_text().rsplit(')',1)[1].split()[19],'command_sha256':hashlib.sha256(cmd).hexdigest()}
   argv=[x.decode('utf-8') for x in cmd.split(b'\0') if x];r['gtk_argv']=argv
   age=time.monotonic()-int(r['gtk_owner']['birth_ticks'])/os.sysconf('SC_CLK_TCK');r['gtk_process_estimated_start_epoch_ns']=int((time.time()-age)*1e9)
   r['gtk_started_after_patch_file_mtime']=r['gtk_process_estimated_start_epoch_ns']>r['identity_source_mtime_ns']
for port,key,path in ((8783,'gui','/api/state'),(8790,'camera','/health')):
 c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
 try:
  c.request('GET',path);v=c.getresponse();assert v.status==200;body=v.read(2097153);assert len(body)<=2097152;h=json.loads(body)
  if key=='gui':
   b=h.get('board_business',{});r['speaker']={k:b.get('speaker',{}).get(k) for k in ('ready','queued_or_active')}
   r['business']={k:b.get(k) for k in ('started','closed','production_cutover','data_origin')}
   r['business_identity_public_keys']={k:sorted(b[k]) for k in ('identity','identity_binding','binding','face','face_readback') if isinstance(b.get(k),dict)}
   hf=h.get('handsfree_dialogue',{});r['handsfree']={k:hf.get(k) for k in ('enabled','state','microphone_open')}
   r['fault_count']=h.get('runtime_faults',{}).get('count')
  else:r['camera_identity']={k:h.get('identity',{}).get(k) for k in ('ready','enabled')};r['camera_identity_error_present']=bool(h.get('identity',{}).get('error'))
 except (OSError,AssertionError,ValueError,http.client.HTTPException) as exc:r[key+'_api_unavailable_error_type']=type(exc).__name__
 finally:c.close()
r.update(board_mutations=False,project_imported=False,database_opened=False,model_or_microphone_or_motion_requested=False,text_or_images_or_templates_exported=False)
print(json.dumps(r,sort_keys=True))
