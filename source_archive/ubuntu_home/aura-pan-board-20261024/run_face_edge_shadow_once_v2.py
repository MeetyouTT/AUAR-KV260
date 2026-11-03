"""One current-boot face-only edge shadow, with existing native/servo checks."""
import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');F=OPS/'pan-face-edge-v2'
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def brief():
 h=get(8790,'/health');d=h['dpu_schedule'];f=h['identity']['face_targets']
 return {'pid':h['pid'],'frames':h['detected_frames'],'primary':d['primary_period_overruns'],'optional':{k:d['optional'][k]['overruns'] for k in ('yunet','sface')},'face_processed':f['processed'],'fenced':d['owner_fenced'],'worker':f['worker_alive']}
s=json.loads((F/'stage-state.json').read_text());assert s['phase']=='CAMERA_READY_WITH_MOTION_FEED'
manifest=json.loads((F/'deployment-manifest.json').read_text());assert all(hashlib.sha256(Path(x['destination']).read_bytes()).hexdigest()==x['sha256'] for x in manifest['files'])
b=brief();u=get(8783,'/api/state');m=u['manual_pan'];before=m['readback']
assert b['pid']==s['camera_pid'] and b['worker'] and not b['fenced'] and u['phase']=='IDLE'
assert m['state']=='READY' and before['flags']==0 and before['lease_left_ms']==0 and not m['automatic_following']
meta=json.loads((OPS/'meta.json').read_text());out=F/'runs'/('live-'+str(time.monotonic_ns()))/'face.jsonl'
args=['/usr/bin/python3','-B',str(F/'run_face_shadow.py'),'--app-root',meta['candidate_root']+'/aura','--config',str(F/'config.json'),'--output',str(out),'--duration','10']
start=time.monotonic();p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30);elapsed=time.monotonic()-start
if p.returncode:print(json.dumps({'child_exit':p.returncode,'stderr':p.stderr[-1000:],'stdout':p.stdout[-500:]}));raise SystemExit(2)
report=json.loads(Path(str(out)+'.summary.json').read_text());a=brief();final=get(8783,'/api/state')['manual_pan'];after=final['readback']
assert a['pid']==b['pid'] and not a['fenced'] and a['worker'] and final['state']=='READY'
assert all(before[k]==after[k] for k in ('flags','lease_left_ms','epoch','ack_seq','width_us'))
print(json.dumps({'shadow':report,'camera_pid':a['pid'],'gui_pid':s['gui_pid'],'yolo_hz':round((a['frames']-b['frames'])/elapsed,3),
 'face_hz':round((a['face_processed']-b['face_processed'])/elapsed,3),'primary_delta':a['primary']-b['primary'],
 'optional_delta':{k:a['optional'][k]-b['optional'][k] for k in b['optional']},'manual_registers_unchanged':True,'left_sign':final['left_sign'],'output':str(out)},sort_keys=True))
