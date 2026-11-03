"""One low-rate observer of the existing camera owner, never a second capture."""
import base64,http.client,json,threading,time
from board.runtime.visual_capture import current_frame

class DeviceObserver:
    def __init__(self,boot,*,interval=15.,host='192.168.50.1'):
        if not 10<=interval<=300:raise ValueError('Bound observation cadence')
        self.boot=boot;self.interval=interval;self.host=host;self.stop=threading.Event()
        self.enabled=False;self.last_sent=None;self.error='';self.sent=0
        self.thread=threading.Thread(target=self.run,name='device-observer',daemon=True);self.thread.start()
    def run(self):
        while not self.stop.wait(self.interval):
            if not self.enabled:continue
            try:
                frame,jpeg=current_frame(self.boot,is_current=lambda:self.enabled and not self.stop.is_set())
                c=http.client.HTTPConnection(self.host,8812,timeout=2)
                try:
                    raw=json.dumps({'frame':frame,'jpeg_base64':base64.b64encode(jpeg).decode()}).encode()
                    if not self.enabled or self.stop.is_set():continue
                    c.request('POST','/v1/observations',raw,{'Content-Type':'application/json'})
                    r=c.getresponse();result=r.read(4097)
                    if r.status!=200 or len(result)>4096:raise ValueError('Observation service unavailable')
                    if json.loads(result).get('accepted'):self.sent+=1;self.last_sent=time.monotonic()
                    self.error=''
                finally:c.close()
            except (OSError,ValueError,KeyError,InterruptedError) as exc:self.error=type(exc).__name__
    def public(self):
        return {'enabled':self.enabled,'interval_seconds':self.interval,'sent':self.sent,'error':self.error,
            'last_sent_age_seconds':None if self.last_sent is None else round(time.monotonic()-self.last_sent,1),
            'raw_image_storage':False,'retention_seconds':86400}
    def close(self):self.enabled=False;self.stop.set();self.thread.join(timeout=.1)
