import hashlib,json,subprocess
from pathlib import Path
A=Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1/runtime/aura')
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/audio-queue-bound-v1')
p=P/'native_queue_benchmark_r2.py'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='03a84e4ab1586842447e77fe770ca5777af2bc47794da26fa0ef60f8c8d52a5a'
cmd=['/usr/bin/python3','-B',str(p),'--role','baseline','--runtime-root',str(A),
 '--baseline-engine',str(A/'tools/gstreamer_persistent_engine.py'),'--candidate-engine',str(P/'gstreamer_persistent_engine.py')]
try:
 job=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=12)
 out=dict(returncode=job.returncode,stages=job.stderr[-6000:],result=json.loads(job.stdout) if job.returncode==0 else None)
except subprocess.TimeoutExpired as exc:
 raw=exc.stderr or b''
 out=dict(returncode=None,timeout_seconds=12,stages=raw.decode('utf-8','replace')[-6000:] if isinstance(raw,bytes) else raw[-6000:],own_child_killed=True)
out.update(motor_commands_sent=0,ALSA_opened=False,business_processes_changed=False)
print(json.dumps(out))
