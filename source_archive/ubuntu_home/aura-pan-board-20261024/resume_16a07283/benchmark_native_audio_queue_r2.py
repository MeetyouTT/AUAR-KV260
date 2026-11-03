import hashlib,json,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283')
A=R/'gui-manual-bound-v1/runtime/aura'
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/audio-queue-bound-v1')
assert hashlib.sha256((P/'native_queue_benchmark_r2.py').read_bytes()).hexdigest()=='03a84e4ab1586842447e77fe770ca5777af2bc47794da26fa0ef60f8c8d52a5a'
assert hashlib.sha256((P/'gstreamer_persistent_engine.py').read_bytes()).hexdigest()=='f5d987904aec0dc679936da27018f404f9cc77f42d300e0579a3b52a95f0655c'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def state():
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:return json.load(f)
u=state();m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following']
assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
before_pcm=Path('/proc/asound/card1/pcm0p/sub0/status').read_text()
job=subprocess.run(['/usr/bin/python3','-B',str(P/'native_queue_benchmark_r2.py'),
 '--runtime-root',str(A),'--baseline-engine',str(A/'tools/gstreamer_persistent_engine.py'),
 '--candidate-engine',str(P/'gstreamer_persistent_engine.py')],
 stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=21)
after=state();assert after['manual_pan']['state']=='READY' and not after['manual_pan']['automatic_following']
assert after['manual_pan']['readback']==m['readback']
assert job.returncode==0,job.stderr[-1800:]
result=json.loads(job.stdout);assert result['status']=='REAL_APPSRC_QUEUE_BOUND_PASS'
after_pcm=Path('/proc/asound/card1/pcm0p/sub0/status').read_text()
owner=lambda raw:next((line.split(':',1)[1].strip() for line in raw.splitlines() if line.startswith('owner_pid')),None)
assert owner(before_pcm)==owner(after_pcm)
print(json.dumps({'status':'KV260_REAL_GST_QUEUE_ISOLATION_PASS','benchmark':result,
 'business_audio_owner_unchanged':owner(after_pcm),'manual_readback':m['readback'],
 'motor_commands_sent':0,'business_pipeline_restarted':False,'USB_root_cause_verified':False}))
