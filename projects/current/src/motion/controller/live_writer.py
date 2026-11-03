"""Latest-only live reports: no filesystem waits on the motion thread.

The final stopped report remains synchronous after motion is stopped and this
writer has exited. Payloads are immutable JSON text prepared by the caller.
"""
import os
from pathlib import Path
import threading
import time


def close_after_stop(writer,report,pending_error=None):
    try:writer.close()
    except BaseException as error:
        report['live_writer_close_error']=type(error).__name__+': '+str(error)[:180]
        if pending_error is not None:raise pending_error from error
        raise


class LatestReportWriter:
    def __init__(self,path,*,write=None,join_timeout_s=.5):
        self.path=Path(path);self.condition=threading.Condition()
        self.cancel=threading.Event();self.pending=None;self.error=None
        self.submitted=self.written=self.coalesced=0
        self.last_write_ms=self.maximum_write_ms=0.
        self.join_timeout_s=join_timeout_s
        self.write=write or self._write
        self.thread=threading.Thread(target=self._work,name='face-live-report',daemon=True)
        self.thread.start()

    def _write(self,raw,cancel):
        temp=self.path.with_name(self.path.name+'.live-'+str(os.getpid()))
        try:
            with temp.open('x') as stream:stream.write(raw)
            os.chmod(temp,0o600)
            if not cancel.is_set():os.replace(temp,self.path)
        finally:
            if temp.exists():temp.unlink()

    def check(self):
        with self.condition:
            if self.error is not None:raise RuntimeError('Live report writer failed') from self.error

    def submit(self,raw):
        if not isinstance(raw,str) or len(raw.encode('utf-8'))>65536:
            raise ValueError('Bounded immutable live JSON text required')
        with self.condition:
            if self.error is not None:raise RuntimeError('Live report writer failed') from self.error
            if self.cancel.is_set():raise RuntimeError('Live report writer is closed')
            if self.pending is not None:self.coalesced+=1
            self.pending=raw;self.submitted+=1;self.condition.notify()

    def _work(self):
        try:
            while True:
                with self.condition:
                    self.condition.wait_for(lambda:self.cancel.is_set() or self.pending is not None)
                    if self.cancel.is_set():return
                    raw,self.pending=self.pending,None
                began=time.monotonic()
                self.write(raw,self.cancel)
                elapsed=(time.monotonic()-began)*1000
                with self.condition:
                    self.written+=1;self.last_write_ms=round(elapsed,3)
                    self.maximum_write_ms=max(self.maximum_write_ms,self.last_write_ms)
        except BaseException as exc:
            with self.condition:self.error=exc;self.cancel.set();self.pending=None

    def diagnostics(self):
        with self.condition:
            return dict(submitted=self.submitted,written=self.written,coalesced=self.coalesced,
                pending=int(self.pending is not None),last_write_ms=self.last_write_ms,
                maximum_write_ms=self.maximum_write_ms,
                error_type=type(self.error).__name__ if self.error is not None else None,
                scope='one pending immutable live snapshot; final proof is written only after STOP and writer exit')

    def close(self):
        with self.condition:self.cancel.set();self.pending=None;self.condition.notify_all()
        self.thread.join(timeout=self.join_timeout_s)
        if self.thread.is_alive():raise RuntimeError('Live report writer did not exit; stopped proof is not complete')
        self.check()

    def __enter__(self):return self
    def __exit__(self,kind,error,traceback):
        try:self.close()
        except BaseException:
            if error is None:raise

