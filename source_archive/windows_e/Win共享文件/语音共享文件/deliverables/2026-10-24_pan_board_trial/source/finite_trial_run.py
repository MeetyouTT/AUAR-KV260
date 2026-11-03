BOOT='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
ROOT='/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2'
MANIFEST_SHA='ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab'
import hashlib,json,subprocess,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
root=Path(ROOT);s=json.loads((root/'trial-state.json').read_text())
assert s['phase']=='CANDIDATE_READY_FOR_FINITE_OBSERVATION',s['phase']
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=4) as response:g=json.load(response)
assert g['phase']=='IDLE' and not g['playing'] and g['audio_output_state']=='IDLE_READY'
assert g.get('local_recording',{}).get('state')!='RECORDING'
assert not g.get('local_transcription',{}).get('service',{}).get('pending')
manifest=root/'candidate-manifest.json';assert hashlib.sha256(manifest.read_bytes()).hexdigest()==MANIFEST_SHA
output=root/'finite-step-result.json';assert not output.exists()
args=['/usr/bin/python3','-B',str(root/'bench_finite_step.py'),'--execute','--confirmation','OBSERVED_FINITE_2S','--initial-us','1420','--target-us','1425','--manifest',str(manifest),'--manifest-sha256',MANIFEST_SHA,'--context',str(root/'context.json'),'--output',str(output)]
p=subprocess.run(args,capture_output=True,text=True)
result=json.loads(output.read_text()) if output.exists() else None
print(json.dumps({'exit_code':p.returncode,'result':result,'stderr':p.stderr[-1000:]}))
