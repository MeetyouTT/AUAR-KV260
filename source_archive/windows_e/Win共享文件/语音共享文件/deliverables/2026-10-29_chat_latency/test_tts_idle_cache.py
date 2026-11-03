"""GPU-free checks: allocator housekeeping cannot change voice or ownership."""
import contextlib,io,json,sys,types
from pathlib import Path
from unittest.mock import patch
from board.runtime.audio import omnivoice_voice as voice
from tools.selected_voice_service import VoiceWorker
MiB=1024*1024
class Cuda:
 def __init__(self,allocated=256*MiB,reserved=512*MiB,initialized=True):
  self.allocated=allocated;self.reserved=reserved;self.initialized=initialized;self.clears=0;self.syncs=0
 def is_initialized(self):return self.initialized
 def memory_allocated(self):return self.allocated
 def memory_reserved(self):return self.reserved
 def empty_cache(self):self.clears+=1;self.reserved=self.allocated+8*MiB
 def synchronize(self):self.syncs+=1
def torch(cuda):return types.SimpleNamespace(cuda=cuda,manual_seed=lambda n:None,inference_mode=contextlib.nullcontext)
def test_uninitialized_cuda_is_not_initialized_to_trim():
 cuda=Cuda(initialized=False)
 with patch.dict(sys.modules,torch=torch(cuda)):result=voice.release_idle_cuda_cache()
 assert result=={'available':False} and cuda.clears==0
def test_small_allocator_cache_stays_warm():
 cuda=Cuda(reserved=288*MiB)
 with patch.dict(sys.modules,torch=torch(cuda)):result=voice.release_idle_cuda_cache()
 assert result['available'] and result['released_bytes']==0 and cuda.clears==0
def test_only_unused_reserved_blocks_are_released():
 cuda=Cuda()
 with patch.dict(sys.modules,torch=torch(cuda)):result=voice.release_idle_cuda_cache()
 assert cuda.clears==1 and cuda.allocated==256*MiB and cuda.syncs==0
 assert result['allocated_bytes']==256*MiB and result['reserved_after_bytes']==264*MiB
 assert result['released_bytes']==248*MiB and result['trim_ms']>=0
def test_optional_allocator_diagnostic_failure_does_not_replace_audio():
 cuda=Cuda()
 def fail():raise RuntimeError('private driver information')
 cuda.empty_cache=fail
 with patch.dict(sys.modules,torch=torch(cuda)):result=voice.release_idle_cuda_cache()
 assert result=={'available':False,'error':'RuntimeError'}
class Text(io.StringIO):
 def reconfigure(self,**kwargs):pass
def worker_result(requests,*,fail=False):
 cuda=Cuda();events=[];output=Text()
 class Synth:
  def __init__(self,*a):pass
  def load(self):events.append('load')
  def generate_waves(self,text):events.append(('warmup_text',text));return [b'public-waves'],24000
  def synthesize(self,text):
   events.append(('synthesize',text))
   if fail:raise ValueError('synthetic inference failure')
   return {'path':'public.wav','sha256':'fixture','identity':{'seed':8701},'cache_hit':False}
 with patch.object(voice,'OmniVoiceSynthesizer',Synth),patch.dict(sys.modules,torch=torch(cuda)),\
      patch.object(sys,'stdin',Text(''.join(json.dumps(r)+'\n' for r in requests))),patch.object(sys,'stdout',output):
  voice.worker_main('public-cache','public-model')
 return [json.loads(line.removeprefix('RESULT ')) for line in output.getvalue().splitlines()],cuda,events
def test_worker_trims_after_warmup_and_finished_audio_preserving_result():
 rows,cuda,events=worker_result([{'type':'warmup','request_id':'warm'},{'text':'公开台词','request_id':'public'}])
 assert rows[0]['request_id']=='warm' and rows[0]['result']['ready']
 assert rows[1]['request_id']=='public' and rows[1]['ok']
 result=rows[1]['result'];assert result['path']=='public.wav' and result['sha256']=='fixture' and result['identity']=={'seed':8701}
 assert 'cuda_idle_cache' in result and cuda.syncs==1 and cuda.clears==1
 assert events==['load',('warmup_text','嗯，我在呢。'),('synthesize','公开台词')]
def test_inference_failure_remains_an_error_without_retry_or_trim():
 rows,cuda,events=worker_result([{'text':'公开台词','request_id':'public'}],fail=True)
 assert len(rows)==1 and not rows[0]['ok'] and 'synthetic inference failure' in rows[0]['error']
 assert cuda.clears==0 and events==[('synthesize','公开台词')]
def test_voice_health_keeps_only_small_allocator_fields():
 result={'path':'public.wav','cuda_idle_cache':{'available':True,'released_bytes':32,'trim_ms':2.5,'arbitrary_payload':{'text':'not health'}}}
 class Transport:
  def request(self,*a,**kw):return result
  def health(self):return {'alive':True,'quarantined':False,'closed':False,'error':''}
 worker=VoiceWorker.__new__(VoiceWorker);worker.cached_only=False;worker.transport=Transport();worker.error='';worker.cuda_idle_cache={}
 assert worker.request({'text':'public'}) is result
 health=worker.health();assert health['ready'] and health['cuda_idle_cache']=={'available':True,'released_bytes':32,'trim_ms':2.5}
 assert result['cuda_idle_cache']['arbitrary_payload']=={'text':'not health'}
def test_synthesis_identity_and_all_quality_parameters_match_before_r9():
 H=Path(__file__).resolve().parent;old=types.ModuleType('before_r9_voice');old.__file__=voice.__file__
 exec(compile((H/'before_r9/board/runtime/audio/omnivoice_voice.py').read_text(encoding='utf-8'),'before_r9_voice','exec'),old.__dict__)
 def fixture(cls):
  synth=cls.__new__(cls);synth.revision=voice.REVISION;synth.selection={'reference_sha256':'public','reference_text':'公开参考'};return synth
 assert fixture(voice.OmniVoiceSynthesizer).identity('请读公开编号一二三。')==fixture(old.OmniVoiceSynthesizer).identity('请读公开编号一二三。')
 assert voice.PARAMETERS==old.PARAMETERS and voice.PARAMETERS['num_step']==16
