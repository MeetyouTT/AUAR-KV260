"""Update only the owned GUI consumer/proxy; original projects stay intact."""
import hashlib,json,os,shutil,subprocess,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');A=N/'runtime/aura'
M=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v1')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
m=M/'deployment-manifest.json';assert sha(m)=='01f117448b79ef214bda1e14809feedaaac00e1e0ef070c6b09e7d54bbbd2828'
assert all(sha(x['destination'])==x['sha256'] for x in json.loads(m.read_text())['files'])
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
p=u['manual_pan'];assert p['state']=='READY' and not p['automatic_following'] and p['readback']['flags']==0 and p['readback']['lease_left_ms']==0
cfgpath=N/'startup/config.json';cfg=json.loads(cfgpath.read_text());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
assert sha(A/'tools/face_pan_controls.py')=='e831dce5fef07f5006dbe7cdeb2ee29525780bb11bf4128ec58e23ac1b70eab9'
backup=N/'continuous-v1-before';assert not backup.exists();backup.mkdir()
shutil.copy2(cfgpath,backup/'startup.json')
def install(dst,data):
 dst.parent.resolve().relative_to(N.resolve());tmp=dst.with_name(dst.name+'.continuous-v1');assert not tmp.exists();tmp.write_bytes(data);os.replace(tmp,dst)
for name in ('tools/face_pan_controls.py','board/motion/follow_readback.py','config/pan_face.local.json'):
 dst=A/name;shutil.copy2(dst,backup/Path(name).name)
 if name.startswith('config/'):
  data=json.loads(dst.read_text());old={'root':data['release_root'],'sha256':data['manifest_sha256']}
  data.update(release_root=str(M),manifest_sha256=sha(m),mode='continuous_face_zone',stopped_readback_predecessors=[old])
  data['arguments'].pop('zone-authorization',None);raw=(json.dumps(data,indent=2)+'\n').encode()
 else:raw=(M/'gui-support'/Path(name).name).read_bytes()
 install(dst,raw);cfg['component_sha256'][name]=sha(dst)
install(cfgpath,(json.dumps(cfg,indent=2)+'\n').encode())
assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
env=dict(os.environ,PYTHONPATH=str(A),PYTHONDONTWRITEBYTECODE='1')
q=subprocess.run(['/usr/bin/python3','-B',str(N/'startup/launcher.py'),'--config',str(cfgpath),'--preflight'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=25)
assert q.returncode==0,q.stderr[-1000:]
code='import json;from board.motion.follow_readback import verified_stopped_face_command;assert verified_stopped_face_command(json.load(open('+repr(str(A/'config/pan_manual.local.json'))+')),'+repr(p['readback'])+')'
q=subprocess.run(['/usr/bin/python3','-B','-c',code],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=10);assert q.returncode==0,q.stderr[-1000:]
print(json.dumps({'status':'CONTINUOUS_GUI_PREPARED_NO_RESTART','pins':len(cfg['component_sha256']),'stopped_predecessor_receipt_verified':True,'motor_writes':0}))
