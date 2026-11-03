import hashlib,json,subprocess,urllib.request
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');P=OPS/'pan-face-edge-v5/yunet-input-fast-20261026'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'fast_yunet_input.py')=='4cadbd723c74041405fa97e34f917656200302bf330d24528b92a570ea3aa7d0'
assert sha(P/'board_benchmark.py')=='62867afe9c8c32f2a1930898ede33774bb752afa73a6c6ecefd9d23e249cbff7'
meta=json.loads((OPS/'meta.json').read_text());runtime=Path(meta['candidate_root'])/'aura'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
before=get(8790,'/health');manual=get(8783,'/api/state')['manual_pan']
assert manual['state']=='READY' and not manual['automatic_following'] and manual['readback']['flags']==0 and manual['readback']['lease_left_ms']==0
r=subprocess.run(['/usr/bin/python3','-B',str(P/'board_benchmark.py'),'--runtime-root',str(runtime),
 '--iterations','20','--max-seconds','12'],capture_output=True,text=True,timeout=16)
assert r.returncode==0,r.stderr[-1800:]+r.stdout[-500:]
report=json.loads(r.stdout);after=get(8790,'/health');end=get(8783,'/api/state')['manual_pan']
assert end['readback']==manual['readback'] and before['pid']==after['pid']
print(json.dumps(dict(benchmark=report,camera_pid=after['pid'],readback_unchanged=end['readback'],
 primary_overruns_before=before['dpu_schedule']['primary_period_overruns'],primary_overruns_after=after['dpu_schedule']['primary_period_overruns'],
 optional_overruns_after={k:after['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},runtime_not_switched=True)))
