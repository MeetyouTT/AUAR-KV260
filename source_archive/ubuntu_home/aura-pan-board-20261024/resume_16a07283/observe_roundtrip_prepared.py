"""One observed 20us return; initialization is not physical calibration."""
import fcntl,hashlib,json,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def brief():
 h=get(8790,'/health');return {'pid':h['pid'],'fenced':h['dpu_schedule']['owner_fenced'],'worker':h['identity']['face_targets']['worker_alive']}
s=json.loads((R/'state.json').read_text());assert s['phase']=='JOINT_NATIVE_RUNNING_GUI_STARTING'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
old=Path(s['old_root']);payload=json.loads((old/'payload.json').read_text())
assert sha(old/'bench_finite_step.py')==payload['files']['bench_finite_step.py']
helper=Path('/home/root/aura-post-power-20261022/helpers/96420fc26d811e16/source.py')
assert sha(helper)=='96420fc26d811e16bd47b8b3d16a0b1a6b3ea9759ba5490564205fc9c0065bb4'
u=get(8783,'/api/state');assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
assert u.get('local_recording',{}).get('state')!='RECORDING' and not u.get('local_transcription',{}).get('service',{}).get('pending')
before=brief();assert before['pid']==s['current_camera_pid'] and not before['fenced'] and before['worker']
lock=(OPS/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
base=['--execute','--manifest',str(old/'candidate-manifest.json'),'--manifest-sha256','ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab','--context',str(R/'context.json')]
init=R/'init1448-to1445.json';trial=R/'observed-20us-current.json';assert not init.exists() and not trial.exists()
p=subprocess.run(['/usr/bin/python3','-B',str(old/'bench_finite_step.py')]+base+['--confirmation','OBSERVED_FINITE_2S','--initial-us','1448','--target-us','1445','--output',str(init)],capture_output=True,text=True)
assert p.returncode==0,p.stderr[-400:]
initial=json.loads(init.read_text());stop=initial['result']['stopped'];assert stop['flags']==0 and stop['lease_left_ms']==0 and stop['width_us']==1445
expected=R/'expected-20us.json';expected.write_text(json.dumps({'boot_id':s['boot'],'registers':stop}))
p=subprocess.run(['/usr/bin/python3','-B',str(helper)]+base+['--confirmation','OBSERVED_20US_RETURN_2S','--expected-state',str(expected),'--output',str(trial)],capture_output=True,text=True)
assert p.returncode==0,p.stderr[-400:]
d=json.loads(trial.read_text());after=brief();assert d['status']=='20US_RETURN_ACK_AND_STOP_PASS_OBSERVATION_PENDING'
stop=d['result']['stopped'];assert stop['flags']==0 and stop['lease_left_ms']==0 and stop['width_us']==1445
s.update(phase='CURRENT_BOOT_FINITE_RETURN_STOPPED_OBSERVATION_PENDING',trial=str(trial),trial_sha256=sha(trial),gui_pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)))
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'boot_id':s['boot'],'init_sequence_us':[1448,1445],'roundtrip_sequence_us':[1445,1465,1445],
 'acks':len(d['events']),'last_elapsed_ms':d['events'][-1]['elapsed_ms'],'final':stop,'trial_sha256':s['trial_sha256'],
 'camera_pid_same':before['pid']==after['pid'],
 'physical_observation_pending':True,'automatic_following':False}))
