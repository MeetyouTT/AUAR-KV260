"""Candidate: return only unused TTS allocator cache, retaining loaded weights."""
import datetime,hashlib,json,shutil,types
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
previous=json.loads((H/'source_plan_r8.json').read_text(encoding='utf-8'))
assert json.loads((H/'deployment_r8.json').read_text(encoding='utf-8'))['status']=='COMMITTED'
assert not (H/'source_plan_r9.json').exists()
for name,entry in previous['files'].items():assert hashlib.sha256((A/name).read_bytes()).hexdigest()==entry['candidate'],name
names=list(previous['files'])+['board/runtime/audio/omnivoice_voice.py','tools/selected_voice_service.py']
for name in names:
 for directory in ('before_r9','candidate_r9_source'):
  dest=H/directory/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(A/name,dest)
path=H/'candidate_r9_source/board/runtime/audio/omnivoice_voice.py';source=path.read_text(encoding='utf-8')
source=source.replace('import sys\n','import sys\nimport time\n',1)
helper='''def release_idle_cuda_cache():
    """Drop unused allocator blocks after inference, never tensors or weights."""
    import torch
    if not torch.cuda.is_initialized():return {'available':False}
    try:
        allocated=int(torch.cuda.memory_allocated())
        before=int(torch.cuda.memory_reserved())
        started=time.perf_counter()
        if before-allocated>=64*1024*1024:torch.cuda.empty_cache()
        after=int(torch.cuda.memory_reserved())
        return {'available':True,'allocated_bytes':allocated,
                'reserved_before_bytes':before,'reserved_after_bytes':after,
                'released_bytes':max(0,before-after),
                'trim_ms':round((time.perf_counter()-started)*1000,2)}
    except RuntimeError as exc:
        # This optional housekeeping must not replace a valid completed WAV.
        # Genuine inference/worker failures retain the existing fault path.
        return {'available':False,'error':type(exc).__name__}

'''
source=source.replace('def worker_main(cache_root,model_path):',helper+'def worker_main(cache_root,model_path):',1)
source=source.replace("            else:result=synth.synthesize(request['text'])\n", "            else:result=synth.synthesize(request['text'])\n            result=dict(result,cuda_idle_cache=release_idle_cuda_cache())\n",1)
assert source.count('cuda_idle_cache=release_idle_cuda_cache()')==1
path.write_text(source,encoding='utf-8')
path=H/'candidate_r9_source/tools/selected_voice_service.py';source=path.read_text(encoding='utf-8')
source=source.replace("        self.ready=False;self.error=''\n","        self.ready=False;self.error='';self.cuda_idle_cache={}\n",1)
source=source.replace("            self.ready=True;self.error=''\n            return result", "            self.ready=True;self.error=''\n            snapshot=result.get('cuda_idle_cache')\n            if isinstance(snapshot,dict):\n                allowed=('available','allocated_bytes','reserved_before_bytes','reserved_after_bytes','released_bytes','trim_ms','error')\n                self.cuda_idle_cache={k:v for k,v in snapshot.items() if k in allowed and type(v) in (bool,int,float,str)}\n            return result",1)
source=source.replace("return dict(status,ready=ready,cached_only=self.cached_only,error=self.error or status['error'])", "return dict(status,ready=ready,cached_only=self.cached_only,error=self.error or status['error'],\n                    cuda_idle_cache=dict(getattr(self,'cuda_idle_cache',{})))",1)
assert 'snapshot=result.get' in source and 'cuda_idle_cache=dict' in source
path.write_text(source,encoding='utf-8')
path=H/'candidate_r9_source/common/voice_service_capabilities.py';source=path.read_text(encoding='utf-8')
source=source.replace('voice-chat-context-20261029-r8','voice-chat-memory-20261029-r9')
source=source.replace("'precise_timeline_voice_intent':1}","'precise_timeline_voice_intent':1,'idle_tts_cuda_cache_release':1}")
assert 'idle_tts_cuda_cache_release' in source;path.write_text(source,encoding='utf-8')
module=types.ModuleType('candidate_capabilities');exec(compile(source,str(path),'exec'),module.__dict__)
digest=hashlib.sha256()
for name in module.SOURCE_FILES:
 path=H/'candidate_r9_source'/name
 if not path.exists():path=A/name
 digest.update(name.encode()+b'\0');digest.update(hashlib.sha256(path.read_bytes()).digest())
