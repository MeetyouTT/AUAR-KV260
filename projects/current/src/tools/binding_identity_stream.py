"""IdentityReplyStream-compatible transform with optional committed receipts."""
from collections import deque
import secrets,threading,time
from common.voice_enrollment import render

class BindingIdentityReplyStream:
    def __init__(self,meta,transform,timeout=110):
        self.meta=dict(meta);self.transform=transform;self.token=secrets.token_hex(24);self.until=time.monotonic()+min(110,timeout)
        self.cancelled=threading.Event();self.condition=threading.Condition();self.pending=deque();self.sequence=0;self.final=False
        self.raw_reply=None;self.metrics={'backend':'unified_board_face_then_voice'};self.thinking_characters=0
    def accept(self,meta,token,value,*,sequence=0,final=True,binding_receipt=None):
        render(value)
        if binding_receipt is not None and (not final or value['code'] not in ('registered','already_known')):raise ValueError('Receipt allowed only with final face result')
        with self.condition:
            if (meta!=self.meta or token!=self.token or time.monotonic()>=self.until or self.cancelled.is_set()
                or self.final or type(sequence) is not int or sequence!=self.sequence or type(final) is not bool):
                raise ValueError('Stale unified identity voice result')
            if not final and value['code'] not in ('sample_front','sample_left','sample_right','sample_validate','sample_auto'):
                raise ValueError('Invalid original sampling progress')
            if self.sequence>=6:raise ValueError('Too many face sampling prompts')
            self.pending.append((dict(value),final,binding_receipt));self.sequence+=1;self.final=final;self.condition.notify_all()
    def cancel(self):
        # Ending a normal streamed prompt is not canceling the multi-turn
        # enrollment. Explicit cancel commands go through UnifiedBindingRouter.
        with self.condition:self.cancelled.set();self.condition.notify_all()
    def __iter__(self):
        text=''
        while True:
            with self.condition:
                while not self.pending and not self.cancelled.is_set():
                    if time.monotonic()>=self.until:raise TimeoutError('Unified identity exchange expired')
                    self.condition.wait(.05)
                if self.cancelled.is_set():raise InterruptedError('Unified identity exchange cancelled')
                value,final,receipt=self.pending.popleft()
            part=self.transform(value,receipt)
            if not isinstance(part,str) or not part or len(part)>240 or len(text)+len(part)>240:raise ValueError('Invalid bounded binding speech')
            text+=part;self.metrics['identity_reply_code']=value['code']
            yield 'text',part;yield 'speech_ready',None
            if final:
                yield 'complete',{'reply_text':text,'emotion':'friendly','avatar_action':''};return
