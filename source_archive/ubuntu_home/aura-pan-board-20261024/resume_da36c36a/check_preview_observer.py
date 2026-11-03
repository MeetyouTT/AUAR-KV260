import hashlib,json,sys,time
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/preview-motion-v1/preview_motion.py')
assert hashlib.sha256(P.read_bytes()).hexdigest()=='324e13111c2412831e9d7f09240116cc53cfcbde21f3bea71f7fdefabaf12a17'
sys.path.insert(0,str(P.parent))
from preview_motion import CachedPreviewFetcher,PreviewMotionObserver
fetch=CachedPreviewFetcher('http://127.0.0.1:8790')
try:
 gray,meta,boxes=fetch();probe={'ok':True,'shape':list(gray.shape),'metadata':meta,'masked_faces':len(boxes)}
except Exception as e:
 raw,_=fetch.get('/v1/ui/status',131072);v=json.loads(raw)
 p=v['preview'];_,headers=fetch.get('/v1/ui/preview.jpg?camera_epoch='+p['camera_epoch']+'&frame_id='+str(p['frame_id']),2097152)
 probe={'ok':False,'error':type(e).__name__+': '+str(e),'status_keys':sorted(v),'preview_keys':sorted(p),'preview':p,'aura_headers':{k:x for k,x in headers.items() if k.startswith('x-aura')}}
print(json.dumps({'probe':probe,'motor_commands':0,'MMIO_opened':False}))
