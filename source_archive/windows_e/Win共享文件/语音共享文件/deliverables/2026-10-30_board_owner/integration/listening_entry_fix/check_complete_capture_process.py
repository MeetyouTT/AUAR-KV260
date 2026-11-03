"""Finite ARM admission of original automatic capture in the owned child."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import hashlib,json,os,pathlib,subprocess,sys,time
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()==EXPECTED
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True).splitlines() if '=' in x)
assert unit==dict(MainPID='0',ActiveState='inactive')
assert os.getpriority(os.PRIO_PROCESS,0)==0
sys.path[:0]=[str(root/'runtime/aura'),
 '/home/root/aura-board-owner-candidate-20261030/fft-ee19b936d17aa451/deps',
 '/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps',
 '/home/root/aura-board-owner-candidate-20261030/webrtcvad-wheels-2.0.14-127741474d07c52f/deps']
os.environ['PYTHONPATH']=':'.join(sys.path[:4])
from tools.production_frontend_selection import create_frontend_pool
from board.runtime.audio.board_frontend_auto import RemoteAutomaticCapture
cfg=json.loads((root/'runtime/aura/config/board_avatar_gtk.json').read_bytes())
assert cfg['board_business']['frontend_capture_process'] is True
pool=create_frontend_pool(cfg['board_business']['frontend_directory'],optimization='baseline',num_threads=1,frontend_process=True)
gate=pool.gate;pid=gate.process.pid
def recorders():
 result=[]
 for path in pathlib.Path('/proc').iterdir():
  if not path.name.isdigit():continue
  try:
   raw=(path/'stat').read_text();parts=raw[raw.rfind(')')+2:].split()
   if int(parts[1])==pid and (path/'comm').read_text().strip()=='arecord':
    result.append(dict(pid=int(path.name),nice=os.getpriority(os.PRIO_PROCESS,int(path.name))))
  except (OSError,ValueError):pass
 return result
cap=RemoteAutomaticCapture(lambda:False,frontend_pool=pool,max_seconds=2,speech_start_ready=lambda cid:True)
out={}
try:
 cap.start();end=time.monotonic()+1.5
 while time.monotonic()<end:
  cap.snapshot();time.sleep(.05)
 snap=cap.snapshot()
 out={k:snap.get(k) for k in ('state','input_ready','listening_seconds')}
 out.update(audio_frontend=snap.get('audio_frontend'),input_queue=snap.get('input_queue'),
  error_code='none' if not snap.get('error') else snap.get('error'),
  process_nice=os.getpriority(os.PRIO_PROCESS,0),owned_arecord=recorders(),
  worker_pid=pid,worker_nice=os.getpriority(os.PRIO_PROCESS,pid),
  duplicate_frontend_resident=False,formal_GUI_running=False,diagnostic_not_performance_acceptance=True,
  raw_audio_saved_or_transferred=False,asr_or_llm_called=False)
 cap.cancel();out['cancel_state']=cap.snapshot()['state'];out['arecord_after_cancel']=recorders()
finally:
 try:cap.close()
 finally:
  pool.close();out['worker_shutdown_confirmed']=gate.shutdown()
  out['worker_exit_code']=gate.process.poll()
out['passed']=(out['state'] in ('RECORDING','READY') and out['error_code']=='none' and out['input_ready'] is True
 and out['audio_frontend'].get('frames',0)>25 and out['process_nice']==0 and out['worker_nice']==-10
 and (out['state']=='READY' or len(out['owned_arecord'])==1 and out['owned_arecord'][0]['nice']==-10)
 and out['cancel_state']=='CANCELLED' and not out['arecord_after_cancel']
 and out['worker_shutdown_confirmed'] is True and out['worker_exit_code']==0)
print(json.dumps(out))
'''

if __name__=='__main__':
    spec=json.loads((HERE.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    value=json.loads(ssh('env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -','EXPECTED='+repr(spec['startup_sha256'])+'\n'+REMOTE,timeout=90))
    (HERE/'actual_complete_capture_process_check.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value))
