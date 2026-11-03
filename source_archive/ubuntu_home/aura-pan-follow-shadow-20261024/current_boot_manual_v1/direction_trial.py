"""One existing bounded 20us bench; preserve GUI/camera, then restore manual owner."""
import fcntl,hashlib,json,os,signal,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
G=R/'gui-manual-bound-v1';A=G/'runtime/aura';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));address='http://127.0.0.1:8783'
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as response:return json.load(response)
def command(kind):
 request=urllib.request.Request(address+'/api/command',data=json.dumps({'type':kind}).encode(),headers={'Origin':address,'Content-Type':'application/json'})
 with op.open(request,timeout=4) as response:return json.load(response)
s=json.loads((R/'state.json').read_text());assert s['phase']=='CURRENT_BOOT_MANUAL_READY_OUTPUT_STOPPED_FOLLOW_LOCKED'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']=='16a07283-9e14-45e6-816d-3bda4cf333a7'
cfg=json.loads((G/'startup/config.json').read_text());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
assert json.loads((A/'config/pan_manual.local.json').read_text())['automatic_following_enabled'] is False
h=get(8790,'/health');u=get(8783,'/api/state');m=u['manual_pan'];registers=m['readback']
assert h['pid']==13537 and not h['dpu_schedule']['owner_fenced'] and m['state']=='READY' and not m['automatic_following']
assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
assert u.get('local_recording',{}).get('state')!='RECORDING' and not u.get('local_transcription',{}).get('service',{}).get('pending')
assert registers['flags']==0 and registers['lease_left_ms']==0 and registers['width_us']==1445 and registers['epoch']==3 and registers['ack_seq']==42
helper=Path('/home/root/aura-post-power-20261022/helpers/96420fc26d811e16/source.py')
assert sha(helper)=='96420fc26d811e16bd47b8b3d16a0b1a6b3ea9759ba5490564205fc9c0065bb4'
pid=m['backend_pid'];proc=Path('/proc')/str(pid);birth=proc.joinpath('stat').read_text().split()[21]
assert 'aura-avatar-ui.service' in (proc/'cgroup').read_text() and b'spawn_main' in (proc/'cmdline').read_bytes()
assert hasattr(os,'pidfd_open') and hasattr(signal,'pidfd_send_signal')
out=R/'direction-20us-from1445.json';expected=R/'expected-direction-20us.json';assert not out.exists() and not expected.exists()
lock=(O/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
with expected.open('x') as f:json.dump({'boot_id':s['boot'],'registers':registers},f)
fd=os.pidfd_open(pid)
try:
 assert proc.joinpath('stat').read_text().split()[21]==birth
 signal.pidfd_send_signal(fd,signal.SIGTERM)
finally:os.close(fd)
exit_deadline=time.monotonic()+6
while proc.exists() and time.monotonic()<exit_deadline:time.sleep(.05)
assert not proc.exists(),'Manual owner did not exit normally; no trial'
s.update(phase='CURRENT_BOOT_DIRECTION_TRIAL_RUNNING',user_paused_motion=False,last_user_motion_instruction='继续',automatic_following=False)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
failure=None;trial=None
try:
 old=Path(s['old_root'])
 p=subprocess.run(['/usr/bin/python3','-B',str(helper),'--execute','--confirmation','OBSERVED_20US_RETURN_2S',
  '--manifest',str(old/'candidate-manifest.json'),'--manifest-sha256','ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab',
  '--context',str(R/'context.json'),'--expected-state',str(expected),'--output',str(out)],capture_output=True,text=True,timeout=15)
 assert p.returncode==0,p.stderr[-700:]
 trial=json.loads(out.read_text());r=trial['result']['stopped']
 assert r['flags']==0 and r['lease_left_ms']==0 and r['width_us']==1445
except Exception as error:failure=type(error).__name__+': '+str(error)[:700]
finally:
 assert command('pan_reconnect').get('ok')
 end=time.monotonic()+5;final=None
 while time.monotonic()<end:
  final=get(8783,'/api/state')['manual_pan']
  if final['state']=='READY':break
  time.sleep(.1)
 assert final['state']=='READY' and not final['automatic_following']
 assert final['readback']['flags']==0 and final['readback']['lease_left_ms']==0
 assert get(8790,'/health')['pid']==13537
s.update(phase='DIRECTION_TRIAL_STOPPED_OBSERVATION_PENDING' if not failure else 'DIRECTION_TRIAL_FAILED_NO_RETRY',
 direction_trial=str(out),direction_trial_sha256=sha(out) if out.exists() else None,current_last_command_us=final['readback']['width_us'],automatic_following=False)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'error':failure,'sequence_us':[1445,1465,1445],
 'acks':len(trial['events']) if trial else None,'final':final['readback'],'new_backend_pid':final['backend_pid'],
 'camera_pid':13537,'gui_restarted':False,'center_reference_us':1420,'center_command_applied':False,'physical_direction_pending':True}))
if failure:raise SystemExit(1)
