"""Public-only native check of the unchanged production ASR adapter with small model pins."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'first_wait_streaming_validation'))
import root_generate_fixtures
from board_ssh import ssh
GUARD=root_generate_fixtures.REMOTE.split('startup=json.loads',1)[0]
WORKER=r'''
import hashlib,importlib.util,json,pathlib,sys,time
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura')
asr=root/'board/runtime/audio/board_asr.py'
assert hashlib.sha256(asr.read_bytes()).hexdigest()=='4edb865881c887d6a290a02e078e14386bd95d017b79820b143b5a1e329997c3'
fixture=pathlib.Path('/home/root/aura-public-streaming-validation-20261031/synthetic-8a9983b6bb9f42c6')
helper=fixture/'quality_293b23f5dd350e5f.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='293b23f5dd350e5f4d1cce1489120a44b2c4d743c1534080da496f3f58407176'
spec=importlib.util.spec_from_file_location('_public_helper',helper);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
raw=(fixture/'manifest.json').read_bytes();assert hashlib.sha256(raw).hexdigest()=='7109ee213126f098a3a3da08bbc521beb0db54a21e0911be02e04f2010b9a869'
audio=h.validate_manifest(json.loads(raw));chosen=[row for row in audio if row[0]['id'] in ('S01','S08')]
assert len(chosen)==2
sys.path[:0]=[str(root),'/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps']
from board.runtime.audio.board_asr import BoardParaformer
with h.quiet_native():
 t=time.monotonic()
 model=BoardParaformer('/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6',
  model_sha256='3ef6c19369b912f7caf3cef8e545c5ccd1a33d9d7ec792a46668dc41c4b229ec',
  tokens_sha256='4b2d964e18b9cf139b473003b6698fb2ed9a2a5ec55b93daa677b28f578897aa',num_threads=3)
 load_ms=(time.monotonic()-t)*1000
 rows=[]
 for repeat in (1,2):
  for case,spans,pcm in chosen:
   start=time.monotonic();cpu=time.process_time()
   text=model.transcribe(pcm,deadline=start+15,cancelled=lambda:False)
   rows.append(dict(id=case['id'],round=repeat,wav_sha256=case['sha256'],hypothesis=text,
    decode_wall_ms=(time.monotonic()-start)*1000,decode_cpu_ms=(time.process_time()-cpu)*1000,
    intended_difference=h.character_error(case['reference_text'],text)))
print(json.dumps(dict(status='EXISTING_ADAPTER_SMALL_PUBLIC_CHECK_PASSED',adapter_sha256=hashlib.sha256(asr.read_bytes()).hexdigest(),asr_threads=3,load_ms=load_ms,results=rows,production_changed=False,microphone_opened=False,store_accessed=False)))
'''
RUN=r'''
import base64,os
raw=base64.b64decode(WORKER_SOURCE);assert hashlib.sha256(raw).hexdigest()==WORKER_SHA
environment=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
try:
 p=subprocess.run(['python3','-B','-'],input=raw.decode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=environment,timeout=70)
 assert len(p.stdout)<65536
 result=json.loads(p.stdout) if p.returncode==0 else dict(status='PUBLIC_ADAPTER_WORKER_FAILED',exit_code=p.returncode)
except subprocess.TimeoutExpired:result=dict(status='OWNED_PUBLIC_ADAPTER_WORKER_TIMED_OUT')
after=guard.metadata(args,allow_background=True)
result.update(before=before,after=after,owners_unchanged=before['ui']==after['ui'] and before['camera']==after['camera'],background_activity_changed=before['memory']!=after['memory'] or not after['model_idle'])
print(json.dumps(result))
'''

if __name__=='__main__':
    spec=json.loads((HERE.parent.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    values=dict(EXPECTED=spec['startup_sha256'],WORKER_SOURCE=base64.b64encode(WORKER.encode()).decode(),WORKER_SHA=hashlib.sha256(WORKER.encode()).hexdigest())
    header=''.join(k+'='+repr(v)+'\n' for k,v in values.items())
    value=json.loads(ssh('python3 -B -',header+GUARD+RUN,timeout=110))
    path=HERE/('EXISTING_ADAPTER_'+str(time.time_ns())+'.json')
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(value,ensure_ascii=True))
