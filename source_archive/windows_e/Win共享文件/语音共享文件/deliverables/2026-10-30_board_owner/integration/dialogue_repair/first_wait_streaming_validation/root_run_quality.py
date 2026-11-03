"""Root guarded transport for the pinned public-only quality worker."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(HERE))
import root_generate_fixtures
from board_ssh import ssh

GUARD = root_generate_fixtures.REMOTE.split("startup=json.loads", 1)[0]
RUN = r'''
import base64,os
fixture=pathlib.Path(MANIFEST_PATH)
assert not fixture.is_symlink() and fixture.parent.parent==pathlib.Path('/home/root/aura-public-streaming-validation-20261031')
assert hashlib.sha256(fixture.read_bytes()).hexdigest()==MANIFEST_SHA
raw=base64.b64decode(SOURCE);assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
worker=fixture.parent/('quality_'+SOURCE_SHA[:16]+'.py');assert not worker.is_symlink()
if worker.exists():assert worker.read_bytes()==raw
else:
 with worker.open('xb') as out:out.write(raw)
config=json.loads((root/'runtime/aura/config/board_avatar_gtk.json').read_bytes())
model=pathlib.Path(config['board_business']['asr_directory']).resolve() if ENGINE=='paraformer' else pathlib.Path('/home/root/aura-public-streaming-asr-20261031/68c9c943840f7d9c')
command=['python3','-B',str(worker),'--engine',ENGINE,'--manifest',str(fixture),'--manifest-sha256',MANIFEST_SHA,
 '--model-dir',str(model),'--external-deadline-managed','--max-seconds','100']
if ENGINE=='paraformer':command.extend(['--paraformer-source',str(root/'runtime/aura/board/runtime/audio/board_asr.py')])
environment=dict(os.environ,PYTHONPATH='/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps',
 OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
try:
 p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=environment,timeout=110)
 assert len(p.stdout)<262144
 try:result=json.loads(p.stdout)
 except Exception:result=dict(status='INVALID_PUBLIC_QUALITY_OUTPUT',exit_code=p.returncode)
except subprocess.TimeoutExpired:
 result=dict(status='OWNED_PUBLIC_QUALITY_WORKER_TIMED_OUT')
after=guard.metadata(args,allow_background=True)
assert before['ui']==after['ui'] and before['camera']==after['camera']
result.update(root_guard_before=before,root_guard_after=after,worker_sha256=SOURCE_SHA,
 production_configuration_changed=False,background_activity_changed=before['memory']!=after['memory'] or not after['model_idle'])
print(json.dumps(result,ensure_ascii=False))
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', required=True, choices=('paraformer', 'ctc'))
    args = parser.parse_args()
    raw = (HERE / 'quality/public_quality_worker.py').read_bytes()
    digest = '293b23f5dd350e5f4d1cce1489120a44b2c4d743c1534080da496f3f58407176'
    assert hashlib.sha256(raw).hexdigest() == digest
    fixture = json.loads((HERE / 'actual_fixture_generation_8a9983b6bb9f42c6.json').read_text(encoding='utf-8'))
    spec = json.loads((HERE.parent.parent / 'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    variables = dict(EXPECTED=spec['startup_sha256'], SOURCE_SHA=digest, SOURCE=base64.b64encode(raw).decode(),
                     ENGINE=args.engine, MANIFEST_PATH=fixture['board_manifest_path'], MANIFEST_SHA=fixture['board_manifest_sha256'])
    header = ''.join(key + '=' + repr(value) + '\n' for key, value in variables.items())
    value = json.loads(ssh('python3 -B -', header + GUARD + RUN, timeout=145))
    output = HERE / ('actual_quality_' + args.engine + '_' + str(time.time_ns()) + '.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(value, ensure_ascii=True))
