"""ARM subprocess admission and owned teardown, finite actual mic diagnostic."""
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
assert hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()=='b81fff59527c11323f9f869c647e0563f393a01c7f59bc39fde23391eb4f4275'
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True).splitlines() if '=' in x)
assert unit==dict(MainPID='0',ActiveState='inactive')
assert os.getpriority(os.PRIO_PROCESS,0)==0
sys.path[:0]=[str(root/'runtime/aura'),
 '/home/root/aura-board-owner-candidate-20261030/fft-ee19b936d17aa451/deps',
 '/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps',
 '/home/root/aura-board-owner-candidate-20261030/webrtcvad-wheels-2.0.14-127741474d07c52f/deps']
os.environ['PYTHONPATH']=':'.join(sys.path[:4])  # Match the formal unit's child environment.
from tools.production_frontend_selection import create_frontend_pool
from board.runtime.audio.board_capture_priority import PriorityBoardAutomaticCapture
cfg=json.loads((root/'runtime/aura/config/board_avatar_gtk.json').read_bytes())
pool=create_frontend_pool(cfg['board_business']['frontend_directory'],optimization='baseline',num_threads=1,frontend_process=True)
gate=pool.gate;pid=gate.process.pid
cap=PriorityBoardAutomaticCapture(lambda:False,frontend_factory=pool.acquire,max_seconds=2)
try:
 cap.start();time.sleep(1.5);snap=cap.snapshot();priority=snap.get('capture_priority',{})
 out={k:snap.get(k) for k in ('state','input_ready','listening_seconds')}
 out.update(audio_frontend=snap.get('audio_frontend'),input_queue=snap.get('input_queue'),capture_priority=priority,
  error_code='none' if not snap.get('error') else 'capture_error',
  process_nice=os.getpriority(os.PRIO_PROCESS,0),arecord_nice=os.getpriority(os.PRIO_PROCESS,cap._process.pid),
  worker_pid=pid,worker_nice=os.getpriority(os.PRIO_PROCESS,pid),
  duplicate_frontend_resident=False,formal_GUI_running=False,diagnostic_not_performance_acceptance=True,
  raw_audio_saved_or_transferred=False,asr_or_llm_called=False)
finally:
 cap.close();out['after_close_priority']=cap.snapshot().get('capture_priority');pool.close()
 out['worker_shutdown_confirmed']=gate.shutdown(timeout=2.)
 out['worker_exit_code']=gate.process.poll()
out['passed']=(out['state']=='RECORDING' and out['error_code']=='none' and out['input_ready'] is True
 and out['process_nice']==0 and out['arecord_nice']==0 and out['worker_nice']==-10
 and out['after_close_priority'].get('restoration_confirmed') is True
 and out['worker_shutdown_confirmed'] is True and out['worker_exit_code']==0)
print(json.dumps(out))
'''

if __name__=='__main__':
    value=json.loads(ssh('env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -',REMOTE,timeout=90))
    (HERE/'actual_frontend_process_check.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value))
