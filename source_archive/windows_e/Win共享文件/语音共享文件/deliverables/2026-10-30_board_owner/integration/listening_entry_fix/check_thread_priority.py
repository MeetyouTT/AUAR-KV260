"""Finite root diagnostic; metadata only, no ASR/playback/audio persistence."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import base64,hashlib,http.client,importlib.util,json,os,pathlib,sys,time
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='8100a7fd-0c6a-46c4-82b8-f874988a1521'
assert os.getpriority(os.PRIO_PROCESS,0)==0
conn=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
try:
 conn.request('GET','/api/state');r=conn.getresponse();raw=r.read(1048577)
 assert r.status==200 and len(raw)<=1048576
 state=json.loads(raw)
finally:conn.close()
h=state['handsfree_dialogue']
assert h.get('enabled') is False and h.get('microphone_open') is False and state.get('playing') is False
assert state['manual_pan']['automatic_following'] is False
raw=base64.b64decode(SOURCE)
assert hashlib.sha256(raw).hexdigest()==PIN
directory=root.parent/('priority-probe-'+PIN[:16])
directory.mkdir(mode=0o700,exist_ok=True)
target=directory/'board_capture_priority.py'
if target.exists():assert target.read_bytes()==raw
else:
 fd=os.open(str(target),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
sys.path[:0]=[str(root/'runtime/aura'),
 '/home/root/aura-board-owner-candidate-20261030/fft-ee19b936d17aa451/deps',
 '/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps',
 '/home/root/aura-board-owner-candidate-20261030/webrtcvad-wheels-2.0.14-127741474d07c52f/deps']
spec=importlib.util.spec_from_file_location('_thread_priority_probe',str(target))
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
from board.runtime.audio.board_capture import BoardFrontendPool
from board.runtime.audio.board_gtcrn_fft import BoardFftSpeechGate
cfg=json.loads((root/'runtime/aura/config/board_avatar_gtk.json').read_bytes())
pool=BoardFrontendPool(BoardFftSpeechGate(cfg['board_business']['frontend_directory'],num_threads=1))
cap=mod.PriorityBoardAutomaticCapture(lambda:False,frontend_factory=pool.acquire,max_seconds=2)
start=time.monotonic();cpu=time.process_time()
try:
 cap.start();time.sleep(1.5);snap=cap.snapshot()
 p=snap.get('capture_priority',{})
 out={k:snap.get(k) for k in ('state','error','input_ready','listening_seconds')}
 out['frontend']=snap.get('frontend');out['queue']=snap.get('pcm_input') or snap.get('queue')
 # Do not export arbitrary snapshot contents or PCM. Selected numeric pipeline
 # fields are already the capture implementation's public metadata.
 out['capture_priority']=p
 out['observed_nice']={name:os.getpriority(os.PRIO_PROCESS,tid) for name,tid in (
  ('process',os.getpid()),('arecord',cap._process.pid),
  ('consumer',p['native_tid']),('pump',p['pump_native_tid'])) if tid}
 out.update(elapsed_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,
  duplicate_frontend_resident=True,diagnostic_not_performance_acceptance=True,
  raw_audio_saved_or_transferred=False,asr_or_llm_called=False)
finally:
 cap.close();out['after_close_priority']=cap.snapshot().get('capture_priority');pool.close()
out['passed']=(out['state']=='RECORDING' and not out['error'] and out['input_ready'] is True
 and out['observed_nice']==dict(process=0,arecord=0,consumer=-10,pump=-10)
 and out['after_close_priority'].get('restoration_confirmed') is True)
print(json.dumps(out))
'''

if __name__ == '__main__':
    path=HERE.parent/'production_frontend_capacity_candidate/after/aura/board/runtime/audio/board_capture_priority.py'
    raw=path.read_bytes()
    pin='f98aeb83285df389417cd3da98d7c95920417ca342926718a31b88926afe1931'
    assert hashlib.sha256(raw).hexdigest()==pin
    prefix='SOURCE='+repr(base64.b64encode(raw).decode())+'\nPIN='+repr(pin)+'\n'
    value=json.loads(ssh('env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -',prefix+REMOTE,timeout=40))
    (HERE/'actual_thread_priority_check.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value))
