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
    def __init__(self, host, port=8792, *, feedback=False,identity_query=False,visual_question=False):
        self.host, self.port = host, port
        self.feedback=bool(feedback)
        self.identity_query=bool(identity_query)
        self.visual_question=bool(visual_question)
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

    def exchange(self, meta, pcm, on_frame, *, is_current=lambda: True,enrollment_state=None,conversation=None,visual_entry=False,profile_token=None,wake_entry=False,speaker_visual=None):
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
            headers={'Content-Type':'application/octet-stream','X-Aura-Asr':encode_context(meta),
                     'X-Aura-Motion':'speech-v1'}
            if conversation is not None:
                from common.conversation_store import conversation_id
                headers['X-Aura-Conversation']='v1:'+conversation_id(conversation)
            if speaker_visual is not None:
                if conversation is None:raise ValueError('Speaker observations require a durable conversation')
                from common.speaker_visual import encode_visual_header
                headers['X-Aura-Speaker-Visual']=encode_visual_header(speaker_visual,meta)
            if profile_token is not None:
                import re
                if conversation is None or enrollment_state is not None or not re.fullmatch('[0-9a-f]{64}',profile_token):
                    raise ValueError('Profile token requires a durable ordinary conversation')
                headers['X-Aura-Profile']='v1:'+profile_token
            if visual_entry and wake_entry:raise ValueError('Conflicting entry modes')
            entry_mode='wake-word-v1' if wake_entry else 'visual-speech-v1' if visual_entry else None
            if entry_mode:headers['X-Aura-Entry']=entry_mode
            if self.visual_question:headers['X-Aura-Visual']='frame-question-v1'
            if self.feedback:headers['X-Aura-Features']='thinking-feedback-v1'
            if enrollment_state is not None:
                headers['X-Aura-Identity']='enrollment-active-v1' if enrollment_state else 'enrollment-v1'
                if self.identity_query:headers['X-Aura-Identity-Query']='current-face-v1'
            self.connection.request('POST', '/v1/voice/channel', pcm, headers)
            response = self.connection.getresponse()
            if entry_mode and response.status==422:
                from common.handsfree_entry import EntryRejected
                raw=response.read(4097)
                if len(raw)<=4096 and json.loads(raw).get('code')=='entry_rejected':raise EntryRejected('No valid initial speech')
            if wake_entry and response.status==204:
                if response.getheader('X-Aura-Entry')!='wake-word-v1':
                    raise RuntimeError('Wake response lacks negotiation')
                response.read()
                if self.cancelled.is_set() or not is_current() or time.monotonic()>=deadline:
                    raise InterruptedError('Wake response expired')
                return {'wake_only':True}
            if response.status != 200 or response.getheader('Content-Type') != CONTENT_TYPE:
                raise RuntimeError('Voice channel HTTP ' + str(response.status))
            if self.visual_question and response.getheader('X-Aura-Visual')!='frame-question-v1':
                raise RuntimeError('Voice host does not support visual questions')
            if conversation is not None and response.getheader('X-Aura-Conversation')!='v1':
                raise RuntimeError('Voice host does not support durable conversations')
            if entry_mode and response.getheader('X-Aura-Entry')!=entry_mode:
                raise RuntimeError('Voice host does not support visual speech entry')
            if response.getheader('Transfer-Encoding') != 'chunked':
                raise ValueError('Voice channel is not streamed')
            while not state.ended:
                if self.cancelled.is_set() or not is_current():raise InterruptedError('Voice channel cancelled')
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
            cancelled=self.cancelled.is_set() or not is_current()
            self.close()
            if cancelled:raise InterruptedError('Voice channel cancelled') from None
            raise
        finally:
            timer.cancel()
            self.inflight.release()

    def visual_frame(self,meta,token,*,is_current=lambda:True):
        import base64
        from board.runtime.visual_capture import current_frame
        if self.cancelled.is_set() or not is_current():raise InterruptedError('Visual capture cancelled')
        body={'context':meta,'token':token}
        try:
            frame,jpeg=current_frame(meta['board_boot_id'],is_current=lambda:not self.cancelled.is_set() and is_current())
            body.update(frame=frame,jpeg_base64=base64.b64encode(jpeg).decode())
        except (OSError,ValueError,KeyError,TypeError):body['unavailable']='fresh_frame_unavailable'
        if self.cancelled.is_set() or not is_current():raise InterruptedError('Visual upload cancelled')
        connection=http.client.HTTPConnection(self.host,self.port,timeout=3)
        try:
            connection.request('POST','/v1/voice/visual/frame',json.dumps(body).encode(),{'Content-Type':'application/json'})
            response=connection.getresponse();raw=response.read(4097)
            if response.status!=200 or len(raw)>4096 or not json.loads(raw).get('accepted'):raise RuntimeError('Visual frame rejected')
        finally:connection.close()

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
