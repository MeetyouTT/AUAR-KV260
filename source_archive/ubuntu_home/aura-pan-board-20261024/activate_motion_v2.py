"""Switch only the finite motor consumer; leave camera and GUI running."""
import hashlib,json,os,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');M=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/motion-v2')
def sha(raw):return hashlib.sha256(raw).hexdigest()
raw=(M/'deployment-manifest.json').read_bytes();assert sha(raw)=='5531558c57454c5351887fae0bdbbea3f3659c52bb6197b059e6cf92aa2386a9'
manifest=json.loads(raw);assert all(sha(Path(x['destination']).read_bytes())==x['sha256'] for x in manifest['files'])
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as reply:u=json.load(reply)
p=u['manual_pan'];assert p['state']=='READY' and not p['automatic_following'] and p['readback']['flags']==0 and p['readback']['lease_left_ms']==0
cfgpath=N/'startup/config.json';cfg=json.loads(cfgpath.read_text());path=N/'runtime/aura/config/pan_face.local.json';path.parent.resolve().relative_to(N.resolve())
before=path.read_bytes();assert sha(before)==cfg['component_sha256']['config/pan_face.local.json']
backup=N/'pan-face-before-motion-v2.json';assert not backup.exists();backup.write_bytes(before)
data=json.loads(before);data['release_root']=str(M);data['manifest_sha256']=sha(raw);updated=(json.dumps(data,indent=2)+'\n').encode()
temp=path.with_name(path.name+'.motion-v2');assert not temp.exists();temp.write_bytes(updated);assert path.read_bytes()==before;os.replace(temp,path)
cfg['component_sha256']['config/pan_face.local.json']=sha(updated);temp=cfgpath.with_name('config.motion-v2.tmp');temp.write_text(json.dumps(cfg,indent=2)+'\n');os.replace(temp,cfgpath)
assert all(sha((Path(cfg['runtime'])/'aura'/name).read_bytes())==expected for name,expected in cfg['component_sha256'].items())
print(json.dumps({'status':'FINITE_MOTION_V2_ACTIVE','enter_margin':.15,'exit_margin':.25,'motion_deadline_ms':250,'camera_restarted':False,'gui_restarted':False,'movement_commands_sent':0}))
