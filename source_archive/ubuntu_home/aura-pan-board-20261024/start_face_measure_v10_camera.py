"""Start the pinned shadow bootstrap after an exact checkpoint passes."""
import hashlib,json,subprocess,time,urllib.request,os
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');SH=OPS/'pan-face-edge-v5/face-source-v10';CAM='aura-camera-ui.service';GUI='aura-avatar-ui.service'
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def props(unit):
 x=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus','-p','Restart','-p','KillMode','-p','SendSIGKILL','-p','TimeoutStopUSec'],text=True)
 return dict(a.split('=',1) for a in x.splitlines() if '=' in a)
def atomic(value):
 p=SH/'stage-state.json';t=SH/'stage-state.json.tmp';t.write_text(json.dumps(value,indent=2)+'\n');os.replace(t,p)
s=json.loads((SH/'stage-state.json').read_text());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();c=props(CAM)
assert s['phase']=='CAMERA_STOPPED_CHECKPOINT_PASS' and s['boot']==boot
assert c['MainPID']=='0' and c['Result']=='success' and c['ExecMainStatus']=='0' and c['Restart']=='no' and c['KillMode']=='process' and c['SendSIGKILL']=='no' and c['TimeoutStopUSec']=='infinity'
drop=Path(s['dropin']);assert drop.is_file() and hashlib.sha256(drop.read_bytes()).hexdigest()==s['dropin_sha256']
g=props(GUI);assert g['ActiveState']=='active' and g['MainPID']==str(s['gui_pid'])
atomic(dict(s,phase='CAMERA_STARTING'))
subprocess.run(['systemctl','reset-failed',CAM],check=True);subprocess.run(['systemctl','start','--no-block',CAM],check=True)
end=time.monotonic()+25;last=None
while time.monotonic()<end:
 try:
  c=props(CAM);h=get(8790,'/health');sch=h['dpu_schedule'];ident=h['identity']
  if (c['MainPID']!='0' and h['pid']==int(c['MainPID']) and sch['native_critical'] and not sch['owner_fenced']
      and ident['face_targets']['worker_alive'] and h['detected_frames']>=5
      and h.get('observation_age_ms') is not None and 0<=h['observation_age_ms']<750):
   last=h;break
 except Exception:pass
 time.sleep(.5)
if last is None:
 s.update(phase='CAMERA_START_HOLD',camera_unit=props(CAM));atomic(s)
 print(json.dumps({'phase':s['phase'],'camera_unit':s['camera_unit'],'automatic_kill':False}));raise SystemExit(2)
feed=get(8790,'/v1/motion/observation')
assert feed.get('protocol_version')=='aura-motion-observation-1' and feed.get('source_kind')=='actual' and feed.get('board_boot_id')==boot
g=props(GUI);u=get(8783,'/api/state');m=u.get('manual_pan',{});r=m.get('readback',{})
assert g['MainPID']==str(s['gui_pid']) and u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
assert m.get('automatic_following') is False and m.get('state') not in ('MOVING','STOPPING','CONNECTING')
b=s['counters_before']
assert sch['primary_calls']>=b['primary_calls'] and sch['primary_period_overruns']>=b['primary_overruns']
for k in ('yunet','sface'):assert sch['optional'][k]['calls']>=b['optional'][k]['calls'] and sch['optional'][k]['overruns']>=b['optional'][k]['overruns']
assert ident['feature_inference']['completed']>=b['sface_completed']
s.update(phase='CAMERA_READY_WITH_MOTION_FEED',camera_pid=int(c['MainPID']),motion_feed_state=feed.get('state'),
 gui_pid=int(g['MainPID']),manual_state=m.get('state'),
 owner_fenced=False,automatic_motion_commands=0)
atomic(s);print(json.dumps({k:s[k] for k in ('phase','camera_pid','motion_feed_state','gui_pid','manual_state','automatic_motion_commands')}))
