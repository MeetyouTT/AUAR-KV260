"""Root-owned bounded public ASR scheduling comparison; no production source edits."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import root_generate_fixtures
from board_ssh import ssh

GUARD = root_generate_fixtures.REMOTE.split('startup=json.loads', 1)[0]
RUN = r'''
import base64, os, signal
destination=pathlib.Path('/home/root/aura-public-streaming-validation-20261031')/('asr-scheduling-'+SOURCE_SHA[:16])
assert not destination.parent.is_symlink() and not destination.is_symlink()
destination.mkdir(mode=0o700,parents=True,exist_ok=True)
for name, encoded, expected in FILES:
 raw=base64.b64decode(encoded); assert hashlib.sha256(raw).hexdigest()==expected
 target=destination/name; assert not target.is_symlink()
 if target.exists(): assert target.read_bytes()==raw
 else:
  with target.open('xb') as out:out.write(raw)
command=['python3','-B',str(destination/'probe_asr_scheduling.py'),
 '--pipeline-source',str(destination/'public_pipeline.py'),'--startup-sha256',EXPECTED,'--camera-health-port','8790',
 '--boot-id',boot,'--ui-pid',str(ui),'--ui-birth',str(args.ui_birth),
 '--camera-pid',str(camera),'--camera-birth',str(args.camera_birth),'--min-available-mib','1500','--run']
environment=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
 PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
 env=environment,start_new_session=True)
try:
 stdout,stderr=process.communicate(timeout=600)
 assert len(stdout)<262144
 try:result=json.loads(stdout)
 except Exception:result=dict(status='INVALID_PUBLIC_ASR_SCHEDULING_OUTPUT',exit_code=process.returncode,
  stdout_bytes=len(stdout.encode()),stderr_bytes=len(stderr.encode()))
except subprocess.TimeoutExpired:
 # Each slot has its own group. On the outer fail-safe, close owned slots first.
 children=pathlib.Path('/proc')/str(process.pid)/'task'/str(process.pid)/'children'
 for child_id in children.read_text().split() if children.exists() else []:
  child_pid=int(child_id)
  try:
   child_stat=(pathlib.Path('/proc')/child_id/'stat').read_text();fields=child_stat[child_stat.rfind(')')+2:].split()
   birth=guard.proc(child_pid)['birth']
   if int(fields[1])==process.pid and os.getpgid(child_pid)==child_pid and guard.proc(child_pid)['birth']==birth:
    os.killpg(child_pid,signal.SIGKILL)
  except (FileNotFoundError,ProcessLookupError):pass
 os.killpg(process.pid,signal.SIGKILL);process.communicate(timeout=5)
 result=dict(status='OWNED_PUBLIC_ASR_SCHEDULING_PROCESS_GROUP_TIMED_OUT')
finally:
 # The group was created here exclusively for this trial, never a production PGID.
 try:os.killpg(process.pid,signal.SIGTERM)
 except ProcessLookupError:pass
after=guard.metadata(args,allow_background=True)
assert before['ui']==after['ui'] and before['camera']==after['camera']
result.update(root_guard_before=before,root_guard_after=after,worker_sha256=SOURCE_SHA,
 production_configuration_changed=False,background_activity_changed=before['memory']!=after['memory'] or not after['model_idle'])
print(json.dumps(result,ensure_ascii=False))
'''

if __name__ == '__main__':
    digest = '0ac78870248f7f1db5a24df585dc0086d5ae0d83d470dd742cbe9615e1d992c6'
    pipeline_sha = 'ac0af16c9f783b5590ab0e1562ece179b8cc50ade3912c8b08e8b8592778e093'
    files = []
    for source, target, expected in (
        (HERE.parent/'asr_scheduling_candidate/probe_asr_scheduling.py', 'probe_asr_scheduling.py', digest),
        (HERE.parent.parent/'resume_frontend_optimization/board_audio_runtime_probe.py', 'public_pipeline.py', pipeline_sha),
    ):
        raw = source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        files.append((target, base64.b64encode(raw).decode(), expected))
    spec = json.loads((HERE.parent.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    values = dict(EXPECTED=spec['startup_sha256'], SOURCE_SHA=digest, PIPELINE_SHA=pipeline_sha, FILES=files)
    header = ''.join(k+'='+repr(v)+'\n' for k, v in values.items())
    result = json.loads(ssh('python3 -B -', header+GUARD+RUN, timeout=650))
    output = HERE/('actual_asr_scheduling_'+str(time.time_ns())+'.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(result, ensure_ascii=True))
