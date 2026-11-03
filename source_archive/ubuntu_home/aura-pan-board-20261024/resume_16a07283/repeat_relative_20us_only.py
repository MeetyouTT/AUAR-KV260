"""Relative 20us only; no initialization."""
import fcntl,hashlib,json,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='16a07283-9e14-45e6-816d-3bda4cf333a7'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
helper=Path('/home/root/aura-post-power-20261022/helpers/96420fc26d811e16/source.py')
assert sha(helper)=='96420fc26d811e16bd47b8b3d16a0b1a6b3ea9759ba5490564205fc9c0065bb4'
s=json.loads((R/'state.json').read_text());assert s['phase']=='USER_REPORTED_APPROX_100DEG_MOTION_TESTS_HALTED'
u=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with u.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
h=get(8790,'/health');q=get(8783,'/api/state')
assert h['pid']==13537 and not h['dpu_schedule']['owner_fenced']
assert q['phase']=='IDLE' and not q['manual_pan']['automatic_following'] and q['manual_pan']['state']=='FAULT'
assert not q.get('playing') and q.get('audio_output_state')=='IDLE_READY'
assert q.get('local_recording',{}).get('state')!='RECORDING'
proof=json.loads((R/'id-stop-after-user-100deg.json').read_text());stop=proof['after_stop']
assert proof['boot_id']==s['boot'] and stop['width_us']==1445 and stop['flags']==0 and stop['lease_left_ms']==0
lock=(O/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
expected=R/'expected-relative-20us.json';trial=R/'relative-20us-no-init.json'
assert not expected.exists() and not trial.exists()
with expected.open('x') as f:json.dump({'boot_id':s['boot'],'registers':stop},f)
s.update(phase='USER_CONFIRMED_CENTER_RELATIVE_TEST_STARTING',
 user_feedback_correction='100deg describes returning to center, not the 20us increment',
 center_confirmation_kind='USER_VISUAL_ONLY',previous_anomaly_interpretation_retracted=True)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
old=Path(s['old_root'])
p=subprocess.run(['/usr/bin/python3','-B',str(helper),'--execute','--confirmation','OBSERVED_20US_RETURN_2S',
 '--manifest',str(old/'candidate-manifest.json'),'--manifest-sha256','ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab',
 '--context',str(R/'context.json'),'--expected-state',str(expected),'--output',str(trial)],capture_output=True,text=True,timeout=15)
assert p.returncode==0,p.stderr[-700:]
t=json.loads(trial.read_text());after=t['result']['stopped'];assert after['flags']==0 and after['lease_left_ms']==0 and after['width_us']==1445
s.update(phase='CURRENT_BOOT_RELATIVE_20US_STOPPED_OBSERVATION_PENDING',trial=str(trial),trial_sha256=sha(trial))
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'initialization_repeated':False,'sequence_us':[1445,1465,1445],
 'acks':len(t['events']),'final':after,'trial_sha256':sha(trial),'physical_effect_pending':True,'automatic_following':False}))
