"""Fresh GUI copy and manual proof for this boot. No MMIO or service changes."""
import hashlib,json,os,shutil,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283')
OLD=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');G=R/'gui-manual-bound-v1'
SOURCE=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/current-boot-manual-v1')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as response:return json.load(response)
s=json.loads((R/'state.json').read_text());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==s['boot']=='16a07283-9e14-45e6-816d-3bda4cf333a7' and s['phase']=='USER_PAUSED_OUTPUT_STOPPED_20US_OBSERVED_CENTER_1420'
assert not G.exists() and sha(OLD/'startup/config.json')=='c05af12f37ed50f59a6b1a9fcdbdcf827d3bdbeee7bf51e2d8affeb4291b3385'
gui=json.loads((OLD/'startup/config.json').read_text());old=Path(gui['runtime'])
assert all(sha(old/'aura'/p)==h for p,h in gui['component_sha256'].items())
assert sha(old/'aura/tools/face_pan_controls.py')=='cb973b5a6dc1e783e0fef84231964c825e24028cf83aaa831777a4594868d20c'
assert sha(SOURCE/'face_pan_controls.py')=='8b4ce76a2e8a148bb2344c803497c2518e7d5b639b6ca42c5a20908b2e68f2e4'
h=get(8790,'/health');u=get(8783,'/api/state')
assert h['pid']==13537 and not h['dpu_schedule']['owner_fenced'] and not u['manual_pan']['automatic_following']
assert u['manual_pan']['state']=='FAULT'
trial=R/'relative-20us-no-init.json';human=R/'relative-20us-human-observation.json';observation=json.loads(human.read_text())
assert sha(trial)=='eb7ec28fbc083be7a312d10b6d26d736c96fe992106ada0821fe94f8d1e3f341'
assert observation['boot_id']==boot and observation['trial_sha256']==sha(trial) and observation['movement_and_return_stop_observed']
assert observation['center_reference_us']==1420 and not observation['center_command_applied']
G.mkdir(mode=0o700);runtime=G/'runtime';runtime.mkdir();startup=G/'startup';startup.mkdir();release=G/'manual-release';release.mkdir()
def clone(src,dst):
 for p in src.iterdir():
  if p.name in {'stage.log','managed-runs','launch.json','__pycache__'} or p.suffix=='.pyc':continue
  q=dst/p.name
  if p.is_symlink():
   if p.name=='config' and p.is_dir():q.mkdir();clone(p.resolve(),q)
   else:q.symlink_to(p.resolve(strict=True),target_is_directory=p.is_dir())
  elif p.is_dir():q.mkdir();clone(p,q)
  else:shutil.copy2(p,q)
clone(old,runtime)
board=Path(s['old_root']);m=board/'candidate-manifest.json'
assert sha(m)=='ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab'
manifest=json.loads(m.read_text());assert all(sha(p)==digest for p,digest in manifest['runtime_files'].items())
for n,digest in manifest['payload_files'].items():
 src=board/'driver'/n;assert sha(src)==digest;shutil.copy2(src,release/n)
shutil.copy2(trial,release/'observed-trial.json');shutil.copy2(human,release/'human-observation.json')
rel=dict(schema_version=1,status='OBSERVED_MANUAL_VSRV2',scope='finite_manual_only',app='aura-visual-servo-b4096-v2',abi=2,build_id=0x778d2512,boot_id=boot,
 manual_minimum_us=1445,manual_maximum_us=1465,external_waveform_verified=False,physical_servo_response_verified=True,dpu_coexistence_verified=True,
 dpu_coexistence_scope='current boot finite 20us return with camera13537 running; not full follow acceptance',
 automatic_following_enabled=False,mechanical_reference_calibrated=False,payload_files=manifest['payload_files'],runtime_files=manifest['runtime_files'],
 trial_sha256=sha(trial),observation_sha256=sha(human))
(release/'release.json').write_text(json.dumps(rel,indent=2)+'\n')
cfg=dict(enabled=True,boot_id=boot,fdt_sha256=s['fdt_sha256'],release_manifest=str(release/'release.json'),release_manifest_sha256=sha(release/'release.json'),
 manual_minimum_us=1445,manual_maximum_us=1465,maximum_step_us=20,maximum_duration_s=2,automatic_following_enabled=False,
 center_reference_us=1420,center_reference_source='USER_REPORTED',face_follow_config=str(runtime/'aura/config/pan_face.local.json'))
(runtime/'aura/config/pan_manual.local.json').write_text(json.dumps(cfg,indent=2)+'\n')
face=json.loads((runtime/'aura/config/pan_face.local.json').read_text());face['mode']='pending_current_boot_direction'
face['arguments'].update({'context':str(R/'context.json'),'human-evidence':str(human),'zone-settings':str(R/'face-zone-settings.json'),'direction-evidence':str(R/'direction-calibration.json')})
(runtime/'aura/config/pan_face.local.json').write_text(json.dumps(face,indent=2)+'\n')
shutil.copy2(SOURCE/'face_pan_controls.py',runtime/'aura/tools/face_pan_controls.py')
gui['runtime']=str(runtime)
for name in ('config/pan_manual.local.json','config/pan_face.local.json','tools/face_pan_controls.py'):gui['component_sha256'][name]=sha(runtime/'aura'/name)
shutil.copy2(OLD/'startup/launcher.py',startup/'launcher.py');(startup/'config.json').write_text(json.dumps(gui,indent=2)+'\n')
env=dict(os.environ,PYTHONPATH=str(runtime/'aura'),PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run(['/usr/bin/python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],env=env,capture_output=True,text=True,timeout=30)
assert p.returncode==0,p.stderr[-900:]
code='from board.motion.manual_vsrv import load_release;import json;load_release(json.load(open('+repr(str(runtime/'aura/config/pan_manual.local.json'))+')))'
p=subprocess.run(['/usr/bin/python3','-B','-c',code],env=env,capture_output=True,text=True,timeout=10);assert p.returncode==0,p.stderr[-900:]
assert get(8790,'/health')['pid']==13537
s.update(phase='NEW_BOOT_MANUAL_GUI_PREPARED_NO_MOTION',gui_release=str(G),startup_config_sha256=sha(startup/'config.json'),manual_release_sha256=sha(release/'release.json'),
 current_camera_pid=13537,gui_pid=13573,automatic_following=False)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status=s['phase'],pins_verified=len(gui['component_sha256']),observed_bounds_us=[1445,1465],user_center_reference_us=1420,
 center_command_applied=False,automatic_following_enabled=False,MMIO_opened=False,motor_commands_sent=0,startup_config_sha256=s['startup_config_sha256'])))
