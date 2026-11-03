import base64,hashlib,json,os,shutil,subprocess,urllib.request
from pathlib import Path
BOOT='5f167a36-a715-4bbb-9186-4dff2bff8ee3'
R=Path('/home/root/aura-system-pan-20261028/restore-5f167a36')
OLD=Path('/home/root/aura-windows-portrait-20261027/handoff-31b0c262c5b74d52966c00b978dfef3f')
G=Path('/home/root/aura-system-pan-20261028/gui-continuity-v1')
B=Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as f:return json.load(f)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT and not G.exists()
assert sha(OLD/'startup/config.json')=='3d84681a728617eea1cb28b619a376f9b3798a41c04d8fb57759947a3479294f'
startup=json.loads((OLD/'startup/config.json').read_text());A=OLD/'runtime/aura'
assert all(sha(A/n)==v for n,v in startup['component_sha256'].items())
assert sha(A/'board/motion/current_reference_release.py')=='e401cfbcda9e05daa657d94c7d4bf3f9fd85261055df8f2e83d1f8e854040498'
h=get(8790,'/health');u=get(8783,'/api/state')
assert h['pid']==234756 and h['identity']['ready'] and not h['dpu_schedule']['owner_fenced']
assert u['phase']=='IDLE' and not u['playing'] and not u['manual_pan']['automatic_following']
refpath=R/'continuity-reference.json';assert sha(refpath)=='a75418eec6ba40b6187c2f399676aa642124bd022231dee58d7ac28e197e7563'
ref=json.loads(refpath.read_text());assert ref['boot_id']==BOOT and ref['stopped_readback']['width_us']==1400
G.mkdir(mode=0o700);runtime=G/'runtime';runtime.mkdir();release=G/'manual-release';release.mkdir();launch=G/'startup';launch.mkdir()
def clone(src,dst):
 for p in src.iterdir():
  if p.name in {'stage.log','managed-runs','launch.json','__pycache__'} or p.suffix=='.pyc':continue
  q=dst/p.name
  if p.is_symlink():
   if p.name=='config' and p.is_dir():q.mkdir();clone(p.resolve(),q)
   else:q.symlink_to(p.resolve(strict=True),target_is_directory=p.is_dir())
  elif p.is_dir():q.mkdir();clone(p,q)
  else:shutil.copy2(p,q)
clone(OLD/'runtime',runtime);NEW=runtime/'aura'
raw=base64.b64decode(QUALIFIER_BASE64);assert hashlib.sha256(raw).hexdigest()==QUALIFIER_SHA
(NEW/'board/motion/current_reference_release.py').write_bytes(raw)
manifest=json.loads((B/'candidate-manifest.json').read_text())
for n,v in manifest['payload_files'].items():assert sha(B/'driver'/n)==v;shutil.copy2(B/'driver'/n,release/n)
shutil.copy2(refpath,release/'reference.json')
oldraw=base64.b64decode(PREVIOUS_BASE64);assert hashlib.sha256(oldraw).hexdigest()==PREVIOUS_SHA
(release/'previous_stop.json').write_bytes(oldraw)
rel=dict(schema_version=1,status='CURRENT_REFERENCE_CONNECTION_VSRV2',scope='face_follow_reference_connection_only',app='aura-visual-servo-b4096-v2',abi=2,build_id=0x778d2512,boot_id=BOOT,manual_minimum_us=1400,manual_maximum_us=1600,manual_motion_enabled=False,physical_range_verified=False,mechanical_reference_calibrated=False,external_waveform_verified=False,automatic_following_enabled=False,payload_files=manifest['payload_files'],runtime_files=manifest['runtime_files'],qualification={'kind':'USER_CONFIRMED_CONTINUITY','reference':{'file':'reference.json','sha256':sha(release/'reference.json')},'previous_stop':{'file':'previous_stop.json','sha256':sha(release/'previous_stop.json')}})
(release/'release.json').write_text(json.dumps(rel,indent=2)+'\n')
previous_direction=json.loads((NEW/'config/pan_direction.current.json').read_text())
assert previous_direction['axis_camera_mirrored_control_polarity']==1 and h['mirror_horizontal'] is True
direction=dict(boot_id=BOOT,status='HUMAN_DIRECTION_CONFIRMED',axis_camera_mirrored_control_polarity=1,calibration_scope='Previous human direction retained by current user confirmation of unchanged installation and pose; no new angle measurement',prior_human_direction_evidence=previous_direction,current_user_quote=ref['user_quote'],current_boot_old_motion_permission_reused=False)
direction_path=NEW/'config/pan_direction.current.json';direction_path.write_text(json.dumps(direction,ensure_ascii=False,indent=2)+'\n')
cfg=json.loads((NEW/'config/pan_manual.local.json').read_text());cfg.update(boot_id=BOOT,fdt_sha256=ref['fdt_sha256'],release_manifest=str(release/'release.json'),release_manifest_sha256=sha(release/'release.json'),center_reference_us=1400,center_reference_source='USER_CONFIRMED_PREVIOUS_STOP_CONTINUITY_NOT_MECHANICAL_ZERO',face_follow_config=str(NEW/'config/pan_face.local.json'))
(NEW/'config/pan_manual.local.json').write_text(json.dumps(cfg,indent=2)+'\n')
face=json.loads((NEW/'config/pan_face.local.json').read_text());zone=json.loads(Path(face['arguments']['zone-settings']).read_text());zone['board_boot_id']=BOOT
zonepath=R/'face-zone-settings.json';zonepath.write_text(json.dumps(zone,indent=2)+'\n')
face['arguments'].update(context=str(R/'context.json'),**{'app-root':str(NEW),'direction-evidence':str(direction_path),'human-evidence':str(release/'reference.json'),'zone-settings':str(zonepath)})
(NEW/'config/pan_face.local.json').write_text(json.dumps(face,indent=2)+'\n')
startup['runtime']=str(runtime)
changed=['board/motion/current_reference_release.py','config/pan_manual.local.json','config/pan_face.local.json','config/pan_direction.current.json']
for n in changed:startup['component_sha256'][n]=sha(NEW/n)
assert all(sha(NEW/n)==v for n,v in startup['component_sha256'].items())
shutil.copy2(OLD/'startup/launcher.py',launch/'launcher.py');(launch/'config.json').write_text(json.dumps(startup,indent=2)+'\n')
env=dict(os.environ,PYTHONPATH=str(NEW),PYTHONDONTWRITEBYTECODE='1')
for argv in [['/usr/bin/python3','-B',str(launch/'launcher.py'),'--config',str(launch/'config.json'),'--preflight'],['/usr/bin/python3','-B','-c','import json;from board.motion.manual_vsrv import load_release;load_release(json.load(open('+repr(str(NEW/'config/pan_manual.local.json'))+')))']]:
 p=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=30);assert p.returncode==0,p.stderr[-800:]
state={'status':'PREPARED_NOT_ACTIVATED','boot_id':BOOT,'old_gui':str(OLD),'old_gui_pid':234790,'camera_pid':234756,'gui':str(G),'config_sha256':sha(launch/'config.json'),'changed_components':changed,'preserved_components':len(startup['component_sha256'])-len(changed),'motion_commands':0,'reference_sha256':sha(release/'reference.json')}
(R/'gui-prepared.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state))
