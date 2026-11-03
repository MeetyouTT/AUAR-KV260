"""Relay the current transcript to the board; the LLM cannot enroll anybody."""
import secrets
import threading
import time
from collections import deque
from common.voice_enrollment import render

class IdentityReplyStream:
    def __init__(self,meta,timeout=15):
        self.meta=dict(meta);self.token=secrets.token_hex(24);self.until=time.monotonic()+timeout
        self.event=threading.Event();self.cancelled=threading.Event();self.result=None
        self.raw_reply=None;self.metrics={'backend':'board_identity_workflow'};self.thinking_characters=0
        self.condition=threading.Condition();self.pending=deque();self.sequence=0;self.final=False

    def accept(self,meta,token,value,*,sequence=0,final=True):
        render(value)
        with self.condition:
            if (meta!=self.meta or token!=self.token or time.monotonic()>=self.until or self.cancelled.is_set()
                    or self.final or type(sequence) is not int or sequence!=self.sequence or type(final) is not bool):
                raise ValueError('Stale identity voice response')
            if not final and value['code'] not in ('sample_front','sample_left','sample_right','sample_validate'):
                raise ValueError('Invalid sampling progress reply')
            if self.sequence>=6:raise ValueError('Too many sampling prompts')
            self.pending.append((dict(value),final));self.sequence+=1;self.final=final
            self.result=dict(value);self.event.set();self.condition.notify_all()

    def cancel(self):
        with self.condition:self.cancelled.set();self.event.set();self.condition.notify_all()

    def __iter__(self):
        text=''
        while True:
            with self.condition:
                while not self.pending and not self.cancelled.is_set():
                    if time.monotonic()>=self.until:raise TimeoutError('Board identity workflow did not respond')
                    self.condition.wait(.05)
                if self.cancelled.is_set():raise InterruptedError('Identity voice exchange cancelled')
                value,final=self.pending.popleft()
            part=render(value);text+=part;self.metrics['identity_reply_code']=value['code']
            yield 'text',part
            yield 'speech_ready',None
            if final:
                yield 'complete',{'reply_text':text,'emotion':'friendly','avatar_action':''};return
