import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');P=F/'face-source-v13'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'deployment-manifest.json')=='55fe7db4d03e48d7c3934ef5c7af701bdefc99909f09b34d6de97bcd65ddbabc'
assert all(sha(n)==v for n,v in json.loads((P/'deployment-manifest.json').read_text())['pins'].items())
b=P/'board_synthetic_benchmark.py';assert sha(b)=='b4925be42df4c88aeea23f15772d82cbbbbbdbf97a61630c64376702dd686dbd'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
before=get(8790,'/health');m=get(8783,'/api/state')['manual_pan']
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
proc=subprocess.run(['/usr/bin/python3','-B',str(b),'--baseline-root',str(F/'face-source-v12'),
 '--candidate-root',str(P),'--iterations','5'],capture_output=True,text=True,timeout=22)
assert proc.returncode==0,proc.stderr[-800:]+proc.stdout[-800:]
result=json.loads(proc.stdout);end=get(8783,'/api/state')['manual_pan'];after=get(8790,'/health')
assert end['readback']==m['readback'] and after['pid']==before['pid']
out=dict(result=result,readback_unchanged=end['readback'],camera_pid=after['pid'],
 primary_overruns_before=before['dpu_schedule']['primary_period_overruns'],primary_overruns_after=after['dpu_schedule']['primary_period_overruns'],
 optional_overruns_after={k:after['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},
 runtime_not_switched=True,actuator_writes=0)
(P/'board-synthetic-benchmark-result.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
