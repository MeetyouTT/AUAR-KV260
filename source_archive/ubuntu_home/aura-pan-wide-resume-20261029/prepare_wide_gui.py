import hashlib,json,os,shutil,subprocess,urllib.request
from pathlib import Path
BOOT='55152f95-ea3a-4c6c-82e6-51bd553d96fd'
R=Path('/home/root/aura-pan-wide-resume-20261029/55152f95')
OLD=Path('/home/root/aura-device-skills-20261028/0cd7c3445a84475098b938d5b97175e0')
G=Path('/home/root/aura-pan-wide-resume-20261029/gui-wide-v1')
B=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
C=Path('/home/root/aura-pan-wide-20261028/control-10282601')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as f:return json.load(f)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT and not G.exists()
assert sha(OLD/'startup/config.json')=='69fa9b565e9e37cbe7d8cb5a6f2aaa071ee2fb2842845c2d7b6e1cd232f2e444'
s=json.loads((R/'state.json').read_text());assert s['phase']=='WIDE_CAMERA_RUNNING_GUI_HELD'
assert subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()=='0'
h=get(8790,'/health');assert h['pid']==s['camera_pid'] and h['identity']['ready'] and not h['dpu_schedule']['owner_fenced']
startup=json.loads((OLD/'startup/config.json').read_text());A=Path(startup['runtime'])/'aura'
assert all(sha(A/n)==v for n,v in startup['component_sha256'].items())
manifest=json.loads((B/'candidate-manifest.json').read_text());assert sha(B/'candidate-manifest.json')==s['wide_manifest_sha256']
assert sha(C/'deployment-manifest.json')=='5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562'
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
changed=[]
for name in ['manual.py','manual_live_config.py','manual_vsrv.py','follow_readback.py','vsrv_driver.py','rated_range_release.py']:
 relative='board/motion/'+name;p=B/'gui_patch'/relative
 if name!='rated_range_release.py':assert sha(A/relative)==EXPECTED_BASE[relative]
 shutil.copy2(p,NEW/relative);changed.append(relative)
for name,digest in manifest['payload_files'].items():
 assert sha(B/'driver'/name)==digest;shutil.copy2(B/'driver'/name,release/name)
proof=json.loads((R/'wide-platform-proof.json').read_text());assert proof['identity_stop_passed'] and proof['boot_id']==BOOT
shutil.copy2(R/'wide-platform-proof.json',release/'platform-proof.json')
auth={'schema':'aura-explicit-rated-range-1','boot_id':BOOT,'bounds_us':[500,2500],'nominal_center_us':1500,'requested_angles_deg':[-90,90],'clearance_confirmed':True,'physical_calibration_claimed':False,'user_instruction_quote':'现在要求放开整个舵机转动角度，可以转左右各90度；直接上你做的，其他我自会评定','range_evaluation_by_user':True}
(release/'authorization.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2)+'\n')
rel={'schema_version':1,'status':'USER_RATED_RANGE_VSRV2','scope':'explicit_user_rated_pulse_range','app':'aura-visual-servo-b4096-wide-v1','abi':2,'build_id':0x10282601,'boot_id':BOOT,'manual_minimum_us':500,'manual_maximum_us':2500,'physical_range_verified':False,'mechanical_reference_calibrated':False,'external_waveform_verified':False,'automatic_following_enabled':False,'payload_files':manifest['payload_files'],'runtime_files':manifest['runtime_files'],'authorization':{'file':'authorization.json','sha256':sha(release/'authorization.json')},'platform_proof':{'file':'platform-proof.json','sha256':sha(release/'platform-proof.json')}}
(release/'release.json').write_text(json.dumps(rel,indent=2)+'\n')
direction_path=NEW/'config/pan_direction.current.json';direction=json.loads(direction_path.read_text());assert direction['axis_camera_mirrored_control_polarity']==1 and h['mirror_horizontal'] is True
direction['historical_confirmation_boot_id']=direction.get('boot_id');direction['boot_id']=BOOT;direction['calibration_scope']='Previous human direction retained for user evaluation; no new angle measurement';direction['current_boot_old_motion_permission_reused']=False
direction_path.write_text(json.dumps(direction,ensure_ascii=False,indent=2)+'\n')
manual_path=NEW/'config/pan_manual.local.json';cfg=json.loads(manual_path.read_text())
cfg.update(boot_id=BOOT,fdt_sha256=s['fdt_sha256'],release_manifest=str(release/'release.json'),release_manifest_sha256=sha(release/'release.json'),manual_minimum_us=500,manual_maximum_us=2500,center_reference_us=1500,center_reference_source='NOMINAL_PULSE_CENTER_NOT_MEASURED_PHYSICAL_ANGLE',automatic_following_enabled=True,face_follow_config=str(NEW/'config/pan_face.local.json'))
manual_path.write_text(json.dumps(cfg,indent=2)+'\n')
face_path=NEW/'config/pan_face.local.json';face=json.loads(face_path.read_text());zone=json.loads(Path(face['arguments']['zone-settings']).read_text());zone['board_boot_id']=BOOT
zone_path=R/'face-zone-settings.json';zone_path.write_text(json.dumps(zone,indent=2)+'\n')
face.update(release_root=str(C),manifest_sha256=sha(C/'deployment-manifest.json'),duration_s=0)
face['arguments'].update(manifest=str(B/'candidate-manifest.json'),**{'manifest-sha256':sha(B/'candidate-manifest.json'),'context':str(R/'context.json'),'app-root':str(NEW),'direction-evidence':str(direction_path),'human-evidence':str(release/'authorization.json'),'zone-settings':str(zone_path)})
face_path.write_text(json.dumps(face,indent=2)+'\n')
changed+=['config/pan_manual.local.json','config/pan_face.local.json','config/pan_direction.current.json']
startup['runtime']=str(runtime)
preserved=sum(n not in changed for n in startup['component_sha256'])
for n in changed:startup['component_sha256'][n]=sha(NEW/n)
assert all(sha(NEW/n)==v for n,v in startup['component_sha256'].items())
shutil.copy2(OLD/'startup/launcher.py',launch/'launcher.py');(launch/'config.json').write_text(json.dumps(startup,indent=2)+'\n')
env=dict(os.environ,PYTHONPATH=str(NEW),PYTHONDONTWRITEBYTECODE='1')
for argv in [['/usr/bin/python3','-B',str(launch/'launcher.py'),'--config',str(launch/'config.json'),'--preflight'],['/usr/bin/python3','-B','-c','import json;from board.motion.manual_vsrv import load_release;load_release(json.load(open('+repr(str(manual_path))+')))']]:
 p=subprocess.run(argv,env=env,capture_output=True,text=True,timeout=30);assert p.returncode==0,p.stderr[-1000:]
result={'phase':'WIDE_GUI_PREPARED','boot_id':BOOT,'gui':str(G),'old_gui':str(OLD),'config_sha256':sha(launch/'config.json'),'camera_pid':h['pid'],'components':len(startup['component_sha256']),'preserved_components':preserved,'changed_components':changed,'manual_range_us':[500,2500],'nominal_center_us':1500,'motion_commands':0,'user_evaluates_physical_range':True}
(R/'wide-gui-prepared.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
