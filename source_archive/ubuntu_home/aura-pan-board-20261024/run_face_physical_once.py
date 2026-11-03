"""Own finite face-edge actuation window; always restore the manual UI."""
import fcntl,hashlib,json,subprocess,time,urllib.request
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');F=OPS/'pan-face-edge-v3'
R=Path('/home/root/aura-pan-current-20261024/463c9307');GUI='aura-avatar-ui.service'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def props():
 x=subprocess.check_output(['systemctl','show',GUI,'-p','MainPID','-p','ActiveState','-p','Result','-p','ExecMainStatus'],text=True)
 return dict(s.split('=',1) for s in x.splitlines() if '=' in s)
lock=(OPS/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
s=json.loads((F/'stage-state.json').read_text());assert s['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
m=json.loads((F/'deployment-manifest.json').read_text());assert all(hashlib.sha256(Path(x['destination']).read_bytes()).hexdigest()==x['sha256'] for x in m['files'])
b=get(8790,'/health');u=get(8783,'/api/state');pan=u['manual_pan'];r=pan['readback']
assert b['pid']==s['camera_pid'] and not b['dpu_schedule']['owner_fenced'] and b['identity']['face_targets']['worker_alive']
assert u['phase']=='IDLE' and not u.get('playing') and pan['state']=='READY' and not pan['automatic_following']
assert r['flags']==0 and r['lease_left_ms']==0 and 1425<=r['width_us']<=1445 and props()['MainPID']==str(s['gui_pid'])
root=Path(json.loads((R/'state.json').read_text())['old_root']);meta=json.loads((OPS/'meta.json').read_text())
out=F/'runs'/('physical-'+str(time.monotonic_ns()))/'trial.json';out.parent.mkdir(mode=0o700,parents=True)
args=['/usr/bin/python3','-B',str(F/'run_face_motion.py'),'--manifest',str(root/'candidate-manifest.json'),
 '--manifest-sha256','ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab','--context',str(R/'context.json'),
 '--app-root',meta['candidate_root']+'/aura','--output',str(out),'--direction-evidence',str(R/'direction-calibration.json'),
 '--human-evidence',str(R/'gui-release/manual-release/human-observation.json'),'--confirmation','FACE_EDGE_OBSERVED_RANGE','--duration','10']
result={};stopped=False
try:
 subprocess.run(['systemctl','stop','--no-block',GUI],check=True);stopped=True;end=time.monotonic()+20
 while time.monotonic()<end and props()['MainPID']!='0':time.sleep(.2)
 q=props();assert q['MainPID']=='0' and q['Result']=='success' and q['ExecMainStatus']=='0'
 child=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=20)
 result={'child_exit':child.returncode,'stderr':child.stderr[-1200:],'stdout':child.stdout[-500:],'report':str(out)}
 if out.is_file():result['trial']=json.loads(out.read_text())
finally:
 if stopped:subprocess.run(['systemctl','start','--no-block',GUI],check=True)
 end=time.monotonic()+70;final=None
 while time.monotonic()<end:
  try:
   v=get(8783,'/api/state');p=v['manual_pan']
   if v['phase']=='IDLE' and p['state']=='READY':final=p;break
  except Exception:pass
  time.sleep(.5)
 result['gui_unit']=props();result['manual_restored']=final is not None
 if final is not None and final['left_sign']==-1:
  base='http://127.0.0.1:8783';req=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_reverse"}',headers={'Origin':base,'Content-Type':'application/json'})
  with o.open(req,timeout=3) as reply:assert json.load(reply)['ok']
  time.sleep(.2);final=get(8783,'/api/state')['manual_pan']
 a=get(8790,'/health');result.update(camera_pid=a['pid'],camera_pid_unchanged=a['pid']==b['pid'],
  primary_delta=a['dpu_schedule']['primary_period_overruns']-b['dpu_schedule']['primary_period_overruns'],
  optional_delta={k:a['dpu_schedule']['optional'][k]['overruns']-b['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},
  manual=final)
 s.update(gui_pid=int(result['gui_unit']['MainPID']));(F/'stage-state.json').write_text(json.dumps(s,indent=2)+'\n')
 print(json.dumps(result,sort_keys=True))
