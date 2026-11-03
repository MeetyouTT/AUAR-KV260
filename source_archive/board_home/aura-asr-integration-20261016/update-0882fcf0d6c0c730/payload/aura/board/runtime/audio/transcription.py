"""One asynchronous ASR request, one latest waiting recording, bounded results."""
from collections import deque
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import socket
import threading
import time
import uuid

from common.asr_wire import PROTOCOL, MAX_REPLY, encode_context, response

DEFAULTS={'enabled':False,'host':'127.0.0.1','port':8791,'timeout_ms':30000}


def configuration(value):
    if not isinstance(value,dict) or set(value)!=set(DEFAULTS):raise ValueError('Invalid transcription configuration')
    if type(value['enabled']) is not bool:raise ValueError('Invalid ASR enabled flag')
    if not isinstance(value['host'],str):raise ValueError('ASR host must be an IPv4 address')
    ipaddress.IPv4Address(value['host'])
    if type(value['port']) is not int or not 1024<=value['port']<=65535:raise ValueError('Invalid ASR port')
    if type(value['timeout_ms']) is not int or not 500<=value['timeout_ms']<=120000:raise ValueError('Invalid ASR timeout')
    return dict(value)


class TranscriptionStore:
    def __init__(self,path):
        self.path=Path(path)

    def read(self):
        return configuration(json.loads(self.path.read_text())) if self.path.exists() else dict(DEFAULTS)

    def update(self,values):
        values=configuration(dict(self.read(),**values))
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_name(self.path.name+'.tmp-'+uuid.uuid4().hex)
        with os.fdopen(os.open(str(temporary),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as out:
            json.dump(values,out,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
        os.replace(str(temporary),str(self.path))
        return values


def recognize(config, meta, pcm, timeout):
    # Direct HTTP has no environment proxy, redirect handling or clock sharing.
    deadline=time.monotonic()+timeout
    connection=http.client.HTTPConnection(config['host'],config['port'],timeout=timeout)
    timer=None
    try:
        connection.connect()
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('ASR connection budget expired')
        connected_socket=connection.sock
        def expire():
            try:connected_socket.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        # A total deadline also interrupts peers that drip bytes below the
        # socket's per-operation timeout.
        timer=threading.Timer(remaining,expire)
        timer.daemon=True
        timer.start()
        connection.request('POST','/v1/asr/transcribe',body=pcm,
            headers={'Content-Type':'application/octet-stream','X-Aura-Asr':encode_context(meta)})
        reply=connection.getresponse()
        raw=reply.read(MAX_REPLY+1)
        if time.monotonic()>=deadline:raise TimeoutError('ASR response budget expired')
        if len(raw)>MAX_REPLY:raise ValueError('ASR response exceeds limit')
        if reply.status!=200:
            try:detail=json.loads(raw).get('error','')
            except (ValueError,UnicodeError):detail=''
            raise RuntimeError('ASR HTTP '+str(reply.status)+': '+str(detail)[:240])
        return response(json.loads(raw),meta)
    finally:
        if timer:timer.cancel()
        connection.close()


class TranscriptionJobs:
    def __init__(self,config,boot_id,*,transport=recognize,clock=time.monotonic):
        self.config=configuration(config)
        self.boot_id,self.session_id=boot_id,uuid.uuid4().hex
        self.transport,self.clock=transport,clock
        self.condition=threading.Condition()
        self.generation=0
        self.waiting=self.active=None
        self.results=deque(maxlen=2)
        self.closed=False
        self.thread=threading.Thread(target=self.work,name='aura-transcription',daemon=True)
        self.thread.start()

    def enabled(self):
        with self.condition:return self.config['enabled'] and not self.closed

    def configure(self,values):
        values=configuration(values)
        with self.condition:
            if self.closed:raise ValueError('Transcription is closed')
            self.config=values
            self._invalidate()

    def _invalidate(self):
        self.generation+=1
        self.waiting=None
        self.results.clear()
        self.condition.notify_all()

    def cancel(self):
        with self.condition:self._invalidate()

    def submit(self,clip):
        with self.condition:
            if self.closed:raise ValueError('Transcription is closed')
            if not self.config['enabled']:raise ValueError('Transcription service is not configured')
            self._invalidate()
            config=dict(self.config)
            meta={'protocol':PROTOCOL,'board_boot_id':self.boot_id,'session_id':self.session_id,
                  'request_id':uuid.uuid4().hex,'generation':self.generation,'capture_id':clip.capture_id,
                  'sample_count':clip.audio.sample_count,'pcm_sha256':hashlib.sha256(clip.pcm).hexdigest(),
                  'budget_ms':config['timeout_ms']}
            # Validate before taking ownership of a pending request.
            from common.asr_wire import context
            context(meta,clip.pcm)
            self.waiting=(meta,clip.pcm,config,self.clock()+config['timeout_ms']/1000)
            self.condition.notify()
            return dict(meta)

    def poll(self):
        with self.condition:
            if not self.results:return None
            return self.results.popleft()

    def public(self):
        with self.condition:
            return {'enabled':self.config['enabled'],'pending':bool(self.waiting or self.active),
                    'host':self.config['host'],'port':self.config['port']}

    def work(self):
        while True:
            with self.condition:
                while not self.closed and self.waiting is None:self.condition.wait()
                if self.closed:return
                job,self.waiting=self.waiting,None
                self.active=job[0]['request_id']
            meta,pcm,config,deadline=job
            result={'context':meta,'text':'','error':''}
            try:
                remaining=deadline-self.clock()
                if remaining<=0:raise TimeoutError('Transcription request expired before sending')
                result.update(response(self.transport(config,meta,pcm,remaining),meta))
                if self.clock()>=deadline:raise TimeoutError('Transcription response expired')
            except Exception as exc:
                result.update(text='',error=type(exc).__name__+': '+str(exc))
            with self.condition:
                self.active=None
                if not self.closed and meta['generation']==self.generation:self.results.append(result)

    def close(self):
        with self.condition:
            self.closed=True
            self._invalidate()
        # The daemon keeps an in-flight network request until its socket timeout;
        # cancellation prevents delivery and never blocks the audio owner.
        self.thread.join(timeout=.1)
