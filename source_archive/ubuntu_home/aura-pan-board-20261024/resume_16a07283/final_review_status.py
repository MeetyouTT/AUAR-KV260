import hashlib,importlib.util,json,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');P=F/'continuous-v10r12';S=F/'face-source-v14'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
state=json.loads((R/'state.json').read_text());cfg=json.loads((G/'startup/config.json').read_text())
face=json.loads((A/'config/pan_face.local.json').read_text());manual=json.loads((A/'config/pan_manual.local.json').read_text())
assert all(sha(A/n)==v for n,v in cfg['component_sha256'].items())
assert face['release_root']==str(P) and face['manifest_sha256']==sha(P/'deployment-manifest.json')
assert all(sha(p['destination'])==p['sha256'] for p in json.loads((P/'deployment-manifest.json').read_text())['files'])
assert all(sha(p)==h for p,h in json.loads((S/'deployment-manifest.json').read_text())['pins'].items())
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
h=get(8790,'/health');u=get(8783,'/api/state');m=u['manual_pan'];obs=get(8790,'/v1/motion/face/observation')
assert h['pid']==state['current_camera_pid'] and not h['dpu_schedule']['owner_fenced']
assert 'face-source-v14/entry.py' in subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','ExecStart'],text=True)
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
spec=importlib.util.spec_from_file_location('checked_face_receipt',A/'board/motion/follow_readback.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert module.verified_stopped_face_command(manual,m['readback'])
assert obs['face_tracking']['algorithm_version']==14
print(json.dumps({'status':state['phase'],'boot_id':state['boot'],'camera_pid':h['pid'],
 'gui_pid':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip(),
 'controller_manifest_sha256':sha(P/'deployment-manifest.json'),'source_manifest_sha256':sha(S/'deployment-manifest.json'),
 'gui_pins':len(cfg['component_sha256']),'control_pins':21,'source_pins':8,'stopped_receipt_valid':True,
 'readback':m['readback'],'automatic_following':False,'identity_ready':h['identity']['ready'],
 'primary_overruns':h['dpu_schedule']['primary_period_overruns'],
 'optional_overruns':{k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},
 'current_face_state':obs['state'],'algorithm_version':14,'motor_commands_sent':0,'gui_restarted':False}))
