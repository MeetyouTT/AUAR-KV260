"""Bounded local speech jobs; the GPU worker is separate from the UI server."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import threading
import time
import uuid
import wave

import numpy as np
from board.runtime.audio.selected_voice import SelectedVoiceSynthesizer,normalize_text,AURA,WORKSPACE
from tools.selected_voice_demo import activity_envelope
from tools.facial_layers import aperture_levels


class VoiceWorker:
    def __init__(self,root,python=None,model_path=None,engine='qwen'):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.cache=self.root/'cache'
        self.python=Path(python or WORKSPACE/'tmp/qwen-voice-audition-venv/Scripts/python.exe')
        self.engine=engine
        if engine=='omnivoice':
            from board.runtime.audio.omnivoice_voice import OmniVoiceSynthesizer
            self.synth=OmniVoiceSynthesizer(self.cache,model_path=model_path)
        elif engine=='qwen':self.synth=SelectedVoiceSynthesizer(self.cache,model_path=model_path)
        else:raise ValueError('Unknown voice engine')
        self.normalize_text=self.synth.normalize_text
        self.ready=False;self.error=''
        self.process=None;self.log=None;self.lock=threading.Lock()

    def generate(self,text):
        cached=self.synth.cached(text)
        if cached:return cached
        return self.request({'text':text})

    def warmup(self):
        try:self.request({'type':'warmup'});self.ready=True
        except Exception as exc:self.error=str(exc)

    def request(self,request):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                python=self.python
                if not python.is_file():raise RuntimeError('Voice Python runtime is unavailable')
                if self.log:self.log.close()
                self.log=(self.root/'worker.log').open('a',encoding='utf-8')
                script='omnivoice_voice.py' if self.engine=='omnivoice' else 'selected_voice.py'
                self.process=subprocess.Popen([str(python),'-B','-u',str(AURA/'board/runtime/audio'/script),
                       '--cache-root',str(self.cache),'--model-path',str(self.synth.model_path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,
                       text=True,encoding='utf-8',bufsize=1,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.process.stdin.write(json.dumps(request,ensure_ascii=False)+'\n');self.process.stdin.flush()
            for line in self.process.stdout:
                if not line.startswith('RESULT '):continue
                result=json.loads(line[7:])
                if not result.get('ok'):raise RuntimeError(result.get('error','Speech synthesis failed'))
                return result['result']
            raise RuntimeError('Speech worker stopped before returning a result')

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
        if self.log:self.log.close()


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

    def cancel(self,key):
        with self.lock:
            if key not in self.jobs:raise KeyError('Unknown speech job')
            self.jobs[key]['status']='CANCELLED'
        return self.get(key)

    def close(self):
        self.executor.shutdown(wait=False,cancel_futures=True);self.worker.close()
