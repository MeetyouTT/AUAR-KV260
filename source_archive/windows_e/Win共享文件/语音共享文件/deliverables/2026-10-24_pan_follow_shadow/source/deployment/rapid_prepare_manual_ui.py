"""Prepare a fresh GUI config/release from this boot's observed motion proof."""
import copy,hashlib,json,os,shutil,subprocess
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/463c9307');OLDGUI=Path('/home/root/aura-pan-ui-v2-20261024/observed-ecfbdef064d157b6');G=R/'gui-release'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=json.loads((R/'state.json').read_text());assert s['phase']=='CURRENT_BOOT_FINITE_RETURN_STOPPED_OBSERVATION_PENDING'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot'] and not G.exists()
trial=Path(s['trial']);assert sha(trial)==s['trial_sha256']
human={'status':'HUMAN_OBSERVED_20US_RETURN_CONFIRMED','boot_id':s['boot'],'trial_sha256':sha(trial),'movement_and_return_stop_observed':True,'external_waveform_verified':False,'feedback_verbatim':'看到了，来会停住','direction_verified':False}
G.mkdir(mode=0o700);runtime=G/'runtime';runtime.mkdir();startup=G/'startup';startup.mkdir();release=G/'manual-release';release.mkdir()
gui=json.loads((OLDGUI/'startup/config.json').read_text());old=Path(gui['runtime'])
excluded={'stage.log','managed-runs','launch.json','__pycache__'}
def clone(src,dst):
 for p in src.iterdir():
  if p.name in excluded or p.suffix=='.pyc':continue
  q=dst/p.name
  if p.is_symlink():
   if p.name=='config' and p.is_dir():q.mkdir();clone(p.resolve(),q)
   else:q.symlink_to(p.resolve(strict=True),target_is_directory=p.is_dir())
  elif p.is_dir():q.mkdir();clone(p,q)
  else:shutil.copy2(p,q)
clone(old,runtime)
board=Path(s['old_root']);manifest=json.loads((board/'candidate-manifest.json').read_text())
shutil.copy2(board/'driver/libvsrv.so',release/'libvsrv.so')
for n in ['vsrv_driver.py','vsrv_transport.py']:shutil.copy2(runtime/'aura/board/motion'/n,release/n)
shutil.copy2(trial,release/'observed-trial.json');(release/'human-observation.json').write_text(json.dumps(human,ensure_ascii=False,indent=2)+'\n')
rel={'schema_version':1,'status':'OBSERVED_MANUAL_VSRV2','scope':'finite_manual_only','app':'aura-visual-servo-b4096-v2','abi':2,'build_id':0x778d2512,'boot_id':s['boot'],
 'manual_minimum_us':1425,'manual_maximum_us':1445,'external_waveform_verified':False,'physical_servo_response_verified':True,'dpu_coexistence_verified':True,
 'dpu_coexistence_scope':'current native YOLO primary; SFace LATCHED retained','automatic_following_enabled':False,'mechanical_reference_calibrated':False,
 'payload_files':{n:sha(release/n) for n in ['libvsrv.so','vsrv_driver.py','vsrv_transport.py']},'runtime_files':manifest['runtime_files'],
 'trial_sha256':sha(release/'observed-trial.json'),'observation_sha256':sha(release/'human-observation.json')}
(release/'release.json').write_text(json.dumps(rel,indent=2)+'\n')
cfg={'enabled':True,'boot_id':s['boot'],'fdt_sha256':s['fdt_sha256'],'release_manifest':str(release/'release.json'),'release_manifest_sha256':sha(release/'release.json'),
 'manual_minimum_us':1425,'manual_maximum_us':1445,'maximum_step_us':20,'maximum_duration_s':2}
(runtime/'aura/config/pan_manual.local.json').write_text(json.dumps(cfg,indent=2)+'\n')
gui['runtime']=str(runtime);gui['component_sha256']['config/pan_manual.local.json']=sha(runtime/'aura/config/pan_manual.local.json')
shutil.copy2(OLDGUI/'startup/launcher.py',startup/'launcher.py');(startup/'config.json').write_text(json.dumps(gui,indent=2)+'\n')
env=dict(os.environ,PYTHONPATH=str(runtime/'aura'),PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run(['/usr/bin/python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],env=env,capture_output=True,text=True,timeout=25);assert p.returncode==0,p.stderr[-700:]
code='from board.motion.manual_vsrv import load_release;import json;load_release(json.load(open('+repr(str(runtime/'aura/config/pan_manual.local.json'))+')))'
p=subprocess.run(['/usr/bin/python3','-B','-c',code],env=env,capture_output=True,text=True,timeout=10);assert p.returncode==0,p.stderr[-700:]
s.update(phase='MANUAL_UI_PREPARED_HUMAN_CONFIRMED',gui_release=str(G),manual_release_sha256=sha(release/'release.json'),startup_config_sha256=sha(startup/'config.json'),human_observation_confirmed=True)
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'phase':s['phase'],'observed_bounds_us':[1425,1445],'source_pins_verified':len(gui['component_sha256']),'physical_response_observed':True,'direction_verified':False,'services_restarted':False,'register_access':False}))
