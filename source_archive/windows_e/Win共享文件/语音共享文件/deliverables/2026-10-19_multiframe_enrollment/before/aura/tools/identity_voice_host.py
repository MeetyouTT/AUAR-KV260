"""Relay the current transcript to the board; the LLM cannot enroll anybody."""
import secrets
import threading
import time
from common.voice_enrollment import render

class IdentityReplyStream:
    def __init__(self,meta,timeout=15):
        self.meta=dict(meta);self.token=secrets.token_hex(24);self.until=time.monotonic()+timeout
        self.event=threading.Event();self.cancelled=threading.Event();self.result=None
        self.raw_reply=None;self.metrics={'backend':'board_identity_workflow'};self.thinking_characters=0

    def accept(self,meta,token,value):
        render(value)
        if meta!=self.meta or token!=self.token or time.monotonic()>=self.until or self.cancelled.is_set() or self.event.is_set():
            raise ValueError('Stale identity voice response')
        self.result=dict(value);self.event.set()

    def cancel(self):self.cancelled.set();self.event.set()

    def __iter__(self):
        while not self.event.wait(.05):
            if time.monotonic()>=self.until:raise TimeoutError('Board identity workflow did not respond')
        if self.cancelled.is_set() or self.result is None:raise InterruptedError('Identity voice exchange cancelled')
        text=render(self.result)
        self.metrics['identity_reply_code']=self.result['code']
        yield 'text',text
        yield 'speech_ready',None
        yield 'complete',{'reply_text':text,'emotion':'friendly','avatar_action':''}
