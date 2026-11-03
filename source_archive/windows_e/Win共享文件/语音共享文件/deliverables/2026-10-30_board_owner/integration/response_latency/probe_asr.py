"""Same pinned ASR, public upstream WAV, normal UI-closed window only."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import base64,hashlib,json,pathlib,subprocess,sys,time,types,wave
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True).splitlines() if '=' in x)
assert unit==dict(MainPID='0',ActiveState='inactive')
raw=(root/'startup/config.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED
pins=json.loads(raw)['component_sha256']
source=root/'runtime/aura/board/runtime/audio/board_asr.py'
assert hashlib.sha256(source.read_bytes()).hexdigest()==pins['board/runtime/audio/board_asr.py']
cfg=json.loads((root/'runtime/aura/config/board_avatar_gtk.json').read_bytes())['board_business']
production_threads=cfg.get('asr_threads',2);threads=THREADS or production_threads;assert threads in (1,2,3)
sys.path[:0]=[str(root/'runtime/aura'),'/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps']
from board.runtime.audio.board_asr import BoardParaformer
if CANDIDATE:
 raw=base64.b64decode(CANDIDATE['base64']);assert hashlib.sha256(raw).hexdigest()==CANDIDATE['sha256']
 module=types.ModuleType('_asr_thread_candidate');exec(compile(raw,'<reviewed-thread-candidate>','exec'),module.__dict__)
 BoardParaformer=module.BoardParaformer
sample=pathlib.Path('/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/models/paraformer/test_wavs/0.wav')
assert hashlib.sha256(sample.read_bytes()).hexdigest()=='1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c'
with wave.open(str(sample),'rb') as wav:
 assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(1,2,16000)
 pcm=wav.readframes(wav.getnframes())
start=time.monotonic()
model=BoardParaformer(cfg['asr_directory'],model_sha256='f36a0433bcf096bd6d6f11b80a3ac8bed110bdca632fe0d731df8d1a84475945',tokens_sha256='59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6',num_threads=threads)
load_ms=(time.monotonic()-start)*1000;runs=[];prior=None
for i in range(2):
 start=time.monotonic();text=model.transcribe(pcm,deadline=start+30)
 digest=hashlib.sha256(text.encode()).hexdigest()
 runs.append(dict(run=i+1,asr_ms=round((time.monotonic()-start)*1000,2),characters=len(text),same_transcript_as_first=prior is None or prior==digest))
 prior=digest
print(json.dumps(dict(status='CURRENT_PINNED_ASR_PUBLIC_WAV_DIAGNOSTIC',threads=threads,asr_threads_match_production=threads==production_threads,load_ms=round(load_ms,2),audio_seconds=len(pcm)/32000,runs=runs,
 formal_GUI_running=False,full_load_latency_acceptance=False,model_or_threshold_changed=False,
 private_store_accessed=False,physical_microphone_opened=False,audio_played=False,raw_audio_archived=False)))
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--threads',type=int,choices=(1,2,3));args=parser.parse_args()
    baseline=json.loads((HERE/'board_baseline.json').read_text(encoding='utf-8'))
    candidate=None
    if args.threads==3:
        raw=(HERE/'asr_threads_candidate/after/board/runtime/audio/board_asr.py').read_bytes()
        assert hashlib.sha256(raw).hexdigest()=='4edb865881c887d6a290a02e078e14386bd95d017b79820b143b5a1e329997c3'
        candidate=dict(sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode())
    result=json.loads(ssh('env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 python3 -B -','EXPECTED='+repr(baseline['startup_sha256'])+'\nTHREADS='+repr(args.threads)+'\nCANDIDATE='+repr(candidate)+'\n'+REMOTE,timeout=80))
    if candidate:result['candidate_sha256']=candidate['sha256']
    output=HERE/('public_asr_threads'+str(args.threads)+'.json' if args.threads else 'public_asr_diagnostic.json')
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
