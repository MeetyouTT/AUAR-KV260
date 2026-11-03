"""Stage current-boot r3 sources and receipt paths. Follow remains disabled."""
import hashlib,json,os,shutil,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');P=F/'continuous-v10r3';S=F/'shadow-v10r3';N=F/'current-boot-follow-v1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=json.loads((R/'state.json').read_text());assert s['phase']=='CURRENT_BOOT_DIRECTION_CONFIRMED_OUTPUT_STOPPED'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
assert sha(R/'direction-calibration.json')==s['direction_evidence_sha256'] and s['axis_camera_mirrored_control_polarity']==-1
assert sha(P/'deployment-manifest.json')=='56f4207a4dc033c9762f1476e8b8a4824bab513c02eae1df9dbaa2e706b34385'
assert sha(S/'manifest.json')=='777dbbddce409215db753a5ad55ed2693d3d6cb90f9ed2c91cd392e3a7cd23f0'
for target in (P/'libaura_trajectory.so',P/'libvsrv_batch.so',S/'libaura_trajectory.so'):
 src=F/'continuous-v9'/target.name
 expected='d08abd38232b6b7040b84befdd45c925a53885774ece339bdc1bf21f5adedd7a' if 'trajectory' in target.name else '93e17fdfd312a565e7cd560b73c7958f34eda3f9024ebeb25327e95494009b76'
 assert sha(src)==expected
 if not target.exists():
  with target.open('xb') as out:out.write(src.read_bytes())
 assert sha(target)==expected
pm=json.loads((P/'deployment-manifest.json').read_text());sm=json.loads((S/'manifest.json').read_text())
assert all(sha(row['destination'])==row['sha256'] for row in pm['files'])
assert all(sha(S/n)==h for n,h in sm['files'].items())
assert sha(N/'face_pan_controls.py')=='bf05dfc9eee27168f2a1a1755112439cbf2f8fe0d209665123302a045119255b'
assert sha(N/'follow_readback.py')=='a4a0a5d5d0430a1670a989d94d9e206216f03d51558d983a8d61429a96bfb52b'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as stream:u=json.load(stream)
m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
c=G/'startup/config.json';cfg=json.loads(c.read_text());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
manual=json.loads((A/'config/pan_manual.local.json').read_text());assert manual['automatic_following_enabled'] is False
backup=G/'before-current-follow-v1';backup.mkdir(mode=0o700)
targets=[c,A/'config/pan_face.local.json',A/'tools/face_pan_controls.py',A/'board/motion/follow_readback.py']
before={str(p):p.read_bytes() for p in targets}
for p in targets:shutil.copy2(p,backup/p.name)
face=json.loads((A/'config/pan_face.local.json').read_text())
face.update(release_root=str(P),manifest_sha256=sha(P/'deployment-manifest.json'),mode='continuous_face_zone',duration_s=20)
face['arguments'].update({'context':str(R/'context.json'),'direction-evidence':str(R/'direction-calibration.json'),
 'human-evidence':str(R/'relative-20us-human-observation.json'),'zone-settings':str(R/'face-zone-settings.json')})
updates={A/'config/pan_face.local.json':(json.dumps(face,indent=2)+'\n').encode(),
 A/'tools/face_pan_controls.py':(N/'face_pan_controls.py').read_bytes(),A/'board/motion/follow_readback.py':(N/'follow_readback.py').read_bytes()}
for p,raw in updates.items():
 assert p.read_bytes()==before[str(p)]
 tmp=p.with_name(p.name+'.r3');assert not tmp.exists();tmp.write_bytes(raw);os.replace(tmp,p)
 cfg['component_sha256'][str(p.relative_to(A))]=sha(p)
assert c.read_bytes()==before[str(c)]
tmp=c.with_name(c.name+'.r3');tmp.write_text(json.dumps(cfg,indent=2)+'\n');os.replace(tmp,c)
env=dict(os.environ,PYTHONPATH=str(A),PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run(['/usr/bin/python3','-B',str(G/'startup/launcher.py'),'--config',str(c),'--preflight'],env=env,capture_output=True,text=True,timeout=30)
assert p.returncode==0,p.stderr[-800:]
s.update(phase='CURRENT_BOOT_R3_PREPARED_OUTPUT_STOPPED',startup_config_sha256=sha(c),physical_consumer_root=str(P),
 physical_consumer_sha256=sha(P/'deployment-manifest.json'),shadow_consumer_sha256=sha(S/'manifest.json'),automatic_following=False)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'gui_pins':len(cfg['component_sha256']),'physical_files':len(pm['files']),'shadow_files':len(sm['files']),
 'control_polarity':-1,'test_duration_s':20,'follow_enabled':False,'motor_commands_sent':0,'center_command_applied':False}))
