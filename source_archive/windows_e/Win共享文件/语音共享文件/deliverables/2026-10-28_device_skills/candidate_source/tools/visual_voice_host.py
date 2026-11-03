"""One request token receives one board-owned frame for a spoken visual reply."""
import base64,secrets,threading,time
from common.asr_wire import context
from common.visual_question import validate_jpeg,MAX_JPEG
from tools.visual_question_host import LocalVisualQuestion

class VisualReplyStream:
    def __init__(self,meta,question,timeout=45,backend=None):
        self.meta=dict(meta);self.question=question;self.token=secrets.token_hex(24)
        self.until=time.monotonic()+min(45,timeout);self.cancelled=threading.Event()
        self.condition=threading.Condition();self.input=None;self.received=False
        self.backend=backend or LocalVisualQuestion();self.raw_reply=None;self.thinking_characters=0
        self.metrics={'backend':'local_visual_question','image_persisted':False}
    def accept(self,value):
        if not isinstance(value,dict) or set(value) not in ({'context','token','frame','jpeg_base64'},{'context','token','unavailable'}):raise ValueError('Invalid visual envelope')
        if context(value['context'])!=self.meta or value['token']!=self.token:raise ValueError('Foreign visual envelope')
        if 'unavailable' in value:
            if value['unavailable']!='fresh_frame_unavailable':raise ValueError('Invalid visual failure')
            item=None
        else:
            raw=value['jpeg_base64']
            if not isinstance(raw,str) or len(raw)>4*((MAX_JPEG+2)//3):raise ValueError('Image too large')
            jpeg=base64.b64decode(raw,validate=True);frame=value['frame'];validate_jpeg(frame,jpeg)
            if frame['board_boot_id']!=self.meta['board_boot_id']:raise ValueError('Foreign image boot')
            item=(dict(frame),jpeg)
        with self.condition:
            if self.received or self.cancelled.is_set() or time.monotonic()>=self.until:raise ValueError('Visual envelope expired/repeated')
            self.received=True;self.input=item;self.condition.notify_all()
    def cancel(self):
        with self.condition:self.cancelled.set();self.input=None;self.condition.notify_all()
    def __iter__(self):
        with self.condition:
            while not self.received and not self.cancelled.is_set():
                remaining=self.until-time.monotonic()
                if remaining<=0:raise TimeoutError('No fresh frame for visual question')
                self.condition.wait(min(.1,remaining))
            if self.cancelled.is_set():raise InterruptedError('Visual question cancelled')
            item=self.input;self.input=None
        if item is None:
            text='我现在没有拿到清晰、实时的画面，请稍后再让我看一下。'
        else:
            frame,jpeg=item;started=time.monotonic()
            value=self.backend.answer(self.question,frame,jpeg,deadline=self.until,cancelled=self.cancelled)
            self.metrics.update(visual_ms=round((time.monotonic()-started)*1000,2),
                frame_id=frame['frame_id'],image_sha256=frame['sha256'])
            text=value['reply_text']
        if self.cancelled.is_set() or time.monotonic()>=self.until:raise InterruptedError('Visual answer no longer current')
        yield 'text',text
        yield 'speech_ready',None
        yield 'complete',{'reply_text':text,'emotion':'neutral','avatar_action':''}

def open_exchange(models,meta,text,timeout):
    value=VisualReplyStream(meta,text,timeout)
    with models.meta_lock:
        rows=getattr(models,'visual_exchanges',None)
        if rows is None:rows={};models.visual_exchanges=rows
        for k,v in list(rows.items()):
            if time.monotonic()>=v.until or v.cancelled.is_set():rows.pop(k,None)
        while len(rows)>=8:rows.pop(next(iter(rows))).cancel()
        rows[meta['request_id']]=value
    return value

def accept_frame(models,value):
    meta=context(value['context']);key=(meta['board_boot_id'],meta['session_id'])
    with models.meta_lock:
        exchange=getattr(models,'visual_exchanges',{}).get(meta['request_id'])
        if exchange is None or models.latest_generations.get(key)!=meta['generation']:raise ValueError('Stale visual generation')
        exchange.accept(value)
    return {'accepted':True}

def handle_frame(handler):
    try:
        if handler.headers.get('Origin') or handler.headers.get('Transfer-Encoding'):raise ValueError('Invalid visual transport')
        if len(handler.headers.get_all('Content-Length',[]))!=1:raise ValueError('Expected one visual length')
        size=int(handler.headers['Content-Length'])
        if not 1<=size<=710000 or handler.headers.get('Content-Type')!='application/json':raise ValueError('Invalid visual body')
        import json
        handler.send(200,accept_frame(handler.server.models,json.loads(handler.rfile.read(size))))
    except (ValueError,TypeError,KeyError,UnicodeError):
        handler.send(400,{'error':'Invalid or stale visual frame'})

