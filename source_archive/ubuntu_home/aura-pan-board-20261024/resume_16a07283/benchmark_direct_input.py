import hashlib,json,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283')
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
B=O/'pan-face-edge-v5/yunet-direct-input-20261026'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def manual():
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:return json.load(f)['manual_pan']
m=manual();assert m['state']=='READY' and not m['automatic_following']
assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
meta=json.loads((O/'meta.json').read_text());root=Path(meta['candidate_root'])/'aura'
assert hashlib.sha256((root/'board/vision/reference_faces.py').read_bytes()).hexdigest()=='ee34109e23423d99a4ea3ff75c2bf9d113329b1c8162cd02f30e7dfcfb6bfeaf'
job=subprocess.run(['/usr/bin/python3','-B',str(B/'board_direct_benchmark.py'),
 '--runtime-root',str(root),'--iterations','20','--max-seconds','12'],
 stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=18)
after=manual();assert after['state']=='READY' and not after['automatic_following']
assert after['readback']==m['readback']
assert job.returncode==0,job.stderr[-500:]
result=json.loads(job.stdout);assert result['dpu_jobs']==0 and result['motor_commands']==0
print(json.dumps({'status':'DIRECT_BENCH_STOP_UNCHANGED','benchmark':result,
 'before_readback':m['readback'],'after_readback':after['readback'],'motor_commands_sent':0}))
