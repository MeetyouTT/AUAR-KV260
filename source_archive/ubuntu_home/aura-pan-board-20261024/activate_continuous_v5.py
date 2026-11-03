import hashlib,json,os,shutil,urllib.request
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');A=N/'runtime/aura'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
p=F/'continuous-v5/deployment-manifest.json'
assert sha(p)=='e3f0cb1c029a778dad5130cb09a40929a8bbb00835ea4ebd4d015627cdea16bc'
assert all(sha(x['destination'])==x['sha256'] for x in json.loads(p.read_text())['files'])
c=N/'startup/config.json';cfg=json.loads(c.read_text());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
q=A/'config/pan_face.local.json';face=json.loads(q.read_text());assert face['release_root']==str(F/'continuous-v4r2')
backup=N/'continuous-v5-before';assert not backup.exists();backup.mkdir(mode=0o700)
shutil.copy2(c,backup/'startup.json');shutil.copy2(q,backup/q.name)
face['stopped_readback_predecessors']=[{'root':face['release_root'],'sha256':face['manifest_sha256']}]+face.get('stopped_readback_predecessors',[])
face.update(release_root=str(p.parent),manifest_sha256=sha(p))
raw=(json.dumps(face,indent=2)+'\n').encode();temp=q.with_name(q.name+'.continuous-v5');assert not temp.exists();temp.write_bytes(raw);os.replace(temp,q)
cfg['component_sha256']['config/pan_face.local.json']=sha(q)
temp=c.with_name(c.name+'.continuous-v5');assert not temp.exists();temp.write_text(json.dumps(cfg,indent=2)+'\n');os.replace(temp,c)
assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
print(json.dumps({'status':'CONTINUOUS_V5_ACTIVATED_OUTPUT_OFF','consumer_sha256':sha(p),'pins':len(cfg['component_sha256']),'readback':m['readback'],'camera_restarted':False,'gui_restarted':False}))
