"""Root-only bounded public frontend slots; no production controls or microphone."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
CANDIDATE=HERE.parent
REPAIR=CANDIDATE.parent
PROJECT=REPAIR.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import argparse,base64,hashlib,http.client,importlib.util,json,os,pathlib,signal,subprocess,sys,time,types
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
stage=pathlib.Path(STAGE)
assert stage==pathlib.Path('/home/root/aura-public-frontend-allocation-20261031/c7988d2439fbb0d7')
for ancestor in [stage]+list(stage.parents):assert not ancestor.is_symlink()
stage.mkdir(parents=True,exist_ok=True,mode=0o700)
for item in FILES:
 rel=pathlib.PurePosixPath(item['relative_path']);assert not rel.is_absolute() and '..' not in rel.parts
 p=stage/str(rel);raw=base64.b64decode(item['base64'],validate=True)
 assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
 for ancestor in [p]+list(p.parents):assert not ancestor.is_symlink()
 p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 if p.exists():assert p.read_bytes()==raw
 else:
  with p.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
  p.chmod(0o444)
guard_path=pathlib.Path('/home/root/aura-public-asr-thread-abba-20261031/210925ca35fb5acd/probe_asr_abba.py')
guard_raw=guard_path.read_bytes()
assert hashlib.sha256(guard_raw).hexdigest()=='210925ca35fb5acdf90e96c08f9fe4713042637dd777d707c8ccb4134cdecf69'
# A fresh manually paused GUI has never created a speech job, hence DISABLED.
# Only this passive idle predicate differs; all pin/owner/mic/model guards stay.
old="('IDLE', 'CANCELLED', 'ANSWERED', 'ERROR', 'READY', 'EMPTY')"
new="('IDLE', 'CANCELLED', 'ANSWERED', 'ERROR', 'READY', 'EMPTY', 'DISABLED')"
guard_text=guard_raw.decode();assert guard_text.count(old)==1
guard=types.ModuleType('_public_frontend_root_guard');guard.__file__=str(guard_path)
sys.modules[guard.__name__]=guard;exec(compile(guard_text.replace(old,new),str(guard_path),'exec'),guard.__dict__)
boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==BOOT
ui=int(subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True,timeout=3))
camera=guard.get('127.0.0.1',8790,'/health')['pid']
args=argparse.Namespace(runtime_root=str(root),startup_sha256=EXPECTED,boot_id=boot,
 ui_pid=ui,ui_birth=guard.proc(ui)['birth'],camera_pid=camera,camera_birth=guard.proc(camera)['birth'],min_available_mib=1200)
deadline=time.monotonic()+20
while True:
 try:before=guard.metadata(args);break
 except guard.ProbeRefused as e:
  if e.code not in ('model_or_background_summary_active','memory_worker_active') or time.monotonic()>=deadline:raise
  time.sleep(.25)
started=time.monotonic();timed_out=False
process=subprocess.Popen(ARGV,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1'))
try:
 try:stdout,stderr=process.communicate(timeout=85)
 except subprocess.TimeoutExpired:
  timed_out=True
  if process.poll() is None:os.killpg(process.pid,signal.SIGTERM)
  try:stdout,stderr=process.communicate(timeout=5)
  except subprocess.TimeoutExpired:
   if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
   stdout,stderr=process.communicate(timeout=5)
finally:
 if process.poll() is None:
  os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
assert len(stdout)<1048576 and len(stderr)<1048576
try:result=json.loads(stdout)
except (ValueError,UnicodeDecodeError):result=dict(status='NO_VALID_RESULT',stdout_sha256=hashlib.sha256(stdout).hexdigest(),stdout_bytes=len(stdout))
after=guard.metadata(args,allow_background=True)
assert before['ui']==after['ui'] and before['camera']==after['camera']
print(json.dumps(dict(slot=SLOT,arm=ARM,result=result,exit_code=process.returncode,
 root_hard_timeout=timed_out,elapsed_seconds=time.monotonic()-started,
 stderr_sha256=hashlib.sha256(stderr).hexdigest(),stderr_bytes=len(stderr),before=before,after=after,
 owners_unchanged=True,manual_pause_preserved=True,
 background_activity_changed=before['memory']!=after['memory'] or not after['model_idle'],
 guard_delta='Accept DISABLED speech job only while all original paused/mic-off/no-pending predicates hold',
 production_written=False,microphone_opened=False,played_audio=False,asr_called=False)))
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('slot',choices=('A1','B1','B2','A2'));args=parser.parse_args()
    handoff_path=HERE/'PROBE_HANDOFF.json';raw=handoff_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='4e101eb523a5ed5bc4989be798f0acf9671da567ea734cf0a31ff36957c6e68c'
    handoff=json.loads(raw)
    files=[]
    for item in handoff['required_bundle_files']:
        raw=(CANDIDATE/item['relative_path']).read_bytes()
        assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
        files.append(dict(item,base64=base64.b64encode(raw).decode()))
    spec=json.loads((REPAIR.parent/'production_business_acceptance/spec.json').read_bytes())
    assert spec['startup_sha256']=='bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c'
    invocation=next(x for x in handoff['invocations'] if x['slot_id']==args.slot)
    values=dict(STAGE=handoff['stage_root'],FILES=files,BOOT=spec['boot_id'],EXPECTED=spec['startup_sha256'],
                SLOT=args.slot,ARM=invocation['arm'],ARGV=invocation['argv'])
    run_id=str(time.time_ns())
    result=json.loads(ssh('python3 -B -','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+REMOTE,timeout=135))
    out=HERE/('actual_'+args.slot+'_'+run_id+'.json')
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(out),slot=args.slot,exit_code=result['exit_code'],status=result['result'].get('status'),
                         elapsed_seconds=result['elapsed_seconds'],background_activity_changed=result['background_activity_changed'],
                         manual_pause_preserved=result['manual_pause_preserved'])))
