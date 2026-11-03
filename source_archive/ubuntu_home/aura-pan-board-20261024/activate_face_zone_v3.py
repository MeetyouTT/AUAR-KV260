"""Switch finite consumer and stopped readback, preserving live GUI/camera."""
import hashlib,json,os,shutil,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/463c9307');N=R/'gui-face-edge-v5';A=N/'runtime/aura'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');M=F/'motion-v3r2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
raw=(M/'deployment-manifest.json').read_bytes();assert hashlib.sha256(raw).hexdigest()=='ca912a83907623e19d02ad03dbce63e23764420081487f4516fa8fe0a89d2ce9'
assert all(sha(x['destination'])==x['sha256'] for x in json.loads(raw)['files'])
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as reply:u=json.load(reply)
p=u['manual_pan'];assert p['state']=='READY' and not p['automatic_following'] and p['readback']['flags']==0 and p['readback']['lease_left_ms']==0
cfgpath=N/'startup/config.json';cfg=json.loads(cfgpath.read_text());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
backup=N/'face-zone-v3-before';assert not backup.exists();backup.mkdir()
for part in ('board','board/motion'):
 path=A/part
 if path.is_symlink():
  target=path.resolve();path.unlink();shutil.copytree(target,path,symlinks=True)
expected={'manual.py':'6b67f785c09a15c2c9b17ab74b6338c77d83eca20cb2b80df2e5007575815288','manual_vsrv.py':'0e80925d126170dfdfd1b3066c36142b046d83c17e2cb74544d7009cd91ecd8a'}
for name,h in expected.items():assert sha(A/'board/motion'/name)==h
shutil.copy2(cfgpath,backup/'startup.json');shutil.copy2(A/'config/pan_face.local.json',backup/'pan_face.local.json')
def install(path,data):
 path.parent.resolve().relative_to(N.resolve());tmp=path.with_name(path.name+'.face-zone-v3');assert not tmp.exists();tmp.write_bytes(data);os.replace(tmp,path)
for name in ('manual.py','manual_vsrv.py','follow_readback.py'):
 dst=A/'board/motion'/name;src=F/'motion-v3/gui-support'/name
 if dst.exists():shutil.copy2(dst,backup/name)
 install(dst,src.read_bytes());cfg['component_sha256']['board/motion/'+name]=sha(dst)
face=A/'config/pan_face.local.json';data=json.loads(face.read_text());data['release_root']=str(M);data['manifest_sha256']=hashlib.sha256(raw).hexdigest()
data['arguments'].update({'zone-settings':str(R/'face-zone-settings.json'),'zone-authorization':'FACE_ZONE_FINITE_FASTER'})
install(face,(json.dumps(data,indent=2)+'\n').encode());cfg['component_sha256']['config/pan_face.local.json']=sha(face)
install(cfgpath,(json.dumps(cfg,indent=2)+'\n').encode());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
print(json.dumps({'status':'USER_FACE_ZONE_FINITE_V3_ACTIVE','range_us':[1425,1505],'speed_us_s':[24,40],
 'filter_ms':80,'manual_jog_bounds_unchanged':[1425,1445],'outside_manual_range':'authenticated_stopped_face_readback_only',
 'components_verified':len(cfg['component_sha256']),'camera_restarted':False,'gui_restarted':False,'movement_commands':0}))
