"""Root bounded execution of an explicitly reviewed public online_paraformer worker."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import root_generate_fixtures
from board_ssh import ssh
GUARD=root_generate_fixtures.REMOTE.split('startup=json.loads',1)[0]
RUN=r'''
import base64,os
fixture=pathlib.Path(MANIFEST_PATH)
assert not fixture.is_symlink() and fixture.parent.parent==pathlib.Path('/home/root/aura-public-streaming-validation-20261031')
assert hashlib.sha256(fixture.read_bytes()).hexdigest()==MANIFEST_SHA
helper=fixture.parent/'quality_293b23f5dd350e5f.py'
assert not helper.is_symlink() and hashlib.sha256(helper.read_bytes()).hexdigest()=='293b23f5dd350e5f4d1cce1489120a44b2c4d743c1534080da496f3f58407176'
raw=base64.b64decode(SOURCE);assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
worker=fixture.parent/('online_paraformer_'+SOURCE_SHA[:16]+'.py');assert not worker.is_symlink()
if worker.exists():assert worker.read_bytes()==raw
else:
 with worker.open('xb') as out:out.write(raw)
command=['python3','-B',str(worker),'--mode',MODE,'--quality-helper',str(helper),
 '--manifest',str(fixture),'--manifest-sha256',MANIFEST_SHA,'--model-dir',MODEL_DIR,
 '--external-deadline-managed','--max-seconds','110','--feed-ms','20']
environment=dict(os.environ,PYTHONPATH='/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps',
 OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
try:
 p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=environment,timeout=120)
 assert len(p.stdout)<262144
 try:result=json.loads(p.stdout)
 except Exception:result=dict(status='INVALID_PUBLIC_ONLINE_PARAFORMER_OUTPUT',exit_code=p.returncode)
except subprocess.TimeoutExpired:
 result=dict(status='OWNED_PUBLIC_ONLINE_PARAFORMER_WORKER_TIMED_OUT')
after=guard.metadata(args,allow_background=True)
assert before['ui']==after['ui'] and before['camera']==after['camera']
result.update(root_guard_before=before,root_guard_after=after,worker_sha256=SOURCE_SHA,
 production_configuration_changed=False,background_activity_changed=before['memory']!=after['memory'] or not after['model_idle'])
print(json.dumps(result,ensure_ascii=False))
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',required=True,choices=('quality','realtime'))
    parser.add_argument('--source-sha256',required=True)
    args=parser.parse_args()
    raw=(HERE/'online_paraformer/public_online_paraformer_worker.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==args.source_sha256
    fixture=json.loads((HERE/'actual_fixture_generation_8a9983b6bb9f42c6.json').read_text(encoding='utf-8'))
    models=json.loads((HERE/'online_paraformer_staged_manifest.json').read_text(encoding='utf-8'))
    spec=json.loads((HERE.parent.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    values=dict(EXPECTED=spec['startup_sha256'],SOURCE_SHA=args.source_sha256,SOURCE=base64.b64encode(raw).decode(),
        MODE=args.mode,MODEL_DIR=models['board_directory'],MANIFEST_PATH=fixture['board_manifest_path'],MANIFEST_SHA=fixture['board_manifest_sha256'])
    header=''.join(k+'='+repr(v)+'\n' for k,v in values.items())
    result=json.loads(ssh('python3 -B -',header+GUARD+RUN,timeout=155))
    path=HERE/('actual_online_paraformer_'+args.mode+'_'+str(time.time_ns())+'.json')
    with path.open('x',encoding='utf-8') as output:
        json.dump(result,output,ensure_ascii=False,indent=2)
        output.write('\n')
    print(json.dumps(result,ensure_ascii=True))
