"""Prepare a fresh GUI/reference connection; no services or motion are started."""
import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path

R=Path('/home/root/aura-pan-current-20261024/da36c36a')
OLD=Path('/home/root/aura-animation-dialogue-20261026/d6d1617467724213b3d9fd3d11530a47')
G=R/'gui-reference-bound-v2';OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
S=OPS/'pan-face-edge-v5/current-reference-connection-v2'
B=Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2')
BOOT='da36c36a-ef4d-4122-8ad6-cfae3931303e'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT and not G.exists()
assert sha(OLD/'startup/config.json')=='43d918e8dac724149cd9eaa5c3b709f0e7186516b5484f0150fab911bcbecd2f'
startup=json.loads((OLD/'startup/config.json').read_text());A=Path(startup['runtime'])/'aura'
assert all(sha(A/n)==v for n,v in startup['component_sha256'].items())
assert all(sha(S/n)==v for n,v in json.loads((S/'source-pins.json').read_text()).items())
h=get(8790,'/health');u=get(8783,'/api/state')
assert h['pid']==54394 and not h['dpu_schedule']['owner_fenced'] and not u['manual_pan']['automatic_following']
refpath=R/'attended-fixed-reference.json';ref=json.loads(refpath.read_text())
trial=R/('fixed-trajectory-'+ref['authorization_id']+'.json');observer=trial.with_suffix('.preview-motion.json')
report=json.loads(trial.read_text());motion=json.loads(observer.read_text())
assert report['status']=='FIXED_TRAJECTORY_STOPPED_OBSERVATION_PENDING' and report['result']['stop_confirmed']
stopped=report['result']['stopped_readback'];assert stopped['width_us']==stopped['target_us']==1420 and stopped['flags']==0 and stopped['lease_left_ms']==0
assert motion['control_report_path']==str(trial) and motion['measured_samples']>=12
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
clone(Path(startup['runtime']),runtime);NEW=runtime/'aura'
for n in ('manual_vsrv.py','current_reference_release.py'):shutil.copy2(S/'board/motion'/n,NEW/'board/motion'/n)
manifest=json.loads((B/'candidate-manifest.json').read_text());assert sha(B/'candidate-manifest.json')=='ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab'
for n,v in manifest['payload_files'].items():assert sha(B/'driver'/n)==v;shutil.copy2(B/'driver'/n,release/n)
qualification={}
for key,path in [('reference',refpath),('control_report',trial),('observer_report',observer)]:
 name=key+'.json';shutil.copy2(path,release/name);qualification[key]=dict(file=name,sha256=sha(path))
qualification['control_report']['source_path']=str(trial)
rel=dict(schema_version=1,status='CURRENT_REFERENCE_CONNECTION_VSRV2',scope='face_follow_reference_connection_only',
 app='aura-visual-servo-b4096-v2',abi=2,build_id=0x778d2512,boot_id=BOOT,manual_minimum_us=1400,manual_maximum_us=1600,
 manual_motion_enabled=False,physical_range_verified=False,mechanical_reference_calibrated=False,external_waveform_verified=False,
 automatic_following_enabled=False,payload_files=manifest['payload_files'],runtime_files=manifest['runtime_files'],qualification=qualification)
(release/'release.json').write_text(json.dumps(rel,indent=2)+'\n')
prior_path=Path('/home/root/aura-pan-current-20261024/16a07283/direction-calibration.json');prior=json.loads(prior_path.read_text())
assert prior['status']=='HUMAN_DIRECTION_CONFIRMED' and prior['axis_camera_mirrored_control_polarity']==1
assert h.get('mirror_horizontal') is True
started=report['result']['started_mono_s']
outbound=[v for v in motion['samples'] if v.get('state')=='MEASURED_BACKGROUND_SHIFT' and .5<=v['captured_mono_ms']/1000-started<=2.5]
assert len(outbound)>=3 and max(v['dx_px'] for v in outbound)>2
direction=dict(boot_id=BOOT,status='HUMAN_DIRECTION_CONFIRMED',axis_camera_mirrored_control_polarity=1,
 calibration_scope='prior human direction retained and revalidated by current-boot signed image response; no new human direction observation claimed',
 prior_human_direction_evidence=prior,prior_human_direction_sha256=sha(prior_path),
 current_boot_revalidation=dict(control_report_sha256=sha(trial),observer_report_sha256=sha(observer),
  negative_pulse_change_us=15,positive_background_shift_px=max(v['dx_px'] for v in outbound),camera_mirror_horizontal=True),
 current_boot_old_motion_permission_reused=False)
direction_path=NEW/'config/pan_direction.current.json';direction_path.write_text(json.dumps(direction,ensure_ascii=False,indent=2)+'\n')
cfg=json.loads((NEW/'config/pan_manual.local.json').read_text())
cfg.update(boot_id=BOOT,fdt_sha256=sha('/sys/firmware/fdt'),release_manifest=str(release/'release.json'),release_manifest_sha256=sha(release/'release.json'),
 manual_minimum_us=1400,manual_maximum_us=1600,automatic_following_enabled=True,face_follow_config=str(NEW/'config/pan_face.local.json'))
(NEW/'config/pan_manual.local.json').write_text(json.dumps(cfg,indent=2)+'\n')
face=json.loads((NEW/'config/pan_face.local.json').read_text());face['duration_s']=30
face['arguments'].update(context=str(R/'context.json'),**{'app-root':str(NEW),'direction-evidence':str(direction_path),
 'human-evidence':str(release/'reference.json'),'zone-settings':str(R/'face-zone-settings.json')})
(NEW/'config/pan_face.local.json').write_text(json.dumps(face,indent=2)+'\n')
startup['runtime']=str(runtime)
for name in ('board/motion/manual_vsrv.py','board/motion/current_reference_release.py','config/pan_manual.local.json','config/pan_face.local.json','config/pan_direction.current.json'):
 startup['component_sha256'][name]=sha(NEW/name)
assert all(sha(NEW/n)==v for n,v in startup['component_sha256'].items())
shutil.copy2(OLD/'startup/launcher.py',launch/'launcher.py');(launch/'config.json').write_text(json.dumps(startup,indent=2)+'\n')
env=dict(os.environ,PYTHONPATH=str(NEW),PYTHONDONTWRITEBYTECODE='1')
job=subprocess.run(['/usr/bin/python3','-B',str(launch/'launcher.py'),'--config',str(launch/'config.json'),'--preflight'],env=env,capture_output=True,text=True,timeout=30)
assert job.returncode==0,job.stderr[-1000:]
code='import json;from board.motion.manual_vsrv import load_release;load_release(json.load(open('+repr(str(NEW/'config/pan_manual.local.json'))+')))'
job=subprocess.run(['/usr/bin/python3','-B','-c',code],env=env,capture_output=True,text=True,timeout=15)
assert job.returncode==0,job.stderr[-1000:]
s=json.loads((R/'state.json').read_text());s.update(phase='CURRENT_REFERENCE_GUI_PREPARED_NO_MOTION',gui_release=str(G),
 startup_config_sha256=sha(launch/'config.json'),manual_release_sha256=sha(release/'release.json'),current_stopped_readback=stopped,
 previous_gui_release=str(OLD),previous_gui_pid=294019,current_camera_pid=54394,automatic_following=False)
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'gui_pins':len(startup['component_sha256']),'read_only_reference_scope':True,
 'manual_jog_authorized':False,'current_reference_qualification_passed':True,'camera_restarted':False,'gui_restarted':False,'motor_commands':0,'MMIO_opened':False}))
