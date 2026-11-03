"""Root-only guarded execution of the reviewed public Paraformer Small/Paraformer file worker."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
VALID = HERE.parent / 'first_wait_streaming_validation'
sys.path.insert(0, str(VALID))
import root_generate_fixtures
from board_ssh import ssh

GUARD = root_generate_fixtures.REMOTE.split('startup=json.loads', 1)[0].replace('min_available_mib=512', 'min_available_mib=1500')
RUN = r'''
import base64,os,math
fixture=pathlib.Path(MANIFEST_PATH)
assert not any(p.is_symlink() for p in (fixture,*fixture.parents))
assert fixture.parent.parent==pathlib.Path('/home/root/aura-public-streaming-validation-20261031')
assert hashlib.sha256(fixture.read_bytes()).hexdigest()==MANIFEST_SHA
helper=fixture.parent/'quality_293b23f5dd350e5f.py'
assert not helper.is_symlink() and hashlib.sha256(helper.read_bytes()).hexdigest()=='293b23f5dd350e5f4d1cce1489120a44b2c4d743c1534080da496f3f58407176'
raw=base64.b64decode(SOURCE);assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
worker=fixture.parent/('paraformer_small_'+SOURCE_SHA[:16]+'.py');assert not worker.is_symlink()
if worker.exists():assert worker.read_bytes()==raw
else:
 with worker.open('xb') as out:out.write(raw)
config_path=root/'runtime/aura/config/board_avatar_gtk.json'
assert hashlib.sha256(config_path.read_bytes()).hexdigest()=='faa5bead11f6c212412cf295db7d11c092c51848a5b08b49d78449ed613ba6d7'
config=json.loads(config_path.read_bytes())
model=pathlib.Path(config['board_business']['asr_directory']).resolve() if ENGINE=='paraformer' else pathlib.Path(MODEL_DIR)
command=['python3','-B',str(worker),'--engine',ENGINE,'--helper',str(helper),
 '--manifest',str(fixture),'--manifest-sha256',MANIFEST_SHA,'--model-dir',str(model),
 '--threads','3','--rounds','2','--external-deadline-managed','--max-seconds','170']
if ENGINE=='paraformer':command.extend(['--paraformer-source',str(root/'runtime/aura/board/runtime/audio/board_asr.py')])

def counters():
 def select(value,paths):
  result={}
  for path in paths:
   item=value
   for key in path.split('.'):item=item.get(key) if isinstance(item,dict) else None
   if type(item) in (int,float) and math.isfinite(item):result[path]=item
  return result
 try:
  state=guard.get('127.0.0.1',8783,'/api/state')
  camera=guard.get('127.0.0.1',8790,'/health')
  return dict(observed_mono=time.monotonic(),gui=select(state,('avatar_display.frames','avatar_display.paint_at','avatar_display.target_fps')),
   camera=select(camera,('capture_frames','detected_frames','preview_frames','observation_frame_id','capture_age_ms','observation_age_ms','capture_hz','detection_hz','preview_hz','last_inference_ms')))
 except Exception:return dict(available=False)

environment=dict(os.environ,PYTHONPATH='/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps',
 OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
counters_before=counters()
try:
 p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=environment,timeout=180)
 assert len(p.stdout)<262144
 try:result=json.loads(p.stdout)
 except Exception:result=dict(status='INVALID_PUBLIC_WORKER_OUTPUT',exit_code=p.returncode)
 result['worker_exit_code']=p.returncode
except subprocess.TimeoutExpired:
 result=dict(status='OWNED_PUBLIC_WORKER_TIMED_OUT')
counters_after=counters()
try:
 after=guard.metadata(args,allow_background=True)
 owners_unchanged=before['ui']==after['ui'] and before['camera']==after['camera']
 result.update(root_guard_after=after,owners_unchanged=owners_unchanged,
  background_activity_changed=before['memory']!=after['memory'] or not after['model_idle'])
except guard.ProbeRefused as error:
 result.update(post_guard_passed=False,post_guard_error_code=error.code,owners_unchanged=None)
result.update(root_guard_before=before,worker_sha256=SOURCE_SHA,production_configuration_changed=False,
 counters_before=counters_before,counters_after=counters_after,
 counters_scope='whole isolated process, including validation and model loading; not decode-only')
print(json.dumps(result,ensure_ascii=False))
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', required=True, choices=('paraformer', 'paraformer_small'))
    parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args()
    raw = (HERE / 'probe/public_paraformer_small_worker.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == args.source_sha256
    handoff_raw = (HERE / 'TEST_HANDOFF.json').read_bytes()
    assert hashlib.sha256(handoff_raw).hexdigest() == '17f107d00c29369c7a2204351e3b9440494656b511257f839ad05fb1c2a81d29'
    assert json.loads(handoff_raw)['worker_sha256'] == args.source_sha256
    fixture = json.loads((VALID / 'actual_fixture_generation_8a9983b6bb9f42c6.json').read_text(encoding='utf-8'))
    models = json.loads((HERE / 'STAGED_MODELS.json').read_text(encoding='utf-8'))
    spec = json.loads((HERE.parent.parent / 'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    values = dict(EXPECTED=spec['startup_sha256'], SOURCE_SHA=args.source_sha256, SOURCE=base64.b64encode(raw).decode(),
        ENGINE=args.engine, MODEL_DIR=models['board_directory'], MANIFEST_PATH=fixture['board_manifest_path'],
        MANIFEST_SHA=fixture['board_manifest_sha256'])
    header = ''.join(k + '=' + repr(v) + '\n' for k, v in values.items())
    value = json.loads(ssh('python3 -B -', header + GUARD + RUN, timeout=220))
    output = HERE / ('actual_public_' + args.engine + '_' + str(time.time_ns()) + '.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(value, ensure_ascii=True))
