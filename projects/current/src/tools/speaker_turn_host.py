"""One bounded background recorder for exact original conversation turns.

Pending metadata is written immediately. Slow CPU results are polled and merged
independently of TTS completion. Queue limits describe this tracker's job slots,
not the number of PCM copies across transports or an active native CPU call.
"""
from contextlib import nullcontext
import queue,threading,time
from common.asr_wire import context
from common.speaker_turns import record,validate_record

class SpeakerTurnRecorder:
    def __init__(self,store,*,client=None,clock=time.monotonic,poll_seconds=.1,analysis_seconds=14.):
        if client is None:
            from tools import device_client
            client=device_client
        self.store=store;self.client=client;self.clock=clock;self.poll_seconds=poll_seconds;self.analysis_seconds=analysis_seconds
        self.queue=queue.Queue(maxsize=2);self.jobs={};self.lock=threading.RLock();self.closed=threading.Event()
        self.counts={'submitted':0,'complete':0,'unavailable':0,'cancelled':0,'expired':0,'store_errors':0}
        self.thread=threading.Thread(target=self._run,name='bounded-speaker-turn-recorder',daemon=True);self.thread.start()
    def submit(self,meta,pcm,cid,visual=None,*,scope=None,deadline=None):
        """Called only after the original turn exists. Never waits for an embedding."""
        meta=context(meta,pcm);value=record(meta,cid,visual=visual)
        job={'meta':meta,'pcm':pcm,'cid':cid,'visual':value['visual'],'scope':scope or (lambda:nullcontext(None)),
             'stage':'QUEUED','expired':False,
             'cancelled':threading.Event(),'deadline':min(self.clock()+self.analysis_seconds,
                 deadline if deadline is not None else self.clock()+meta['budget_ms']/1000)}
        pcm=None
        with self.lock:
            if self.closed.is_set():return False
            if meta['request_id'] in self.jobs:raise ValueError('Duplicate speaker recorder request')
            # A normal next turn does not cancel descriptive analysis of an
            # earlier played turn. Only explicit cancellation/expiry does.
            capacity=len(self.jobs)<3
            if capacity:self.jobs[meta['request_id']]=job
        try:
            with job['scope']() as profile:pending=self.store.attribution_pending(meta,cid,job['visual'],profile=profile)
            if pending['status']!='PENDING':self._forget(job);return False
            if job['cancelled'].is_set():self._cancel(job);self._forget(job);return False
            if not capacity:
                self._merge(job,record(meta,cid,status='UNAVAILABLE',reason='RECORDER_BACKPRESSURE',visual=job['visual']))
                self._forget(job);return False
            try:self.queue.put_nowait(job)
            except queue.Full:
                self._merge(job,record(meta,cid,status='UNAVAILABLE',reason='RECORDER_BACKPRESSURE',visual=job['visual']))
                self._forget(job);return False
            with self.lock:self.counts['submitted']+=1
            return True
        except Exception:
            with self.lock:self.counts['store_errors']+=1
            self._forget(job);return False
    def _forget(self,job):
        job['pcm']=None
        with self.lock:
            if self.jobs.get(job['meta']['request_id']) is job:self.jobs.pop(job['meta']['request_id'])
    def _cancel(self,job,*,expired=False):
        # Queued tasks lose their owned PCM reference immediately. An active
        # client/native call may still own its local argument until it returns.
        with self.lock:
            job['pcm']=None;job['expired']=bool(expired or job['expired']);expired=job['expired']
        for attempt in range(4):
            try:
                self.store.attribution_cancel(job['meta'],job['cid'],
                  'ANALYSIS_DEADLINE' if expired else 'REQUEST_CANCELLED',expired=expired)
                with self.lock:self.counts['expired' if expired else 'cancelled']+=1
                return
            except Exception:
                if attempt==3:
                    with self.lock:self.counts['store_errors']+=1
                else:self.closed.wait(.03)
    def _expire_waiting(self):
        # The existing poll loop sweeps queued jobs too. No per-turn timer or
        # additional thread is needed to release an expired queued PCM value.
        with self.lock:
            expired=[]
            for job in self.jobs.values():
                if job['stage']=='QUEUED' and not job['expired'] and self.clock()>=job['deadline']:
                    job['expired']=True;job['cancelled'].set();job['pcm']=None;expired.append(job)
        for job in expired:self._cancel(job,expired=True)
    def _merge(self,job,value):
        value=validate_record(value,job['meta'],job['cid'])
        for attempt in range(4):
            if job['cancelled'].is_set() or self.closed.is_set():self._cancel(job);return
            try:
                with job['scope']() as profile:self.store.attribution_merge(job['meta'],job['cid'],value,profile=profile)
                with self.lock:self.counts['complete' if value['status']=='COMPLETE' else 'unavailable']+=1
                return
            except PermissionError:self._cancel(job);return
            except Exception:
                if attempt==3:
                    self._cancel(job,expired=True)
                    with self.lock:self.counts['store_errors']+=1
                else:self.closed.wait(.03)
    def _process(self,job):
        meta,cid=job['meta'],job['cid'];attempted=False;abandoned=False;raw=None
        try:
            self._expire_waiting()
            if job['cancelled'].is_set() or self.closed.is_set():self._cancel(job);return
            if self.clock()>=job['deadline']:self._cancel(job,expired=True);return
            with self.lock:
                if job['cancelled'].is_set() or self.closed.is_set():
                    self._cancel(job);return
                raw=job['pcm'];job['pcm']=None;job['stage']='SUBMITTING'
            try:
                if job['cancelled'].is_set() or self.closed.is_set():self._cancel(job);return
                attempted=True
                value=self.client.submit_speaker_turn(meta,raw,cid,job['visual'],timeout=.2)
                job['stage']='SUBMITTED'
            finally:raw=None
            value=validate_record(value,meta,cid)
            while value['status']=='PENDING':
                self._expire_waiting()
                if job['cancelled'].is_set() or self.closed.is_set():self._cancel(job);return
                if self.clock()>=job['deadline']:self._cancel(job,expired=True);return
                job['cancelled'].wait(min(self.poll_seconds,max(0,job['deadline']-self.clock())))
                if job['cancelled'].is_set():self._cancel(job);return
                value=validate_record(self.client.speaker_turn_result(meta,cid,timeout=.2),meta,cid)
            if self.clock()>=job['deadline']:self._cancel(job,expired=True);return
            self._merge(job,value)
        except Exception:
            abandoned=True
            self._merge(job,record(meta,cid,status='UNAVAILABLE',reason='ATTRIBUTION_SERVICE_UNAVAILABLE',visual=job['visual']))
        finally:
            raw=None
            # A lost HTTP acknowledgement can still mean the hub accepted the
            # job. Cancel by exact owner even when submit did not return.
            if attempted and (abandoned or job['cancelled'].is_set() or self.closed.is_set() or self.clock()>=job['deadline']):
                try:self.client.cancel_speaker_turn(meta,cid,timeout=.2)
                except Exception:pass
            self._forget(job)
    def _run(self):
        while not self.closed.is_set():
            self._expire_waiting()
            try:job=self.queue.get(timeout=.1)
            except queue.Empty:continue
            try:self._process(job)
            finally:self.queue.task_done()
    def cancel(self,meta):
        meta=context(meta)
        with self.lock:
            job=self.jobs.get(meta['request_id'])
            if job is None:return False
            if job['meta']!=meta:raise ValueError('Foreign speaker cancellation')
            job['cancelled'].set();job['pcm']=None
        self._cancel(job);return True
    def close(self):
        self.closed.set()
        with self.lock:
            jobs=list(self.jobs.values())
            for job in jobs:job['cancelled'].set();job['pcm']=None
        for job in jobs:job['cancelled'].set();self._cancel(job)
        self.thread.join(timeout=1.)
        while True:
            try:job=self.queue.get_nowait()
            except queue.Empty:break
            self._forget(job);self.queue.task_done()
    def health(self):
        with self.lock:return dict(version=1,**self.counts,queued=self.queue.qsize(),maximum_queued=2,
          active_jobs=len(self.jobs),maximum_job_slots=3,worker_alive=self.thread.is_alive(),
          pcm_limit_scope='tracker_job_references_only',active_call_released_on_return=True,
          ordinary_conversation_independent=True,pcm_persisted=False,automatic_profile_access=False)
