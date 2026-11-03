"""Persistent wired transport; delivers verified PCM immediately to a callback.

This module does not load ASR/LLM/TTS or replace the accepted board player.
Closing the active socket cancels delivery; a future turn opens a fresh one.
"""
import http.client
import json
import select
import socket
import threading
import time

from common.asr_wire import context, encode_context
from common.voice_channel import CONTENT_TYPE, ChannelState, read_frame


class VoiceChannel:
    def __init__(self, host, port=8792, *, feedback=False,identity_query=False):
        self.host, self.port = host, port
        self.feedback=bool(feedback)
        self.identity_query=bool(identity_query)
        self.connection = None
        self.socket = None
        self.cancelled = threading.Event()
        self.inflight = threading.Lock()

    def cancel(self):
        self.cancelled.set()
        connected = self.socket
        if connected:
            try: connected.shutdown(socket.SHUT_RDWR)
            except OSError: pass

    def close(self):
        self.cancel()
        if self.connection: self.connection.close()
        self.connection = self.socket = None

    def exchange(self, meta, pcm, on_frame, *, is_current=lambda: True,enrollment_state=None):
        """Callback cost/backpressure counts toward the same total turn budget."""
        context(meta, pcm)
        if not self.inflight.acquire(blocking=False): raise RuntimeError('Channel already in use')
        self.cancelled.clear()
        deadline = time.monotonic() + meta['budget_ms']/1000
        timer = threading.Timer(meta['budget_ms']/1000, self.cancel)
        timer.daemon = True
        state = ChannelState(meta)
        try:
            if not is_current(): raise InterruptedError('Stale turn before sending')
            if self.connection is None:
                self.connection = http.client.HTTPConnection(self.host, self.port, timeout=meta['budget_ms']/1000)
            connected=self.connection.sock
            if connected is not None and select.select([connected],[],[],0)[0]:
                if not connected.recv(1,socket.MSG_PEEK):self.connection.close()
            if self.connection.sock is None:
                self.connection.connect()
            self.socket = self.connection.sock
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Channel connection budget expired')
            self.socket.settimeout(remaining)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            timer.interval=remaining
            timer.start()
            headers={'Content-Type':'application/octet-stream','X-Aura-Asr':encode_context(meta)}
            if self.feedback:headers['X-Aura-Features']='thinking-feedback-v1'
            if enrollment_state is not None:
                headers['X-Aura-Identity']='enrollment-active-v1' if enrollment_state else 'enrollment-v1'
                if self.identity_query:headers['X-Aura-Identity-Query']='current-face-v1'
            self.connection.request('POST', '/v1/voice/channel', pcm, headers)
            response = self.connection.getresponse()
            if response.status != 200 or response.getheader('Content-Type') != CONTENT_TYPE:
                raise RuntimeError('Voice channel HTTP ' + str(response.status))
            if response.getheader('Transfer-Encoding') != 'chunked':
                raise ValueError('Voice channel is not streamed')
            while not state.ended:
                header, payload = read_frame(response)
                if self.cancelled.is_set() or not is_current(): raise InterruptedError('Voice channel cancelled')
                if time.monotonic() >= deadline: raise TimeoutError('Voice channel expired')
                state.accept(header, payload)
                if header['kind'] == 'error': raise RuntimeError(header['error'])
                on_frame(header, payload)
            if response.read(1): raise ValueError('Data after channel completion')
            if self.cancelled.is_set() or not is_current(): raise InterruptedError('Turn expired after reception')
            return {'sample_count': state.samples, 'pcm_sha256': state.digest.hexdigest(),
                    'reply_text': state.text, 'network_complete': True, 'playback_verified': False}
        except Exception:
            self.close()
            raise
        finally:
            timer.cancel()
            self.inflight.release()

    def identity_result(self,meta,token,reply,*,sequence=None,final=True):
        from common.voice_enrollment import render
        render(reply)
        connection=http.client.HTTPConnection(self.host,self.port,timeout=3)
        try:
            body={'context':meta,'token':token,'reply':reply}
            if sequence is not None:body.update(sequence=sequence,final=final)
            connection.request('POST','/v1/voice/identity/result',json.dumps(body).encode(),{'Content-Type':'application/json'})
            response=connection.getresponse();raw=response.read(4097)
            if response.status!=200 or len(raw)>4096 or not json.loads(raw).get('accepted'):
                raise RuntimeError('Identity voice result rejected')
        finally:connection.close()
