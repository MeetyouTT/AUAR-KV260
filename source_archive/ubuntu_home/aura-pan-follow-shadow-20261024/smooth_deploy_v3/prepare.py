"""Install the explicit firmware-envelope scope and reconnect only motor child."""
import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');F=OPS/'pan-face-edge-v5';N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');A=N/'runtime/aura'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def install(p,raw):
 p.parent.resolve().relative_to(N.resolve());temp=p.with_name(p.name+'.smooth-v3');assert not temp.exists();temp.write_bytes(raw);os.replace(temp,p)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def ui():
 with op.open(base+'/api/state',timeout=3) as f:return json.load(f)
def command(kind):
 q=urllib.request.Request(base+'/api/command',data=json.dumps({'type':kind}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with op.open(q,timeout=3) as f:return json.load(f)
m=ui()['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
controller=F/'continuous-v3';manifest=controller/'deployment-manifest.json';assert sha(manifest)=='7dadfb6c3f56a32f5d828537219ea8fbd3ed24f5ef6e1541ac82f9ed71a05168'
assert all(sha(x['destination'])==x['sha256'] for x in json.loads(manifest.read_text())['files'])
source=F/'face-source-v6/deployment-manifest.json';assert sha(source)=='167a8df8d881937a071272854865557352f1ef93e007383960586832bbdb7a10'
assert all(sha(p)==h for p,h in json.loads(source.read_text())['pins'].items())
cfgpath=N/'startup/config.json';cfg=json.loads(cfgpath.read_text());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
backup=N/'smooth-v3-before';assert not backup.exists();backup.mkdir();shutil.copy2(cfgpath,backup/'startup.json')
manual_path=A/'config/pan_manual.local.json';manual=json.loads(manual_path.read_text());old_path=Path(manual['release_manifest']);old=json.loads(old_path.read_text());assert sha(old_path)==manual['release_manifest_sha256']
prior=old.get('observed_predecessor') or {'path':str(old_path),'sha256':sha(old_path)}
legacy=Path(prior['path']);assert sha(legacy)==prior['sha256'];assert json.loads(legacy.read_text())['status']=='OBSERVED_MANUAL_VSRV2'
release_root=N/'manual-user-bounds-v2';assert not release_root.exists();release_root.mkdir(mode=0o700)
auth={'schema':'aura-user-bounded-manual-1','boot_id':manual['boot_id'],'bounds_us':[1400,1600],
 'implementation_choice':'align_manual_with_authorized_face_follow_range','physical_calibration_claimed':False,
 'user_instruction_quote':'转动的不自然，而且转了一下就不转动了，希望你能改进一下，不是平滑的，转动就转了一小下后面就不动了',
 'scope_note':'Existing verified VSRV2 firmware accepts 1400..1600. Expand software limits to that envelope; no mechanical-limit claim.'}
(release_root/'authorization.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2)+'\n')
for name in old['payload_files']:shutil.copy2(old_path.parent/name,release_root/name)
release=dict(old,status='USER_BOUNDED_MANUAL_VSRV2',scope='finite_manual_user_authorized_bounds',manual_minimum_us=1400,manual_maximum_us=1600,
 physical_range_verified=False,mechanical_reference_calibrated=False,physical_servo_response_verified=False,dpu_coexistence_verified=False,
 authorization_sha256=sha(release_root/'authorization.json'),observed_predecessor=prior)
(release_root/'release.json').write_text(json.dumps(release,indent=2)+'\n')
for name in ('manual_release.py','manual_vsrv.py','manual_process.py','manual_live_config.py'):
 path=A/'board/motion'/name
 if path.exists():shutil.copy2(path,backup/name)
 install(path,(F/'manual-bounds-v2'/name).read_bytes());cfg['component_sha256']['board/motion/'+name]=sha(path)
for path in (manual_path,A/'config/pan_face.local.json'):shutil.copy2(path,backup/path.name)
manual.update(release_manifest=str(release_root/'release.json'),release_manifest_sha256=sha(release_root/'release.json'),manual_minimum_us=1400,manual_maximum_us=1600)
install(manual_path,(json.dumps(manual,indent=2)+'\n').encode());cfg['component_sha256']['config/pan_manual.local.json']=sha(manual_path)
face_path=A/'config/pan_face.local.json';face=json.loads(face_path.read_text());face['stopped_readback_predecessors']=[{'root':face['release_root'],'sha256':face['manifest_sha256']}]+face.get('stopped_readback_predecessors',[])
face.update(release_root=str(controller),manifest_sha256=sha(manifest));install(face_path,(json.dumps(face,indent=2)+'\n').encode());cfg['component_sha256']['config/pan_face.local.json']=sha(face_path)
install(cfgpath,(json.dumps(cfg,indent=2)+'\n').encode());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
env=dict(os.environ,PYTHONPATH=str(A),PYTHONDONTWRITEBYTECODE='1');code='import json;from board.motion.manual_vsrv import ManualVSRV;ManualVSRV(json.load(open('+repr(str(manual_path))+'))).verify_platform()'
p=subprocess.run(['/usr/bin/python3','-B','-c',code],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15);assert p.returncode==0,p.stderr[-1500:]
assert command('pan_reconnect')['ok'];end=time.monotonic()+10
while time.monotonic()<end:
 m=ui()['manual_pan']
 if m['state']=='READY' and m['maximum_us']==1600:break
 if m['state']=='FAULT':raise RuntimeError(m['error'])
 time.sleep(.15)
assert m['state']=='READY' and m['maximum_us']==1600 and m['minimum_us']==1400
if m['left_sign']==-1:assert command('pan_reverse')['ok']
print(json.dumps({'status':'SMOOTH_V3_PREPARED_MOTOR_RECONNECTED','manual_bounds':[1400,1600],'pins':len(cfg['component_sha256']),
 'camera_restarted':False,'gui_restarted':False,'movement_commands':0,'readback':m['readback']}))
