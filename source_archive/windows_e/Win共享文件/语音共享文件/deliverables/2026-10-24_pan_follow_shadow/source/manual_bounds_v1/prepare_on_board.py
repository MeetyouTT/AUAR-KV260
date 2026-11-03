"""Align finite manual controls with the already authorized face-follow range."""
import hashlib,json,os,shutil,subprocess,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');A=N/'runtime/aura';R=N/'manual-user-bounds-v1'
S=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/manual-bounds-v1')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
cfgpath=N/'startup/config.json';cfg=json.loads(cfgpath.read_text());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
p=u['manual_pan'];assert p['state']=='READY' and not p['automatic_following'] and p['readback']['flags']==0 and p['readback']['lease_left_ms']==0
manual_path=A/'config/pan_manual.local.json';manual=json.loads(manual_path.read_text());old_path=Path(manual['release_manifest']);old=json.loads(old_path.read_text());assert sha(old_path)==manual['release_manifest_sha256']
assert old['status']=='OBSERVED_MANUAL_VSRV2' and not R.exists();R.mkdir(mode=0o700)
auth={'schema':'aura-user-bounded-manual-1','boot_id':manual['boot_id'],'bounds_us':[1425,1505],
 'implementation_choice':'align_manual_with_authorized_face_follow_range','physical_calibration_claimed':False,
 'scope_note':'Implementation choice under autonomous task authorization; new bounds are software limits, not measured mechanical limits',
 'user_instruction_quote':'你这边自己开始做，然后在做一个能根据我这个人脸移动速度做一个反馈，然后加一些中直滤波让转动平滑，另外的任务你自己做，我先离开了，去睡觉，你先完成为完成的任务再做刚才那两点要求'}
(R/'authorization.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2)+'\n')
for name in old['payload_files']:shutil.copy2(old_path.parent/name,R/name)
release=dict(old,status='USER_BOUNDED_MANUAL_VSRV2',scope='finite_manual_user_authorized_bounds',manual_minimum_us=1425,manual_maximum_us=1505,
 physical_servo_response_verified=False,dpu_coexistence_verified=False,previous_20us_human_observation_verified=True,
 physical_range_verified=False,mechanical_reference_calibrated=False,authorization_sha256=sha(R/'authorization.json'),
 observed_predecessor={'path':str(old_path),'sha256':sha(old_path)},
 dpu_coexistence_scope='Earlier same-boot limited YOLO plus servo motion; no new full-range or three-model mechanical acceptance')
for key in ('trial_sha256','observation_sha256'):release.pop(key,None)
(R/'release.json').write_text(json.dumps(release,indent=2)+'\n')
backup=N/'manual-user-bounds-before';assert not backup.exists();backup.mkdir();shutil.copy2(cfgpath,backup/'startup.json');shutil.copy2(manual_path,backup/'pan_manual.local.json')
def install(path,raw):
 path.parent.resolve().relative_to(N.resolve());tmp=path.with_name(path.name+'.manual-bounds');assert not tmp.exists();tmp.write_bytes(raw);os.replace(tmp,path)
for name in ('manual_release.py','manual_vsrv.py'):
 path=A/'board/motion'/name;shutil.copy2(path,backup/name);install(path,(S/name).read_bytes());cfg['component_sha256']['board/motion/'+name]=sha(path)
manual.update(release_manifest=str(R/'release.json'),release_manifest_sha256=sha(R/'release.json'),manual_minimum_us=1425,manual_maximum_us=1505)
install(manual_path,(json.dumps(manual,indent=2)+'\n').encode());cfg['component_sha256']['config/pan_manual.local.json']=sha(manual_path)
install(cfgpath,(json.dumps(cfg,indent=2)+'\n').encode());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
env=dict(os.environ,PYTHONPATH=str(A),PYTHONDONTWRITEBYTECODE='1')
code='import json;from board.motion.manual_vsrv import ManualVSRV;v=ManualVSRV(json.load(open('+repr(str(manual_path))+')));v.verify_platform()'
q=subprocess.run(['/usr/bin/python3','-B','-c',code],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15);assert q.returncode==0,q.stderr[-1000:]
print(json.dumps({'status':'USER_BOUNDED_MANUAL_PREFLIGHT_PASS_NO_MMIO','range_us':[1425,1505],'maximum_step_us':20,
 'maximum_duration_s':2,'physical_range_verified':False,'old_20us_proof_kept_in_original_scope':True,'pins':len(cfg['component_sha256']),'movement_commands':0}))
