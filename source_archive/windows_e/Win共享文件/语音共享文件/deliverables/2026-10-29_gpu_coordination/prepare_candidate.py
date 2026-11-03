"""Copy the current sources into an isolated integration candidate, then patch."""
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';base=H/'candidate'
names=('tools/voice_channel_source.py','tools/selected_voice_service.py','board/runtime/audio/omnivoice_voice.py')
manifest={}
for name in names:
    raw=(A/name).read_bytes();manifest[name]=hashlib.sha256(raw).hexdigest()
    path=base/name;path.parent.mkdir(parents=True,exist_ok=True);assert not path.exists();path.write_bytes(raw)
def patch(name,old,new):
    path=base/name;text=path.read_text(encoding='utf-8');assert text.count(old)==1,(name,old[:100],text.count(old))
    path.write_text(text.replace(old,new),encoding='utf-8',newline='\n')

name='tools/selected_voice_service.py'
patch(name,"*,cached_only=False):","*,cached_only=False,gpu_coordinator=None):")
patch(name,"        self.cached_only=cached_only\n","        self.cached_only=cached_only\n        self.gpu_coordinator=gpu_coordinator\n")
path=base/name;text=path.read_text(encoding='utf-8');assert text.count('        if cached:return cached')==2
text=text.replace('        if cached:return cached',"""        if cached:
            if getattr(self,'gpu_coordinator',None) is not None:self.gpu_coordinator.note_tts(cached)
            return cached""")
path.write_text(text,encoding='utf-8',newline='\n')
patch(name,"        try:\n            result=self.transport.request(request,**options)","""        lease=None
        if getattr(self,'gpu_coordinator',None) is not None:
            # Compute once before admission, so waiting never extends the
            # original transport deadline or the r6 warm-TTS handoff budget.
            deadline=options.get('deadline')
            if deadline is None:deadline=time.monotonic()+options.get('timeout',120.)
            options=dict(options,deadline=deadline)
            lease=self.gpu_coordinator.acquire('tts',deadline=deadline,cancelled=options.get('cancelled'))
        try:
            result=self.transport.request(request,**options)
            if getattr(self,'gpu_coordinator',None) is not None:self.gpu_coordinator.note_tts(result,warmup=request.get('type')=='warmup')""")
patch(name,"            raise\n\n    def cancel_request", "            raise\n        finally:\n            if lease is not None:lease.release()\n\n    def cancel_request")
patch(name,"        return dict(status,ready=ready,cached_only=self.cached_only,error=self.error or status['error'],\n                    cuda_idle_cache=dict(getattr(self,'cuda_idle_cache',{})))", """        result=dict(status,ready=ready,cached_only=self.cached_only,error=self.error or status['error'],
                    cuda_idle_cache=dict(getattr(self,'cuda_idle_cache',{})))
        if getattr(self,'gpu_coordinator',None) is not None:result['gpu_resources']=self.gpu_coordinator.public()
        return result""")

name='board/runtime/audio/omnivoice_voice.py'
patch(name,"            request_id=request.get('request_id')\n", """            request_id=request.get('request_id')
            import torch
            from tools.cuda_memory_stats import begin as begin_memory,finish as finish_memory
            before_memory=begin_memory(torch)
""")
patch(name,"            result=dict(result,cuda_idle_cache=release_idle_cuda_cache())", """            result=dict(result,cuda_inference=finish_memory(torch,before_memory,
                cache_hit=bool(result.get('cache_hit')),warmup=request.get('type')=='warmup'))
            result=dict(result,cuda_idle_cache=release_idle_cuda_cache())""")

name='tools/voice_channel_source.py'
patch(name,"    stopped = threading.Event()\n", """    stopped = threading.Event()
    coordinator=getattr(models,'gpu_coordinator',None)
    from common.gpu_coordination import DeferredLlmEvents
    deferred=DeferredLlmEvents() if coordinator is not None else None
    gpu_timing={}
""")
patch(name,"    def read_llm():\n        try:\n            for kind, value in stream:", """    def read_llm():
        lease=None
        try:
            if coordinator is not None and board_exchange is None and memory_reply is None:
                lease=coordinator.acquire('llm',deadline=deadline,cancelled=stopped)
                gpu_timing['llm_admission_wait_ms']=round(lease.wait_ms,2)
            for kind, value in stream:""")
patch(name,"        finally:\n            put(('eof', None))", """        finally:
            # Release before EOF delivery; the small producer queue may be
            # full while the main thread waits for TTS admission.
            if lease is not None:lease.release()
            put(('eof', None))""")
patch(name,"        while True:\n            # OmniVoice cannot abort", """        while True:
            # Do not deadlock low-headroom fallback: let the LLM producer
            # finish/release while TTS waits, preserving every event in order.
            if deferred is not None:deferred.drain(pending)
            # OmniVoice cannot abort""")
patch(name,"                generated=future.result(timeout=.1)","                generated=future.result(timeout=.01 if deferred is not None else .1)")
patch(name,"                kind, value = pending.get(timeout=.1)","                kind, value = deferred.get(pending,.1) if deferred is not None else pending.get(timeout=.1)")
patch(name,"                yield owner.frame('end', reply_text=owner.state.text", """                if coordinator is not None:
                    timing['gpu_coordination']=dict(gpu_timing,deferred_event_high_water_bytes=deferred.high_water,
                        mode=coordinator.policy.mode)
                yield owner.frame('end', reply_text=owner.state.text""")
for name in names:compile((base/name).read_text(encoding='utf-8'),name,'exec')
(H/'baseline_sources.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'status':'CANDIDATE_ONLY','sources':list(names),'live_sources_changed':False}))
