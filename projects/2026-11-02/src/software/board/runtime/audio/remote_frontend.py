"""One synchronous bounded PCM transaction per capture-worker frame.

This detector never changes the PCM used by the existing endpoint/ASR.
The socket belongs to this instance and can be shut down during cancellation.
"""
import socket
import threading
import time
import uuid
import numpy as np
from common.frontend_wire import PROTOCOL,configuration,owner,send,receive


class RemoteSpeechGate:
    def __init__(self,config):
        self.config=configuration(config)
        self.stream_id=uuid.uuid4().hex
        self.connection=None;self.lock=threading.Lock()
        self.closed=False;self.error='';self.sequence=0;self.processed_samples=0
        self.last_ms=None;self.max_ms=0.

    def _open(self):
        timeout=self.config['timeout_ms']/1000
        connection=socket.create_connection((self.config['host'],self.config['port']),timeout=timeout)
        connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        with self.lock:
            if self.closed:connection.close();raise RuntimeError('Frontend capture cancelled')
            self.connection=connection
        send(connection,{'protocol':PROTOCOL,'kind':'open','stream_id':self.stream_id,'sequence':0})
        meta,pcm=receive(connection,timeout)
        owner(meta,'ready',self.stream_id,0)
        if pcm:raise ValueError('Unexpected frontend handshake audio')

    def __call__(self,frame):
        if self.closed or self.error:raise RuntimeError('Frontend capture closed or failed')
        values=np.asarray(frame,dtype=np.float32)
        if values.shape!=(320,) or not np.isfinite(values).all() or np.max(np.abs(values))>1:
            raise ValueError('Frontend requires 20 ms normalized 16 kHz mono audio')
        began=time.monotonic()
        try:
            if self.connection is None:self._open()
            self.sequence+=1
            connection=self.connection
            raw=np.rint(values*32768).clip(-32768,32767).astype('<i2').tobytes()
            send(connection,{'protocol':PROTOCOL,'kind':'frame','stream_id':self.stream_id,
                             'sequence':self.sequence},raw)
            meta,pcm=receive(connection,self.config['timeout_ms']/1000)
            owner(meta,'decision',self.stream_id,self.sequence)
            if (pcm or type(meta.get('speech')) is not bool or type(meta.get('input_samples')) is not int
                    or meta['input_samples']!=self.sequence*320
                    or type(meta.get('processed_samples')) is not int
                    or not self.processed_samples<=meta['processed_samples']<=meta['input_samples']
                    or meta['input_samples']-meta['processed_samples']>1024):
                raise ValueError('Invalid frontend sample timeline')
            with self.lock:
                if self.closed:raise RuntimeError('Frontend result belongs to cancelled capture')
                self.processed_samples=meta['processed_samples']
                self.last_ms=round((time.monotonic()-began)*1000,2)
                self.max_ms=max(self.max_ms,self.last_ms)
            return meta['speech']
        except Exception as exc:
            self.error=type(exc).__name__;self.close();raise

    def close(self):
        with self.lock:
            self.closed=True;connection=self.connection;self.connection=None
        if connection:
            try:connection.shutdown(socket.SHUT_RDWR)
            except OSError:pass
            connection.close()

    def public(self):
        with self.lock:
            return {'enabled':True,'backend':'gtcrn-silero-v5-pc-cpu','frames':self.sequence,
                    'processed_samples':self.processed_samples,'closed':self.closed,'error':self.error,
                    'last_roundtrip_ms':self.last_ms,'max_roundtrip_ms':self.max_ms}


def health(config):
    config=configuration(config);timeout=config['timeout_ms']/1000
    with socket.create_connection((config['host'],config['port']),timeout=timeout) as connection:
        send(connection,{'protocol':PROTOCOL,'kind':'health'})
        meta,pcm=receive(connection,timeout)
        if pcm or meta.get('protocol')!=PROTOCOL or meta.get('kind')!='health' or meta.get('ready') is not True:
            raise RuntimeError('Frontend not ready')
        return meta
