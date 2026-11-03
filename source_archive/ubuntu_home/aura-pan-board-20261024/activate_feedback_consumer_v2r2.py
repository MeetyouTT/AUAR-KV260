"""Switch only the stopped consumer; keep running GUI and camera unchanged."""
import hashlib,json,os,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');A=N/'runtime/aura'
M=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v2r2')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=M/'deployment-manifest.json';assert sha(manifest)=='251ec5808b2b028ec09835561df817523d6c8969562c74e4160fe9ba29375027'
assert all(sha(x['destination'])==x['sha256'] for x in json.loads(manifest.read_text())['files'])
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
p=u['manual_pan'];assert p['state']=='READY' and not p['automatic_following'] and p['readback']['flags']==0 and p['readback']['lease_left_ms']==0
cfgpath=N/'startup/config.json';cfg=json.loads(cfgpath.read_text());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
path=A/'config/pan_face.local.json';before=path.read_bytes();backup=N/'pan-face-before-feedback-v2r2.json';assert not backup.exists();backup.write_bytes(before)
data=json.loads(before);assert data['mode']=='continuous_face_zone'
previous={'root':data['release_root'],'sha256':data['manifest_sha256']}
data['stopped_readback_predecessors']=[previous]+data.get('stopped_readback_predecessors',[])
data.update(release_root=str(M),manifest_sha256=sha(manifest));raw=(json.dumps(data,indent=2)+'\n').encode()
temp=path.with_name(path.name+'.feedback-v2r2');assert not temp.exists();temp.write_bytes(raw);os.replace(temp,path)
cfg['component_sha256']['config/pan_face.local.json']=sha(path);temp=cfgpath.with_name('config.feedback-v2r2.tmp');temp.write_text(json.dumps(cfg,indent=2)+'\n');os.replace(temp,cfgpath)
assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
print(json.dumps({'status':'FACE_SPEED_FEEDBACK_MEDIAN3_ACTIVE','median_window':3,'maximum_speed_us_s':60,'base_speed_us_s':24,
 'minimum_speed_us_s':8,'range_us':[1425,1505],'maximum_step_us':4,'maximum_acceleration_us_s2':120,
 'camera_restarted':False,'gui_restarted':False,'motor_writes':0}))
