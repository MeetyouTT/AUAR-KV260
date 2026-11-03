import hashlib,importlib.util,json,os,shutil,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/attended-reference-1420')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following']
assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0 and m['readback']['width_us']==1402
s=json.loads((R/'state.json').read_text());assert s['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
C=G/'startup/config.json';Q=A/'config/pan_manual.local.json';cfg=json.loads(C.read_text());manual=json.loads(Q.read_text())
assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
assert sha(A/'board/motion/manual_release.py')=='a9cfced9fb8bd3299315ac82ecec3e0c50e66c439efbf8d79e87bab9b919e2f7'
prior=Path(manual['release_manifest']);assert sha(prior)==manual['release_manifest_sha256']
release=json.loads(prior.read_text());assert release['status']=='OBSERVED_MANUAL_VSRV2'
backup=G/'before-attended-reference-1420';backup.mkdir(mode=0o700)
for src,name in [(C,'startup-config.json'),(Q,'pan_manual.local.json'),(A/'board/motion/manual_release.py','manual_release.py')]:shutil.copy2(src,backup/name)
out=P/'manual-release';out.mkdir(mode=0o700)
for name,h in release['payload_files'].items():
 assert sha(prior.parent/name)==h;shutil.copyfile(prior.parent/name,out/name)
authorization=dict(schema='aura-user-bounded-manual-1',boot_id=s['boot'],bounds_us=[1402,1420],
 implementation_choice='attended_reference_window',physical_calibration_claimed=False,user_instruction_quote='是的',
 context='User confirms present after proposed small-step return from stopped1402 to user-reported1420',
 commanded_sequence_us=[1402,1407,1412,1417,1420],automatic_following=False)
(out/'authorization.json').write_text(json.dumps(authorization,ensure_ascii=False,indent=2)+'\n')
release.update(status='USER_BOUNDED_MANUAL_VSRV2',scope='finite_manual_user_authorized_bounds',manual_minimum_us=1402,
 manual_maximum_us=1420,physical_range_verified=False,mechanical_reference_calibrated=False,
 authorization_sha256=sha(out/'authorization.json'),observed_predecessor=dict(path=str(prior),sha256=sha(prior)))
(out/'release.json').write_text(json.dumps(release,indent=2)+'\n')
manual.update(release_manifest=str(out/'release.json'),release_manifest_sha256=sha(out/'release.json'),manual_minimum_us=1402,manual_maximum_us=1420)
spec=importlib.util.spec_from_file_location('reference_release',P/'manual_release.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert module.authorized_bounds(release,manual,out)==(1402,1420)
dst=A/'board/motion/manual_release.py';tmp=dst.with_name(dst.name+'.attended');shutil.copyfile(P/'manual_release.py',tmp);tmp.chmod(dst.stat().st_mode&0o777);os.replace(tmp,dst)
tmp=Q.with_name(Q.name+'.attended');tmp.write_text(json.dumps(manual,indent=2)+'\n');tmp.chmod(Q.stat().st_mode&0o777);os.replace(tmp,Q)
cfg['component_sha256']['board/motion/manual_release.py']=sha(dst);cfg['component_sha256']['config/pan_manual.local.json']=sha(Q)
tmp=C.with_name(C.name+'.attended');tmp.write_text(json.dumps(cfg,indent=2)+'\n');tmp.chmod(C.stat().st_mode&0o777);os.replace(tmp,C)
assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
(P/'prepared.json').write_text(json.dumps(dict(boot_id=s['boot'],before=m['readback'],camera_pid=s['current_camera_pid'],gui_pid=s['current_gui_pid'],backend_pid=m['backend_pid'],manual_config_sha256=sha(Q),startup_config_sha256=sha(C)),indent=2)+'\n')
print(json.dumps({'status':'ATTENDED_REFERENCE_PREPARED_NO_MOTION','bounds_us':[1402,1420],'readback':m['readback'],'motor_commands_sent':0,'gui_restarted':False}))
