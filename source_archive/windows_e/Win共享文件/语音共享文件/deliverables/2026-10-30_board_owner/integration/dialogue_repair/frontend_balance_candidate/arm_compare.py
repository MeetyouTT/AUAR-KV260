"""Bounded sequential ARM comparison on the pinned public fixture, UI closed."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import gc,hashlib,json,os,pathlib,statistics,subprocess,sys,time,wave
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','ActiveState','-p','MainPID'],text=True).splitlines() if '=' in x)
assert unit=={'MainPID':'0','ActiveState':'inactive'},'production_must_be_normally_closed'
cfgraw=(root/'startup/config.json').read_bytes()
assert hashlib.sha256(cfgraw).hexdigest()==BASELINE['startup_sha256']
cfg=json.loads(cfgraw)
for rel in ('board/runtime/audio/board_gtcrn_fft.py','board/runtime/audio/board_gtcrn_reuse.py','board/runtime/audio/board_asr_frontend.py','board/runtime/audio/automatic_capture.py','board/runtime/audio/board_capture.py'):
 assert hashlib.sha256((root/'runtime/aura'/rel).read_bytes()).hexdigest()==BASELINE['component_sha256'][rel]
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
paths=[str(root/'runtime/aura'),'/home/root/aura-board-owner-candidate-20261030/fft-ee19b936d17aa451/deps','/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps','/home/root/aura-board-owner-candidate-20261030/webrtcvad-wheels-2.0.14-127741474d07c52f/deps']
sys.path[:0]=paths
import numpy as np
import onnxruntime as ort
from board.runtime.audio.board_gtcrn_fft import BoardFftSpeechGate
from board.runtime.audio.board_gtcrn_reuse import ReuseFftSpeechGate
from board.runtime.audio.board_capture import BoardFrontendPool
from board.runtime.audio.automatic_capture import SpeechEndpoint
models=pathlib.Path(BASELINE['resource_directories']['frontend_directory'])
wavpath=pathlib.Path(BASELINE['resource_directories']['asr_directory'])/'test_wavs/0.wav'
assert hashlib.sha256(wavpath.read_bytes()).hexdigest()=='1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c'
with wave.open(str(wavpath),'rb') as w:
 assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,16000)
 pcm=w.readframes(w.getnframes())
samples=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
reference=None; reference_result=None;reference_decisions=None;records=[]
nice=os.getpriority(os.PRIO_PROCESS,0)
os.setpriority(os.PRIO_PROCESS,0,-10)
def stats(rows):
 s=sorted(rows)
 return dict(count=len(s),mean_ms=sum(s)/len(s),p95_ms=s[int(.95*(len(s)-1))],maximum_ms=max(s))
try:
 for block,mode in enumerate(('baseline','combined','combined','baseline')):
  started=time.monotonic()
  gate=(BoardFftSpeechGate(models,num_threads=1) if mode=='baseline' else
        ReuseFftSpeechGate(models,num_threads=1,buffer_reuse=True,io_binding=True))
  load_ms=(time.monotonic()-started)*1000
  # Full denoised output stays in RAM; only error statistics leave this process.
  gate.denoiser.reset();parts=[]
  for offset in range(0,len(samples),320):parts.append(gate.denoiser(samples[offset:offset+320]).samples.copy())
  parts.append(gate.denoiser.flush().samples.copy());actual=np.concatenate(parts)
  if reference is None:reference=actual.copy()
  assert len(actual)==len(reference)==len(samples)
  delta=actual.astype(np.float64)-reference.astype(np.float64)
  maximum=float(np.max(np.abs(delta)));rms=float(np.sqrt(np.mean(delta*delta)))
  exact=bool(np.array_equal(np.rint(actual*32768).clip(-32768,32767),np.rint(reference*32768).clip(-32768,32767)))
  assert maximum<=1e-4 and rms<=1e-5 and exact,'denoised_numerical_equivalence_failed'
  pool=BoardFrontendPool(gate);trials=[]
  for trial in range(2):
   lease=pool.acquire();decisions=[]
   def classified(frame):
    decision=bool(lease(frame));decisions.append(decision);return decision
   endpoint=SpeechEndpoint(frame_classifier=classified,pre_roll_ms=500)
   wall=[];cpu=[];result=None;data=pcm+bytes(48000)
   for offset in range(0,len(data),640):
    raw=data[offset:offset+640].ljust(640,b'\0')
    t=time.perf_counter();c=time.thread_time()
    result=endpoint.feed(raw)
    cpu.append((time.thread_time()-c)*1000);wall.append((time.perf_counter()-t)*1000)
    if result is not None:break
   lease.close();assert result is not None,'public_endpoint_failed'
   if reference_result is None:reference_result=result;reference_decisions=decisions
   assert result==reference_result and decisions==reference_decisions,'vad_or_endpoint_pcm_changed'
   trials.append(dict(trial=trial,wall=stats(wall),cpu=stats(cpu),same_vad=True,same_endpoint_pcm=True))
   del endpoint,lease,classified
  pool.close()
  records.append(dict(block=block,mode=mode,load_ms=load_ms,max_abs_error=maximum,rms_error=rms,
    pcm16_equal=exact,trials=trials))
  del gate,pool,parts,actual,delta;gc.collect()
finally:os.setpriority(os.PRIO_PROCESS,0,nice)
print(json.dumps(dict(status='ARM_PUBLIC_NUMERICAL_AND_ENDPOINT_ABBA_PASS',records=records,
 startup_sha256=BASELINE['startup_sha256'],onnxruntime=ort.__version__,numpy=np.__version__,
 num_threads=1,scope='sequential_public_fixture_UI_closed_camera_unchanged',
 microphone_opened=False,production_database_opened=False,production_sources_modified=False)))
'''

if __name__ == '__main__':
    baseline = json.loads((HERE/'baseline_manifest.json').read_text(encoding='utf-8'))
    value = json.loads(ssh('python3 -B -', 'BASELINE='+repr(baseline)+'\n'+REMOTE, timeout=180))
    (HERE/'arm_public_comparison.json').write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    for mode in ('baseline','combined'):
        rows = [t for r in value['records'] if r['mode']==mode for t in r['trials']]
        print(json.dumps(dict(mode=mode,wall_mean_ms=sum(t['wall']['mean_ms'] for t in rows)/len(rows),
                             cpu_mean_ms=sum(t['cpu']['mean_ms'] for t in rows)/len(rows),trials=len(rows))))
    print(value['status'])
