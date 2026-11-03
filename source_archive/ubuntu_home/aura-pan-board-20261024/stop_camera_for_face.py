"""Stop the current camera owner once, with no timeout kill or auto-restart."""
import fcntl,json,os,subprocess,time,urllib.request
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');SH=OPS/'pan-face-edge-v1';CAM='aura-camera-ui.service';GUI='aura-avatar-ui.service'
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def props(unit):
 x=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus','-p','Restart','-p','KillMode','-p','SendSIGKILL','-p','TimeoutStopUSec'],text=True)
 return dict(a.split('=',1) for a in x.splitlines() if '=' in a)
def ticks(pid):return int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])
s=json.loads((SH/'stage-state.json').read_text());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert s['phase']=='DROPIN_STAGED_NO_RESTART' and s['boot']==boot
lock=(OPS/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
c=props(CAM);g=props(GUI);h=get(8790,'/health');u=get(8783,'/api/state');m=u.get('manual_pan',{});r=m.get('readback',{});pid=int(s['camera_pid_before']);birth=ticks(pid)
assert c['MainPID']==str(pid) and c['ActiveState']=='active' and c['Restart']=='no' and c['KillMode']=='process' and c['SendSIGKILL']=='no' and c['TimeoutStopUSec']=='infinity'
assert h['pid']==pid and h['dpu_schedule']['native_critical'] and not h['dpu_schedule']['owner_fenced'] and h['identity']['face_targets']['worker_alive']
assert g['MainPID']==str(s['gui_pid']) and g['ActiveState']=='active' and u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
assert m.get('state') not in ('MOVING','STOPPING','CONNECTING') and not m.get('automatic_following')
b={'pid':pid,'birth':birth,'primary_calls':h['dpu_schedule']['primary_calls'],'primary_overruns':h['dpu_schedule']['primary_period_overruns'],'optional':{k:{'calls':v['calls'],'overruns':v['overruns']} for k,v in h['dpu_schedule']['optional'].items()},'sface_completed':h['identity']['feature_inference']['completed']}
s.update(phase='CAMERA_STOPPING',stop_source_pid=pid,stop_source_birth_ticks=birth,counters_before=b,manual_panel_open=m.get('panel_open'))
(SH/'stage-state.json.tmp').write_text(json.dumps(s,indent=2)+'\n');os.replace(SH/'stage-state.json.tmp',SH/'stage-state.json')
subprocess.run(['systemctl','stop','--no-block',CAM],check=True);end=time.monotonic()+90
while time.monotonic()<end:
 c=props(CAM)
 if c['MainPID']=='0':break
 time.sleep(.25)
assert c['MainPID']=='0' and c['Result']=='success' and c['ExecMainStatus']=='0'
if (Path('/proc')/str(pid)/'stat').exists():assert ticks(pid)!=birth
s.update(phase='CAMERA_STOPPED_AWAIT_CHECKPOINT')
(SH/'stage-state.json.tmp').write_text(json.dumps(s,indent=2)+'\n');os.replace(SH/'stage-state.json.tmp',SH/'stage-state.json')
print(json.dumps({'phase':s['phase'],'stopped_pid':pid,'result':c['Result'],'exec_status':c['ExecMainStatus']}))
