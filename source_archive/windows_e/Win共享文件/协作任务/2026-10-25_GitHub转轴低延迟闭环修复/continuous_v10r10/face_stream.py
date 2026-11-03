"""Read camera packets off the motor thread; all motor ownership stays in main."""
import http.client,json,queue,threading,time


class FaceStream:
    def __init__(self):
        self.queue=queue.Queue(256);self.closed=threading.Event();self.connection=None
        self.thread=threading.Thread(target=self.work,name='face-input-reader',daemon=True)
        self.thread.start()
    def send(self,kind,value=None):
        try:self.queue.put_nowait((kind,value))
        except queue.Full:self.closed.set()
    def work(self):
        while not self.closed.is_set():
            connection=http.client.HTTPConnection('127.0.0.1',8790,timeout=.25)
            self.connection=connection;began=time.monotonic()
            try:
                connection.request('GET','/v1/motion/face-stream?duration_ms=10000')
                response=connection.getresponse()
                if response.status!=200:raise OSError('Face stream unavailable')
                while not self.closed.is_set():
                    raw=response.readline(8193)
                    if not raw:
                        if time.monotonic()-began<9.5:self.send('disconnect')
                        break
                    if len(raw)>8192 or not raw.endswith(b'\n'):raise ValueError('Invalid face stream packet')
                    self.send('packet',json.loads(raw))
            except (OSError,TimeoutError,http.client.HTTPException):
                self.send('disconnect')
                self.closed.wait(.02)
            except BaseException as error:
                self.send('fault',type(error).__name__);self.closed.set()
            finally:connection.close()
    def drain(self):
        values=[]
        while True:
            try:values.append(self.queue.get_nowait())
            except queue.Empty:break
        if self.closed.is_set() and not any(k=='fault' for k,_ in values):values.append(('fault','STREAM_QUEUE_OR_READER_STOPPED'))
        return values
    def close(self):
        self.closed.set()
        if self.connection is not None:self.connection.close()
        self.thread.join(timeout=.5)
