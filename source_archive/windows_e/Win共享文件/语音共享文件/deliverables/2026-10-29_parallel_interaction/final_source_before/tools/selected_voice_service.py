"""Bounded local speech jobs; the GPU worker is separate from the UI server."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid
import wave

from board.runtime.audio.selected_voice import SelectedVoiceSynthesizer,normalize_text,AURA,WORKSPACE
from tools.voice_worker_transport import BoundedSpeechProcess


class VoiceWorker:
    def __init__(self,root,python=None,model_path=None,engine='qwen',*,cached_only=False,gpu_coordinator=None):
        if not isinstance(cached_only,bool):raise ValueError('cached_only must be a boolean')
        self.cached_only=cached_only
        self.gpu_coordinator=gpu_coordinator
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.cache=self.root/'cache'
        self.python=Path(python or WORKSPACE/'tmp/qwen-voice-audition-venv/Scripts/python.exe')
        self.engine=engine
        if engine=='omnivoice':
            from board.runtime.audio.omnivoice_voice import OmniVoiceSynthesizer
            self.synth=OmniVoiceSynthesizer(self.cache,model_path=model_path)
        elif engine=='qwen':self.synth=SelectedVoiceSynthesizer(self.cache,model_path=model_path)
        else:raise ValueError('Unknown voice engine')
        self.normalize_text=getattr(self.synth,'normalize_text',normalize_text)
        self.ready=False;self.error='';self.cuda_idle_cache={}
        self.transport=BoundedSpeechProcess(self._worker_command,self.root/'worker.log')
        self.lock=self.transport.lock

    @property
    def process(self):return self.transport.process

    def _worker_command(self):
        if not self.python.is_file():raise RuntimeError('Voice Python runtime is unavailable')
        script='omnivoice_voice.py' if self.engine=='omnivoice' else 'selected_voice.py'
        return [str(self.python),'-B','-u',str(AURA/'board/runtime/audio'/script),
                '--cache-root',str(self.cache),'--model-path',str(self.synth.model_path)]

    def generate(self,text):
        cached=self.synth.cached(text)
        if cached:
            if getattr(self,'gpu_coordinator',None) is not None:self.gpu_coordinator.note_tts(cached)
            return cached
        if self.cached_only:raise RuntimeError('当前为仅缓存播放模式，缺少有效音频缓存')
        return self.request({'text':text})

    def generate_bounded(self,text,*,deadline,cancelled,request_id):
        if cancelled.is_set():raise InterruptedError('Speech request cancelled')
        if time.monotonic()>=deadline:raise TimeoutError('Speech worker deadline expired')
        cached=self.synth.cached(text)
        if cancelled.is_set():raise InterruptedError('Speech request cancelled')
        if time.monotonic()>=deadline:raise TimeoutError('Speech worker deadline expired')
        if cached:
            if getattr(self,'gpu_coordinator',None) is not None:self.gpu_coordinator.note_tts(cached)
            return cached
        if self.cached_only:raise RuntimeError('当前为仅缓存播放模式，缺少有效音频缓存')
        return self.request({'text':text},deadline=deadline,cancelled=cancelled,request_id=request_id)

    def warmup(self,timeout=240.):
        if self.cached_only:
            self.ready=True
            return
        try:self.request({'type':'warmup'},timeout=timeout);self.ready=True
        except Exception as exc:self.ready=False;self.error=str(exc)

    def request(self,request,**options):
        if self.cached_only:raise RuntimeError('当前为仅缓存播放模式，禁止启动语音合成进程')
        lease=None
        if getattr(self,'gpu_coordinator',None) is not None:
            # Compute once before admission, so waiting never extends the
            # original transport deadline or the r6 warm-TTS handoff budget.
            deadline=options.get('deadline')
            if deadline is None:deadline=time.monotonic()+options.get('timeout',120.)
            options=dict(options,deadline=deadline)
            lease=self.gpu_coordinator.acquire('tts',deadline=deadline,cancelled=options.get('cancelled'))
        try:
            result=self.transport.request(request,**options)
            if getattr(self,'gpu_coordinator',None) is not None:self.gpu_coordinator.note_tts(result,warmup=request.get('type')=='warmup')
            self.ready=True;self.error=''
            snapshot=result.get('cuda_idle_cache')
            if isinstance(snapshot,dict):
                allowed=('available','allocated_bytes','reserved_before_bytes','reserved_after_bytes','released_bytes','trim_ms','error')
                self.cuda_idle_cache={k:v for k,v in snapshot.items() if k in allowed and type(v) in (bool,int,float,str)}
            return result
        except Exception as exc:
            self.ready=False;self.error=type(exc).__name__+': '+str(exc)[:300]
            raise
        finally:
            if lease is not None:lease.release()

    def cancel_request(self,request_id):
        cancelled=self.transport.cancel_request(request_id)
        if cancelled:self.ready=False;self.error='Speech request cancelled'
        return cancelled

    def health(self):
        status=self.transport.health()
        ready=bool(self.ready and (self.cached_only or status['alive']) and not status['quarantined'] and not status['closed'])
        result=dict(status,ready=ready,cached_only=self.cached_only,error=self.error or status['error'],
                    cuda_idle_cache=dict(getattr(self,'cuda_idle_cache',{})))
        if getattr(self,'gpu_coordinator',None) is not None:result['gpu_resources']=self.gpu_coordinator.public()
        return result

    def close(self):
        self.ready=False
        self.transport.close()


class SpeechJobs:
    def __init__(self,root,worker=None):
        self.root=Path(root);self.worker=worker or VoiceWorker(root)
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='aura-speech')
        self.normalize_text=getattr(self.worker,'normalize_text',normalize_text)
        self.jobs={};self.lock=threading.Lock()

    def submit(self,text,emotion='neutral'):
        text=self.normalize_text(text)
        if emotion not in {'neutral','happy','sad'}:raise ValueError('Unknown emotion')
        with self.lock:
            pending=sum(job['status'] in {'QUEUED','GENERATING'} for job in self.jobs.values())
            if pending>=4:raise ValueError('Speech queue is full; wait for the current request')
            job={'id':uuid.uuid4().hex,'status':'QUEUED','text':text,'emotion':emotion,'created_at':time.time()}
            self.jobs[job['id']]=job
            # Bound retained metadata while keeping all active jobs.
            for key in list(self.jobs):
                if len(self.jobs)<=100:break
                if self.jobs[key]['status'] in {'COMPLETE','FAILED','CANCELLED'}:del self.jobs[key]
        self.executor.submit(self._run,job['id']);return self.get(job['id'])

    def _run(self,key):
        with self.lock:
            job=self.jobs.get(key)
            if job is None:return
            if job['status']=='CANCELLED':return
            job['status']='GENERATING'
        try:
            result=self.worker.generate(job['text'])
            import numpy as np
            from tools.selected_voice_demo import activity_envelope
            from tools.facial_layers import aperture_levels
            with wave.open(result['path'],'rb') as audio:
                if (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())!=(24000,1,2):raise ValueError('Wrong generated WAV format')
                pcm=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2')
            envelope=activity_envelope(pcm);envelope['levels']=aperture_levels(pcm)
            public={'key':result['key'],'audio':f"cache/{result['key']}.wav",'duration_seconds':result['duration_seconds'],
                    'cache_hit':result['cache_hit'],'generation_seconds':result['generation_seconds'],
                    'sha256':result['sha256'],'envelope':envelope,'voice':'柔亮俏皮'}
            with self.lock:
                if job['status']!='CANCELLED':job.update(status='COMPLETE',result=public,finished_at=time.time())
        except Exception as exc:
            with self.lock:
                if job['status']!='CANCELLED':job.update(status='FAILED',error=str(exc))

    def get(self,key):
        with self.lock:
            if key not in self.jobs:raise KeyError('Unknown speech job')
            return dict(self.jobs[key])

    def import_generated(self,value):
        from common.voice_wire import wav_payload
        import numpy as np
        from tools.selected_voice_demo import activity_envelope
        from tools.facial_layers import aperture_levels
        path=Path(value['path']).resolve()
        if path.parent!=(self.root/'cache').resolve() or path.name!=value['sha256']+'.wav':
            raise ValueError('Remote voice must be in the local content-hash cache')
        raw=path.read_bytes();value=wav_payload(value,raw)
        with wave.open(str(path),'rb') as audio:
            pcm=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2')
        envelope=activity_envelope(pcm);envelope['levels']=aperture_levels(pcm)
        result={'key':value['sha256'],'audio':'cache/'+value['sha256']+'.wav',
                'duration_seconds':value['duration_seconds'],'cache_hit':False,'generation_seconds':value.get('tts_ms',0)/1000,
                'sha256':value['sha256'],'envelope':envelope,'voice':'柔亮俏皮','source_engine':'omnivoice'}
        job={'id':uuid.uuid4().hex,'status':'COMPLETE','text':value['reply_text'],'emotion':value['emotion'],
             'created_at':time.time(),'finished_at':time.time(),'result':result}
        with self.lock:
            for key in list(self.jobs):
                if len(self.jobs)<100:break
                if self.jobs[key]['status'] not in {'QUEUED','GENERATING'}:del self.jobs[key]
            self.jobs[job['id']]=job
        return dict(job)

    def cancel(self,key):
        with self.lock:
            if key not in self.jobs:raise KeyError('Unknown speech job')
            self.jobs[key]['status']='CANCELLED'
        return self.get(key)

    def close(self):
        if sys.version_info >= (3,9):self.executor.shutdown(wait=False,cancel_futures=True)
        else:self.executor.shutdown(wait=False)
        self.worker.close()