plan={'status':'TESTING','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'production_revision':previous['candidate_revision'],'production_fingerprint':previous['candidate_fingerprint'],
 'candidate_revision':module.SERVICE_REVISION,'candidate_fingerprint':digest.hexdigest(),
 'preserved_latency_sha256':previous['preserved_latency_sha256'],'tests_passed':None,
 'files':{name:{'before':hashlib.sha256((A/name).read_bytes()).hexdigest(),
               'candidate':hashlib.sha256((H/'candidate_r9_source'/name).read_bytes()).hexdigest()} for name in names},
 'scope':'Release only unused allocator blocks after completed TTS/warmup; preserve resident weight tensors, synthesis parameters and other models.',
 'board_migration':False,'listening_remains_off':True}
(H/'source_plan_r9.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
source=(H/'bootstrap_r8.py').read_text(encoding='utf-8').replace('candidate_r8_source','candidate_r9_source')
point='def service_module():'
injection='''# Load candidate TTS with its actual runtime __file__, without GPU/model loading.
tts_name='board.runtime.audio.omnivoice_voice'
importlib.import_module('board.runtime.audio')
tts=types.ModuleType(tts_name);tts.__file__=str(AURA/'board/runtime/audio/omnivoice_voice.py');tts.__package__='board.runtime.audio'
sys.modules[tts_name]=tts
exec(compile((HERE/'candidate_r9_source/board/runtime/audio/omnivoice_voice.py').read_text(encoding='utf-8'),tts.__file__,'exec'),tts.__dict__)

'''
source=source.replace(point,injection+point,1);(H/'bootstrap_r9.py').write_text(source,encoding='utf-8')
source=(H/'run_tests_r8.py').read_text(encoding='utf-8').replace('import bootstrap_r8 as bootstrap','import bootstrap_r9 as bootstrap').replace('tests_r8.xml','tests_r9.xml')
source=source.replace("'-q',str(H/'test_timeline_intent.py')","'-q',str(H/'test_tts_idle_cache.py'),str(H/'test_timeline_intent.py')")
(H/'run_tests_r9.py').write_text(source,encoding='utf-8')
for original,final in [('deploy_windows_r8.py','deploy_windows_r9.py'),('benchmark_voice_r8.py','benchmark_voice_r9.py'),
 ('live_handoff_r8.py','live_handoff_r9.py'),('verify_private_r8.py','verify_private_r9.py')]:
 source=(H/original).read_text(encoding='utf-8')
 for left,right in [('source_plan_r8.json','source_plan_r9.json'),('deployment_r8.json','deployment_r9.json'),
  ('candidate_r8_source','candidate_r9_source'),('before_r8','before_r9'),('==347','==355'),('live_handoff_r8_final','live_handoff_r9_final')]:source=source.replace(left,right)
 if final=='benchmark_voice_r9.py':source=source.replace('refined','trimmed')
 if final=='deploy_windows_r9.py':source=source.replace("('request_input_fingerprint','precise_timeline_voice_intent')","('request_input_fingerprint','precise_timeline_voice_intent','idle_tts_cuda_cache_release')")
 compile(source,str(H/final),'exec');(H/final).write_text(source,encoding='utf-8')
print(json.dumps({'status':'CANDIDATE_READY_FOR_TEST','revision':module.SERVICE_REVISION,'fingerprint':plan['candidate_fingerprint']}))
